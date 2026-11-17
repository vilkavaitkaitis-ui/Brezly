"""
Brėžly - tavo braižymo draugas (bandomoji versija). Veikia su AutoCAD.

Mokymosi programa: tu braižai AutoCAD'e pats, o Brėžly veda žingsnis po žingsnio,
tikrina tavo brėžinį, duoda užuominas ir XP taškus.

Paleidimas: BREZLY.bat arba nuoroda "Brėžly".
Progresas saugomas: Dokumentai\\Brezly\\progresas.json
"""

import contextlib
import datetime
import hashlib
import hmac
import io
import json
import os
import platform
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
import zipfile

PROGRAMOS_APLANKAS = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
os.chdir(PROGRAMOS_APLANKAS)

import serveris as P            # noqa: E402  (serveris, langas, ryšys su AutoCAD)
import pamokos                  # noqa: E402
import praktika                 # noqa: E402



def _versija():
    """versija.txt įrašo GitHub surinkimas pagal žymą (pvz. v0.9 -> 0.9). Be jo - numatytoji."""
    try:
        with open(os.path.join(PROGRAMOS_APLANKAS, "versija.txt"), encoding="utf-8") as f:
            v = f.read().strip().lstrip("vV")
        if v and v[0].isdigit():
            return v if " " in v else v + " beta"
    except OSError:
        pass
    return "0.9 beta"


VERSIJA_BREZLY = _versija()
LANGO_PAVADINIMAS = "Brėžly"
# Atnaujinimų aprašas (JSON: {"versija","zip","setup","pastabos"}). Tuščias - tikrinimas išjungtas.
def _atnaujinimu_url():
    if os.environ.get("BREZLY_ATNAUJINIMAI"):
        return os.environ["BREZLY_ATNAUJINIMAI"]
    try:        # failas šalia programos: viena eilutė su adresu (pvz. GitHub atnaujinimai.json)
        with open(os.path.join(PROGRAMOS_APLANKAS, "atnaujinimai_url.txt"), encoding="utf-8") as f:
            u = f.read().strip()
        return u if u.startswith("https://") else ""
    except OSError:
        return ""


ATNAUJINIMU_URL = _atnaujinimu_url()
WINDOWS = sys.platform == "win32"


# ================================================================== duomenų aplankas
def dokumentu_aplankas():
    """Tikrasis „Dokumentai“ aplankas (ir kai jis perkeltas į OneDrive)."""
    if os.environ.get("BREZLY_DUOMENYS"):
        return os.environ["BREZLY_DUOMENYS"]
    if WINDOWS:
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(260)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
                return os.path.join(buf.value, "Brezly")
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Documents", "Brezly")


DUOM = dokumentu_aplankas()
PROGRESAS = os.path.join(DUOM, "progresas.json")
ZURNALAS = os.path.join(DUOM, "brezly.log")


def _aplankas():
    os.makedirs(DUOM, exist_ok=True)
    return DUOM


def rasyti_zurnala(tekstas):
    try:
        _aplankas()
        if os.path.exists(ZURNALAS) and os.path.getsize(ZURNALAS) > 400_000:
            os.replace(ZURNALAS, ZURNALAS + ".1")
        with open(ZURNALAS, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {tekstas}\n")
    except Exception:
        pass


def irasyti_atomiskai(kelias, tekstas):
    tmp = kelias + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(tekstas)
    if os.path.exists(kelias):
        shutil.copyfile(kelias, kelias + ".bak")
    os.replace(tmp, kelias)


# ================================================================== progresas faile
def progresas(duom):
    """GET - grąžina išsaugotą progresą; POST {S, nustatymai} - išsaugo."""
    if duom.get("S") is None and duom.get("nustatymai") is None:
        for kelias in (PROGRESAS, PROGRESAS + ".bak"):
            try:
                with open(kelias, encoding="utf-8") as f:
                    d = json.load(f)
                return {"ok": True, "yra": True, "S": d.get("S"), "nustatymai": d.get("nustatymai", {}),
                        "kelias": PROGRESAS}
            except FileNotFoundError:
                continue
            except Exception:
                rasyti_zurnala("Sugadintas progreso failas: " + kelias)
                continue
        return {"ok": True, "yra": False, "kelias": PROGRESAS}
    _aplankas()
    senas = {}
    try:
        with open(PROGRESAS, encoding="utf-8") as f:
            senas = json.load(f)
    except Exception:
        pass
    naujas = {"versija": VERSIJA_BREZLY, "irasyta": datetime.datetime.now().isoformat(timespec="seconds"),
              "S": duom.get("S", senas.get("S")),
              "nustatymai": {**senas.get("nustatymai", {}), **(duom.get("nustatymai") or {})}}
    irasyti_atomiskai(PROGRESAS, json.dumps(naujas, ensure_ascii=False, indent=1))
    return {"ok": True}


# ================================================================== testavimo įrankiai (slaptažodis)
TESTAVIMO_FAILAS = os.path.join(PROGRAMOS_APLANKAS, "testavimas.json")
_TEST = {"zetonai": {}, "klaidos": 0, "uzrakinta_iki": 0.0}
ZETONO_GALIOJIMAS = 30 * 60      # s be veiklos - kūrėjo režimas užsirakina


def _zetonas_galioja(z, atnaujinti=True):
    t = _TEST["zetonai"].get(z or "")
    if t is None:
        return False
    if time.time() - t > ZETONO_GALIOJIMAS or _testavimo_nustatymai() is None:
        _TEST["zetonai"].pop(z, None)
        return False
    if atnaujinti:
        _TEST["zetonai"][z] = time.time()
    return True


def _testavimo_nustatymai():
    try:
        with open(TESTAVIMO_FAILAS, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("maisa") and d.get("druska"):
            if d.get("kompiuteris") and d["kompiuteris"].lower() != platform.node().lower():
                return None             # kūrėjo režimas leidžiamas tik tam kompiuteriui
            return d
    except Exception:
        pass
    return None


def maisa(slaptazodis, druska, kartu=200_000):
    return hashlib.pbkdf2_hmac("sha256", slaptazodis.encode("utf-8"), bytes.fromhex(druska), kartu).hex()


def nustatyti_slaptazodi(slaptazodis, tik_siame=False):
    druska = secrets.token_hex(16)
    d = {"druska": druska, "kartu": 200_000, "maisa": maisa(slaptazodis, druska)}
    if tik_siame:
        d["kompiuteris"] = platform.node()
    with open(TESTAVIMO_FAILAS, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)


def testas_atrakinti(duom):
    nust = _testavimo_nustatymai()
    if not nust:
        return {"ok": False, "klaida": "Testavimo įrankiai šioje versijoje išjungti."}
    liko = _TEST["uzrakinta_iki"] - time.time()
    if liko > 0:
        return {"ok": False, "klaida": f"Per daug bandymų. Palauk {int(liko) + 1} s."}
    tikras = maisa(str(duom.get("slaptazodis", "")), nust["druska"], int(nust.get("kartu", 200_000)))
    if not hmac.compare_digest(tikras, nust["maisa"]):
        _TEST["klaidos"] += 1
        if _TEST["klaidos"] >= 5:
            _TEST["uzrakinta_iki"] = time.time() + 60
            _TEST["klaidos"] = 0
        time.sleep(0.4)
        return {"ok": False, "klaida": "Neteisingas slaptažodis."}
    _TEST["klaidos"] = 0
    zetonas = secrets.token_hex(16)
    _TEST["zetonai"][zetonas] = time.time()
    return {"ok": True, "zetonas": zetonas}


def testas_patikrinti(duom):
    return {"ok": True, "galioja": _zetonas_galioja(duom.get("zetonas"))}


def testas_uzrakinti(duom):
    _TEST["zetonai"].pop(duom.get("zetonas", ""), None)
    return {"ok": True}


# ================================================================== AutoCAD aplinka
def _registras(kelias):
    """Grąžina registro rakto poraktų sąrašą (HKLM ir HKCU)."""
    if not WINDOWS:
        return []
    import winreg
    rez = []
    for sakn in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(sakn, kelias) as k:
                i = 0
                while True:
                    try:
                        rez.append(winreg.EnumKey(k, i)); i += 1
                    except OSError:
                        break
        except OSError:
            continue
    return rez


def _procesai():
    if not WINDOWS:
        return ""
    try:
        return subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=5,
                              creationflags=0x08000000).stdout.lower()
    except Exception:
        return ""


_APLINKA = {"laikas": 0, "duom": None}


def aplinka(_=None):
    """Kas įdiegta ir kas veikia: pilnas AutoCAD, AutoCAD LT."""
    if _APLINKA["duom"] and time.time() - _APLINKA["laikas"] < 30:
        return _APLINKA["duom"]
    pilnas = [v for v in _registras(r"SOFTWARE\Autodesk\AutoCAD") if v.startswith("R")]
    lt = [v for v in _registras(r"SOFTWARE\Autodesk\AutoCAD LT") if v.startswith("R")]
    pr = _procesai()
    d = {"ok": True, "windows": WINDOWS, "pilnas_idiegtas": bool(pilnas), "lt_idiegtas": bool(lt),
         "pilnas_veikia": '"acad.exe"' in pr, "lt_veikia": '"acadlt.exe"' in pr}
    _APLINKA.update(laikas=time.time(), duom=d)
    return d


def busena(duom):
    if KUREJAS["imitacija"]:
        return {"ok": True, "prisijungta": True, "brezinys": "Imitacija.dwg", "laisvas": True, "imitacija": KUREJAS["imitacija"]}
    r = P.busena(duom)
    if r.get("prisijungta"):
        try:
            b = P.BUSENA["darbas"].b
            r["kalba"] = str(P.A.kartoti(lambda: b.doc.GetVariable("LOCALE"), bandymu=2))
            r["laisvas"] = bool(P.A.kartoti(lambda: b.acad.GetAcadState().IsQuiescent, bandymu=2))
        except Exception:
            pass
        return r
    a = aplinka()
    r.update({k: a[k] for k in ("pilnas_idiegtas", "lt_idiegtas", "pilnas_veikia", "lt_veikia", "windows")})
    r["paleidziamas"] = _PALEIDIMAS["vyksta"]
    return r


_PALEIDIMAS = {"vyksta": False, "klaida": ""}


def paleisti_autocad(_):
    """Paleidžia AutoCAD atskiroje gijoje (užtrunka iki minutės), kad langas neužstrigtų."""
    if _PALEIDIMAS["vyksta"]:
        return {"ok": True, "vyksta": True}
    a = aplinka()
    if not a["pilnas_idiegtas"] and a["lt_idiegtas"]:
        return {"ok": False, "lt": True, "klaida": "Įdiegtas tik AutoCAD LT - jo programos valdyti negali."}

    def darbas():
        _PALEIDIMAS.update(vyksta=True, klaida="")
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    P.A.prisijungti()
            finally:
                pythoncom.CoUninitialize()
        except Exception as e:
            _PALEIDIMAS["klaida"] = str(e)
            rasyti_zurnala("AutoCAD paleidimas: " + traceback.format_exc())
        finally:
            _PALEIDIMAS["vyksta"] = False
    threading.Thread(target=darbas, daemon=True).start()
    return {"ok": True, "vyksta": True}


# ================================================================== pamokos
def info(_):
    return {"ok": True, "versija": VERSIJA_BREZLY, "testavimas": _testavimo_nustatymai() is not None,
            "funkcijos": funkcijos(),
            "langas": dict(P.LANGAS), "klavisai": KLAVISAI, "ekranas": P.darbo_sritis(),
            "atnaujinimai": bool(ATNAUJINIMU_URL), "duomenys": DUOM, "windows": WINDOWS} | pamokos.viesai()


def _zingsnis(duom):
    pam = pamokos.pamoka(duom.get("pamoka"))
    nr = int(duom.get("zingsnis", 0))
    return pam["zingsniai"][nr]


def tikrinti(duom):
    z = _zingsnis(duom)
    if KUREJAS["imitacija"]:
        return _imituotas_tikrinimas()
    if z["tikrinti"] is None:
        return {"ok": True, "teisingai": True, "pastabos": []}
    with contextlib.redirect_stdout(io.StringIO()):
        b = P.braizytojas()
    if duom.get("tyliai"):          # automatinis tikrinimas: netrukdom, kai AutoCAD'e vyksta komanda
        try:
            if not P.A.kartoti(lambda: b.acad.GetAcadState().IsQuiescent, bandymu=2):
                return {"ok": True, "laukia": True}
        except AttributeError:
            pass                    # senas AutoCAD be GetAcadState - tikrinam vis tiek
        except Exception:
            return {"ok": True, "laukia": True}     # AutoCAD užimtas (vykdoma komanda)
    try:
        pastabos = z["tikrinti"](b)
    except Exception as e:
        if duom.get("tyliai"):
            return {"ok": True, "laukia": True}
        pastabos = [f"Nepavyko perskaityti brėžinio: {e}. Ar AutoCAD'e nevykdoma kita komanda? Spausk Esc."]
    return {"ok": True, "teisingai": not pastabos, "pastabos": pastabos}


def parodyti(duom):
    z = _zingsnis(duom)
    if KUREJAS["imitacija"]:
        return {"ok": True, "log": "(imitacija - AutoCAD nenaudojamas)"}
    if z["demo"] is None:
        return {"ok": False, "klaida": "Šiam žingsniui demonstracijos nėra - padaryk pagal aprašą."}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        b = P.braizytojas()
        z["demo"](b)
        b.palaukti()
        try:
            P.A.kartoti(b.acad.ZoomExtents)
        except Exception:
            pass
    return {"ok": True, "log": buf.getvalue()}


def naujas_brezinys(_):
    if KUREJAS["imitacija"]:
        return {"ok": True}
    with contextlib.redirect_stdout(io.StringIO()):
        b = P.braizytojas()
        P.A.naujas_brezinys(b.acad, "acadiso.dwt")
        b.palaukti()
        b.kunas = None
    return {"ok": True}


# ================================================================== langas: kompaktiškas / įprastas
def _rasti_langa():
    import win32gui
    rasti = []

    def f(h, _):
        if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h).startswith(LANGO_PAVADINIMAS):
            rasti.append(h)
    win32gui.EnumWindows(f, None)
    return rasti[0] if rasti else None


def _saugiai(f):
    try:
        f()
    except Exception:
        rasyti_zurnala("Spartieji klavišai: " + traceback.format_exc())


_ACAD_ISDESTYTAS = {"h": None, "buvo_max": False}


def _rasti_acad():
    """AutoCAD pagrindinis langas pagal pavadinimą („Autodesk AutoCAD 2025 - [Drawing1.dwg]“)."""
    import win32gui
    rasti = []

    def f(h, _):
        if win32gui.IsWindowVisible(h) and win32gui.GetParent(h) == 0:
            t = win32gui.GetWindowText(h)
            if t.startswith("Autodesk AutoCAD") or (t.startswith("AutoCAD") and " - [" in t):
                rasti.append(h)
    win32gui.EnumWindows(f, None)
    return rasti[0] if rasti else None


def _grazinti_acad():
    """Jei AutoCAD langą buvome sumažinę - grąžinam kaip buvo (išdidintą)."""
    import win32con
    import win32gui
    h = _ACAD_ISDESTYTAS["h"]
    if h and win32gui.IsWindow(h) and _ACAD_ISDESTYTAS["buvo_max"]:
        win32gui.ShowWindow(h, win32con.SW_MAXIMIZE)
    _ACAD_ISDESTYTAS.update(h=None, buvo_max=False)


def langas(duom):
    """{rezimas: 'kompaktiskas'|'mini'|'iprastas', acad: bool}
    kompaktiskas - Brėžly siauras dešinėje, AutoCAD užima likusią vietą kairėje (niekas neuždengta);
    mini - maža plaukiojanti kortelė apačioje dešinėje; iprastas - didelis langas pagal ekraną."""
    if not WINDOWS:
        return {"ok": False, "klaida": "Veikia tik Windows."}
    import win32api
    import win32con
    import win32gui
    h = _rasti_langa()
    if not h:
        return {"ok": False, "klaida": "Neradau Brėžly lango."}
    mon = win32api.GetMonitorInfo(win32api.MonitorFromWindow(h, win32con.MONITOR_DEFAULTTONEAREST))
    x0, y0, x1, y1 = mon["Work"]
    W, H = x1 - x0, y1 - y0
    if win32gui.IsIconic(h) or win32gui.GetWindowPlacement(h)[1] == win32con.SW_SHOWMAXIMIZED:
        win32gui.ShowWindow(h, win32con.SW_RESTORE)
    rez = duom.get("rezimas")
    acad_isdestytas = False
    if rez == "kompaktiskas":
        plotis = max(360, min(460, round(W * 0.3)))
        win32gui.SetWindowPos(h, win32con.HWND_TOPMOST, x1 - plotis, y0, plotis, H, win32con.SWP_SHOWWINDOW)
        if duom.get("acad", True):
            a = _rasti_acad()
            if a:
                if _ACAD_ISDESTYTAS["h"] != a:
                    _ACAD_ISDESTYTAS.update(h=a, buvo_max=win32gui.GetWindowPlacement(a)[1] == win32con.SW_SHOWMAXIMIZED)
                if win32gui.IsIconic(a) or win32gui.GetWindowPlacement(a)[1] == win32con.SW_SHOWMAXIMIZED:
                    win32gui.ShowWindow(a, win32con.SW_RESTORE)
                win32gui.SetWindowPos(a, 0, x0, y0, W - plotis, H, win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)
                acad_isdestytas = True
    elif rez == "mini":
        _grazinti_acad()
        w, hh = 360, max(250, min(330, H // 2))
        win32gui.SetWindowPos(h, win32con.HWND_TOPMOST, x1 - w - 12, y1 - hh - 12, w, hh, win32con.SWP_SHOWWINDOW)
    else:
        _grazinti_acad()
        w, hh = min(1280, int(W * 0.92)), min(860, int(H * 0.94))
        win32gui.SetWindowPos(h, win32con.HWND_NOTOPMOST, x0 + (W - w) // 2, y0 + (H - hh) // 2,
                              w, hh, win32con.SWP_SHOWWINDOW)
    return {"ok": True, "acad": acad_isdestytas}


# ================================================================== spartieji klavišai (veikia ir kai aktyvus AutoCAD)
IVYKIAI = {"n": 0, "sar": []}
KLAVISAI = {"veikia": [], "nepavyko": []}
_KLAVISU_SARASAS = [(1, "T", "tikrinti", "Ctrl+Alt+T"), (2, "M", "mini", "Ctrl+Alt+M"), (3, "B", "rodyti", "Ctrl+Alt+B")]


def _ivykis(veiksmas):
    IVYKIAI["n"] += 1
    IVYKIAI["sar"] = (IVYKIAI["sar"] + [{"id": IVYKIAI["n"], "veiksmas": veiksmas}])[-20:]


def _rodyti_langa():
    try:
        import win32con
        import win32gui
        h = _rasti_langa()
        if h:
            if win32gui.IsIconic(h):
                win32gui.ShowWindow(h, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(h)
    except Exception:
        pass


def klavisu_gija():
    """RegisterHotKey + pranešimų ciklas atskiroje gijoje. Užimtas derinys - tiesiog praleidžiamas."""
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    for nr, raide, _, pav in _KLAVISU_SARASAS:
        if u.RegisterHotKey(None, nr, 0x0001 | 0x0002 | 0x4000, ord(raide)):     # Alt | Ctrl | NOREPEAT
            KLAVISAI["veikia"].append(pav)
        else:
            KLAVISAI["nepavyko"].append(pav)
    msg = wintypes.MSG()
    while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == 0x0312:                                                   # WM_HOTKEY
            veiksmas = {nr: v for nr, _, v, _ in _KLAVISU_SARASAS}.get(msg.wParam)
            if veiksmas == "rodyti":
                _rodyti_langa()
            elif veiksmas:
                _ivykis(veiksmas)


def ivykiai(duom):
    nuo = int(duom.get("nuo", 0))
    return {"ok": True, "n": IVYKIAI["n"], "ivykiai": [e for e in IVYKIAI["sar"] if e["id"] > nuo]}


# ================================================================== pranešimas apie klaidą
def ataskaita(duom):
    """Sukuria ZIP su informacija apie klaidą Dokumentai\\Brezly\\ataskaitos ir parodo jį."""
    ap = os.path.join(_aplankas(), "ataskaitos")
    os.makedirs(ap, exist_ok=True)
    kelias = os.path.join(ap, f"Brezly_ataskaita_{datetime.datetime.now():%Y%m%d_%H%M%S}.zip")
    sist = {"brezly": VERSIJA_BREZLY, "python": sys.version, "os": platform.platform(),
            "laikas": datetime.datetime.now().isoformat(timespec="seconds"), "aplinka": aplinka()}
    try:
        b = P.BUSENA["darbas"].b
        if b is not None:
            sist["autocad"] = str(P.A.kartoti(lambda: b.acad.Version, bandymu=2))
            sist["kalba"] = str(P.A.kartoti(lambda: b.doc.GetVariable("LOCALE"), bandymu=2))
    except Exception:
        pass
    with zipfile.ZipFile(kelias, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("aprasymas.txt", str(duom.get("aprasymas", "")).strip() or "(neaprašyta)")
        z.writestr("sistema.json", json.dumps(sist, ensure_ascii=False, indent=1))
        z.writestr("rodinys.json", json.dumps(duom.get("busena", {}), ensure_ascii=False, indent=1))
        for f in (ZURNALAS, ZURNALAS + ".1", PROGRESAS, os.path.join(PROGRAMOS_APLANKAS, "klaida.txt")):
            if os.path.exists(f):
                z.write(f, os.path.basename(f))
    if WINDOWS:
        try:
            subprocess.Popen(["explorer", "/select,", kelias])
        except Exception:
            pass
    return {"ok": True, "kelias": kelias}


def atidaryti_duomenis(_):
    _aplankas()
    if WINDOWS:
        os.startfile(DUOM)
    return {"ok": True, "kelias": DUOM}


# ================================================================== atnaujinimai
def _versija_sk(v):
    return tuple(int(x) for x in "".join(c if c.isdigit() or c == "." else " " for c in v).split()[0].split("."))


def _aprasas():
    """atnaujinimai.json iš GitHub Releases: {versija, setup, setup_sha256, zip, zip_sha256, pastabos}."""
    req = urllib.request.Request(ATNAUJINIMU_URL, headers={"User-Agent": "Brezly/" + VERSIJA_BREZLY, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def _atsisiusti(url, kelias, sha256=""):
    """Atsisiunčia failą ir patikrina SHA-256 (jei pateiktas) - sugadintas ar pakeistas failas nediegiamas."""
    req = urllib.request.Request(url, headers={"User-Agent": "Brezly/" + VERSIJA_BREZLY})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=30) as r, open(kelias, "wb") as f:
        while True:
            b = r.read(1 << 16)
            if not b:
                break
            h.update(b); f.write(b)
    if sha256 and h.hexdigest().lower() != sha256.lower():
        os.remove(kelias)
        raise ValueError("Atsisiųstas failas sugadintas (nesutampa kontrolinė suma). Bandyk dar kartą vėliau.")


def atnaujinimai(_):
    if not ATNAUJINIMU_URL:
        return {"ok": True, "yra": False}
    try:
        d = _aprasas()
    except Exception as e:
        return {"ok": False, "klaida": f"Nepavyko patikrinti atnaujinimų ({e.__class__.__name__}). Ar yra internetas?"}
    yra = _versija_sk(d["versija"]) > _versija_sk(VERSIJA_BREZLY)
    return {"ok": True, "yra": yra, "versija": d["versija"], "pastabos": d.get("pastabos", ""), "dabartine": VERSIJA_BREZLY}


def atnaujinti(_):
    """Atsisiunčia ir įdiegia naują versiją. .exe versijai - diegimo programa tyliai, kitaip - ZIP failai."""
    d = _aprasas()
    if getattr(sys, "frozen", False):
        if not d.get("setup"):
            return {"ok": False, "klaida": "Naujoje versijoje nėra diegimo programos."}
        kelias = os.path.join(tempfile.gettempdir(), "Brezly_Setup_naujas.exe")
        _atsisiusti(d["setup"], kelias, d.get("setup_sha256", ""))
        # /SILENT - rodoma tik eigos juosta; po diegimo Brėžly pasileidžia pats ([Run] skipifnotsilent)
        subprocess.Popen([kelias, "/SP-", "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"])
        P.BUSENA["veikia"] = False
        return {"ok": True, "budas": "setup"}
    if not d.get("zip"):
        return {"ok": False, "klaida": "Šiai versijai reikia įdiegti iš naujo - atsisiųsk Brezly_Setup.exe."}
    kelias = os.path.join(tempfile.gettempdir(), "brezly_atnaujinimas.zip")
    _atsisiusti(d["zip"], kelias, d.get("zip_sha256", ""))
    with zipfile.ZipFile(kelias) as z:
        for n in z.namelist():                     # plokšti failai + praktika/<failas> (be kitų katalogų)
            gilus = n.startswith("praktika/") and n.count("/") == 1 and ".." not in n and len(n) > 9
            if (("/" in n and not gilus) or "\\" in n or n.startswith(".") or n in ("testavimas.json",)):
                continue
            if gilus:
                os.makedirs(os.path.join(PROGRAMOS_APLANKAS, "praktika"), exist_ok=True)
            with z.open(n) as src, open(os.path.join(PROGRAMOS_APLANKAS, n + ".naujas"), "wb") as dst:
                shutil.copyfileobj(src, dst)
        for n in z.namelist():
            nauj = os.path.join(PROGRAMOS_APLANKAS, n + ".naujas")
            if os.path.exists(nauj):
                os.replace(nauj, os.path.join(PROGRAMOS_APLANKAS, n))
    os.remove(kelias)
    return {"ok": True, "budas": "zip", "perkrauti": True}


def perkrauti(_):
    """Paleidžia Brėžly iš naujo (po atnaujinimo)."""
    exe = sys.executable.replace("python.exe", "pythonw.exe")
    args = [exe] if getattr(sys, "frozen", False) else [exe, os.path.abspath(__file__)]
    env = dict(os.environ, BREZLY_BE_LANGO="1")     # langas jau atidarytas - jis tik persikraus
    threading.Timer(1.5, lambda: subprocess.Popen(args, cwd=PROGRAMOS_APLANKAS, env=env)).start()
    P.BUSENA["veikia"] = False
    return {"ok": True}


# ================================================================== praktikos užduotys (0.8)
def praktika_atidaryti(duom):
    """kas: "ruosinys" (tuščias lapas braižymui) arba "pavyzdys" (atsakymas)."""
    uid = praktika._uzd(duom)
    kelias = praktika.paruosti(uid, duom.get("kas", "ruosinys"), DUOM)
    if KUREJAS["imitacija"]:
        return {"ok": True, "failas": os.path.basename(kelias)}
    with contextlib.redirect_stdout(io.StringIO()):
        b = P.braizytojas()
        P.A.kartoti(lambda: b.acad.Documents.Open(kelias))
        b.kunas = None
        try:
            P.A.kartoti(b.acad.ZoomExtents)
        except Exception:
            pass
    return {"ok": True, "failas": os.path.basename(kelias)}


def praktika_pdf(duom):
    uid = praktika._uzd(duom)
    praktika.atidaryti_faila(praktika.failas(uid + ".pdf"))
    return {"ok": True}


def praktika_aplankas(_):
    praktika.atidaryti_faila(praktika.darbo_aplankas(DUOM))
    return {"ok": True}


def praktika_tikrinti(duom):
    uid = praktika._uzd(duom)
    if KUREJAS["imitacija"]:
        return _imituotas_tikrinimas()
    with contextlib.redirect_stdout(io.StringIO()):
        b = P.braizytojas()
    try:
        pastabos = praktika.tikrinti(uid, b, P.A.kartoti)
    except Exception as e:
        pastabos = [f"Nepavyko perskaityti brėžinio: {e}. Ar AutoCAD'e nevykdoma kita komanda? Spausk Esc."]
    return {"ok": True, "teisingai": not pastabos, "pastabos": pastabos}


# ================================================================== kūrėjo įrankiai (tik su slaptažodžiu)
KUREJAS = {"imitacija": None}       # None | "gerai" | "blogai" - tikrinimas be AutoCAD
FUNKCIJU_FAILAS = os.path.join(PROGRAMOS_APLANKAS, "funkcijos.json")
FUNKCIJOS = ("praktika", "spinta", "lygiai", "kartoti", "profilis")


def funkcijos():
    d = {k: True for k in FUNKCIJOS}
    try:
        with open(FUNKCIJU_FAILAS, encoding="utf-8") as f:
            d.update({k: bool(v) for k, v in json.load(f).items() if k in FUNKCIJOS})
    except Exception:
        pass
    return d


def _imituotas_tikrinimas():
    if KUREJAS["imitacija"] == "gerai":
        return {"ok": True, "teisingai": True, "pastabos": []}
    return {"ok": True, "teisingai": False, "pastabos": ["(Imitacija) Taip atrodo klaidos pranešimas: trūksta apskritimo ø40.",
                                                         "Patarimas: CIRCLE prašo spindulio, ne skersmens."]}


def _kurejui(f):
    """Leidžia kviesti tik su galiojančiu kūrėjo žetonu."""
    def apvalkas(duom):
        if not _zetonas_galioja(duom.get("zetonas")):
            return {"ok": False, "klaida": "Kūrėjo režimas užrakintas - atrakink iš naujo.", "uzrakinta": True}
        return f(duom)
    apvalkas.__name__ = f.__name__
    return apvalkas


def k_busena(duom):
    nust = _testavimo_nustatymai() or {}
    return {"ok": True, "imitacija": KUREJAS["imitacija"], "funkcijos": funkcijos(),
            "kompiuteris": platform.node(), "susietas": nust.get("kompiuteris", ""),
            "python": sys.version.split()[0], "aplankas": PROGRAMOS_APLANKAS, "duomenys": DUOM,
            "galiojimas_min": ZETONO_GALIOJIMAS // 60}


def k_imitacija(duom):
    v = duom.get("rezimas")
    KUREJAS["imitacija"] = v if v in ("gerai", "blogai") else None
    return {"ok": True, "imitacija": KUREJAS["imitacija"]}


def k_funkcijos(duom):
    d = funkcijos()
    d.update({k: bool(v) for k, v in (duom.get("funkcijos") or {}).items() if k in FUNKCIJOS})
    if all(d.values()):
        if os.path.exists(FUNKCIJU_FAILAS):
            os.remove(FUNKCIJU_FAILAS)          # viskas įjungta - failo nereikia
    else:
        irasyti_atomiskai(FUNKCIJU_FAILAS, json.dumps(d, indent=1))
    return {"ok": True, "funkcijos": d}


def k_zurnalas(_):
    eil = []
    for f in (ZURNALAS + ".1", ZURNALAS):
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                eil += fh.read().splitlines()
        except OSError:
            pass
    klaida = ""
    try:
        with open(os.path.join(PROGRAMOS_APLANKAS, "klaida.txt"), encoding="utf-8", errors="replace") as fh:
            klaida = fh.read()[-4000:]
    except OSError:
        pass
    return {"ok": True, "eilutes": eil[-300:], "klaida": klaida, "kelias": ZURNALAS}


def k_acad(duom):
    """Ką mato tikrinimas: AutoCAD informacija ir brėžinio turinys."""
    if KUREJAS["imitacija"]:
        return {"ok": False, "klaida": "Įjungta imitacija - išjunk ją, kad matytum tikrą AutoCAD."}
    with contextlib.redirect_stdout(io.StringIO()):
        b = P.braizytojas()
    k = P.A.kartoti
    r = {"ok": True}
    for raktas, f in (("versija", lambda: b.acad.Version), ("failas", lambda: b.acad.ActiveDocument.FullName),
                      ("kalba", lambda: b.doc.GetVariable("LOCALE")), ("vienetai", lambda: b.doc.GetVariable("INSUNITS")),
                      ("sluoksnis", lambda: b.doc.ActiveLayer.Name)):
        try:
            r[raktas] = str(k(f, bandymu=2))
        except Exception as e:
            r[raktas] = f"? ({e.__class__.__name__})"
    a = praktika.analizuoti(b, k)
    r.update(tipai=a["tipai"], skersmenys=sorted(round(x * 2, 3) for x in a["spinduliai"]),
             turiai=[round(v, 1) for v in a["turiai"]])
    try:
        r["kunai"] = [{"min": [round(x, 2) for x in q["min"]], "max": [round(x, 2) for x in q["max"]],
                       "turis": round(q["turis"] or 0, 1), "sluoksnis": q["sluoksnis"]} for q in pamokos.kunai(b)][:30]
    except Exception:
        r["kunai"] = []
    try:
        sl = b.doc.Layers
        r["sluoksniai"] = [k(lambda i=i: sl.Item(i).Name) for i in range(k(lambda: sl.Count))]
    except Exception:
        r["sluoksniai"] = []
    if duom.get("pamoka") is not None and duom.get("zingsnis") is not None:
        try:
            z = _zingsnis(duom)
            r["pamokos_pastabos"] = z["tikrinti"](b) if z["tikrinti"] else ["(šis žingsnis netikrinamas)"]
        except Exception as e:
            r["pamokos_pastabos"] = [f"Klaida: {e}"]
    if duom.get("praktika") in praktika.UZDUOTYS:
        r["praktikos_pastabos"] = praktika.tikrinti(duom["praktika"], b, k)
    return r


def k_slaptazodis(duom):
    nust = _testavimo_nustatymai()
    if not nust or not hmac.compare_digest(maisa(str(duom.get("senas", "")), nust["druska"], int(nust.get("kartu", 200_000))), nust["maisa"]):
        time.sleep(0.4)
        return {"ok": False, "klaida": "Senas slaptažodis neteisingas."}
    naujas = str(duom.get("naujas", ""))
    if len(naujas) < 8:
        return {"ok": False, "klaida": "Naujas slaptažodis per trumpas - bent 8 simboliai."}
    nustatyti_slaptazodi(naujas, bool(duom.get("tik_siame")))
    return {"ok": True, "kompiuteris": platform.node() if duom.get("tik_siame") else ""}


def k_nuotrauka(_):
    """Brėžly lango ekrano nuotrauka -> Dokumentai\\Brezly\\Nuotraukos\\*.png"""
    if not WINDOWS:
        return {"ok": False, "klaida": "Veikia tik Windows."}
    import ctypes
    import win32gui
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
    h = _rasti_langa()
    if not h:
        return {"ok": False, "klaida": "Neradau Brėžly lango."}
    x0, y0, x1, y1 = win32gui.GetWindowRect(h)
    ap = os.path.join(_aplankas(), "Nuotraukos")
    os.makedirs(ap, exist_ok=True)
    kelias = os.path.join(ap, f"Brezly_{datetime.datetime.now():%Y%m%d_%H%M%S}.png")
    try:
        from PIL import ImageGrab
        ImageGrab.grab(bbox=(x0, y0, x1, y1), all_screens=True).save(kelias)
    except ImportError:
        ps = ("Add-Type -AssemblyName System.Drawing;"
              "Add-Type -Namespace W -Name U -MemberDefinition '[DllImport(\"user32.dll\")] public static extern bool SetProcessDPIAware();';"
              "[W.U]::SetProcessDPIAware() | Out-Null;"
              f"$b=New-Object Drawing.Bitmap {x1 - x0},{y1 - y0};$g=[Drawing.Graphics]::FromImage($b);"
              f"$g.CopyFromScreen({x0},{y0},0,0,$b.Size);$b.Save('{kelias}',[Drawing.Imaging.ImageFormat]::Png)")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=20,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if not os.path.exists(kelias):
        return {"ok": False, "klaida": "Nepavyko padaryti nuotraukos."}
    try:
        subprocess.Popen(["explorer", "/select,", kelias])
    except Exception:
        pass
    return {"ok": True, "kelias": kelias}


# ================================================================== serveris
def _su_zurnalu(f):
    def apvalkas(duom):
        try:
            return f(duom)
        except Exception:
            rasyti_zurnala(f"{f.__name__}: {traceback.format_exc()}")
            raise
    apvalkas.__name__ = f.__name__
    return apvalkas


class BrezlyTvarkykle(P.Tvarkykle):
    HTML = "brezly.html"
    IKONA = "brezly.ico"

    def do_GET(self):
        if self.path.startswith("/praktika/"):          # praktikos brėžinių peržiūra (SVG/PDF)
            kelias = praktika.failas(self.path.split("?")[0][len("/praktika/"):])
            if not kelias:
                return self._siusti(404, b"{}")
            tipas = {".svg": "image/svg+xml", ".pdf": "application/pdf"}.get(os.path.splitext(kelias)[1].lower(), "application/octet-stream")
            with open(kelias, "rb") as f:
                return self._siusti(200, f.read(), tipas)
        return super().do_GET()

    VEIKSMAI = {k: _su_zurnalu(f) for k, f in {
        "/api/info": info, "/api/tikrinti": tikrinti, "/api/parodyti": parodyti,
        "/api/naujas": naujas_brezinys, "/api/busena": busena, "/api/aplinka": aplinka,
        "/api/prisijungti": P.prisijungti, "/api/paleisti_autocad": paleisti_autocad, "/api/ping": P.ping,
        "/api/progresas": progresas, "/api/testas": testas_atrakinti, "/api/testas_galioja": testas_patikrinti,
        "/api/langas": langas, "/api/ivykiai": ivykiai, "/api/ataskaita": ataskaita, "/api/duomenys": atidaryti_duomenis,
        "/api/atnaujinimai": atnaujinimai, "/api/atnaujinti": atnaujinti, "/api/perkrauti": perkrauti,
        "/api/praktika_atidaryti": praktika_atidaryti, "/api/praktika_pdf": praktika_pdf,
        "/api/praktika_aplankas": praktika_aplankas, "/api/praktika_tikrinti": praktika_tikrinti,
        "/api/testas_uzrakinti": testas_uzrakinti,
        **{f"/api/k_{f.__name__[2:]}": _kurejui(f) for f in (k_busena, k_imitacija, k_funkcijos, k_zurnalas,
                                                           k_acad, k_slaptazodis, k_nuotrauka)},
    }.items()}


if __name__ == "__main__":
    if WINDOWS:
        threading.Thread(target=lambda: _saugiai(klavisu_gija), daemon=True).start()
    try:
        P.main(BrezlyTvarkykle, 8732)
    except Exception:
        rasyti_zurnala("Paleidimas: " + traceback.format_exc())
        with open("klaida.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise

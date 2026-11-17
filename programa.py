"""
Brėžly Pilotas - programa su grafine sąsaja.

Paleidžia mažą vietinį serverį (tik šiame kompiuteryje) ir atidaro sąsają atskirame
programos lange (Microsoft Edge "app" režimu, be naršyklės juostų).
Uždarius langą, programa po kelių sekundžių išsijungia pati.

Paleidimas: PROGRAMA.bat arba nuoroda "Brėžly Pilotas" (po IDIEGTI.bat).
"""

import contextlib
import glob
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

os.chdir(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)))

import branduolys as A          # noqa: E402
import kalba                    # noqa: E402
import meniu as M               # noqa: E402

BUSENA = {"darbas": M.Darbas(), "paskutinis_ping": time.time(), "buvo_ping": False, "veikia": True}
TIPO_PAVADINIMAI = {"3D": "Detalė", "2D": "Detalės brėžinys", "SCHEMA": "Elektrinė principinė schema"}


# ------------------------------------------------------------------ pagalbinės
def zurnalas():
    """Kontekstas, surenkantis print() tekstą į eilutę."""
    return contextlib.redirect_stdout(io.StringIO())


def braizytojas():
    d = BUSENA["darbas"]
    if d.b is None:
        d.b = A.Braizytojas(A.prisijungti())
    else:
        try:                                    # ar AutoCAD vis dar gyvas
            A.kartoti(lambda: d.b.acad.ActiveDocument.Name)
        except Exception:
            d.b = A.Braizytojas(A.prisijungti())
    return d.b


def mano_failai():
    zinomi = {f for sar in M.PARUOSTOS.values() for f, _ in sar} | M.NE_DETALES
    return sorted(f for f in glob.glob("*.txt") if f not in zinomi)


def info():
    return {
        "versija": A.VERSIJA.split()[0], "langas": dict(LANGAS),
        "formatai": [{"id": k, "w": w, "h": h} for k, (w, h, _) in A.FORMATAI.items()],
        "tipai": [{"id": i, "pav": p.split(" (")[0], "aprasas": p.split(" (")[1].rstrip(")") if " (" in p else ""}
                  for i, p in M.TIPAI],
        "sablonai": [{"id": i, "pav": p} for i, p in A.SABLONAI],
        "issaugojimas": [{"id": k, "ext": v[0], "pav": v[2]} for k, v in A.ISSAUGOJIMO_FORMATAI.items()],
        "paruostos": {t: [{"failas": f, "pav": p} for f, p in sar] for t, sar in M.PARUOSTOS.items()},
        "mano": mano_failai(),
        "ai": A.gauti_rakta() is not None,
        "pavyzdziai": {"3D": kalba.PAVYZDZIAI_BREZINYS, "2D": kalba.PAVYZDZIAI_2D,
                       "SCHEMA": kalba.PAVYZDZIAI_SCHEMA},
    }


def saugus_failas(vardas):
    """Leidžia skaityti tik .txt failus iš programos aplanko."""
    vardas = os.path.basename(vardas or "")
    if not vardas.lower().endswith(".txt") or not os.path.exists(vardas):
        raise ValueError("Tokio failo nėra.")
    return vardas


# ------------------------------------------------------------------ veiksmai
def prisijungti(_):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        BUSENA["darbas"].b = None
        b = braizytojas()
        vardas = A.kartoti(lambda: b.acad.ActiveDocument.Name)
    return {"ok": True, "brezinys": vardas, "log": buf.getvalue()}


def busena(_):
    d = BUSENA["darbas"]
    if d.b is None:
        try:
            with zurnalas():
                d.b = A.Braizytojas(A.win32com.client.GetActiveObject("AutoCAD.Application"))
        except Exception:
            return {"ok": True, "prisijungta": False}
    try:
        vardas = A.kartoti(lambda: d.b.acad.ActiveDocument.Name, bandymu=2)
        return {"ok": True, "prisijungta": True, "brezinys": vardas}
    except Exception:
        d.b = None
        return {"ok": True, "prisijungta": False}


class Ribos:
    """Sekame detalės ribas peržiūrai - kad skylių gylis ir kampų suapvalinimas būtų kaip braižant."""
    def __init__(self):
        self.r = None

    def virsus(self):
        return self.r[1][2] if self.r else None

    def ribos(self):
        return self.r

    def prideti(self, komanda):
        dalys = komanda.split()
        cmd = dalys[0].lower()
        if cmd == "naujas":
            self.r = None
            return
        if cmd.startswith("-"):
            return
        try:
            v = [float(x) for x in dalys[1:7] if x.lower() not in ("+x", "-x")]
        except ValueError:
            return
        if cmd in ("deze", "pleistas") and len(v) >= 6:
            d = ((v[0], v[1], v[2]), (v[0] + v[3], v[1] + v[4], v[2] + v[5]))
        elif cmd == "cilindras" and len(v) >= 5:
            d = ((v[0] - v[3], v[1] - v[3], v[2]), (v[0] + v[3], v[1] + v[3], v[2] + v[4]))
        elif cmd == "cilindrasy" and len(v) >= 5:
            d = ((v[0] - v[3], v[1], v[2] - v[3]), (v[0] + v[3], v[1] + v[4], v[2] + v[3]))
        elif cmd == "sesiakampis" and len(v) >= 5:
            rr = v[3] / 3 ** 0.5
            d = ((v[0] - rr, v[1] - rr, v[2]), (v[0] + rr, v[1] + rr, v[2] + v[4]))
        else:
            return
        if self.r is None:
            self.r = d
        else:
            self.r = (tuple(map(min, self.r[0], d[0])), tuple(map(max, self.r[1], d[1])))


def perziura(duom):
    rb = Ribos()
    k = kalba.Kalba(A.KOMANDOS.keys(), virsus=rb.virsus, ribos=rb.ribos)
    kom, nes = [], []
    for sakinys in kalba.skaidyti_sakinius(duom.get("tekstas", "")):
        try:
            rez = k.sakinys(sakinys)
        except Exception:
            rez = None
        if not rez:
            nes.append(sakinys)
            continue
        for c in rez:
            kom.append(c)
            rb.prideti(c)
    return {"ok": True, "komandos": kom, "nesuprasta": nes}


def failo_turinys(duom):
    vardas = saugus_failas(duom.get("vardas"))
    with open(vardas, encoding="utf-8") as f:
        return {"ok": True, "tekstas": f.read()}


def vykdyti(duom):
    d = BUSENA["darbas"]
    buf = io.StringIO()
    klaidos_pries = 0
    with contextlib.redirect_stdout(buf):
        b = braizytojas()
        tipas = duom.get("tipas", "3D")
        fmt = duom.get("fmt") or None
        saltinis = duom.get("saltinis", {})
        if duom.get("sablonas"):
            A.naujas_brezinys(b.acad, duom["sablonas"])
            b.palaukti()
        b.kunas = None
        b.remelio_vieta = None
        if duom.get("sriftai"):
            b.vykdyti_saugiai("sriftai")
        b.vykdyti_saugiai("sluoksniai")
        if tipas == "3D":
            b.vykdyti_saugiai("naujas")
        nuo = A.kartoti(lambda: b.ms.Count)
        pavadinimas = TIPO_PAVADINIMAI.get(tipas, "Brėžinys")

        budas = saltinis.get("budas")
        if budas == "paruosta":
            vardas = saugus_failas(saltinis.get("failas"))
            with open(vardas, encoding="utf-8") as f:
                klaidos_pries = d.vykdyti_eilutes(f.readlines())
            pavadinimas = dict((x, y) for sar in M.PARUOSTOS.values() for x, y in sar).get(vardas, pavadinimas)
        elif budas == "tekstas":
            klaidos_pries = d.vykdyti_eilutes(saltinis.get("tekstas", "").splitlines())
        elif budas == "ai":
            turinys_tekstas = M.AI_TIPO_TEKSTAS[tipas]
            if saltinis.get("tekstas"):
                turinys_tekstas += " Užduotis: " + saltinis["tekstas"]
            pav = saltinis.get("paveikslas")
            if pav:
                turinys = [{"type": "image", "source": {"type": "base64", "media_type": pav["media"],
                                                         "data": pav["data"]}},
                           {"type": "text", "text": turinys_tekstas}]
            else:
                turinys = turinys_tekstas
            print("Klausiu AI, palauk...")
            atsakymas = A.paklausti_ai(turinys)
            klaidos_pries = d.vykdyti_eilutes(atsakymas.splitlines(), "ai")
        else:
            raise ValueError("Nepasirinktas turinys.")

        kampinis = {k: v for k, v in (duom.get("kampinis") or {}).items() if v}
        if kampinis.get("PAVADINIMAS"):
            pavadinimas = kampinis["PAVADINIMAS"]
        d.iforminti(tipas, fmt, nuo, pavadinimas, kampinis=kampinis,
                    ketvirtine=bool(duom.get("ketvirtine")))
    return {"ok": True, "log": buf.getvalue(), "klaidos": klaidos_pries,
            "vardas": M.failo_vardas(pavadinimas)}


def issaugoti(duom):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        b = braizytojas()
        vardas = duom.get("vardas") or "brezinys"
        if not os.path.isabs(vardas) and not os.path.dirname(vardas):
            vardas = os.path.join("brezinai", vardas)
        kelias = b.issaugoti(vardas, duom.get("formatas", "dwg"))
    return {"ok": True, "log": buf.getvalue(), "kelias": kelias}


def komanda(duom):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        b = braizytojas()
        tekstas = duom.get("tekstas", "").strip()
        if tekstas == "isvalyti":
            b.patvirtinti = lambda klausimas: True       # sąsaja jau paklausė
        b.vykdyti_zodziais(tekstas)
    return {"ok": True, "log": buf.getvalue()}


def atidaryti_aplanka(_):
    os.makedirs("brezinai", exist_ok=True)
    if os.name == "nt":
        os.startfile(os.path.abspath("brezinai"))
    return {"ok": True}


def ping(_):
    return {"ok": True}


VEIKSMAI = {"/api/prisijungti": prisijungti, "/api/busena": busena, "/api/perziura": perziura,
            "/api/failas": failo_turinys, "/api/vykdyti": vykdyti, "/api/issaugoti": issaugoti,
            "/api/komanda": komanda, "/api/aplankas": atidaryti_aplanka, "/api/ping": ping}


# ------------------------------------------------------------------ serveris
class Tvarkykle(BaseHTTPRequestHandler):
    HTML = "ui.html"
    IKONA = "robotas.ico"
    VEIKSMAI = VEIKSMAI

    def log_message(self, *a):
        pass

    def _siusti(self, kodas, turinys, tipas="application/json; charset=utf-8"):
        if isinstance(turinys, (dict, list)):
            turinys = json.dumps(turinys, ensure_ascii=False).encode("utf-8")
        elif isinstance(turinys, str):
            turinys = turinys.encode("utf-8")
        self.send_response(kodas)
        self.send_header("Content-Type", tipas)
        self.send_header("Content-Length", str(len(turinys)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(turinys)

    def _ping(self):
        BUSENA["paskutinis_ping"] = time.time()
        BUSENA["buvo_ping"] = True

    def do_GET(self):
        self._ping()
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            with open(self.HTML, encoding="utf-8") as f:
                return self._siusti(200, f.read(), "text/html; charset=utf-8")
        if u.path in ("/robotas.ico", "/ikona.ico"):
            with open(self.IKONA, "rb") as f:
                return self._siusti(200, f.read(), "image/x-icon")
        if u.path == "/api/info" and "/api/info" not in self.VEIKSMAI:
            return self._siusti(200, info())
        if u.path in self.VEIKSMAI:
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            return self._atsakyti(self.VEIKSMAI[u.path], q)
        self._siusti(404, {"ok": False, "klaida": "Nėra"})

    def do_POST(self):
        self._ping()
        u = urlparse(self.path)
        if u.path not in self.VEIKSMAI:
            return self._siusti(404, {"ok": False, "klaida": "Nėra"})
        ilgis = int(self.headers.get("Content-Length") or 0)
        try:
            duom = json.loads(self.rfile.read(ilgis) or b"{}")
        except Exception:
            duom = {}
        self._atsakyti(self.VEIKSMAI[u.path], duom)

    def _atsakyti(self, f, duom):
        try:
            rez = f(duom)
        except Exception as e:
            rez = {"ok": False, "klaida": str(e) or e.__class__.__name__,
                   "log": traceback.format_exc(limit=2) if os.environ.get("BREZLY_DEBUG") else ""}
        self._ping()
        self._siusti(200, rez)


def laisvas_prievadas(pageidaujamas=None):
    """Pastovus prievadas, kad naršyklė išsaugotų nustatymus ir progresą (localStorage priklauso nuo prievado).
    Jei užimtas - atsitiktinis."""
    for p in ([pageidaujamas] if pageidaujamas else []) + [0]:
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", p))
                return s.getsockname()[1]
        except OSError:
            continue


LANGAS = {"budas": "", "narsykle": ""}     # kaip atidarytas langas: "app" (atskiras langas) / "narsykle"

# Chromium naršyklės palaiko --app (atskiras langas be adreso juostos). Firefox - ne.
_CHROMIUM = [("msedge.exe", "Microsoft Edge", [r"Microsoft\Edge\Application"]),
             ("chrome.exe", "Google Chrome", [r"Google\Chrome\Application"]),
             ("brave.exe", "Brave", [r"BraveSoftware\Brave-Browser\Application"]),
             ("vivaldi.exe", "Vivaldi", [r"Vivaldi\Application"]),
             ("browser.exe", "Yandex", [r"Yandex\YandexBrowser\Application"]),
             ("opera.exe", "Opera", [r"Programs\Opera", r"Programs\Opera GX"]),
             ("chromium.exe", "Chromium", [r"Chromium\Application"])]


def _registro_kelias(exe):
    """Windows registras: App Paths (ten Edge/Chrome užsiregistruoja net įdiegti ne standartinėje vietoje)."""
    try:
        import winreg
    except ImportError:
        return None
    for sakn in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for vaizd in (0, getattr(winreg, "KEY_WOW64_32KEY", 0)):
            try:
                with winreg.OpenKey(sakn, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\" + exe, 0,
                                    winreg.KEY_READ | vaizd) as k:
                    v = winreg.QueryValue(k, None)
                    if v:
                        return v.strip('"')
            except OSError:
                continue
    return None


def _numatytoji_narsykle():
    """Numatytosios naršyklės .exe, jei ji Chromium tipo."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice") as k:
            progid = winreg.QueryValueEx(k, "ProgId")[0]
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid + r"\shell\open\command") as k:
            kom = winreg.QueryValue(k, None)
        exe = kom.split('"')[1] if kom.startswith('"') else kom.split()[0]
        if os.path.basename(exe).lower() in {e for e, _, _ in _CHROMIUM}:
            return exe
    except Exception:
        pass
    return None


def rasti_narsykles():
    """[(kelias, pavadinimas)] - Chromium naršyklės, tinkančios atskiram langui (pirma Edge, Chrome)."""
    rasta, mat = [], set()

    def prideti(k, pav):
        if k and os.path.isfile(k) and k.lower() not in mat:
            mat.add(k.lower()); rasta.append((k, pav))
    aplankai = [os.environ.get(v, "") for v in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "LOCALAPPDATA")]
    for exe, pav, sub in _CHROMIUM:
        prideti(shutil.which(exe[:-4]), pav)
        prideti(_registro_kelias(exe), pav)
        for ap in aplankai:
            for s_ in sub:
                if ap:
                    prideti(os.path.join(ap, s_, exe), pav)
    nk = _numatytoji_narsykle()
    if nk:
        prideti(nk, os.path.basename(nk))
    return rasta


def darbo_sritis():
    """Pagrindinio ekrano darbo sritis be užduočių juostos: (x, y, plotis, aukštis) loginiais taškais."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            r = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0):   # SPI_GETWORKAREA
                return r.left, r.top, r.right - r.left, r.bottom - r.top
        except Exception:
            pass
    return 0, 0, 1920, 1040


def lango_dydis():
    """Pradinis lango dydis: ne didesnis nei ekranas (nešiojamiems kompiuteriams 1366×768, 125 % mastelis...)."""
    x, y, w, h = darbo_sritis()
    lw, lh = min(1280, int(w * 0.92)), min(860, int(h * 0.94))
    return lw, lh, x + (w - lw) // 2, y + (h - lh) // 2


def atidaryti_langa(url):
    """Atskiras programos langas (Edge/Chrome/Brave... --app). Jei nieko nerasta - įprasta naršyklė."""
    lw, lh, lx, ly = lango_dydis()
    for kelias, pav in rasti_narsykles():
        try:
            subprocess.Popen([kelias, f"--app={url}", f"--window-size={lw},{lh}", f"--window-position={lx},{ly}", "--no-first-run"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            LANGAS.update(budas="app", narsykle=pav)
            return
        except Exception:
            continue
    LANGAS.update(budas="narsykle", narsykle="numatytoji")
    webbrowser.open(url)


def main(tvarkykle=None, pageidaujamas=8731):
    prievadas = laisvas_prievadas(pageidaujamas)
    serveris = HTTPServer(("127.0.0.1", prievadas), tvarkykle or Tvarkykle)
    serveris.timeout = 1.0
    url = f"http://127.0.0.1:{prievadas}/"
    if not os.environ.get("BREZLY_BE_LANGO"):
        threading.Timer(0.3, atidaryti_langa, args=(url,)).start()
    print(f"Veikia: {url}  (uždaryk langą, kad išjungtum)")
    pradzia = time.time()
    while BUSENA["veikia"]:
        serveris.handle_request()
        tyla = time.time() - BUSENA["paskutinis_ping"]
        if BUSENA["buvo_ping"] and tyla > 12:
            break                                   # langas uždarytas
        if not BUSENA["buvo_ping"] and time.time() - pradzia > 120:
            break                                   # langas taip ir neatsidarė
    serveris.server_close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open("klaida.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise

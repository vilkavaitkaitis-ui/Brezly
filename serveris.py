"""
Bendras Brėžly ir Brėžly Piloto pagrindas.

  * mažas vietinis HTTP serveris (tik 127.0.0.1) - sąsaja HTML lange, veiksmai per /api/...;
  * programos langas: Edge/Chrome/Brave... „--app“ režimu (be naršyklės juostų);
  * ryšys su AutoCAD per COM (branduolys.Braizytojas).

Uždarius langą (nebeateina /api/ping), programa po kelių sekundžių išsijungia pati.
"""

import contextlib
import csv
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

PROGRAMOS_APLANKAS = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
os.chdir(PROGRAMOS_APLANKAS)

import branduolys as A          # noqa: E402
from vertimas import tr         # noqa: E402


class Rysys:
    """AutoCAD ryšio laikiklis: b - branduolys.Braizytojas arba None.
    Brėžly Pilotas jį pakeičia savo meniu.Darbas (tas pats laukas b + braižymo veiksmai)."""

    def __init__(self):
        self.b = None


BUSENA = {"darbas": Rysys(), "paskutinis_ping": time.time(), "buvo_ping": False, "veikia": True}


# ------------------------------------------------------------------ AutoCAD ryšys
def zurnalas():
    """Kontekstas, surenkantis print() tekstą į eilutę."""
    return contextlib.redirect_stdout(io.StringIO())


def braizytojas(paleisti=True, brezinys=True):
    """Prisijungęs Braizytojas su aktyviu brėžiniu (brezinys=False - be jo: tuoj atidarysime ar sukursime).
    Jei AutoCAD buvo uždarytas - prisijungia iš naujo."""
    d = BUSENA["darbas"]
    if d.b is not None:
        try:                                    # ar AutoCAD vis dar gyvas
            A.kartoti(lambda: d.b.acad.Documents.Count)
        except Exception as e:
            if A.atmesta(e):                    # gyvas, tik užimtas - prisijungimas iš naujo nepadėtų
                raise RuntimeError(tr("AutoCAD užimtas - užbaik komandą arba uždaryk atidarytą langą (Esc).",
                                      "AutoCAD is busy - finish the command or close the open dialog (Esc).")) from None
            d.b = None
    if d.b is None:
        d.b = A.Braizytojas(A.prisijungti(paleisti, brezinys))
    elif brezinys:
        A.uztikrinti_brezini(d.b.acad)
    return d.b


# ------------------------------------------------------------------ kodėl neprisijungia
def dekoduoti(baitai):
    """Windows konsolės programų (tasklist) išvestis - OEM koduote (lietuviškame Windows - ne UTF-8)."""
    for koduote in ("oem", "mbcs"):
        try:
            return baitai.decode(koduote, "replace")
        except LookupError:
            continue
    return baitai.decode("utf-8", "replace")


def acad_procesai():
    """Veikiančių acad.exe PID (ne Windows - tuščias)."""
    if sys.platform != "win32":
        return []
    try:
        isvestis = subprocess.run(["tasklist", "/fo", "csv", "/nh", "/fi", "imagename eq acad.exe"],
                                  capture_output=True, timeout=5, creationflags=0x08000000).stdout
    except Exception:
        return []
    return [int(e[1]) for e in csv.reader(io.StringIO(dekoduoti(isvestis)))
            if len(e) > 1 and e[0].lower() == "acad.exe" and e[1].isdigit()]


def pakeltas(pid=None):
    """Ar procesas (None - pats Brėžly) paleistas „kaip administratorius“. None - nežinoma."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        adv = ctypes.WinDLL("advapi32", use_last_error=True)
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        k32.CloseHandle.argtypes = (wintypes.HANDLE,)
        adv.OpenProcessToken.argtypes = (wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE))
        adv.GetTokenInformation.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                            ctypes.POINTER(wintypes.DWORD))
        h = k32.GetCurrentProcess() if pid is None else k32.OpenProcess(0x1000, False, pid)   # QUERY_LIMITED_INFORMATION
        if not h:
            return None
        zetonas = wintypes.HANDLE()
        try:
            if not adv.OpenProcessToken(h, 0x0008, ctypes.byref(zetonas)):                    # TOKEN_QUERY
                # administratoriaus proceso žetono paprasta programa neperskaito (ERROR_ACCESS_DENIED)
                return True if pid is not None and ctypes.get_last_error() == 5 else None
            reiksme, ilgis = wintypes.DWORD(), wintypes.DWORD()
            ok = adv.GetTokenInformation(zetonas, 20, ctypes.byref(reiksme), 4, ctypes.byref(ilgis))  # TokenElevation
            return bool(reiksme.value) if ok else None
        finally:
            if zetonas:
                k32.CloseHandle(zetonas)
            if pid is not None:
                k32.CloseHandle(h)
    except Exception:
        return None


def priezastis(klaida):
    """Kodėl nepavyko prisijungti prie AutoCAD: (kodas, techninis tekstas). Kodai:
    pywin32, neatidarytas, uzimtas, teises_acad, teises_brezly, kraunasi, neregistruotas, kita."""
    if A.win32com is None:
        return "pywin32", A.IMPORTO_KLAIDA
    k = A.com_kodas(klaida)
    tekstas = f"{k & 0xFFFFFFFF:#010x} {klaida}" if k is not None else f"{klaida.__class__.__name__}: {klaida}"
    pid = acad_procesai()
    if not pid:
        return "neatidarytas", tekstas
    if A.atmesta(klaida):
        return "uzimtas", tekstas
    if k in (A.MK_E_UNAVAILABLE, A.E_ACCESSDENIED):
        mes = pakeltas()
        jie = [j for j in (pakeltas(p) for p in pid) if j is not None]
        if mes is not None and jie and all(j != mes for j in jie):
            return ("teises_brezly" if mes else "teises_acad"), tekstas
        return "kraunasi", tekstas
    if k in (A.CO_E_CLASSSTRING, A.REGDB_E_CLASSNOTREG):
        return "neregistruotas", tekstas
    return "kita", tekstas


def paaiskinimas(kodas):
    """Ką daryti - rodoma po būsena ir prisijungimo klaidoje."""
    return {
        "pywin32": tr("Trūksta Brėžly dalies, per kurią jungiamasi prie AutoCAD (pywin32). Įdiek Brėžly iš naujo.",
                      "A part of Brėžly that connects to AutoCAD (pywin32) is missing. Reinstall Brėžly.")
        if getattr(sys, "frozen", False) else
        tr("Trūksta pywin32 paketo. Paleisk IDIEGTI.bat arba: python -m pip install pywin32",
           "The pywin32 package is missing. Run IDIEGTI.bat or: python -m pip install pywin32"),
        "neatidarytas": tr("AutoCAD neatidarytas.", "AutoCAD is not open."),
        "uzimtas": tr("AutoCAD užimtas - užbaik komandą arba uždaryk atidarytą langą (Esc).",
                      "AutoCAD is busy - finish the command or close the open dialog (Esc)."),
        "teises_acad": tr("AutoCAD paleistas „kaip administratorius“, o Brėžly - ne, todėl Windows neleidžia jiems susikalbėti. "
                          "Išsaugok brėžinį, uždaryk AutoCAD ir atidaryk jį įprastai (ne „Run as administrator“).",
                          "AutoCAD is running as administrator and Brėžly is not, so Windows won't let them talk. "
                          "Save your drawing, close AutoCAD and open it normally (not „Run as administrator“)."),
        "teises_brezly": tr("Brėžly paleistas „kaip administratorius“, o AutoCAD - ne, todėl Windows neleidžia jiems susikalbėti. "
                            "Uždaryk Brėžly ir atidaryk jį įprastai.",
                            "Brėžly is running as administrator and AutoCAD is not, so Windows won't let them talk. "
                            "Close Brėžly and open it normally."),
        "kraunasi": tr("AutoCAD atidarytas, bet dar neatsiliepia. Palauk, kol jis visiškai užsikraus. "
                       "Jei per minutę neprisijungia - uždaryk AutoCAD ir atidaryk jį įprastai (ne „kaip administratorius“).",
                       "AutoCAD is open but not answering yet. Wait until it has fully loaded. "
                       "If it doesn't connect within a minute, close AutoCAD and open it normally (not as administrator)."),
        "neregistruotas": tr("Windows nežino, kaip pasiekti šį AutoCAD (gali būti AutoCAD LT arba nebaigtas diegimas). "
                             "Pabandyk AutoCAD diegimo programoje pasirinkti „Repair“.",
                             "Windows doesn't know how to reach this AutoCAD (it may be AutoCAD LT or an unfinished install). "
                             "Try „Repair“ in the AutoCAD installer."),
    }.get(kodas, tr("Nepavyko prisijungti prie AutoCAD.", "Couldn't connect to AutoCAD."))


def brezinio_busena(b):
    """{"brezinys": vardas} arba be_brezinio, kai AutoCAD rodo tik pradžios (Start) langą."""
    n = A.kartoti(lambda: b.acad.Documents.Count, bandymu=2)
    if not n:
        return {"brezinys": tr("nėra atidaryto brėžinio", "no drawing open"), "be_brezinio": True}
    try:
        vardas = A.kartoti(lambda: b.acad.ActiveDocument.Name, bandymu=2)
    except Exception as e:
        if A.atmesta(e):
            raise
        vardas = A.kartoti(lambda: b.acad.Documents.Item(n - 1).Name, bandymu=2)   # aktyvus pradžios skirtukas
    BUSENA["brezinys"] = vardas
    return {"brezinys": vardas}


def prisijungti(_):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        BUSENA["darbas"].b = None
        try:                # AutoCAD veikia, bet nepasiekiamas - antro AutoCAD nepaleidžiame
            b = braizytojas(paleisti=not acad_procesai())
            vardas = brezinio_busena(b)["brezinys"]
        except Exception as e:
            BUSENA["darbas"].b = None
            kodas, tekstas = priezastis(e)
            return {"ok": False, "priezastis": kodas, "klaida": f"{paaiskinimas(kodas)} ({tekstas})", "log": buf.getvalue()}
    return {"ok": True, "brezinys": vardas, "log": buf.getvalue()}


def busena(_):
    """Ar prisijungta prie jau veikiančio AutoCAD (pats AutoCAD nepaleidžiamas).
    Jei ne - priezastis (žr. priezastis()), paaiskinimas ir klaida (techninis kodas)."""
    d = BUSENA["darbas"]
    klaida = None
    for _ in range(2):                          # antras ratas - kai AutoCAD buvo perkrautas
        if d.b is None:
            try:
                with zurnalas():
                    d.b = A.Braizytojas(A.rasti_atidaryta())
            except Exception as e:
                klaida = e
                break
        try:
            return {"ok": True, "prisijungta": True, **brezinio_busena(d.b)}
        except Exception as e:
            if A.atmesta(e):                    # atidarytas dialogas ar ilga komanda - ryšys yra
                return {"ok": True, "prisijungta": True, "uzimtas": True, "brezinys": BUSENA.get("brezinys", "")}
            d.b, klaida = None, e
    kodas, tekstas = priezastis(klaida)
    return {"ok": True, "prisijungta": False, "priezastis": kodas, "paaiskinimas": paaiskinimas(kodas), "klaida": tekstas}


def ping(_):
    return {"ok": True}


# ------------------------------------------------------------------ HTTP tvarkyklė
TIPAI = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
         ".ico": "image/x-icon", ".svg": "image/svg+xml", ".png": "image/png", ".pdf": "application/pdf"}


class Tvarkykle(BaseHTTPRequestHandler):
    """Bazinė tvarkyklė. Programa paveldi ir nurodo HTML, IKONA, FAILAI ir VEIKSMAI."""
    HTML = "index.html"
    IKONA = "ikona.ico"
    FAILAI = ()                 # papildomi statiniai failai šalia programos, pvz. ("brezly.css", "brezly.js")
    VEIKSMAI = {"/api/prisijungti": prisijungti, "/api/busena": busena, "/api/ping": ping}

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

    def _failas(self, vardas):
        with open(os.path.join(PROGRAMOS_APLANKAS, vardas), "rb") as f:
            return self._siusti(200, f.read(), TIPAI.get(os.path.splitext(vardas)[1].lower(), "application/octet-stream"))

    def _ping(self):
        BUSENA["paskutinis_ping"] = time.time()
        BUSENA["buvo_ping"] = True

    def do_GET(self):
        self._ping()
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._failas(self.HTML)
        if u.path in ("/ikona.ico", "/robotas.ico", "/favicon.ico"):
            return self._failas(self.IKONA)
        if u.path.lstrip("/") in self.FAILAI:
            return self._failas(u.path.lstrip("/"))
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


# ------------------------------------------------------------------ programos langas
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
            mat.add(k.lower())
            rasta.append((k, pav))
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


def main(tvarkykle, pageidaujamas):
    """Paleidžia serverį ir langą; grįžta, kai langas uždarytas (12 s be /api/ping) arba BUSENA["veikia"] = False."""
    prievadas = laisvas_prievadas(pageidaujamas)
    serveris = HTTPServer(("127.0.0.1", prievadas), tvarkykle)
    serveris.timeout = 1.0
    url = f"http://127.0.0.1:{prievadas}/"
    if not os.environ.get("BREZLY_BE_LANGO"):
        threading.Timer(0.3, atidaryti_langa, args=(url,)).start()
    print(f"Veikia: {url}  (uždaryk langą, kad išjungtum)", flush=True)
    pradzia = time.time()
    while BUSENA["veikia"]:
        serveris.handle_request()
        tyla = time.time() - BUSENA["paskutinis_ping"]
        if BUSENA["buvo_ping"] and tyla > 12:
            break                                   # langas uždarytas
        if not BUSENA["buvo_ping"] and time.time() - pradzia > 120:
            break                                   # langas taip ir neatsidarė
    serveris.server_close()

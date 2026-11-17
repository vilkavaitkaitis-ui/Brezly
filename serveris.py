"""
Bendras Brėžly ir Brėžly Piloto pagrindas.

  * mažas vietinis HTTP serveris (tik 127.0.0.1) - sąsaja HTML lange, veiksmai per /api/...;
  * programos langas: Edge/Chrome/Brave... „--app“ režimu (be naršyklės juostų);
  * ryšys su AutoCAD per COM (branduolys.Braizytojas).

Uždarius langą (nebeateina /api/ping), programa po kelių sekundžių išsijungia pati.
"""

import contextlib
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


def braizytojas():
    """Prisijungęs Braizytojas. Jei AutoCAD buvo uždarytas - prisijungia iš naujo."""
    d = BUSENA["darbas"]
    if d.b is None:
        d.b = A.Braizytojas(A.prisijungti())
    else:
        try:                                    # ar AutoCAD vis dar gyvas
            A.kartoti(lambda: d.b.acad.ActiveDocument.Name)
        except Exception:
            d.b = A.Braizytojas(A.prisijungti())
    return d.b


def prisijungti(_):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        BUSENA["darbas"].b = None
        b = braizytojas()
        vardas = A.kartoti(lambda: b.acad.ActiveDocument.Name)
    return {"ok": True, "brezinys": vardas, "log": buf.getvalue()}


def busena(_):
    """Ar prisijungta prie jau veikiančio AutoCAD (pats AutoCAD nepaleidžiamas)."""
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

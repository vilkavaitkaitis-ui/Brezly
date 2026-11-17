"""
DarkCAD - Brėžly Piloto tamsioji pusė. 😈
Ta pati Brėžly Piloto programa (braižo už tave), tik su piktadario išvaizda.
Mygtukas „Grįžti į šviesiąją pusę“ atidaro Brėžly - mokymosi programą.

Paleidimas: DARKCAD.bat arba nuoroda "DarkCAD".
Nustatymai, istorija ir šablonai: Dokumentai\\DarkCAD\\darkcad.json
Išsaugoti brėžiniai: Dokumentai\\DarkCAD\\Breziniai
"""

import contextlib
import datetime
import io
import json
import os
import subprocess
import sys
import threading
import traceback

APLANKAS = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
os.chdir(APLANKAS)

import programa as P            # noqa: E402
import brezly as B              # noqa: E402  (bendros 0.6 funkcijos: AutoCAD paieška, langas, ataskaita, atnaujinimai)

VERSIJA_DARK = "1.5"
B.LANGO_PAVADINIMAS = "DarkCAD"
B.VERSIJA_BREZLY = "DarkCAD " + VERSIJA_DARK
B.DUOM = os.path.join(os.path.dirname(B.dokumentu_aplankas()), "DarkCAD") if not os.environ.get("BREZLY_DUOMENYS") \
    else os.path.join(os.environ["BREZLY_DUOMENYS"], "DarkCAD")
B.ZURNALAS = os.path.join(B.DUOM, "darkcad.log")
B.PROGRESAS = os.path.join(B.DUOM, "darkcad.json")
DUOMENYS = B.PROGRESAS
BREZINIAI = os.path.join(B.DUOM, "Breziniai")
ISTORIJOS_ILGIS = 30


# ------------------------------------------------------------------ nustatymai, istorija, šablonai
def _skaityti():
    for kelias in (DUOMENYS, DUOMENYS + ".bak"):
        try:
            with open(kelias, encoding="utf-8") as f:
                d = json.load(f)
            d.setdefault("nustatymai", {}); d.setdefault("istorija", []); d.setdefault("sablonai", {})
            return d
        except FileNotFoundError:
            continue
        except Exception:
            B.rasyti_zurnala("Sugadintas " + kelias)
    return {"nustatymai": {}, "istorija": [], "sablonai": {}}


def _rasyti(d):
    os.makedirs(B.DUOM, exist_ok=True)
    d["versija"] = VERSIJA_DARK
    B.irasyti_atomiskai(DUOMENYS, json.dumps(d, ensure_ascii=False, indent=1))


def duomenys(duom):
    """GET - viskas; POST {nustatymai} / {istorija: įrašas} / {sablonas: {vardas, tekstas}} / {trinti_sablona} / {trinti_istorija}."""
    d = _skaityti()
    if not duom:
        return {"ok": True, **d, "kelias": DUOMENYS, "breziniai": BREZINIAI}
    if isinstance(duom.get("nustatymai"), dict):
        d["nustatymai"].update(duom["nustatymai"])
    if isinstance(duom.get("istorija"), dict):
        irasas = dict(duom["istorija"], laikas=datetime.datetime.now().isoformat(timespec="minutes"))
        irasas.get("saltinis", {}).pop("paveikslas", None)          # nuotraukų istorijoje nesaugom
        d["istorija"] = ([irasas] + d["istorija"])[:ISTORIJOS_ILGIS]
    if isinstance(duom.get("sablonas"), dict):
        v = str(duom["sablonas"].get("vardas", "")).strip()[:60]
        if v:
            d["sablonai"][v] = {"tekstas": str(duom["sablonas"].get("tekstas", "")), "tipas": duom["sablonas"].get("tipas")}
    if duom.get("trinti_sablona"):
        d["sablonai"].pop(duom["trinti_sablona"], None)
    if duom.get("trinti_istorija") is not None:
        i = int(duom["trinti_istorija"])
        if i < 0:
            d["istorija"] = []
        elif i < len(d["istorija"]):
            d["istorija"].pop(i)
    _rasyti(d)
    return {"ok": True, **d}


# ------------------------------------------------------------------ brėžiniai į Dokumentai\DarkCAD
def issaugoti(duom):
    vardas = os.path.basename(str(duom.get("vardas") or "brezinys")) or "brezinys"
    os.makedirs(BREZINIAI, exist_ok=True)
    return P.issaugoti({**duom, "vardas": os.path.join(BREZINIAI, vardas)})


def atidaryti_aplanka(_):
    os.makedirs(BREZINIAI, exist_ok=True)
    if os.name == "nt":
        os.startfile(BREZINIAI)
    return {"ok": True, "kelias": BREZINIAI}


def greita(duom):
    """Viena ar kelios eilutės žodžiais - tiesiai į atidarytą brėžinį (be lapo, be naujo failo)."""
    tekstas = str(duom.get("tekstas", "")).strip()
    if not tekstas:
        return {"ok": False, "klaida": "Tuščia komanda."}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        P.braizytojas()
        klaidos = P.BUSENA["darbas"].vykdyti_eilutes(tekstas.splitlines())
        try:
            b = P.BUSENA["darbas"].b
            P.A.kartoti(b.acad.ZoomExtents)
        except Exception:
            pass
    return {"ok": True, "log": buf.getvalue(), "klaidos": klaidos}


def info(_):
    return {**P.info(), "darkcad": VERSIJA_DARK, "windows": B.WINDOWS, "atnaujinimai": bool(B.ATNAUJINIMU_URL),
            "duomenys": B.DUOM, "breziniai": BREZINIAI}


def perkrauti(_):
    exe = sys.executable.replace("python.exe", "pythonw.exe")
    args = [exe] if getattr(sys, "frozen", False) else [exe, os.path.abspath(__file__)]
    env = dict(os.environ, BREZLY_BE_LANGO="1")
    threading.Timer(1.5, lambda: subprocess.Popen(args, cwd=APLANKAS, env=env)).start()
    P.BUSENA["veikia"] = False
    return {"ok": True}


def i_sviesiaja(_):
    """Atidaro Brėžly (mokymosi programą)."""
    if os.name != "nt":
        return {"ok": False, "klaida": "Tik Windows"}
    for kelias in ("Brezly.exe", "BREZLY.bat"):
        if os.path.exists(kelias):
            os.startfile(os.path.abspath(kelias))
            return {"ok": True}
    return {"ok": False, "klaida": "Nerandu Brėžly programos"}


class DarkTvarkykle(P.Tvarkykle):
    HTML = "darkcad.html"
    IKONA = "darkcad.ico"
    VEIKSMAI = {k: B._su_zurnalu(f) for k, f in {
        **P.VEIKSMAI,
        "/api/info": info, "/api/brezly": i_sviesiaja, "/api/busena": B.busena, "/api/aplinka": B.aplinka,
        "/api/paleisti_autocad": B.paleisti_autocad, "/api/langas": B.langas, "/api/ataskaita": B.ataskaita,
        "/api/duomenys": duomenys, "/api/issaugoti": issaugoti, "/api/aplankas": atidaryti_aplanka,
        "/api/greita": greita, "/api/atnaujinimai": B.atnaujinimai, "/api/atnaujinti": B.atnaujinti,
        "/api/perkrauti": perkrauti,
    }.items()}


if __name__ == "__main__":
    try:
        P.main(DarkTvarkykle, 8733)
    except Exception:
        B.rasyti_zurnala("Paleidimas: " + traceback.format_exc())
        with open("klaida.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise

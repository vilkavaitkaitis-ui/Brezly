"""
Brėžly praktikos užduotys (0.8): 2D - A4, 3D - A3.

Kiekvienai užduočiai aplanke praktika/ yra:
  <id>.svg / .pdf      - brėžinys peržiūrai ir spausdinimui
  <id>.dxf             - pavyzdys (atsakymas) AutoCAD'ui
  <id>_ruosinys.dxf    - tuščias lapas su rėmeliu ir pagrindiniu įrašu - jame mokinys braižo
Tikrinimas skaito aktyvų brėžinį per AutoCAD COM: apskritimų spindulius, objektų tipus, 3D kūno tūrį.
"""

import json
import os
import shutil
import subprocess
import sys

from vertimas import tr

APLANKAS = os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)), "praktika")

UZDUOCIU_FAILAS = os.path.join(APLANKAS, "uzduotys.json")
# Taisyklės faile naudoja DXF tipų vardus (kaip programėlė), AutoCAD COM grąžina AcDb* vardus
COM_TIPAI = {"LINE": "AcDbLine", "ARC": "AcDbArc", "HATCH": "AcDbHatch", "ELLIPSE": "AcDbEllipse",
             "INSERT": "AcDbBlockReference", "CIRCLE": "AcDbCircle", "3DSOLID": "AcDb3dSolid"}
PAVADINIMAI = {"AcDbLine": "linijų", "AcDbArc": "lankų", "AcDbHatch": "brūkšniuotės (HATCH)",
               "AcDbEllipse": "elipsių (ELLIPSE → Isocircle)", "AcDbBlockReference": "įterptų blokų (INSERT)"}
PAVADINIMAI_EN = {"AcDbLine": "lines", "AcDbArc": "arcs", "AcDbHatch": "hatches (HATCH)",
                  "AcDbEllipse": "ellipses (ELLIPSE → Isocircle)", "AcDbBlockReference": "inserted blocks (INSERT)"}


def _ikelti():
    """praktika/uzduotys.json -> {id: {xp, apskritimai {spindulys: kiekis}, tipai {AcDb...: kiekis}, turis}}"""
    with open(UZDUOCIU_FAILAS, encoding="utf-8") as f:
        d = json.load(f)
    uzd = {}
    for u in d["uzduotys"]:
        t = u.get("tikrinimas", {})
        r = {"xp": u["xp"]}
        if t.get("apskritimai"):
            r["apskritimai"] = dict(sorted(((float(k), v) for k, v in t["apskritimai"].items()), reverse=True))
        if t.get("tipai"):
            r["tipai"] = {COM_TIPAI.get(k, k): v for k, v in t["tipai"].items()}
        if t.get("turis"):
            r["turis"] = float(t["turis"])
        uzd[u["id"]] = r
    return d, uzd


_DUOM, UZDUOTYS = _ikelti()
SARASAS = _DUOM["uzduotys"]                     # visa informacija sąsajai (pavadinimai, žingsniai...)


def sarasas(kalba="lt"):
    """Užduočių sąrašas sąsajai pasirinkta kalba (anglų - laukas „en“ uzduotys.json)."""
    if kalba != "en":
        return SARASAS
    return [{**u, **u.get("en", {})} for u in SARASAS]
TOL_R = _DUOM["tolerancija"]["spindulys"]
TOL_V = _DUOM["tolerancija"]["turis"]


def _uzd(duom):
    uid = str(duom.get("id", ""))
    if uid not in UZDUOTYS:
        raise ValueError(tr("Nežinoma užduotis", "Unknown task"))
    return uid


def failas(vardas):
    """Saugus kelias į praktikos failą (tik vardas, be katalogų)."""
    vardas = os.path.basename(vardas)
    kelias = os.path.join(APLANKAS, vardas)
    return kelias if os.path.isfile(kelias) and os.path.splitext(vardas)[1].lower() in (".svg", ".pdf", ".dxf") else None


def darbo_aplankas(dokai):
    d = os.path.join(dokai, "Praktika")
    os.makedirs(d, exist_ok=True)
    return d


def paruosti(uid, kas, dokai):
    """Nukopijuoja DXF į Dokumentai\\Brezly\\Praktika (originalas lieka nepaliestas)."""
    if kas == "pavyzdys":
        src, vardas = os.path.join(APLANKAS, uid + ".dxf"), uid + "_PAVYZDYS.dxf"
    else:
        src, vardas = os.path.join(APLANKAS, uid + "_ruosinys.dxf"), uid + "_mano.dxf"
    dst = os.path.join(darbo_aplankas(dokai), vardas)
    if kas == "pavyzdys" or not os.path.exists(dst):
        shutil.copyfile(src, dst)
    # jei jau braižė ir išsaugojo DWG - atidarom jį, kad darbas nedingtų
    dwg = os.path.splitext(dst)[0] + ".dwg"
    return dwg if kas != "pavyzdys" and os.path.exists(dwg) else dst


def atidaryti_faila(kelias):
    if sys.platform == "win32":
        os.startfile(kelias)            # noqa  (tik Windows)
    else:
        subprocess.Popen(["xdg-open", kelias])


def _objektai(b, kartoti):
    ms = b.ms
    rez = []
    for i in range(kartoti(lambda: ms.Count)):
        try:
            e = kartoti(lambda: ms.Item(i))
            rez.append(e)
        except Exception:
            pass
    return rez


def analizuoti(b, kartoti):
    """Ką mato tikrinimas: objektų tipai, apskritimų spinduliai, 3D kūnų tūriai."""
    tipai, spinduliai, turiai = {}, [], []
    for e in _objektai(b, kartoti):
        try:
            t = e.ObjectName
        except Exception:
            continue
        tipai[t] = tipai.get(t, 0) + 1
        try:
            if t == "AcDbCircle":
                spinduliai.append(float(e.Radius))
            elif t == "AcDb3dSolid":
                turiai.append(float(e.Volume))
        except Exception:
            pass
    return {"tipai": tipai, "spinduliai": spinduliai, "turiai": turiai}


def tikrinti(uid, b, kartoti):
    """Grąžina pastabų sąrašą (tuščias - viskas gerai)."""
    u = UZDUOTYS[uid]
    try:
        vardas = kartoti(lambda: b.acad.ActiveDocument.Name)
    except Exception:
        vardas = ""
    if "PAVYZDYS" in vardas.upper():
        return [tr("Dabar atidarytas pavyzdys (atsakymas). Spausk „Pradėti“ - atidarysiu tuščią lapą, jame ir braižyk.", "The example (answer) is open now. Click „Start“ - I'll open a blank sheet for you to draw on.")]
    a = analizuoti(b, kartoti)
    tipai, spinduliai, turiai = a["tipai"], a["spinduliai"], a["turiai"]
    pastabos = []
    for r, kiek in u.get("apskritimai", {}).items():
        rasta = sum(1 for x in spinduliai if abs(x - r) <= TOL_R)
        if rasta < kiek:
            artimi = sorted({round(x * 2, 2) for x in spinduliai if abs(x - r) <= max(2, r * 0.3) and abs(x - r) > TOL_R})
            p = tr(f"Trūksta apskritimo ø{r * 2:g}", f"Missing circle ø{r * 2:g}") + (tr(f" ({rasta} iš {kiek})", f" ({rasta} of {kiek})") if kiek > 1 else "") + "."
            if any(abs(x - 2 * r) <= TOL_R for x in spinduliai):
                p += tr(f" Radau apskritimą su spinduliu {r * 2:g} - tai skersmuo! CIRCLE prašo spindulio: įvesk {r:g} (arba spausk D ir įvesk {r * 2:g}).", f" Found a circle with radius {r * 2:g} - that's the diameter! CIRCLE asks for the radius: type {r:g} (or press D and type {r * 2:g}).")
            elif artimi:
                p += tr(f" Radau ø{', ø'.join(f'{a:g}' for a in artimi)} - patikrink: CIRCLE prašo spindulio (R = ø / 2).", f" Found ø{', ø'.join(f'{a:g}' for a in artimi)} - check: CIRCLE asks for the radius (R = ø / 2).")
            pastabos.append(p)
    for t, kiek in u.get("tipai", {}).items():
        rasta = tipai.get(t, 0)
        if t == "AcDbLine":
            rasta += tipai.get("AcDbPolyline", 0) * 4          # PLINE/RECTANG kontūras skaičiuojasi kaip kelios linijos
        if t == "AcDbArc":
            rasta += tipai.get("AcDbPolyline", 0) and kiek    # užapvalinta PLINE turi lankus viduje
        if rasta < kiek:
            pastabos.append(tr(f"Per mažai {PAVADINIMAI.get(t, t)}: radau {rasta}, reikia bent {kiek}.", f"Too few {PAVADINIMAI_EN.get(t, t)}: found {rasta}, need at least {kiek}."))
    if "turis" in u:
        tikslas = u["turis"]
        if not turiai:
            pastabos.append(tr("Neradau 3D kūno. Naudok BOX ir CYLINDER, sujunk UNION, skyles išimk SUBTRACT.", "No 3D body found. Use BOX and CYLINDER, join with UNION, cut holes with SUBTRACT."))
        elif not any(abs(v - tikslas) <= tikslas * TOL_V for v in turiai):
            v = max(turiai)
            sk = lambda x: f"{x:,.0f}".replace(",", " ")
            pastabos.append(tr(f"Kūno tūris {sk(v)} mm³, o turi būti ≈ {sk(tikslas)} mm³.", f"The body volume is {sk(v)} mm³ but should be ≈ {sk(tikslas)} mm³."))
            if len(turiai) > 1:
                pastabos.append(tr(f"Brėžinyje yra {len(turiai)} atskiri kūnai - sujunk juos UNION, skyles išimk SUBTRACT.", f"The drawing has {len(turiai)} separate bodies - join them with UNION, cut holes with SUBTRACT."))
            elif v > tikslas:
                pastabos.append(tr("Tūris per didelis - gal dar neišėmei skylių (SUBTRACT)?", "The volume is too large - haven't you cut the holes (SUBTRACT) yet?"))
    return pastabos

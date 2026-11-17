"""
Brėžly praktikos užduotys (0.8): 2D - A4, 3D - A3.

Kiekvienai užduočiai aplanke praktika/ yra:
  <id>.svg / .pdf      - brėžinys peržiūrai ir spausdinimui
  <id>.dxf             - pavyzdys (atsakymas) AutoCAD'ui
  <id>_ruosinys.dxf    - tuščias lapas su rėmeliu ir pagrindiniu įrašu - jame mokinys braižo
Tikrinimas skaito aktyvų brėžinį per AutoCAD COM: apskritimų spindulius, objektų tipus, 3D kūno tūrį.
"""

import math
import os
import shutil
import subprocess
import sys

APLANKAS = os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)), "praktika")

# apskritimai: {spindulys: kiekis}; tipai: {ObjectName: min kiekis}; turis: mm³ (3D kūnas)
UZDUOTYS = {
    "U1_Tarpine":     {"xp": 30, "apskritimai": {20: 1, 5: 4}, "tipai": {"AcDbLine": 4, "AcDbArc": 4}},
    "U2_Flansas":     {"xp": 45, "apskritimai": {60: 1, 25: 1, 6: 6}},
    "U3_Laikiklis":   {"xp": 45, "apskritimai": {6: 1}, "tipai": {"AcDbArc": 3}},
    "U4_Velenas":     {"xp": 50, "tipai": {"AcDbLine": 14, "AcDbHatch": 1}},
    "U5_Projekcijos": {"xp": 60, "apskritimai": {7: 1}, "tipai": {"AcDbLine": 14}},
    "U6_Izometrija":  {"xp": 60, "tipai": {"AcDbLine": 12, "AcDbEllipse": 1}},
    "U7_Schema":      {"xp": 45, "tipai": {"AcDbBlockReference": 4, "AcDbLine": 6}},
    "U8_3D_detale":   {"xp": 80, "turis": 40000 + math.pi * 15 ** 2 * 25 - math.pi * 8 ** 2 * 35 - 4 * math.pi * 4 ** 2 * 10},  # ≈ 48 623
}
PAVADINIMAI = {"AcDbLine": "linijų", "AcDbArc": "lankų", "AcDbHatch": "brūkšniuotės (HATCH)",
               "AcDbEllipse": "elipsių (ELLIPSE → Isocircle)", "AcDbBlockReference": "įterptų blokų (INSERT)"}
TOL_R = 0.05
TOL_V = 0.02


def _uzd(duom):
    uid = str(duom.get("id", ""))
    if uid not in UZDUOTYS:
        raise ValueError("Nežinoma užduotis")
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
        return ["Dabar atidarytas pavyzdys (atsakymas). Spausk „Pradėti“ - atidarysiu tuščią lapą, jame ir braižyk."]
    a = analizuoti(b, kartoti)
    tipai, spinduliai, turiai = a["tipai"], a["spinduliai"], a["turiai"]
    pastabos = []
    for r, kiek in u.get("apskritimai", {}).items():
        rasta = sum(1 for x in spinduliai if abs(x - r) <= TOL_R)
        if rasta < kiek:
            artimi = sorted({round(x * 2, 2) for x in spinduliai if abs(x - r) <= max(2, r * 0.3) and abs(x - r) > TOL_R})
            p = f"Trūksta apskritimo ø{r * 2:g}" + (f" ({rasta} iš {kiek})" if kiek > 1 else "") + "."
            if any(abs(x - 2 * r) <= TOL_R for x in spinduliai):
                p += f" Radau apskritimą su spinduliu {r * 2:g} - tai skersmuo! CIRCLE prašo spindulio: įvesk {r:g} (arba spausk D ir įvesk {r * 2:g})."
            elif artimi:
                p += f" Radau ø{', ø'.join(f'{a:g}' for a in artimi)} - patikrink: CIRCLE prašo spindulio (R = ø / 2)."
            pastabos.append(p)
    for t, kiek in u.get("tipai", {}).items():
        rasta = tipai.get(t, 0)
        if t == "AcDbLine":
            rasta += tipai.get("AcDbPolyline", 0) * 4          # PLINE/RECTANG kontūras skaičiuojasi kaip kelios linijos
        if t == "AcDbArc":
            rasta += tipai.get("AcDbPolyline", 0) and kiek    # užapvalinta PLINE turi lankus viduje
        if rasta < kiek:
            pastabos.append(f"Per mažai {PAVADINIMAI.get(t, t)}: radau {rasta}, reikia bent {kiek}.")
    if "turis" in u:
        tikslas = u["turis"]
        if not turiai:
            pastabos.append("Neradau 3D kūno. Naudok BOX ir CYLINDER, sujunk UNION, skyles išimk SUBTRACT.")
        elif not any(abs(v - tikslas) <= tikslas * TOL_V for v in turiai):
            v = max(turiai)
            sk = lambda x: f"{x:,.0f}".replace(",", " ")
            pastabos.append(f"Kūno tūris {sk(v)} mm³, o turi būti ≈ {sk(tikslas)} mm³.")
            if len(turiai) > 1:
                pastabos.append(f"Brėžinyje yra {len(turiai)} atskiri kūnai - sujunk juos UNION, skyles išimk SUBTRACT.")
            elif v > tikslas:
                pastabos.append("Tūris per didelis - gal dar neišėmei skylių (SUBTRACT)?")
    return pastabos

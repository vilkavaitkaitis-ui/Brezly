"""
Brėžly pamokos: žingsniai, ką daryti AutoCAD'e, užuominos, tikrinimas ir demonstracijos.

Tikrinimas skaito tavo brėžinį (MODEL erdvę) per AutoCAD COM:
3D kūnų ribas (GetBoundingBox), tūrį (Volume) ir sluoksnį, sluoksnių savybes.
"""

import json
import math
import os
import sys
import time

try:
    import pythoncom
    import win32com.client
except ImportError:         # ne Windows: sąsają ir tikrinimą galima kurti bei testuoti be AutoCAD
    pythoncom = win32com = None

import branduolys as A
from vertimas import tr

TOL = 0.6          # mm - leidžiama paklaida koordinatėms
TOL_V = 0.015      # 1.5 % - leidžiama tūrio paklaida

# Tikslūs tūriai (apskaičiuoti iš anksto)
V_DEZE = 100 * 60 * 20
V_SUJUNGTA = V_DEZE + math.pi * 20 ** 2 * 40                  # 170265.5
V_SU_SKYLE = V_SUJUNGTA - 3 * math.sqrt(3) / 2 * 10 ** 2 * 60   # 154677.0
V_GALUTINIS = 158568.8                                        # + 2 briaunos be persidengimo su cilindru
# Ketvirtinė išpjova (pamoka „Pjūviai“): atimamas ketvirtis x 50..100, y 0..30, z 0..60 =
#   dėžės dalis 30000 + cilindro ketvirtis π·20²·40/4 + pusė briaunos už cilindro 1945.9/2 - kiaurymės ketvirtis
V_ISPJOVA = 118926.6


# ------------------------------------------------------------------ brėžinio skaitymas
def kunai(b):
    """Visi 3D kūnai MODEL erdvėje: [{obj, min, max, turis, sluoksnis}]"""
    ms = b.ms
    rez = []
    for i in range(A.kartoti(lambda: ms.Count)):
        try:
            ent = A.kartoti(lambda: ms.Item(i))
            if ent.ObjectName != "AcDb3dSolid":
                continue
            mn, mx = ent.GetBoundingBox()
            try:
                turis = float(ent.Volume)
            except Exception:
                turis = None
            rez.append({"obj": ent, "min": tuple(mn), "max": tuple(mx), "turis": turis,
                        "sluoksnis": getattr(ent, "Layer", "")})
        except Exception:
            continue
    return rez


def ribos_atitinka(k, mn, mx, tol=TOL):
    return all(abs(a - b) <= tol for a, b in zip(k["min"] + k["max"], tuple(mn) + tuple(mx)))


def rasti(ks, mn, mx, tol=TOL):
    for k in ks:
        if ribos_atitinka(k, mn, mx, tol):
            return k
    return None


def tf(v):
    return f"{v:g}"


def ribos_tekstas(k):
    (x0, y0, z0), (x1, y1, z1) = k["min"], k["max"]
    nuo = f"({tf(round(x0,1))}, {tf(round(y0,1))}, {tf(round(z0,1))})"
    iki = f"({tf(round(x1,1))}, {tf(round(y1,1))}, {tf(round(z1,1))})"
    return tr(f"nuo {nuo} iki {iki}", f"from {nuo} to {iki}")


def turis_tinka(k, tikslas):
    return k["turis"] is not None and abs(k["turis"] - tikslas) <= tikslas * TOL_V


def artimiausias(ks, mn, mx):
    """Kūnas, kurio ribos arčiausiai norimų - kad galėtume pasakyti, kas ne taip."""
    if not ks:
        return None
    return min(ks, key=lambda k: sum(abs(a - b) for a, b in zip(k["min"] + k["max"], tuple(mn) + tuple(mx))))


def kas_ne_taip(k, mn, mx):
    """Žmogiškas paaiškinimas, kuo skiriasi kūno ribos."""
    pastabos = []
    vardai = ("X", "Y", "Z")
    dydis = [k["max"][i] - k["min"][i] for i in range(3)]
    norimas = [mx[i] - mn[i] for i in range(3)]
    for i in range(3):
        if abs(dydis[i] - norimas[i]) > TOL:
            pastabos.append(tr(f"dydis pagal {vardai[i]} yra {tf(round(dydis[i],1))}, o turi būti {tf(norimas[i])}", f"size along {vardai[i]} is {tf(round(dydis[i],1))} but should be {tf(norimas[i])}"))
    if not pastabos:
        for i in range(3):
            if abs(k["min"][i] - mn[i]) > TOL:
                pastabos.append(tr(f"pradžia pagal {vardai[i]} yra {tf(round(k['min'][i],1))}, o turi būti {tf(mn[i])}", f"start along {vardai[i]} is {tf(round(k['min'][i],1))} but should be {tf(mn[i])}"))
    return "; ".join(pastabos) or tr("ribos beveik sutampa", "the limits almost match")


# ------------------------------------------------------------------ tikrinimai
def t_sluoksniai(b):
    doc = b.doc
    reikia = {"KONTURAS": 7, "ASYS": 1, "MATMENYS": 3}
    klaidos = []
    for vardas, spalva in reikia.items():
        try:
            sl = doc.Layers.Item(vardas)
        except Exception:
            klaidos.append(tr(f"Nerandu sluoksnio {vardas}.", f"Layer {vardas} not found."))
            continue
        try:
            if int(sl.Color) != spalva:
                klaidos.append(tr(f"Sluoksnio {vardas} spalva turi būti {spalva}.", f"Layer {vardas} must have colour {spalva}."))
        except Exception:
            pass
    try:
        if not klaidos and doc.Layers.Item("ASYS").Linetype.upper() != "CENTER":
            klaidos.append(tr("Sluoksnio ASYS linijos tipas turi būti CENTER (Load... → CENTER).", "Layer ASYS must use the CENTER linetype (Load... → CENTER)."))
    except Exception:
        pass
    try:
        if not klaidos and doc.ActiveLayer.Name.upper() != "KONTURAS":
            klaidos.append(tr("Padaryk KONTURAS aktyviu (dukart spustelėk jį - atsiras žalia varnelė).", "Make KONTURAS current (double-click it - a green tick appears)."))
    except Exception:
        pass
    return klaidos


def t_deze(b):
    ks = kunai(b)
    if not ks:
        return [tr("Brėžinyje nerandu nė vieno 3D kūno. Ar tikrai baigei BOX komandą (aukštis + Enter)?", "There are no 3D bodies in the drawing. Did you finish the BOX command (height + Enter)?")]
    k = rasti(ks, (0, 0, 0), (100, 60, 20))
    if not k:
        a = artimiausias(ks, (0, 0, 0), (100, 60, 20))
        return [tr(f"Radau dėžę {ribos_tekstas(a)}: {kas_ne_taip(a, (0,0,0), (100,60,20))}.", f"Found a box {ribos_tekstas(a)}: {kas_ne_taip(a, (0,0,0), (100,60,20))}."),
                tr("Patarimas: ištrink ją (ERASE) ir bandyk iš naujo, koordinates rašyk su kableliais: 0,0,0", "Tip: delete it (ERASE) and try again, type coordinates with commas: 0,0,0")]
    if k["sluoksnis"].upper() != "KONTURAS":
        return [tr(f"Dėžė nubraižyta sluoksnyje „{k['sluoksnis']}“, o turi būti KONTURAS. "
                "Pažymėk ją ir viršuje sluoksnių sąraše pasirink KONTURAS.", f"The box is on layer „{k['sluoksnis']}“ but should be on KONTURAS. Select it and choose KONTURAS in the layer list at the top.")]
    return []


def t_cilindras(b):
    ks = kunai(b)
    tikslas = ((30, 10, 20), (70, 50, 60))
    if rasti(ks, *tikslas):
        return []
    kiti = [k for k in ks if not ribos_atitinka(k, (0, 0, 0), (100, 60, 20))]
    if not kiti:
        return [tr("Nerandu cilindro. Ar įvedei CYLINDER ir visus tris atsakymus (centras, spindulys, aukštis)?", "No cylinder found. Did you type CYLINDER and all three answers (centre, radius, height)?")]
    a = artimiausias(kiti, *tikslas)
    return [tr(f"Radau kūną {ribos_tekstas(a)}: {kas_ne_taip(a, *tikslas)}.", f"Found a body {ribos_tekstas(a)}: {kas_ne_taip(a, *tikslas)}."),
            tr("Cilindro centras turi būti ant dėžės viršaus: 50,30,20 (z = 20!).", "The cylinder centre must be on top of the box: 50,30,20 (z = 20!).")]


def t_sujungta(b):
    ks = kunai(b)
    if len(ks) > 1:
        return [tr(f"Brėžinyje yra {len(ks)} atskiri kūnai - jie dar nesujungti. "
                "UNION → pažymėk dėžę IR cilindrą → Enter.", f"The drawing has {len(ks)} separate bodies - not joined yet. UNION → select the box AND the cylinder → Enter.")]
    if not ks:
        return [tr("Nerandu kūnų - gal netyčia ištrynei? Spausk „Parodyk man“ ankstesniuose žingsniuose.", "No bodies found - deleted by accident? Click „Show me“ in the previous steps.")]
    k = ks[0]
    if not ribos_atitinka(k, (0, 0, 0), (100, 60, 60)) or not turis_tinka(k, V_SUJUNGTA):
        return [tr(f"Sujungtas kūnas {ribos_tekstas(k)} - formos neatitinka. Patikrink ankstesnius žingsnius.", f"The joined body {ribos_tekstas(k)} - the shape doesn't match. Check the previous steps.")]
    return []


def t_prizme(b):
    ks = kunai(b)
    if len(ks) < 2:
        return [tr("Nerandu šešiakampės prizmės. POLYGON nubraižo tik plokščią šešiakampį - "
                "jį dar reikia ištempti EXTRUDE komanda (aukštis 60).", "No hexagonal prism found. POLYGON only draws a flat hexagon - you still need to EXTRUDE it (height 60).")]
    for k in ks:
        dx, dy = k["max"][0] - k["min"][0], k["max"][1] - k["min"][1]
        cx, cy = (k["max"][0] + k["min"][0]) / 2, (k["max"][1] + k["min"][1]) / 2
        if abs(cx - 50) < 1 and abs(cy - 30) < 1 and sorted([round(dx, 1), round(dy, 1)]) in ([17.3, 20.0], [17.4, 20.0]):
            if abs(k["min"][2]) > TOL or abs(k["max"][2] - 60) > TOL:
                return [tr(f"Prizmė yra, bet jos aukštis nuo {tf(round(k['min'][2],1))} iki {tf(round(k['max'][2],1))}. "
                        "Šešiakampį braižyk ant z = 0 ir ištempk 60 aukštyn.", f"The prism is there, but its height goes from {tf(round(k['min'][2],1))} to {tf(round(k['max'][2],1))}. Draw the hexagon at z = 0 and extrude it 60 up.")]
            return []
    mazi = [k for k in ks if k["max"][0] - k["min"][0] < 50]
    if mazi:
        k = mazi[0]
        return [tr(f"Radau kūną {ribos_tekstas(k)}. Šešiakampio centras turi būti 50,30, "
                "o „Inscribed in circle“ spindulys - 10 (plotis 20 × 17,3).", f"Found a body {ribos_tekstas(k)}. The hexagon centre must be 50,30 and the „Inscribed in circle“ radius 10 (width 20 × 17.3).")]
    return [tr("Nerandu šešiakampės prizmės ties centru 50,30.", "No hexagonal prism found at the centre 50,30.")]


def t_atimta(b):
    ks = kunai(b)
    if len(ks) > 1:
        return [tr("Vis dar yra atskiri kūnai. SUBTRACT: pirma pažymėk DETALĘ → Enter, "
                "tada pažymėk PRIZMĘ (ką išpjauti) → Enter.", "There are still separate bodies. SUBTRACT: select the PART first → Enter, then the PRISM (what to cut out) → Enter.")]
    if not ks:
        return [tr("Nerandu kūnų.", "No bodies found.")]
    k = ks[0]
    if turis_tinka(k, V_SUJUNGTA - 0) and not turis_tinka(k, V_SU_SKYLE):
        return [tr("Tūris nepasikeitė - gal sujungei (UNION) vietoj atėmimo (SUBTRACT)? Atšauk: U.", "The volume didn't change - did you join (UNION) instead of subtracting (SUBTRACT)? Undo: U.")]
    if not turis_tinka(k, V_SU_SKYLE):
        return [tr(f"Detalės tūris {tf(round(k['turis'] or 0))} mm³, tikėtasi apie {tf(round(V_SU_SKYLE))} mm³. "
                "Patikrink šešiakampį (spindulys 10, aukštis 60).", f"The part volume is {tf(round(k['turis'] or 0))} mm³, expected about {tf(round(V_SU_SKYLE))} mm³. Check the hexagon (radius 10, height 60).")]
    return []


def t_pleistas(b):
    ks = kunai(b)
    tikslas = ((65, 26, 20), (90, 34, 50))
    if rasti(ks, *tikslas):
        return []
    kiti = [k for k in ks if k["max"][0] - k["min"][0] < 60]
    if not kiti:
        return [tr("Nerandu standumo briaunos. WEDGE: pirmas kampas 65,26,20, antras 90,34, aukštis 30.", "No stiffening rib found. WEDGE: first corner 65,26,20, second 90,34, height 30.")]
    a = artimiausias(kiti, *tikslas)
    return [tr(f"Radau kūną {ribos_tekstas(a)}: {kas_ne_taip(a, *tikslas)}.", f"Found a body {ribos_tekstas(a)}: {kas_ne_taip(a, *tikslas)}.")]


def t_veidrodis(b):
    ks = kunai(b)
    desine = rasti(ks, (65, 26, 20), (90, 34, 50))
    kaire = rasti(ks, (10, 26, 20), (35, 34, 50))
    if not desine:
        return [tr("Dingo dešinioji briauna - MIRROR3D klausime „Delete source objects?“ reikėjo atsakyti No.", "The right rib disappeared - MIRROR3D „Delete source objects?“ needed the answer No.")]
    if not kaire:
        return [tr("Nerandu kairiosios briaunos (x nuo 10 iki 35). MIRROR3D plokštuma: YZ, taškas 50,30,0.", "No left rib found (x from 10 to 35). MIRROR3D plane: YZ, point 50,30,0.")]
    return []


def t_galutinis(b):
    ks = kunai(b)
    if len(ks) > 1:
        return [tr(f"Dar yra {len(ks)} atskiri kūnai. UNION → pažymėk viską (galima rėmeliu) → Enter.", f"There are still {len(ks)} separate bodies. UNION → select everything (a window is fine) → Enter.")]
    if not ks:
        return [tr("Nerandu kūnų.", "No bodies found.")]
    k = ks[0]
    if not ribos_atitinka(k, (0, 0, 0), (100, 60, 60)):
        return [tr(f"Detalė {ribos_tekstas(k)} - turi būti nuo (0,0,0) iki (100,60,60).", f"The part {ribos_tekstas(k)} - it must go from (0,0,0) to (100,60,60).")]
    if not turis_tinka(k, V_GALUTINIS):
        return [tr(f"Tūris {tf(round(k['turis'] or 0))} mm³, tikėtasi apie {tf(round(V_GALUTINIS))} mm³.", f"Volume {tf(round(k['turis'] or 0))} mm³, expected about {tf(round(V_GALUTINIS))} mm³.")]
    return []


# ------------------------------------------------------------------ demonstracijos ("Parodyk man")
def d_sluoksniai(b):
    b.vykdyti_saugiai("sluoksniai")


def d_deze(b):
    b.kunas = None
    b.vykdyti_saugiai("deze 0 0 0 100 60 20")


def d_cilindras(b):
    b.ms.AddCylinder(A.taskas(50, 30, 40), 20, 40)


def _sujungti_visus(b):
    ks = sorted(kunai(b), key=lambda k: -(k["turis"] or 0))
    if not ks:
        return
    pagr = ks[0]["obj"]
    for k in ks[1:]:
        pagr.Boolean(0, k["obj"])
    b.kunas = pagr


def d_sujungti(b):
    _sujungti_visus(b)


def d_prizme(b):
    b.sukurti_3d("sesiakampis", ["50", "30", "0", str(10 * math.sqrt(3)), "60"], "sesiakampis")


def d_atimti(b):
    ks = kunai(b)
    pagr = max(ks, key=lambda k: k["turis"] or 0)
    for k in ks:
        if k is not pagr:
            pagr["obj"].Boolean(2, k["obj"])
    b.kunas = pagr["obj"]


def d_pleistas(b):
    b.sukurti_3d("pleistas", ["65", "26", "20", "25", "8", "30", "-x"], "pleistas")


def d_veidrodis(b):
    k = rasti(kunai(b), (65, 26, 20), (90, 34, 50))
    if k:
        k["obj"].Mirror3D(A.taskas(50, 0, 0), A.taskas(50, 1, 0), A.taskas(50, 0, 1))


def d_galutinis(b):
    _sujungti_visus(b)
    b.vykdyti_saugiai("vaizdas3d")


# =====================================================================
#  PAMOKOS (tvarka - pamokos.json): failas, 2D, šriftai, matmenys, lapas, schema
# =====================================================================


def _pl(talpa, taskai, uzdara=True):
    """Lengva polilinija iš [(x,y), ...]."""
    koord = tuple(float(v) for p in taskai for v in p)
    pl = talpa.AddLightWeightPolyline(win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, koord))
    pl.Closed = uzdara
    return pl


def objektai(talpa):
    """Visi talpos (ModelSpace, lapo Block) objektai: [{obj, tipas, min, max, sluoksnis}]"""
    rez = []
    try:
        n = A.kartoti(lambda: talpa.Count)
    except Exception:
        return rez
    for i in range(n):
        try:
            o = A.kartoti(lambda: talpa.Item(i))
            try:
                mn, mx = o.GetBoundingBox()
            except Exception:
                mn, mx = (0, 0, 0), (0, 0, 0)
            rez.append({"obj": o, "tipas": o.ObjectName, "min": tuple(mn), "max": tuple(mx),
                        "sluoksnis": getattr(o, "Layer", "")})
        except Exception:
            continue
    return rez


def artima(a, b, tol=TOL):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def staciakampis(objs, x0, y0, x1, y1, tol=1.0):
    """Ar yra polilinija (ar 4 linijos) su tokiomis ribomis."""
    for o in objs:
        if o["tipas"] == "AcDbPolyline" and artima(o["min"][:2] + o["max"][:2], (x0, y0, x1, y1), tol):
            return o
    linijos = [o for o in objs if o["tipas"] == "AcDbLine"
               and x0 - tol <= o["min"][0] and o["max"][0] <= x1 + tol and y0 - tol <= o["min"][1] and o["max"][1] <= y1 + tol]
    if len(linijos) >= 4:
        mn = (min(o["min"][0] for o in linijos), min(o["min"][1] for o in linijos))
        mx = (max(o["max"][0] for o in linijos), max(o["max"][1] for o in linijos))
        if artima(mn + mx, (x0, y0, x1, y1), tol):
            return linijos[0]
    return None


def apskritimai(objs, r=None, tol=0.3):
    rez = []
    for o in objs:
        if o["tipas"] == "AcDbCircle":
            try:
                c, rr = tuple(o["obj"].Center), float(o["obj"].Radius)
            except Exception:
                continue
            if r is None or abs(rr - r) <= tol:
                rez.append({**o, "c": c, "r": rr})
    return rez


def tekstai(objs):
    rez = []
    for o in objs:
        if o["tipas"] in ("AcDbText", "AcDbMText"):
            try:
                rez.append({**o, "txt": o["obj"].TextString, "h": float(o["obj"].Height),
                            "stilius": o["obj"].StyleName, "p": tuple(o["obj"].InsertionPoint)})
            except Exception:
                continue
    return rez


def a3_lapas(b):
    doc = b.doc
    for i in range(A.kartoti(lambda: doc.Layouts.Count)):
        try:
            L = doc.Layouts.Item(i)
            if L.ModelType:
                continue
            if "A3" in (L.CanonicalMediaName or "").upper() or L.Name.upper().startswith("A3"):
                return L
        except Exception:
            continue
    return None


def kintamasis(b, vardas):
    try:
        return b.doc.GetVariable(vardas)
    except Exception:
        return None


def mano_aplankas():
    k = os.path.join(os.path.expanduser("~"), "Documents", "Brėžly")
    os.makedirs(k, exist_ok=True)
    return k


def nauji_failai(aplankai, ext, per_s=7200):
    riba = time.time() - per_s
    for ap in aplankai:
        if not ap or not os.path.isdir(ap):
            continue
        for f in os.listdir(ap):
            if f.lower().endswith(ext) and os.path.getmtime(os.path.join(ap, f)) >= riba:
                return f
    return None


# ------------------------------------------------------------- 1. FAILAS
def t_naujas(b):
    m, u = kintamasis(b, "MEASUREMENT"), kintamasis(b, "INSUNITS")
    if m is None:
        return [tr("Nepavyko perskaityti brėžinio nustatymų - ar atidarytas brėžinys?", "Couldn't read the drawing settings - is a drawing open?")]
    if int(m) != 1:
        return [tr("Šis brėžinys sukurtas iš imperinio (colių) šablono. Uždaryk jį ir sukurk naują iš acadiso.dwt.", "This drawing was made from an imperial (inch) template. Close it and create a new one from acadiso.dwt.")]
    if int(u) != 4:
        return [tr(f"Brėžinio vienetai ne milimetrai (INSUNITS = {u}). Sukurk naują iš acadiso.dwt.", f"The drawing units are not millimetres (INSUNITS = {u}). Create a new one from acadiso.dwt.")]
    return []


def d_naujas(b):
    A.naujas_brezinys(b.acad, "acadiso.dwt")
    b.palaukti()
    b.kunas = None


def t_vienetai(b):
    lu, pr, u = kintamasis(b, "LUNITS"), kintamasis(b, "LUPREC"), kintamasis(b, "INSUNITS")
    kl = []
    if lu is not None and int(lu) != 2:
        kl.append(tr("Length Type turi būti Decimal (dešimtainiai).", "Length Type must be Decimal."))
    if u is not None and int(u) != 4:
        kl.append(tr("Insertion scale turi būti Millimeters.", "Insertion scale must be Millimeters."))
    if pr is not None and int(pr) > 2:
        kl.append(tr(f"Tikslumas dabar {pr} skaitmenys po kablelio - brėžiniams užtenka 0 arba 0.0.", f"Precision is now {pr} decimal places - 0 or 0.0 is enough for drawings."))
    return kl


def d_vienetai(b):
    for k, v in (("LUNITS", 2), ("INSUNITS", 4), ("LUPREC", 0)):
        b.doc.SetVariable(k, v)


def t_issaugota(b):
    doc = b.doc
    kelias = (doc.FullName or "")
    if not kelias:
        return [tr("Brėžinys dar neišsaugotas. Ctrl+Shift+S (SAVEAS) → įrašyk vardą → Save.", "The drawing isn't saved yet. Ctrl+Shift+S (SAVEAS) → type a name → Save.")]
    if not kelias.lower().endswith(".dwg"):
        return [tr(f"Brėžinys išsaugotas kaip {os.path.splitext(kelias)[1]}, o reikia .dwg.", f"The drawing is saved as {os.path.splitext(kelias)[1]}, but it should be .dwg.")]
    if "drawing" in os.path.basename(kelias).lower():
        return [tr("Duok failui prasmingą vardą, pvz. Pirmasis_brezinys.dwg, o ne Drawing1.", "Give the file a meaningful name, e.g. My_first_part.dwg, not Drawing1.")]
    return []


def d_issaugoti(b):
    b.issaugoti(os.path.join(mano_aplankas(), "Pirmasis_brezinys"), "dwg")


def t_pdf(b):
    ap = [getattr(b.doc, "Path", ""), mano_aplankas()]
    if nauji_failai(ap, ".pdf"):
        return []
    return [tr("Neradau naujo PDF failo šalia brėžinio. PLOT → Printer: DWG To PDF.pc3 → OK → išsaugok.", "No new PDF file next to the drawing. PLOT → Printer: DWG To PDF.pc3 → OK → save.")]


def d_pdf(b):
    b.issaugoti(os.path.join(mano_aplankas(), "Pirmasis_brezinys"), "pdf")


# ------------------------------------------------------------- KAMPINIS ĮRAŠAS (pirmas brėžinys, Model)
# Koordinatės tos pačios kaip A3 lape (230,5 - 415,45): paskutinėje pamokoje lentelė su COPYBASE /
# PASTECLIP 0,0 atsiduria rėmelio kampe.
KI_X0, KI_Y0, KI_X1, KI_Y1 = 230, 5, 415, 45
KI_LINIJOS = ((295, 5, 295, 45), (230, 15, 295, 15), (230, 25, 295, 25), (230, 35, 295, 35),
              (295, 20, 415, 20), (335, 5, 335, 20), (375, 5, 375, 20))


def _ki_vidaus_linijos(objs, tol=1.0):
    """Linijos lentelės viduje (ne ant išorinio kontūro)."""
    rez = []
    for o in objs:
        if o["tipas"] != "AcDbLine":
            continue
        (x0, y0), (x1, y1) = o["min"][:2], o["max"][:2]
        if not (KI_X0 - tol <= x0 and x1 <= KI_X1 + tol and KI_Y0 - tol <= y0 and y1 <= KI_Y1 + tol):
            continue
        ant_krasto = ((abs(y0 - y1) <= tol and (abs(y0 - KI_Y0) <= tol or abs(y0 - KI_Y1) <= tol))
                      or (abs(x0 - x1) <= tol and (abs(x0 - KI_X0) <= tol or abs(x0 - KI_X1) <= tol)))
        if not ant_krasto:
            rez.append(o)
    return rez


def t_ki_konturas(b):
    if not staciakampis(objektai(b.ms), KI_X0, KI_Y0, KI_X1, KI_Y1):
        return [tr("Neradau lentelės kontūro. Model erdvėje: RECTANG → 230,5 → 415,45 (185 × 40).",
                   "No table outline found. In Model space: RECTANG → 230,5 → 415,45 (185 × 40).")]
    return []


def d_ki_konturas(b):
    _pl(b.ms, [(KI_X0, KI_Y0), (KI_X1, KI_Y0), (KI_X1, KI_Y1), (KI_X0, KI_Y1)])


def t_ki_linijos(b):
    objs = objektai(b.ms)
    if not staciakampis(objs, KI_X0, KI_Y0, KI_X1, KI_Y1):
        return [tr("Pirma nubraižyk lentelės kontūrą (ankstesnis žingsnis).", "Draw the table outline first (previous step).")]
    vid = _ki_vidaus_linijos(objs)
    skirtukas = any(abs(o["min"][0] - 295) <= 1 and abs(o["max"][0] - 295) <= 1 and o["min"][1] <= KI_Y0 + 1
                    and o["max"][1] >= KI_Y1 - 1 for o in vid)
    if not skirtukas:
        return [tr("Trūksta vertikalios skiriamosios linijos: LINE → 295,5 → 295,45.",
                   "The vertical divider is missing: LINE → 295,5 → 295,45.")]
    if len(vid) < 4:
        return [tr(f"Lentelės viduje radau {len(vid)} linijas(-ų), reikia bent 4 (pagal pavyzdį - 7).",
                   f"Found {len(vid)} line(s) inside the table, need at least 4 (the example has 7).")]
    return []


def d_ki_linijos(b):
    for (x0, y0, x1, y1) in KI_LINIJOS:
        b.ms.AddLine(A.taskas(x0, y0), A.taskas(x1, y1))


def t_ki_tekstas(b):
    viduj = [t for t in tekstai(objektai(b.ms))
             if KI_X0 - 1 <= t["p"][0] <= KI_X1 + 1 and KI_Y0 - 1 <= t["p"][1] <= KI_Y1 + 1]
    if len(viduj) < 2:
        return [tr(f"Lentelėje radau {len(viduj)} tekstą(-us). Įrašyk bent darbo pavadinimą ir savo vardą (TEXT).",
                   f"Found {len(viduj)} text(s) in the table. Write at least the drawing title and your name (TEXT).")]
    return []


def d_ki_tekstas(b):
    b.ms.AddText(tr("Detalė", "Part"), A.taskas(300, 28), 5)
    b.ms.AddText(tr("Braižė", "Drawn"), A.taskas(232, 27), 2.5)
    b.ms.AddText(tr("Vardas Pavardė", "Name Surname"), A.taskas(250, 27), 2.5)


def t_ki_issaugota(b):
    vardas = os.path.basename((getattr(b.doc, "FullName", "") or "").lower())
    if not vardas.endswith(".dwg") or not any(z in vardas for z in ("kampin", "title")):
        return [tr("Išsaugok brėžinį vardu Kampinis_irasas.dwg (SAVEAS) - jo prireiks paskutinėje pamokoje.",
                   "Save the drawing as Title_block.dwg (SAVEAS) - you will need it in the last lesson.")]
    return []


def d_ki_issaugoti(b):
    b.issaugoti(os.path.join(mano_aplankas(), tr("Kampinis_irasas", "Title_block")), "dwg")


# ------------------------------------------------------------- A3 LAPAS (paskutinė pamoka)
def t_a3(b):
    L = a3_lapas(b)
    if not L:
        return [tr("Neradau A3 lapo. LAYOUTWIZARD → vardas A3 → DWG To PDF.pc3 → ISO full bleed A3 (420 x 297) → Landscape → Title block: None → Viewports: None.", "No A3 sheet found. LAYOUTWIZARD → name A3 → DWG To PDF.pc3 → ISO full bleed A3 (420 x 297) → Landscape → Title block: None → Viewports: None.")]
    try:
        if "A3" not in (L.CanonicalMediaName or "").upper():
            return [tr(f"Lapas „{L.Name}“ yra, bet popierius ne A3. Page Setup Manager → Modify → ISO full bleed A3.",
                       f"Sheet „{L.Name}“ exists, but the paper is not A3. Page Setup Manager → Modify → ISO full bleed A3.")]
    except Exception:
        pass
    return []


def d_a3(b):
    doc = b.doc
    try:
        L = doc.Layouts.Item("A3")
    except Exception:
        L = doc.Layouts.Add("A3")
    doc.ActiveLayout = L
    try:
        L.ConfigName = "DWG To PDF.pc3"
        L.RefreshPlotDeviceInfo()
        L.CanonicalMediaName = A.FORMATAI["A3"][2]
    except Exception:
        pass
    ps = doc.PaperSpace
    for i in range(ps.Count - 1, -1, -1):
        try:
            if ps.Item(i).ObjectName == "AcDbViewport":
                ps.Item(i).Delete()
        except Exception:
            pass


def _lapo_objektai(b):
    L = a3_lapas(b)
    return objektai(L.Block) if L else None


def t_remelis(b):
    objs = _lapo_objektai(b)
    if objs is None:
        return [tr("Pirma sukurk A3 lapą (ankstesnis žingsnis).", "Create the A3 sheet first (previous step).")]
    if not staciakampis(objs, 20, 5, 415, 292):
        return [tr("Neradau rėmelio. Lape (ne Model!) įvesk RECTANG → 20,5 → 415,292.", "No border found. On the sheet (not Model!) type RECTANG → 20,5 → 415,292.")]
    return []


def d_remelis(b):
    if not a3_lapas(b):
        d_a3(b)
    L = a3_lapas(b)
    b.doc.ActiveLayout = L
    _pl(L.Block, [(0, 0), (420, 0), (420, 297), (0, 297)])
    _pl(L.Block, [(20, 5), (415, 5), (415, 292), (20, 292)])


def t_kampinis(b):
    objs = _lapo_objektai(b)
    if objs is None:
        return [tr("Pirma sukurk A3 lapą.", "Create the A3 sheet first.")]
    if not staciakampis(objs, 230, 5, 415, 45):
        return [tr("Neradau kampinio įrašo lentelės. RECTANG → 230,5 → 415,45 (185 × 40, apatiniame dešiniame kampe).", "No title block table found. RECTANG → 230,5 → 415,45 (185 × 40, bottom right corner).")]
    return []


def d_kampinis(b):
    if not a3_lapas(b):
        d_a3(b)
    L = a3_lapas(b)
    blk = L.Block
    _pl(blk, [(230, 5), (415, 5), (415, 45), (230, 45)])
    for (x0, y0, x1, y1) in ((295, 5, 295, 45), (230, 15, 295, 15), (230, 25, 295, 25), (230, 35, 295, 35),
                             (295, 20, 415, 20), (335, 5, 335, 20), (375, 5, 375, 20)):
        blk.AddLine(A.taskas(x0, y0), A.taskas(x1, y1))


def t_uzpildyta(b):
    objs = _lapo_objektai(b)
    if objs is None:
        return [tr("Pirma sukurk A3 lapą.", "Create the A3 sheet first.")]
    viduj = [t for t in tekstai(objs) if 229 <= t["p"][0] <= 416 and 4 <= t["p"][1] <= 46]
    if len(viduj) < 2:
        return [tr(f"Kampiniame įraše radau {len(viduj)} tekstą(-us). Įrašyk bent darbo pavadinimą ir savo vardą (TEXT, aukštis 3.5 arba 5).", f"Found {len(viduj)} text(s) in the title block. Write at least the drawing title and your name (TEXT, height 3.5 or 5).")]
    return []


def d_uzpildyti(b):
    L = a3_lapas(b)
    blk = L.Block
    blk.AddText("Detalė", A.taskas(300, 28), 5)
    blk.AddText("Braižė", A.taskas(232, 27), 2.5)
    blk.AddText("Vardas Pavardė", A.taskas(250, 27), 2.5)


# ------------------------------------------------------------- 3. 2D
def t_plokste(b):
    objs = objektai(b.ms)
    o = staciakampis(objs, 0, 0, 100, 60)
    if not o:
        return [tr("Neradau plokštės kontūro. RECTANG → 0,0 → 100,60.", "No plate outline found. RECTANG → 0,0 → 100,60.")]
    if o["sluoksnis"].upper() != "KONTURAS":
        return [tr(f"Kontūras nubraižytas sluoksnyje „{o['sluoksnis']}“, o turi būti KONTURAS.", f"The outline is on layer „{o['sluoksnis']}“ but should be on KONTURAS.")]
    return []


def d_plokste(b):
    try:
        b.doc.ActiveLayer = b.doc.Layers.Item("KONTURAS")
    except Exception:
        b.vykdyti_saugiai("sluoksniai")
        b.doc.ActiveLayer = b.doc.Layers.Item("KONTURAS")
    _pl(b.ms, [(0, 0), (100, 0), (100, 60), (0, 60)])


def t_centras(b):
    for c in apskritimai(objektai(b.ms), 15):
        if artima(c["c"][:2], (50, 30)):
            return []
    kiti = apskritimai(objektai(b.ms))
    if kiti:
        c = kiti[0]
        return [tr(f"Radau apskritimą centre ({c['c'][0]:g}, {c['c'][1]:g}) spinduliu {c['r']:g}. Reikia: centras 50,30, spindulys 15 (ø30).", f"Found a circle at ({c['c'][0]:g}, {c['c'][1]:g}) with radius {c['r']:g}. Needed: centre 50,30, radius 15 (ø30).")]
    return [tr("Neradau apskritimo. CIRCLE → 50,30 → 15.", "No circle found. CIRCLE → 50,30 → 15.")]


def d_centras(b):
    b.ms.AddCircle(A.taskas(50, 30), 15)


def t_skyles(b):
    rasta = [c for c in apskritimai(objektai(b.ms), 5)]
    reikia = [(15, 15), (85, 15), (15, 45), (85, 45)]
    truksta = [p for p in reikia if not any(artima(c["c"][:2], p) for c in rasta)]
    if truksta:
        return [tr("Trūksta skylių ø10 taškuose: ", "Missing ø10 holes at: ") + ", ".join(f"{x},{y}" for x, y in truksta) + tr(". CIRCLE → taškas → 5.", ". CIRCLE → point → 5.")]
    return []


def d_skyles(b):
    for p in [(15, 15), (85, 15), (15, 45), (85, 45)]:
        b.ms.AddCircle(A.taskas(*p), 5)


def t_asys(b):
    linijos = [o for o in objektai(b.ms) if o["tipas"] == "AcDbLine" and o["sluoksnis"].upper() == "ASYS"]
    horiz = any(abs(o["min"][1] - 30) < 1 and abs(o["max"][1] - 30) < 1 and o["max"][0] - o["min"][0] >= 100 for o in linijos)
    vert = any(abs(o["min"][0] - 50) < 1 and abs(o["max"][0] - 50) < 1 and o["max"][1] - o["min"][1] >= 60 for o in linijos)
    kl = []
    if not linijos:
        kl.append(tr("Sluoksnyje ASYS neradau linijų. Pasirink sluoksnį ASYS ir braižyk LINE.", "No lines on layer ASYS. Make ASYS current and draw with LINE."))
    else:
        if not horiz:
            kl.append(tr("Trūksta horizontalios ašies: LINE → -5,30 → 105,30.", "The horizontal centre line is missing: LINE → -5,30 → 105,30."))
        if not vert:
            kl.append(tr("Trūksta vertikalios ašies: LINE → 50,-5 → 50,65.", "The vertical centre line is missing: LINE → 50,-5 → 50,65."))
    return kl


def d_asys(b):
    try:
        sl = b.doc.Layers.Item("ASYS")
    except Exception:
        b.vykdyti_saugiai("sluoksniai")
        sl = b.doc.Layers.Item("ASYS")
    for p1, p2 in (((-5, 30), (105, 30)), ((50, -5), (50, 65))):
        l = b.ms.AddLine(A.taskas(*p1), A.taskas(*p2))
        l.Layer = "ASYS"
    b.doc.ActiveLayer = b.doc.Layers.Item("KONTURAS")


def t_fillet(b):
    o = staciakampis(objektai(b.ms), 0, 0, 100, 60)
    if not o or o["tipas"] != "AcDbPolyline":
        return [tr("Neradau plokštės polilinijos (RECTANG 0,0 → 100,60).", "No plate polyline found (RECTANG 0,0 → 100,60).")]
    pl = o["obj"]
    try:
        n = len(pl.Coordinates) // 2
        lankai = sum(1 for i in range(n) if abs(pl.GetBulge(i)) > 1e-6)
    except Exception:
        return [tr("Nepavyko perskaityti kontūro.", "Couldn't read the outline.")]
    if lankai < 4:
        return [tr(f"Suapvalinti kampai: {lankai} iš 4. FILLET → R (Radius) → 10 → P (Polyline) → spustelėk kontūrą.", f"Rounded corners: {lankai} of 4. FILLET → R (Radius) → 10 → P (Polyline) → click the outline.")]
    return []


def d_fillet(b):
    o = staciakampis(objektai(b.ms), 0, 0, 100, 60)
    if o:
        o["obj"].Delete()
    _sl(b, "KONTURAS")
    r, k = 10, 0.41421356  # tan(22.5°) - 90° lankas
    taskai = [(r, 0), (100 - r, 0), (100, r), (100, 60 - r), (100 - r, 60), (r, 60), (0, 60 - r), (0, r)]
    pl = _pl(b.ms, taskai)
    for i in (1, 3, 5, 7):
        pl.SetBulge(i, k)


# ------------------------------------------------------------- 4. SCHEMA
def t_zenklas(b):
    objs = objektai(b.ms)
    if not staciakampis(objs, 5, -2, 15, 2, tol=0.5):
        return [tr("Neradau rezistoriaus stačiakampio. RECTANG → 5,-2 → 15,2.", "No resistor rectangle found. RECTANG → 5,-2 → 15,2.")]
    lin = [o for o in objs if o["tipas"] == "AcDbLine" and abs(o["min"][1]) < 0.5 and abs(o["max"][1]) < 0.5]
    if len(lin) < 2:
        return [tr("Trūksta išvadų: LINE → 0,0 → 5,0 ir LINE → 15,0 → 20,0.", "The leads are missing: LINE → 0,0 → 5,0 and LINE → 15,0 → 20,0.")]
    return []


def d_zenklas(b):
    _pl(b.ms, [(5, -2), (15, -2), (15, 2), (5, 2)])
    b.ms.AddLine(A.taskas(0, 0), A.taskas(5, 0))
    b.ms.AddLine(A.taskas(15, 0), A.taskas(20, 0))


def _atributai(talpa):
    return {o["obj"].TagString.upper(): o["obj"] for o in objektai(talpa) if o["tipas"] == "AcDbAttributeDefinition"}


def t_attdef(b):
    at = _atributai(b.ms)
    try:
        if "REZISTORIUS" in [b.doc.Blocks.Item(i).Name.upper() for i in range(b.doc.Blocks.Count)]:
            at = at or _atributai(b.doc.Blocks.Item("REZISTORIUS"))
    except Exception:
        pass
    kl = []
    if "POZ" not in at:
        kl.append(tr("Trūksta atributo POZ: ATTDEF → Tag: POZ, Prompt: Pozicinis žymuo, Default: R → taškas 7,4.", "Attribute POZ is missing: ATTDEF → Tag: POZ, Prompt: Reference designator, Default: R → point 7,4."))
    if "NUORODA" not in at:
        kl.append(tr("Trūksta atributo NUORODA: ATTDEF → pažymėk Invisible → Tag: NUORODA → taškas 7,-7.", "Attribute NUORODA is missing: ATTDEF → tick Invisible → Tag: NUORODA → point 7,-7."))
    elif not (getattr(at["NUORODA"], "Invisible", False) or (int(getattr(at["NUORODA"], "Mode", 0)) & 1)):
        kl.append(tr("Atributas NUORODA turi būti nematomas (Invisible).", "Attribute NUORODA must be Invisible."))
    return kl


def d_attdef(b):
    b.ms.AddAttribute(3.5, 0, "Pozicinis žymuo", A.taskas(7, 4), "POZ", "R")
    b.ms.AddAttribute(3.5, 1, "Nuoroda (parametrai)", A.taskas(7, -7), "NUORODA", "")


def t_blokas(b):
    try:
        blk = b.doc.Blocks.Item("REZISTORIUS")
    except Exception:
        return [tr("Neradau bloko REZISTORIUS. BLOCK → Name: REZISTORIUS → Base point 0,0 → Objects: pažymėk ženklą ir atributus → Delete → OK.", "Block REZISTORIUS not found. BLOCK → Name: REZISTORIUS → Base point 0,0 → Objects: select the symbol and the attributes → Delete → OK.")]
    at = _atributai(blk)
    if "POZ" not in at or "NUORODA" not in at:
        return [tr("Blokas REZISTORIUS yra, bet jame trūksta atributų POZ ir NUORODA - pažymėk juos kuriant bloką.", "Block REZISTORIUS exists but lacks the attributes POZ and NUORODA - select them when creating the block.")]
    return []


def d_blokas(b):
    doc = b.doc
    try:
        doc.Blocks.Item("REZISTORIUS")
        return
    except Exception:
        pass
    blk = doc.Blocks.Add(A.taskas(0, 0), "REZISTORIUS")
    _pl(blk, [(5, -2), (15, -2), (15, 2), (5, 2)])
    blk.AddLine(A.taskas(0, 0), A.taskas(5, 0))
    blk.AddLine(A.taskas(15, 0), A.taskas(20, 0))
    blk.AddAttribute(3.5, 0, "Pozicinis žymuo", A.taskas(7, 4), "POZ", "R")
    blk.AddAttribute(3.5, 1, "Nuoroda (parametrai)", A.taskas(7, -7), "NUORODA", "")
    for o in objektai(b.ms):        # ištrinam laisvą ženklą ir atributus (kaip „Delete“ kuriant bloką)
        if -1 <= o["min"][0] <= 21 and o["min"][1] >= -8 and o["max"][1] <= 8 and o["tipas"] != "AcDbBlockReference":
            try:
                o["obj"].Delete()
            except Exception:
                pass


def _rezistoriai(b):
    rez = []
    for o in objektai(b.ms):
        if o["tipas"] == "AcDbBlockReference":
            try:
                if o["obj"].EffectiveName.upper() == "REZISTORIUS":
                    atr = {a.TagString.upper(): a.TextString for a in o["obj"].GetAttributes()}
                    rez.append(atr)
            except Exception:
                continue
    return rez


def t_insert(b):
    r = _rezistoriai(b)
    if len(r) < 3:
        return [tr(f"Schemoje radau {len(r)} rezistorių. INSERT → REZISTORIUS → įstatyk 3 kartus, POZ: R1, R2, R3.", f"Found {len(r)} resistor(s) on the diagram. INSERT → REZISTORIUS → place it 3 times, POZ: R1, R2, R3.")]
    poz = [x.get("POZ", "") for x in r]
    if len(set(poz)) < len(poz) or any(p in ("", "R") for p in poz):
        return [tr(f"Poziciniai žymenys: {', '.join(poz)}. Kiekvienas turi būti skirtingas: R1, R2, R3.", f"Reference designators: {', '.join(poz)}. Each must be different: R1, R2, R3.")]
    return []


def d_insert(b):
    d_blokas(b)
    for i, (x, nuor) in enumerate(((40, "1 kΩ"), (80, "2,2 kΩ"), (120, "4,7 kΩ")), 1):
        ref = b.ms.InsertBlock(A.taskas(x, 100), "REZISTORIUS", 1, 1, 1, 0)
        for a in ref.GetAttributes():
            a.TextString = {"POZ": f"R{i}", "NUORODA": nuor}.get(a.TagString.upper(), a.TextString)


def t_lentele(b):
    for o in objektai(b.ms):
        if o["tipas"] == "AcDbTable":
            try:
                if int(o["obj"].Rows) >= 3:
                    return []
            except Exception:
                return []
    return [tr("Neradau aprašo lentelės. DATAEXTRACTION → naujas → pažymėk blokus → stulpeliai POZ, Name, Count, NUORODA → Insert table.", "No parts list found. DATAEXTRACTION → new → select the blocks → columns POZ, Name, Count, NUORODA → Insert table.")]


def d_lentele(b):
    b._aprasas((150, 60))


# ------------------------------------------------------------- 5. MATMENYS
def t_plokste_yra(b):
    objs = objektai(b.ms)
    if not staciakampis(objs, 0, 0, 100, 60, tol=1.5) or not apskritimai(objs, 15):
        return [tr("Neradau plokštės iš pamokos „2D brėžinys“ (100 × 60 su skyle ø30). Atidaryk tą brėžinį arba spausk „Parodyk man“.", "The plate from the lesson „2D drawing“ (100 × 60 with a ø30 hole) was not found. Open that drawing or click „Show me“.")]
    return []


def d_plokste_yra(b):
    b.vykdyti_saugiai("sluoksniai")
    d_fillet(b)
    d_centras(b)
    d_skyles(b)


def t_dimstyle(b):
    try:
        b.doc.DimStyles.Item("ISO_MATMENYS")
    except Exception:
        return [tr("Neradau matmenų stiliaus ISO_MATMENYS. DIMSTYLE → New → vardas ISO_MATMENYS → Text height 3.5, Arrow size 3.", "Dimension style ISO_MATMENYS not found. DIMSTYLE → New → name ISO_MATMENYS → Text height 3.5, Arrow size 3.")]
    try:
        akt = b.doc.ActiveDimStyle.Name
    except Exception:
        akt = ""
    if akt.upper() != "ISO_MATMENYS":
        return [tr("Stilius yra, bet neaktyvus. DIMSTYLE → pažymėk ISO_MATMENYS → Set Current.", "The style exists but isn't current. DIMSTYLE → select ISO_MATMENYS → Set Current.")]
    h = kintamasis(b, "DIMTXT")
    if h is not None and abs(float(h) - 3.5) > 0.05:
        return [tr(f"Matmenų teksto aukštis {float(h):g}, o turi būti 3.5 (Text → Text height).", f"Dimension text height is {float(h):g} but should be 3.5 (Text → Text height).")]
    return []


def d_dimstyle(b):
    b._sriftai()


def _matmenys(b):
    rez = []
    for o in objektai(b.ms):
        if "Dimension" in o["tipas"]:
            try:
                rez.append({**o, "m": float(o["obj"].Measurement)})
            except Exception:
                continue
    return rez


def _t_matmuo(b, tipas, verte, kaip):
    m = [x for x in _matmenys(b) if tipas in x["tipas"] and abs(x["m"] - verte) < 0.3]
    if not m:
        return [tr(f"Neradau matmens {verte:g}. {kaip}", f"Dimension {verte:g} not found. {kaip}")]
    if m[0]["sluoksnis"].upper() != "MATMENYS":
        return [tr(f"Matmuo {verte:g} yra sluoksnyje „{m[0]['sluoksnis']}“ - perkelk į MATMENYS.", f"Dimension {verte:g} is on layer „{m[0]['sluoksnis']}“ - move it to MATMENYS.")]
    return []


def t_ilgis(b):
    return _t_matmuo(b, "Rotated", 100, tr("Sluoksnis MATMENYS → DIMLINEAR → spustelėk du apatinius kampus → patrauk žemyn.", "Layer MATMENYS → DIMLINEAR → click the two bottom corners → drag down."))


def t_aukstis(b):
    return _t_matmuo(b, "Rotated", 60, tr("DIMLINEAR → du kairiosios kraštinės galai → patrauk kairėn.", "DIMLINEAR → both ends of the left edge → drag left."))


def t_skersmuo(b):
    return _t_matmuo(b, "Diametric", 30, tr("DIMDIAMETER → spustelėk didįjį apskritimą → padėk tekstą.", "DIMDIAMETER → click the large circle → place the text."))


def _sl(b, vardas):
    try:
        b.doc.ActiveLayer = b.doc.Layers.Item(vardas)
    except Exception:
        b.vykdyti_saugiai("sluoksniai")
        b.doc.ActiveLayer = b.doc.Layers.Item(vardas)


def d_ilgis(b):
    _sl(b, "MATMENYS")
    b.ms.AddDimRotated(A.taskas(0, 0), A.taskas(100, 0), A.taskas(50, -15), 0)


def d_aukstis(b):
    _sl(b, "MATMENYS")
    b.ms.AddDimRotated(A.taskas(0, 0), A.taskas(0, 60), A.taskas(-15, 30), math.pi / 2)


def d_skersmuo(b):
    _sl(b, "MATMENYS")
    b.ms.AddDimDiametric(A.taskas(65, 30), A.taskas(35, 30), 15)


# ------------------------------------------------------------- 6. ŠRIFTAI
def t_iso(b):
    try:
        st = b.doc.TextStyles.Item("ISO")
    except Exception:
        return [tr("Neradau teksto stiliaus ISO. STYLE → New → ISO → Font: isocp.shx → Apply.", "Text style ISO not found. STYLE → New → ISO → Font: isocp.shx → Apply.")]
    if "isocp" not in (st.fontFile or "").lower():
        return [tr(f"Stilius ISO naudoja šriftą „{st.fontFile}“, o reikia isocp.shx.", f"Style ISO uses the font „{st.fontFile}“, but it should be isocp.shx.")]
    return []


def t_isolt(b):
    try:
        st = b.doc.TextStyles.Item("ISO_LT")
    except Exception:
        return [tr("Neradau stiliaus ISO_LT. STYLE → New → ISO_LT → Font: ISOCPEUR (su lietuviškomis raidėmis) → Oblique angle 15 → Apply.", "Style ISO_LT not found. STYLE → New → ISO_LT → Font: ISOCPEUR (with Lithuanian letters) → Oblique angle 15 → Apply.")]
    try:
        sriftas = st.GetFont()[0]
    except Exception:
        sriftas = st.fontFile or ""
    if "isocpeur" not in str(sriftas).lower():
        return [tr(f"Stilius ISO_LT naudoja „{sriftas}“, o reikia ISOCPEUR - jis turi ąčęėįšųūž.", f"Style ISO_LT uses „{sriftas}“, but it should be ISOCPEUR - it has ąčęėįšųūž.")]
    if abs(math.degrees(float(st.ObliqueAngle)) - 15) > 1:
        return [tr("Nustatyk pasvirimą: Oblique angle 15 (ISO 3098 B tipas).", "Set the slant: Oblique angle 15 (ISO 3098 type B).")]
    return []


def d_sriftai(b):
    b._sriftai()


def t_tekstas(b):
    lt = "ąčęėįšųūžĄČĘĖĮŠŲŪŽ"
    for t in tekstai(objektai(b.ms)):
        if t["stilius"].upper() == "ISO_LT" and abs(t["h"] - 5) < 0.05 and any(c in t["txt"] for c in lt):
            return []
    tt = [t for t in tekstai(objektai(b.ms)) if t["stilius"].upper() == "ISO_LT"]
    if tt:
        t = tt[0]
        return [tr(f"Radau tekstą „{t['txt']}“ aukščio {t['h']:g}. Reikia aukščio 5 ir lietuviškų raidžių, pvz. „Brėžinys“.", f"Found the text „{t['txt']}“ with height {t['h']:g}. Height 5 and Lithuanian letters are needed, e.g. „Brėžinys“.")]
    return [tr("Neradau teksto stiliumi ISO_LT. Padaryk ISO_LT aktyvų → TEXT → taškas → aukštis 5 → „Brėžinys“.", "No text in style ISO_LT. Make ISO_LT current → TEXT → point → height 5 → „Brėžinys“.")]


def d_tekstas(b):
    t = b.ms.AddText("Brėžinys", A.taskas(0, 80), 5)
    try:
        t.StyleName = "ISO_LT"
    except Exception:
        pass


# =====================================================================
#  3D IR VAIZDAI LAPE: pjūviai, projekcijos iš 3D, aksonometrija
# =====================================================================
DETALE_MIN, DETALE_MAX = (0, 0, 0), (100, 60, 60)
ISPJOVA_MIN, ISPJOVA_MAX = (50, 0, 0), (100, 30, 60)


def _viena_detale(b):
    """(kūnas, pastabos) - pamokos „Pirmoji 3D detalė“ detalė 100 × 60 × 60 (su išpjova ar be)."""
    ks = kunai(b)
    if not ks:
        return None, [tr("Neradau 3D detalės. Atidaryk brėžinį su detale iš pamokos „Pirmoji 3D detalė“ arba spausk „Parodyk man“.", "No 3D part found. Open the drawing with the part from the lesson „First 3D part“ or click „Show me“.")]
    if len(ks) > 1:
        if rasti(ks, ISPJOVA_MIN, ISPJOVA_MAX):
            return None, [tr("Dėžė jau yra, bet dar neatimta: SUBTRACT → pirma detalė, Enter, tada dėžė, Enter.", "The box is there but not subtracted yet: SUBTRACT → the part first, Enter, then the box, Enter.")]
        return None, [tr(f"Brėžinyje {len(ks)} kūnai, o detalė turi būti vienas kūnas. Sujunk UNION.", f"The drawing has {len(ks)} bodies, but the part must be one body. Join them with UNION.")]
    k = ks[0]
    if not ribos_atitinka(k, DETALE_MIN, DETALE_MAX, tol=1.0):
        return None, [tr("Tai ne detalė iš pamokos „Pirmoji 3D detalė“: ", "This is not the part from the lesson „First 3D part“: ") + kas_ne_taip(k, DETALE_MIN, DETALE_MAX) + "."]
    return k, []


def t_detale3d(b):
    k, pastabos = _viena_detale(b)
    if pastabos:
        return pastabos
    if not (turis_tinka(k, V_GALUTINIS) or turis_tinka(k, V_ISPJOVA)):
        return [tr(f"Detalės tūris {tf(round(k['turis'] or 0))} mm³, tikėtasi apie {tf(round(V_GALUTINIS))} mm³. Ar visos detalės dalys sujungtos (UNION)?", f"The part volume is {tf(round(k['turis'] or 0))} mm³, expected about {tf(round(V_GALUTINIS))} mm³. Are all pieces of the part joined (UNION)?")]
    return []


def t_ispjova(b):
    k, pastabos = _viena_detale(b)
    if pastabos:
        return pastabos
    if turis_tinka(k, V_GALUTINIS):
        return [tr("Ketvirtis dar neišpjautas: BOX nuo 50,0,0 iki 100,30, aukštis 60, tada SUBTRACT.", "The quarter isn't cut out yet: BOX from 50,0,0 to 100,30, height 60, then SUBTRACT.")]
    if not turis_tinka(k, V_ISPJOVA):
        return [tr(f"Tūris {tf(round(k['turis'] or 0))} mm³, tikėtasi apie {tf(round(V_ISPJOVA))} mm³. "
                "Patikrink dėžės kampus: 50,0,0 ir 100,30, aukštis 60.", f"Volume {tf(round(k['turis'] or 0))} mm³, expected about {tf(round(V_ISPJOVA))} mm³. Check the box corners: 50,0,0 and 100,30, height 60.")]
    return []


def _lapu_vaizdai(b):
    """{lapo vardas: {"vaizdai": n, "pjuviai": n}} - Model Documentation objektai lapuose
    (AcDbViewBorder - vaizdo rėmelis, AcDbSectionSymbol - pjūvio linija A-A)."""
    rez = {}
    doc = b.doc
    for i in range(A.kartoti(lambda: doc.Layouts.Count)):
        try:
            L = doc.Layouts.Item(i)
            if L.ModelType:
                continue
            tipai = [o["tipas"] for o in objektai(L.Block)]
            rez[L.Name] = {"vaizdai": sum("ViewBorder" in t for t in tipai),
                           "pjuviai": sum("SectionSymbol" in t for t in tipai)}
        except Exception:
            continue
    return rez


def be_model_doc():
    return tr(" Jei AutoCAD nežino komandos - tavo versija be Model Documentation (pvz. LT): žingsnį gali praleisti.",
              " If AutoCAD doesn't know the command, your version has no Model Documentation (e.g. LT): you can skip this step.")


def t_plokstuma(b):
    if any("Section" in o["tipas"] and "Symbol" not in o["tipas"] for o in objektai(b.ms)):
        return []
    return [tr("Neradau pjūvio plokštumos modelyje: SECTIONPLANE → O → Front.", "No section plane in the model: SECTIONPLANE → O → Front.")]


def t_vaizdas(b):
    if sum(v["vaizdai"] for v in _lapu_vaizdai(b).values()) >= 1:
        return []
    return [tr("Lapuose nerandu vaizdų: spustelėk Layout1, VIEWBASE → Model → Front.", "No views on the sheets: click Layout1, VIEWBASE → Model → Front.") + be_model_doc()]


def t_pjuvis(b):
    v = _lapu_vaizdai(b)
    if sum(x["pjuviai"] for x in v.values()) >= 1:
        return []
    if sum(x["vaizdai"] for x in v.values()) == 0:
        return [tr("Pirma reikia pagrindinio vaizdo (ankstesnis žingsnis).", "The base view comes first (previous step).")]
    return [tr("Pjūvio dar nėra: VIEWSECTION → spustelėk vaizdą → Full → du taškai per vidurį → padėk pjūvį.", "No section yet: VIEWSECTION → click the view → Full → two points across the middle → place the section.")]


def _a3_vaizdai(b, kiek, ka):
    L = a3_lapas(b)
    if not L:
        return [tr("Neradau A3 lapo - pirmas šios pamokos žingsnis.", "No A3 sheet found - the first step of this lesson.")]
    n = _lapu_vaizdai(b).get(L.Name, {}).get("vaizdai", 0)
    if n >= kiek:
        return []
    kiti = sum(v["vaizdai"] for k, v in _lapu_vaizdai(b).items() if k != L.Name)
    if n == 0 and kiti:
        return [tr(f"Vaizdai yra kitame lape, o reikia lape „{L.Name}“. Pereik į jį ir pakartok.", f"The views are on another sheet, but they belong on „{L.Name}“. Switch to it and repeat.")]
    return [tr(f"A3 lape vaizdų: {n}, reikia {kiek}. {ka}", f"Views on the A3 sheet: {n}, needed {kiek}. {ka}")]


def t_pr_priekis(b):
    return _a3_vaizdai(b, 1, "VIEWBASE → Model → Front." + be_model_doc())


def t_pr_projekcijos(b):
    return _a3_vaizdai(b, 3, tr("VIEWPROJ → spustelėk vaizdą iš priekio → žemyn → dešinėn → Enter.", "VIEWPROJ → click the front view → down → right → Enter."))


def t_pr_aksonometrija(b):
    return _a3_vaizdai(b, 4, tr("VIEWPROJ → vaizdas iš priekio → patrauk įstrižai → Enter.", "VIEWPROJ → the front view → drag diagonally → Enter."))


# ---- 10. aksonometrija (2D izometrija)
ISO_R = 10
ISO_DIDZ, ISO_MAZ = ISO_R * math.sqrt(1.5), ISO_R * math.sqrt(0.5)       # izoapskritimo pusašės 12.25 ir 7.07
ISO_A = (100.0, 50.0)                                                      # dėžės priekinis apatinis kampas
ISO_CENTRAS = (ISO_A[0] + (60 - 40) * math.cos(math.radians(30)) / 2, ISO_A[1] + 30 + (60 + 40) * 0.5 / 2)   # (108.66, 105)
ISO_BRIAUNOS = ((60, 30), (40, 150), (30, 90))                             # (ilgis, kryptis °) po 3


def _linijos(b):
    rez = []
    for o in objektai(b.ms):
        if o["tipas"] != "AcDbLine":
            continue
        try:
            p, q = tuple(o["obj"].StartPoint), tuple(o["obj"].EndPoint)
        except Exception:
            continue
        ilgis = math.hypot(q[0] - p[0], q[1] - p[1])
        kampas = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 180
        rez.append((ilgis, kampas))
    return rez


def _kampas_artimas(a, b, tol=0.5):
    d = abs(a - b) % 180
    return min(d, 180 - d) <= tol


def t_isodraft(b):
    if str(kintamasis(b, "SNAPSTYL")) in ("1", "1.0"):
        return []
    return [tr("Izometrija neįjungta: ISODRAFT → T (arba SNAP → Style → Isometric).", "Isometric drafting is off: ISODRAFT → T (or SNAP → Style → Isometric).")]


def t_iso_deze(b):
    lin = _linijos(b)
    truksta = []
    for ilgis, kryptis in ISO_BRIAUNOS:
        n = sum(1 for l, k in lin if abs(l - ilgis) <= 0.2 and _kampas_artimas(k, kryptis))
        if n < 3:
            truksta.append(tr(f"{ilgis} mm {kryptis}° kryptimi: {n} iš 3", f"{ilgis} mm at {kryptis}°: {n} of 3"))
    if truksta:
        return [tr("Trūksta briaunų - ", "Missing edges - ") + "; ".join(truksta) + tr(". Rašyk taškus @ilgis<kampas tiksliai kaip komandų eilutėje.", ". Type the points @length<angle exactly as in the command line.")]
    return []


def t_iso_apskritimas(b):
    elipses = []
    for o in objektai(b.ms):
        if o["tipas"] == "AcDbEllipse":
            try:
                c, ax = tuple(o["obj"].Center), tuple(o["obj"].MajorAxis)
                elipses.append((c, float(o["obj"].MajorRadius), float(o["obj"].MinorRadius),
                                math.degrees(math.atan2(ax[1], ax[0])) % 180))
            except Exception:
                continue
    if not elipses:
        if apskritimai(objektai(b.ms), ISO_R):
            return [tr("Nubraižei apskritimą - izometrijoje reikia ELLIPSE → I (Isocircle).", "You drew a circle - in isometric you need ELLIPSE → I (Isocircle).")]
        return [tr("Neradau elipsės: F5 iki <Isoplane Top>, tada ELLIPSE → I → centras → 10.", "No ellipse found: F5 until <Isoplane Top>, then ELLIPSE → I → centre → 10.")]
    tinka = [e for e in elipses if abs(e[1] - ISO_DIDZ) <= 0.15 and abs(e[2] - ISO_MAZ) <= 0.15]
    if not tinka:
        e = elipses[0]
        return [tr(f"Elipsės pusašės {e[1]:.2f} ir {e[2]:.2f}, o spinduliui 10 turi būti {ISO_DIDZ:.2f} ir {ISO_MAZ:.2f}. Ar nubraižei per Isocircle su spinduliu 10?", f"The ellipse semi-axes are {e[1]:.2f} and {e[2]:.2f}, for radius 10 they should be {ISO_DIDZ:.2f} and {ISO_MAZ:.2f}. Did you draw it with Isocircle, radius 10?")]
    virsuje = [e for e in tinka if _kampas_artimas(e[3], 0, 1.0)]
    if not virsuje:
        return [tr("Elipsė ne toje plokštumoje: spausk F5, kol bus <Isoplane Top>, ir nubraižyk iš naujo.", "The ellipse is in the wrong plane: press F5 until <Isoplane Top> and draw it again.")]
    if not any(artima(e[0][:2], ISO_CENTRAS, 1.5) for e in virsuje):
        return [tr(f"Elipsė ne viršaus sienos centre - centras turi būti {ISO_CENTRAS[0]:.2f},{ISO_CENTRAS[1]:.0f}.", f"The ellipse is not in the middle of the top face - the centre must be {ISO_CENTRAS[0]:.2f},{ISO_CENTRAS[1]:.0f}.")]
    return []


def t_iso_matmuo(b):
    for o in objektai(b.ms):
        if o["tipas"] == "AcDbAlignedDimension":
            try:
                if any(abs(float(o["obj"].Measurement) - m) <= 0.1 for m, _ in ISO_BRIAUNOS):
                    return []
            except Exception:
                continue
    return [tr("Neradau lygiagretaus matmens (DIMALIGNED) ant dėžės briaunos - galus pagauk su OSNAP Endpoint.", "No aligned dimension (DIMALIGNED) on a box edge - pick the ends with OSNAP Endpoint.")]


# ---- demonstracijos
def d_detale3d(b):
    """Nubraižo pamokos „Pirmoji 3D detalė“ detalę, jei jos nėra."""
    if kunai(b):
        return
    for f in (d_deze, d_cilindras, d_sujungti, d_prizme, d_atimti, d_pleistas, d_veidrodis, d_galutinis):
        f(b)


def d_ispjova(b):
    d_detale3d(b)
    det = max(kunai(b), key=lambda k: k["turis"] or 0)["obj"]
    deze = b.ms.AddBox(A.taskas(75, 15, 30), 50, 30, 60)
    det.Boolean(2, deze)                       # acSubtraction
    b.kunas = det


def d_isodraft(b):
    b.doc.SetVariable("SNAPSTYL", 1)
    b.doc.SetVariable("SNAPISOPAIR", 1)        # Top


def _iso_taskas(p, ilgis, kampas):
    return (p[0] + ilgis * math.cos(math.radians(kampas)), p[1] + ilgis * math.sin(math.radians(kampas)))


def d_iso_deze(b):
    a = ISO_A
    bb = _iso_taskas(a, 60, 30)
    d = _iso_taskas(a, 40, 150)
    a2, b2, d2 = (a[0], a[1] + 30), (bb[0], bb[1] + 30), (d[0], d[1] + 30)
    c2 = _iso_taskas(b2, 40, 150)
    for p, q in ((a, bb), (a, d), (a, a2), (bb, b2), (d, d2), (a2, b2), (a2, d2), (b2, c2), (d2, c2)):
        b.ms.AddLine(A.taskas(*p), A.taskas(*q))


def d_iso_apskritimas(b):
    b.ms.AddEllipse(A.taskas(*ISO_CENTRAS), A.taskas(ISO_DIDZ, 0), ISO_MAZ / ISO_DIDZ)


def d_iso_matmuo(b):
    a, bb = ISO_A, _iso_taskas(ISO_A, 60, 30)
    b.ms.AddDimAligned(A.taskas(*a), A.taskas(*bb), A.taskas(a[0] + 20, a[1] - 5))


# ------------------------------------------------------------- pamokų turinys: pamokos.json
# Tekstai (žingsniai, užuominos, testai, kortelės) - pamokos.json. Jį naudoja ir programėlė (app/).
# Čia - tik kas tikrina žingsnį ir kas jį parodo AutoCAD'e: žingsnio id -> (tikrinti, demo).
# Naujas žingsnis be įrašo čia veiks, tik nebus tikrinamas ir demonstruojamas.

# ------------------------------------------------------------- bendri 2D pagalbininkai (1.2)
def _galai(o):
    """Linijos galai (x, y) iš StartPoint/EndPoint - įstrižai linijai ribos nepasako krypties."""
    try:
        return tuple(o["obj"].StartPoint)[:2], tuple(o["obj"].EndPoint)[:2]
    except Exception:
        return None


def atkarpos(objs, sluoksnis=None):
    """Tiesios atkarpos: linijos ir polilinijų kraštinės be lankų. [(p, q, objektas)]"""
    rez = []
    for o in objs:
        if sluoksnis and o["sluoksnis"].upper() != sluoksnis:
            continue
        if o["tipas"] == "AcDbLine":
            g = _galai(o)
            if g:
                rez.append((g[0], g[1], o))
        elif o["tipas"] == "AcDbPolyline":
            try:
                k = list(o["obj"].Coordinates)
                uzd = bool(o["obj"].Closed)
            except Exception:
                continue
            v = list(zip(k[0::2], k[1::2]))
            for i in range(len(v) - (0 if uzd else 1)):
                try:
                    bl = float(o["obj"].GetBulge(i))
                except Exception:
                    bl = 0.0
                if abs(bl) < 1e-6:
                    rez.append((v[i], v[(i + 1) % len(v)], o))
    return rez


def yra_atkarpa(seg, p, q, tol=TOL):
    return any((artima(a, p, tol) and artima(c, q, tol)) or (artima(a, q, tol) and artima(c, p, tol)) for a, c, _ in seg)


def lankai(objs, r=None, tol=0.3):
    """Lankai su centru, spinduliu, apimtimi (rad) ir vidurio tašku."""
    rez = []
    for o in objs:
        if o["tipas"] != "AcDbArc":
            continue
        try:
            c, rr = tuple(o["obj"].Center)[:2], float(o["obj"].Radius)
            a0, a1 = float(o["obj"].StartAngle), float(o["obj"].EndAngle)
        except Exception:
            continue
        if r is None or abs(rr - r) <= tol:
            apimtis = (a1 - a0) % (2 * math.pi)
            v = a0 + apimtis / 2
            rez.append({**o, "c": c, "r": rr, "apimtis": apimtis, "vid": (c[0] + rr * math.cos(v), c[1] + rr * math.sin(v))})
    return rez


def _p(t):
    return f"{t[0]:g},{t[1]:g}"


def _objektu_masyvas(objs):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, list(objs))


# ------------------------------------------------------------- TIKSLUS BRAIŽYMAS (OSNAP, OTRACK, POLAR, AREA)
TK_ROMBAS = ((40, 0), (80, 25), (40, 50), (0, 25))          # 80 × 50 stačiakampio kraštinių viduriai
TK_CENTRAS, TK_R = (40, 25), 10
TK_POLAR = ((80, 50), (80 + 40 * math.cos(math.radians(30)), 50 + 40 * math.sin(math.radians(30))))   # (114.64, 70)
TK_PLOTAS = 2000                                              # rombo plotas = 80 · 50 / 2
OSNAP_REIKIA = ((1, "Endpoint"), (2, "Midpoint"), (4, "Center"), (16, "Quadrant"), (32, "Intersection"))


def t_tk_osnap(b):
    m = kintamasis(b, "OSMODE")
    if m is None:
        return [tr("Nepavyko perskaityti pritraukimo nustatymų (OSMODE).", "Couldn't read the object snap settings (OSMODE).")]
    m = int(m)
    if m & 16384:
        return [tr("Objekto pritraukimas išjungtas - spausk F3 (apačioje užsidegs pritraukimo mygtukas).",
                   "Object snap is off - press F3 (the snap button at the bottom lights up).")]
    truksta = [v for bitas, v in OSNAP_REIKIA if not m & bitas]
    if truksta:
        return [tr("Įjunk pritraukimus: ", "Turn on the snaps: ") + ", ".join(truksta)
                + tr(". OSNAP → skirtukas Object Snap → pažymėk varneles → OK.", ". OSNAP → Object Snap tab → tick the boxes → OK.")]
    return []


def d_tk_osnap(b):
    b.doc.SetVariable("OSMODE", 1 | 2 | 4 | 16 | 32)


def t_tk_rombas(b):
    objs = objektai(b.ms)
    if not staciakampis(objs, 0, 0, 80, 50):
        return [tr("Neradau stačiakampio 80 × 50. RECTANG → 0,0 → @80,50.", "No 80 × 50 rectangle found. RECTANG → 0,0 → @80,50.")]
    seg = atkarpos(objs)
    truksta = [(p, q) for p, q in zip(TK_ROMBAS, TK_ROMBAS[1:] + TK_ROMBAS[:1]) if not yra_atkarpa(seg, p, q)]
    if truksta:
        p, q = truksta[0]
        return [tr(f"Trūksta rombo kraštinės {_p(p)} → {_p(q)} (dar {len(truksta)} iš 4). LINE ir spustelėk kraštinių vidurius, kai pasirodo trikampis (Midpoint).",
                   f"A rhombus side is missing: {_p(p)} → {_p(q)} ({len(truksta)} of 4 left). LINE and click the side midpoints when the triangle appears (Midpoint).")]
    return []


def d_tk_rombas(b):
    _pl(b.ms, [(0, 0), (80, 0), (80, 50), (0, 50)])
    for p, q in zip(TK_ROMBAS, TK_ROMBAS[1:] + TK_ROMBAS[:1]):
        b.ms.AddLine(A.taskas(*p), A.taskas(*q))


def t_tk_centras(b):
    objs = objektai(b.ms)
    if any(artima(c["c"][:2], TK_CENTRAS) for c in apskritimai(objs, TK_R)):
        return []
    kiti = apskritimai(objs)
    if kiti:
        c = kiti[-1]
        return [tr(f"Apskritimas yra ({_p(c['c'])}), spindulys {c['r']:g}. Reikia: centras rombo viduryje (40,25), spindulys 10. Su F11 (OTRACK) užvesk žymeklį ant dviejų kraštinių vidurių ir nuvesk į susikirtimą.",
                   f"The circle is at ({_p(c['c'])}), radius {c['r']:g}. Needed: centre in the middle of the rhombus (40,25), radius 10. With F11 (OTRACK) hover over two side midpoints and move to where the tracking lines cross.")]
    return [tr("Neradau apskritimo. CIRCLE → centras rombo viduryje (OTRACK, F11) → 10.", "No circle found. CIRCLE → centre in the middle of the rhombus (OTRACK, F11) → 10.")]


def d_tk_centras(b):
    b.ms.AddCircle(A.taskas(*TK_CENTRAS), TK_R)


def t_tk_polar(b):
    seg = atkarpos(objektai(b.ms))
    if yra_atkarpa(seg, *TK_POLAR):
        return []
    nuo = [(a, c) if artima(a, TK_POLAR[0]) else (c, a) for a, c, _ in seg
           if (artima(a, TK_POLAR[0]) or artima(c, TK_POLAR[0])) and not (artima(a, (80, 0)) or artima(c, (80, 0)) or artima(a, (0, 50)) or artima(c, (0, 50)))]
    if nuo:
        a, c = nuo[-1]
        ilgis = math.dist(a, c)
        kampas = math.degrees(math.atan2(c[1] - a[1], c[0] - a[0]))
        return [tr(f"Linija nuo 80,50 yra {ilgis:.1f} ilgio ir {kampas:.0f}° kampu. Reikia 40 ilgio ir 30°: F10, žymeklį - 30° kryptimi, įvesk 40 → Enter.",
                   f"The line from 80,50 is {ilgis:.1f} long at {kampas:.0f}°. Needed: length 40 at 30°: F10, move the cursor along 30°, type 40 → Enter.")]
    return [tr("Neradau linijos nuo stačiakampio kampo 80,50. LINE → spustelėk kampą (Endpoint) → 30° kryptimi įvesk 40 → Enter.",
               "No line from the rectangle corner 80,50. LINE → click the corner (Endpoint) → along 30° type 40 → Enter.")]


def d_tk_polar(b):
    b.doc.SetVariable("POLARANG", math.radians(30))
    b.ms.AddLine(A.taskas(*TK_POLAR[0]), A.taskas(*TK_POLAR[1]))


def t_tk_plotas(b):
    t = tekstai(objektai(b.ms))
    sk = ["".join(x["txt"].split()).replace(",", ".") for x in t]
    if any(str(TK_PLOTAS) in x for x in sk):
        return []
    if any("4000" in x for x in sk):
        return [tr("4000 - tai viso stačiakampio plotas. Matuok rombą: AREA → spustelėk 4 rombo viršūnes → Enter.",
                   "4000 is the area of the whole rectangle. Measure the rhombus: AREA → click its 4 corners → Enter.")]
    if t:
        return [tr("Tekste nerandu rombo ploto. AREA → 4 rombo viršūnės → Enter - AutoCAD parodys Area = ... Įrašyk tą skaičių.",
                   "I can't find the rhombus area in your text. AREA → the 4 rhombus corners → Enter - AutoCAD shows Area = ... Write that number.")]
    return [tr("Neradau teksto. Išmatuok AREA ir įrašyk TEXT, pvz. S = ... (aukštis 3.5).", "No text found. Measure with AREA and write it with TEXT, e.g. A = ... (height 3.5).")]


def d_tk_plotas(b):
    b.ms.AddText(tr(f"S = {TK_PLOTAS}", f"A = {TK_PLOTAS}"), A.taskas(85, 5), 3.5)


# ------------------------------------------------------------- REDAGAVIMAS (COPY, CHAMFER, TRIM, MIRROR)
RD_PLOKSTE = (0, 0, 120, 80)
RD_NUOSKLEMBOS = ((10, 0), (110, 0), (120, 10), (120, 70), (110, 80), (10, 80), (0, 70), (0, 10))
RD_R = 6
RD_SKYLE = ((25, 40), (55, 40))            # pailga skylė: du pusapskritimiai ir dvi liestinės
RD_KOPIJA = ((65, 40), (95, 40))           # MIRROR per 60 (plokštės vidurį)


def _rd_liestines(xa, xb):
    return (((xa, 40 + RD_R), (xb, 40 + RD_R)), ((xa, 40 - RD_R), (xb, 40 - RD_R)))


def _plokstes_pl(objs):
    for o in objs:
        if o["tipas"] == "AcDbPolyline" and artima(o["min"][:2] + o["max"][:2], RD_PLOKSTE, 1.0):
            return o
    return None


def t_rd_plokste(b):
    objs = objektai(b.ms)
    o = staciakampis(objs, *RD_PLOKSTE) or _plokstes_pl(objs)
    if not o:
        return [tr("Neradau plokštės 120 × 80. RECTANG → 0,0 → @120,80.", "No 120 × 80 plate found. RECTANG → 0,0 → @120,80.")]
    if o["sluoksnis"].upper() != "KONTURAS":
        return [tr(f"Plokštė sluoksnyje „{o['sluoksnis']}“, o turi būti KONTURAS. Pažymėk ją ir sluoksnių sąraše pasirink KONTURAS.",
                   f"The plate is on layer „{o['sluoksnis']}“ but should be on KONTURAS. Select it and pick KONTURAS in the layer list.")]
    return []


def d_rd_plokste(b):
    _sl(b, "KONTURAS")
    _pl(b.ms, [(0, 0), (120, 0), (120, 80), (0, 80)])


def t_rd_chamfer(b):
    o = _plokstes_pl(objektai(b.ms))
    if not o:
        return [tr("Neradau plokštės polilinijos (RECTANG 0,0 → @120,80).", "No plate polyline found (RECTANG 0,0 → @120,80).")]
    try:
        k = list(o["obj"].Coordinates)
    except Exception:
        return [tr("Nepavyko perskaityti kontūro.", "Couldn't read the outline.")]
    v = list(zip(k[0::2], k[1::2]))
    if len(v) <= 4:
        return [tr("Kampai dar nenusklembti. CHAMFER → D → 10 → 10 → P → spustelėk kontūrą.", "The corners aren't chamfered yet. CHAMFER → D → 10 → 10 → P → click the outline.")]
    truksta = [p for p in RD_NUOSKLEMBOS if not any(artima(p, q) for q in v)]
    if truksta:
        return [tr(f"Nuosklembos ne 10 × 10 (pvz. nėra taško {_p(truksta[0])}). U → CHAMFER → D → 10 → 10 → P.",
                   f"The chamfers aren't 10 × 10 (e.g. point {_p(truksta[0])} is missing). U → CHAMFER → D → 10 → 10 → P.")]
    return []


def d_rd_chamfer(b):
    o = _plokstes_pl(objektai(b.ms))
    if o:
        o["obj"].Delete()
    _sl(b, "KONTURAS")
    _pl(b.ms, RD_NUOSKLEMBOS)


def _rd_apskritimas_ar_lankas(objs, c):
    return any(artima(x["c"][:2], c) for x in apskritimai(objs, RD_R) + lankai(objs, RD_R))


def t_rd_kopija(b):
    objs = objektai(b.ms)
    if not _rd_apskritimas_ar_lankas(objs, RD_SKYLE[0]):
        return [tr("Neradau apskritimo R6 taške 25,40. CIRCLE → 25,40 → 6.", "No R6 circle at 25,40. CIRCLE → 25,40 → 6.")]
    if not _rd_apskritimas_ar_lankas(objs, RD_SKYLE[1]):
        return [tr("Neradau kopijos taške 55,40. COPY → spustelėk apskritimą → Enter → bazinis taškas - centras → @30,0 → Enter.",
                   "No copy at 55,40. COPY → click the circle → Enter → base point - the centre → @30,0 → Enter.")]
    return []


def d_rd_kopija(b):
    _sl(b, "KONTURAS")
    for c in RD_SKYLE:
        b.ms.AddCircle(A.taskas(*c), RD_R)


def _t_liestines(seg, xa, xb):
    return [(p, q) for p, q in _rd_liestines(xa, xb) if not yra_atkarpa(seg, p, q)]


def t_rd_liestines(b):
    truksta = _t_liestines(atkarpos(objektai(b.ms)), 25, 55)
    if truksta:
        p, q = truksta[0]
        return [tr(f"Trūksta linijos {_p(p)} → {_p(q)}. LINE → įvesk QUA → spustelėk apskritimo viršų (Quadrant) → QUA → kito apskritimo viršų.",
                   f"Line {_p(p)} → {_p(q)} is missing. LINE → type QUA → click the top of the circle (Quadrant) → QUA → the top of the other circle.")]
    return []


def d_rd_liestines(b):
    for p, q in _rd_liestines(25, 55):
        b.ms.AddLine(A.taskas(*p), A.taskas(*q))


def _pusapskritimis(objs, c, kryptis):
    """Pusė apskritimo R6, išgaubta į kryptį (-1 kairėn, +1 dešinėn)."""
    return any(artima(x["c"][:2], c) and abs(x["apimtis"] - math.pi) < 0.05 and artima(x["vid"], (c[0] + kryptis * RD_R, c[1]))
               for x in lankai(objs, RD_R))


def _t_skyle(objs, ca, cb, kas):
    pilni = [c for c in (ca, cb) if any(artima(x["c"][:2], c) for x in apskritimai(objs, RD_R))]
    if pilni:
        return [tr(f"{kas}: apskritimas {_p(pilni[0])} dar neapkarpytas. TRIM → spustelėk vidinę apskritimo pusę (tarp linijų) → Enter.",
                   f"{kas}: circle {_p(pilni[0])} isn't trimmed yet. TRIM → click the inner half of the circle (between the lines) → Enter.")]
    if not _pusapskritimis(objs, ca, -1) or not _pusapskritimis(objs, cb, +1):
        if lankai(objs, RD_R):
            return [tr(f"{kas}: nukirpta ne ta pusė. Turi likti išorinės pusės (kairėje - kairioji, dešinėje - dešinioji). U ir pakartok.",
                       f"{kas}: the wrong half was trimmed. The outer halves must stay (left half on the left, right half on the right). U and repeat.")]
        return [tr(f"{kas}: neradau lankų R6 ties {_p(ca)} ir {_p(cb)}.", f"{kas}: no R6 arcs at {_p(ca)} and {_p(cb)}.")]
    return []


def t_rd_trim(b):
    objs = objektai(b.ms)
    kl = _t_skyle(objs, *RD_SKYLE, tr("Skylė", "Slot"))
    if not kl and _t_liestines(atkarpos(objs), 25, 55):
        kl = [tr("Dingo tiesios skylės linijos - TRIM nukirpo per daug. U ir spausk tik apskritimų vidines puses.",
                 "The straight slot lines are gone - TRIM cut too much. U and click only the inner halves of the circles.")]
    return kl


def _rd_lankas(b, c, kryptis):
    a0 = math.pi / 2 if kryptis < 0 else 3 * math.pi / 2
    b.ms.AddArc(A.taskas(*c), RD_R, a0, a0 + math.pi)


def d_rd_trim(b):
    for o in objektai(b.ms):
        if o["tipas"] == "AcDbCircle" and any(artima(x["c"][:2], c) for x in apskritimai([o], RD_R) for c in RD_SKYLE):
            o["obj"].Delete()
    _sl(b, "KONTURAS")
    _rd_lankas(b, RD_SKYLE[0], -1)
    _rd_lankas(b, RD_SKYLE[1], +1)


def t_rd_mirror(b):
    objs = objektai(b.ms)
    if _t_skyle(objs, *RD_SKYLE, ""):
        return [tr("Pirmoji skylė dingo - ar į „Erase source objects?“ atsakei Y? U ir pakartok, atsakydamas N.",
                   "The first slot is gone - did you answer Y to „Erase source objects?“? U and repeat answering N.")]
    if not lankai(objs, RD_R) or not any(artima(x["c"][:2], c) for x in lankai(objs, RD_R) for c in RD_KOPIJA):
        return [tr("Neradau veidrodinės skylės dešinėje. MIRROR → pažymėk skylę rėmeliu iš kairės į dešinę → Enter → viršutinės kraštinės vidurys → apatinės vidurys → N.",
                   "No mirrored slot on the right. MIRROR → select the slot with a box from left to right → Enter → top edge midpoint → bottom edge midpoint → N.")]
    kl = _t_skyle(objs, *RD_KOPIJA, tr("Veidrodinė skylė", "Mirrored slot"))
    if not kl and _t_liestines(atkarpos(objs), 65, 95):
        kl = [tr("Veidrodinė skylė be tiesių linijų - pažymėk visą skylę: rėmelis turi apimti ir lankus, ir linijas.",
                 "The mirrored slot has no straight lines - select the whole slot: the box must enclose both arcs and lines.")]
    return kl


def d_rd_mirror(b):
    _sl(b, "KONTURAS")
    _rd_lankas(b, RD_KOPIJA[0], -1)
    _rd_lankas(b, RD_KOPIJA[1], +1)
    for p, q in _rd_liestines(65, 95):
        b.ms.AddLine(A.taskas(*p), A.taskas(*q))


# ------------------------------------------------------------- MASYVAI (OFFSET, sluoksnio keitimas, ARRAYPOLAR, ROTATE)
MS_R, MS_SKYLE_R, MS_PCD_R = 50, 5, 35


def _ms_kampai(nuo):
    return [(MS_PCD_R * math.cos(math.radians(nuo + 60 * i)), MS_PCD_R * math.sin(math.radians(nuo + 60 * i))) for i in range(6)]


MS_PRIES, MS_PO = _ms_kampai(90), _ms_kampai(0)          # po ARRAYPOLAR ir po ROTATE 30°


def _apskritimas(objs, c, r):
    rr = [x for x in apskritimai(objs, r) if artima(x["c"][:2], c)]
    return rr[0] if rr else None


def t_ms_offset(b):
    objs = objektai(b.ms)
    if not _apskritimas(objs, (0, 0), MS_R):
        return [tr("Neradau apskritimo ⌀100. CIRCLE → 0,0 → 50.", "No ⌀100 circle found. CIRCLE → 0,0 → 50.")]
    if not _apskritimas(objs, (0, 0), 20):
        return [tr("Neradau kiaurymės ⌀40. OFFSET → 30 → spustelėk apskritimą → spustelėk jo viduje → Enter.",
                   "No ⌀40 bore found. OFFSET → 30 → click the circle → click inside it → Enter.")]
    return []


def d_ms_offset(b):
    _sl(b, "KONTURAS")
    b.ms.AddCircle(A.taskas(0, 0), MS_R)
    b.ms.AddCircle(A.taskas(0, 0), 20)


def t_ms_pcd(b):
    c = _apskritimas(objektai(b.ms), (0, 0), MS_PCD_R)
    if not c:
        return [tr("Neradau centrų apskritimo ⌀70. OFFSET → 15 → spustelėk ⌀100 apskritimą → spustelėk viduje.",
                   "No ⌀70 pitch circle found. OFFSET → 15 → click the ⌀100 circle → click inside.")]
    if c["sluoksnis"].upper() != "ASYS":
        return [tr(f"Apskritimas ⌀70 sluoksnyje „{c['sluoksnis']}“. Pažymėk jį (spustelėk) ir sluoksnių sąraše (Home → Layers) pasirink ASYS → Esc.",
                   f"The ⌀70 circle is on layer „{c['sluoksnis']}“. Select it (click) and pick ASYS in the layer list (Home → Layers) → Esc.")]
    return []


def d_ms_pcd(b):
    c = b.ms.AddCircle(A.taskas(0, 0), MS_PCD_R)
    c.Layer = "ASYS"


def t_ms_skyle(b):
    c = _apskritimas(objektai(b.ms), MS_PRIES[0], MS_SKYLE_R)
    if not c:
        return [tr("Neradau skylės ⌀10 taške 0,35. CIRCLE → spustelėk ⌀70 apskritimo viršų (Quadrant) → 5.",
                   "No ⌀10 hole at 0,35. CIRCLE → click the top of the ⌀70 circle (Quadrant) → 5.")]
    if c["sluoksnis"].upper() == "ASYS":
        return [tr("Skylė nubraižyta sluoksnyje ASYS. Pažymėk ją → sluoksnių sąraše pasirink KONTURAS (ir padaryk KONTURAS aktyvų).",
                   "The hole is on layer ASYS. Select it → pick KONTURAS in the layer list (and make KONTURAS current).")]
    return []


def d_ms_skyle(b):
    _sl(b, "KONTURAS")
    b.ms.AddCircle(A.taskas(*MS_PRIES[0]), MS_SKYLE_R)


def _ms_truksta(objs, vietos):
    return [p for p in vietos if not _apskritimas(objs, p, MS_SKYLE_R)]


def t_ms_masyvas(b):
    objs = objektai(b.ms)
    truksta = _ms_truksta(objs, MS_PRIES)
    if not truksta:
        return []
    if any("BlockReference" in o["tipas"] or "Array" in o["tipas"] for o in objs):
        return [tr("Masyvas sukurtas kaip susietas (Associative) - jo skylių negaliu patikrinti po vieną. Pažymėk masyvą → EXPLODE → Enter (arba U ir kartok su AS → N).",
                   "The array is associative - I can't check its holes one by one. Select the array → EXPLODE → Enter (or U and repeat with AS → N).")]
    return [tr(f"Radau {6 - len(truksta)} skyles(-ių) iš 6. ARRAYPOLAR → skylė → Enter → centras 0,0 → AS → N → I → 6 → Enter.",
               f"Found {6 - len(truksta)} of 6 holes. ARRAYPOLAR → the hole → Enter → centre 0,0 → AS → N → I → 6 → Enter.")]


def d_ms_masyvas(b):
    _sl(b, "KONTURAS")
    for p in MS_PRIES[1:]:
        b.ms.AddCircle(A.taskas(*p), MS_SKYLE_R)


def t_ms_rotate(b):
    objs = objektai(b.ms)
    if not _ms_truksta(objs, MS_PO):
        return []
    if not _ms_truksta(objs, MS_PRIES):
        return [tr("Skylės dar nepasuktos. ROTATE → spustelėk visas 6 skyles → Enter → 0,0 → 30.",
                   "The holes aren't rotated yet. ROTATE → click all 6 holes → Enter → 0,0 → 30.")]
    return [tr("Skylės ne ten, kur reikia: dvi turi būti ant horizontalios ašies (35,0 ir -35,0). U ir ROTATE → 6 skylės → 0,0 → 30.",
               "The holes are in the wrong place: two must lie on the horizontal axis (35,0 and -35,0). U and ROTATE → 6 holes → 0,0 → 30.")]


def d_ms_rotate(b):
    for o in objektai(b.ms):
        if o["tipas"] == "AcDbCircle" and any(artima(x["c"][:2], p) for x in apskritimai([o], MS_SKYLE_R) for p in MS_PRIES):
            o["obj"].Delete()
    _sl(b, "KONTURAS")
    for p in MS_PO:
        b.ms.AddCircle(A.taskas(*p), MS_SKYLE_R)


def _t_asys(b, horiz, vert, kaip_h, kaip_v):
    """horiz/vert: ((x0, x1), y) ir (x, (y0, y1)) - ašis turi siekti bent tiek."""
    seg = atkarpos(objektai(b.ms), "ASYS")
    if not seg:
        return [tr("Sluoksnyje ASYS neradau linijų. Pasirink sluoksnį ASYS ir braižyk LINE.", "No lines on layer ASYS. Make ASYS current and draw with LINE.")]
    kl = []
    (hx0, hx1), hy = horiz
    if not any(abs(p[1] - hy) < 1 and abs(q[1] - hy) < 1 and min(p[0], q[0]) <= hx0 + 1 and max(p[0], q[0]) >= hx1 - 1 for p, q, _ in seg):
        kl.append(tr("Trūksta horizontalios ašies: ", "The horizontal centre line is missing: ") + kaip_h)
    if vert:
        vx, (vy0, vy1) = vert
        if not any(abs(p[0] - vx) < 1 and abs(q[0] - vx) < 1 and min(p[1], q[1]) <= vy0 + 1 and max(p[1], q[1]) >= vy1 - 1 for p, q, _ in seg):
            kl.append(tr("Trūksta vertikalios ašies: ", "The vertical centre line is missing: ") + kaip_v)
    return kl


def t_ms_asys(b):
    return _t_asys(b, ((-50, 50), 0), (0, (-50, 50)), "LINE → -55,0 → 55,0.", "LINE → 0,-55 → 0,55.")


def d_ms_asys(b):
    for p, q in (((-55, 0), (55, 0)), ((0, -55), (0, 55))):
        l = b.ms.AddLine(A.taskas(*p), A.taskas(*q))
        l.Layer = "ASYS"


# ------------------------------------------------------------- 2D PJŪVIS (PLINE, HATCH)
BK_ISOR, BK_VID, BK_L = 20, 10, 50          # įvorė ⌀40 / ⌀20, ilgis 50
BK_SIENELES = ((0, BK_VID, BK_L, BK_ISOR), (0, -BK_ISOR, BK_L, -BK_VID))


def t_bk_sluoksniai(b):
    try:
        b.doc.Layers.Item("BRUKSNIAI")
    except Exception:
        return [tr("Nerandu sluoksnio BRUKSNIAI. LAYER → New Layer → BRUKSNIAI (spalva 8 - pilka).",
                   "Layer BRUKSNIAI not found. LAYER → New Layer → BRUKSNIAI (colour 8 - grey).")]
    return t_sluoksniai(b)


def d_bk_sluoksniai(b):
    b.vykdyti_saugiai("sluoksniai")


def t_bk_konturas(b):
    objs = objektai(b.ms)
    if not staciakampis(objs, 0, -BK_ISOR, BK_L, BK_ISOR):
        return [tr("Neradau įvorės kontūro 50 × 40. PLINE → 0,-20 → @50,0 → @0,40 → @-50,0 → C.",
                   "No 50 × 40 bushing outline found. PLINE → 0,-20 → @50,0 → @0,40 → @-50,0 → C.")]
    seg = atkarpos(objs)
    truksta = [y for y in (BK_VID, -BK_VID) if not yra_atkarpa(seg, (0, y), (BK_L, y))]
    if truksta:
        return [tr(f"Trūksta kiaurymės linijos y = {truksta[0]:g}: LINE → 0,{truksta[0]:g} → @50,0.",
                   f"The bore line y = {truksta[0]:g} is missing: LINE → 0,{truksta[0]:g} → @50,0.")]
    return []


def d_bk_konturas(b):
    _sl(b, "KONTURAS")
    _pl(b.ms, [(0, -BK_ISOR), (BK_L, -BK_ISOR), (BK_L, BK_ISOR), (0, BK_ISOR)])
    for y in (BK_VID, -BK_VID):
        b.ms.AddLine(A.taskas(0, y), A.taskas(BK_L, y))


def _ribos_sutampa(o, r, tol=1.0):
    return artima(o["min"][:2] + o["max"][:2], r, tol)


def t_bk_hatch(b):
    hs = [o for o in objektai(b.ms) if o["tipas"] == "AcDbHatch"]
    if not hs:
        return [tr("Neradau brūkšniavimo. HATCH → Pattern ANSI31 → spustelėk viršutinės ir apatinės sienelės vidų → Enter.",
                   "No hatch found. HATCH → Pattern ANSI31 → click inside the top and bottom walls → Enter.")]
    for h in hs:
        try:
            rastas = (h["obj"].PatternName or "").upper()
        except Exception:
            rastas = "ANSI31"
        if rastas != "ANSI31":
            return [tr(f"Raštas {rastas} - pjūviams naudok ANSI31 (linijos 45°). Pažymėk brūkšniavimą ir pakeisk Pattern.",
                       f"Pattern {rastas} - use ANSI31 (45° lines) for sections. Select the hatch and change the Pattern.")]
        if h["sluoksnis"].upper() != "BRUKSNIAI":
            return [tr(f"Brūkšniavimas sluoksnyje „{h['sluoksnis']}“ - pažymėk jį ir pasirink sluoksnį BRUKSNIAI.",
                       f"The hatch is on layer „{h['sluoksnis']}“ - select it and pick layer BRUKSNIAI.")]
    visa = (0, -BK_ISOR, BK_L, BK_ISOR)
    for h in hs:
        if _ribos_sutampa(h, visa):
            try:
                kilpos = int(h["obj"].NumberOfLoops)
            except Exception:
                kilpos = 2
            if kilpos < 2:
                return [tr("Užbrūkšniavai ir kiaurymę. Kiaurymėje medžiagos nėra - U ir spustelėk tik sienelių vidų.",
                           "You hatched the bore too. There's no material in the bore - U and click only inside the walls.")]
            return []
    truksta = [r for r in BK_SIENELES if not any(_ribos_sutampa(h, r) for h in hs)]
    if truksta:
        kuri = tr("viršutinės", "top") if truksta[0][1] > 0 else tr("apatinės", "bottom")
        return [tr(f"Trūksta {kuri} sienelės brūkšniavimo. HATCH → spustelėk jos vidų → Enter.",
                   f"The {kuri} wall isn't hatched. HATCH → click inside it → Enter.")]
    return []


def d_bk_hatch(b):
    _sl(b, "BRUKSNIAI")
    h = b.ms.AddHatch(1, "ANSI31", False)       # acHatchPatternTypePreDefined
    laikinos = []
    for x0, y0, x1, y1 in BK_SIENELES:
        pl = _pl(b.ms, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        laikinos.append(pl)
        h.AppendOuterLoop(_objektu_masyvas([pl]))
    h.Evaluate()
    h.Layer = "BRUKSNIAI"
    for pl in laikinos:
        pl.Delete()
    _sl(b, "KONTURAS")


def t_bk_asis(b):
    return _t_asys(b, ((0, BK_L), 0), None, "LINE → -5,0 → 55,0.", "")


def d_bk_asis(b):
    l = b.ms.AddLine(A.taskas(-5, 0), A.taskas(BK_L + 5, 0))
    l.Layer = "ASYS"


# ------------------------------------------------------------- MATMENYS: spindulys
def t_spindulys(b):
    return _t_matmuo(b, "Radial", 10, tr("DIMRADIUS → spustelėk suapvalintą kampą → padėk tekstą.", "DIMRADIUS → click a rounded corner → place the text."))


def d_spindulys(b):
    _sl(b, "MATMENYS")
    k = math.radians(45)
    b.ms.AddDimRadial(A.taskas(90, 50), A.taskas(90 + 10 * math.cos(k), 50 + 10 * math.sin(k)), 12)


TIKRINIMAS = {
    # failas
    "naujas": (t_naujas, d_naujas),
    "vienetai": (t_vienetai, d_vienetai),
    "dwg": (t_issaugota, d_issaugoti),
    "pdf": (t_pdf, d_pdf),
    # lapas
    "ki-konturas": (t_ki_konturas, d_ki_konturas),
    "ki-linijos": (t_ki_linijos, d_ki_linijos),
    "ki-tekstas": (t_ki_tekstas, d_ki_tekstas),
    "ki-issaugok": (t_ki_issaugota, d_ki_issaugoti),
    "a3": (t_a3, d_a3),
    "remelis": (t_remelis, d_remelis),
    "kampinis": (t_kampinis, d_kampinis),
    "uzpildyk": (t_uzpildyta, d_uzpildyti),
    # 2d
    "sluoksniai2d": (t_sluoksniai, d_sluoksniai),
    "plokste": (t_plokste, d_plokste),
    "centras": (t_centras, d_centras),
    "skyles": (t_skyles, d_skyles),
    "asys": (t_asys, d_asys),
    "fillet": (t_fillet, d_fillet),
    # schema
    "naujas_sch": (None, d_naujas),
    "zenklas": (t_zenklas, d_zenklas),
    "attdef": (t_attdef, d_attdef),
    "block": (t_blokas, d_blokas),
    "insert": (t_insert, d_insert),
    "lentele": (t_lentele, d_lentele),
    # matmenys
    "plokste_m": (t_plokste_yra, d_plokste_yra),
    "dimstyle": (t_dimstyle, d_dimstyle),
    "ilgis": (t_ilgis, d_ilgis),
    "aukstis": (t_aukstis, d_aukstis),
    "skersmuo": (t_skersmuo, d_skersmuo),
    "spindulys": (t_spindulys, d_spindulys),
    # tikslumas
    "tk-naujas": (t_naujas, d_naujas),
    "tk-osnap": (t_tk_osnap, d_tk_osnap),
    "tk-rombas": (t_tk_rombas, d_tk_rombas),
    "tk-centras": (t_tk_centras, d_tk_centras),
    "tk-polar": (t_tk_polar, d_tk_polar),
    "tk-plotas": (t_tk_plotas, d_tk_plotas),
    # redagavimas
    "rd-sluoksniai": (t_sluoksniai, d_sluoksniai),
    "rd-plokste": (t_rd_plokste, d_rd_plokste),
    "rd-chamfer": (t_rd_chamfer, d_rd_chamfer),
    "rd-kopija": (t_rd_kopija, d_rd_kopija),
    "rd-liestines": (t_rd_liestines, d_rd_liestines),
    "rd-trim": (t_rd_trim, d_rd_trim),
    "rd-mirror": (t_rd_mirror, d_rd_mirror),
    # masyvai
    "ms-sluoksniai": (t_sluoksniai, d_sluoksniai),
    "ms-offset": (t_ms_offset, d_ms_offset),
    "ms-pcd": (t_ms_pcd, d_ms_pcd),
    "ms-skyle": (t_ms_skyle, d_ms_skyle),
    "ms-masyvas": (t_ms_masyvas, d_ms_masyvas),
    "ms-rotate": (t_ms_rotate, d_ms_rotate),
    "ms-asys": (t_ms_asys, d_ms_asys),
    # 2D pjūvis
    "bk-sluoksniai": (t_bk_sluoksniai, d_bk_sluoksniai),
    "bk-konturas": (t_bk_konturas, d_bk_konturas),
    "bk-hatch": (t_bk_hatch, d_bk_hatch),
    "bk-asis": (t_bk_asis, d_bk_asis),
    # sriftai
    "iso": (t_iso, d_sriftai),
    "isolt": (t_isolt, d_sriftai),
    "tekstas": (t_tekstas, d_tekstas),
    # pirmoji-3d
    "pasiruosimas": (None, None),
    "sluoksniai": (t_sluoksniai, d_sluoksniai),
    "box": (t_deze, d_deze),
    "cylinder": (t_cilindras, d_cilindras),
    "union": (t_sujungta, d_sujungti),
    "polygon": (t_prizme, d_prizme),
    "subtract": (t_atimta, d_atimti),
    "wedge": (t_pleistas, d_pleistas),
    "mirror": (t_veidrodis, d_veidrodis),
    "final": (t_galutinis, d_galutinis),
    # pjuviai
    "pj-detale": (t_detale3d, d_detale3d),
    "pj-ispjova": (t_ispjova, d_ispjova),
    "pj-plokstuma": (t_plokstuma, None),
    "pj-vaizdas": (t_vaizdas, None),
    "pj-pjuvis": (t_pjuvis, None),
    # projekcijos
    "pr-a3": (t_a3, d_a3),
    "pr-standartas": (None, None),
    "pr-priekis": (t_pr_priekis, None),
    "pr-projekcijos": (t_pr_projekcijos, None),
    "pr-aksonometrija": (t_pr_aksonometrija, None),
    # aksonometrija
    "ax-isodraft": (t_isodraft, d_isodraft),
    "ax-deze": (t_iso_deze, d_iso_deze),
    "ax-apskritimas": (t_iso_apskritimas, d_iso_apskritimas),
    "ax-matmuo": (t_iso_matmuo, d_iso_matmuo),
}

PAMOKU_FAILAS = os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)),
                             "pamokos.json")


def _ikelti():
    with open(PAMOKU_FAILAS, encoding="utf-8") as f:
        d = json.load(f)
    for p in d["pamokos"]:
        for z in p["zingsniai"]:
            z["tikrinti"], z["demo"] = TIKRINIMAS.get(z["id"], (None, None))
    return d


_TURINYS = _ikelti()
PAMOKOS = _TURINYS["pamokos"]
ATEITYJE = _TURINYS["ateityje"]
PATARIMAI = _TURINYS["patarimai"]
KORTELES = _TURINYS["korteles"]


def pamoka(pid):
    for p in PAMOKOS:
        if p["id"] == pid:
            return p
    raise ValueError("Tokios pamokos nėra.")


EN_FAILAS = os.path.join(os.path.dirname(PAMOKU_FAILAS), "pamokos_en.json")
_EN = {}


def _en():
    if not _EN:
        try:
            with open(EN_FAILAS, encoding="utf-8") as f:
                _EN.update(json.load(f))
        except (OSError, ValueError):
            _EN["pamokos"] = {}
    return _EN


ZINGSNIO_TEKSTAI = ("pavadinimas", "kodel", "zingsniai", "komandos", "uzuominos", "tikslas")


def _isversta(p, en):
    """Pamoka su anglų tekstais (pamokos_en.json: tik tekstai pagal id; xp, testų atsakymai - iš pamokos.json)."""
    e = en.get(p["id"])
    if not e:
        return p
    q = {**p, **{k: e[k] for k in ("pavadinimas", "aprasas", "trukme", "pabaiga") if k in e}}
    q["zingsniai"] = [{**z, **{k: v for k, v in e.get("zingsniai", {}).get(z["id"], {}).items() if k in ZINGSNIO_TEKSTAI}}
                      for z in p["zingsniai"]]
    if len(e.get("testas", [])) == len(p["testas"]):
        q["testas"] = [{**t, **{k: et[k] for k in ("k", "v", "p") if k in et}} for t, et in zip(p["testas"], e["testas"])]
    return q


PAVEIKSLELIAI = os.path.join(os.path.dirname(PAMOKU_FAILAS), "paveiksleliai")


def _paveikslelis(zid, kalba):
    """Tikslo paveikslėlis „taip turi atrodyti“ (irankiai/paveiksleliai.py) - kelias arba None."""
    for kel in ([f"en/{zid}.svg"] if kalba == "en" else []) + [f"{zid}.svg"]:
        if os.path.exists(os.path.join(PAVEIKSLELIAI, kel)):
            return "paveiksleliai/" + kel
    return None


def viesai(kalba="lt"):
    """Pamokos be Python funkcijų - siuntimui į sąsają (ir programėlei). kalba "en" - anglų tekstai."""
    rez = []
    pamokos, ateityje, patarimai, korteles = PAMOKOS, ATEITYJE, PATARIMAI, KORTELES
    if kalba == "en":
        en = _en()
        pamokos = [_isversta(p, en.get("pamokos", {})) for p in PAMOKOS]
        ateityje = en.get("ateityje", ATEITYJE)
        patarimai = en.get("patarimai", PATARIMAI)
        korteles = [{**k, **en.get("korteles", {}).get(k["k"], {})} for k in KORTELES]
    for p in pamokos:
        z = [{k: v for k, v in s.items() if k not in ("tikrinti", "demo")} |
             {"tikrinama": s["tikrinti"] is not None, "demonstruojama": s["demo"] is not None} |
             ({"pav": _paveikslelis(s["id"], kalba)} if _paveikslelis(s["id"], kalba) else {})
             for s in p["zingsniai"]]
        rez.append({k: v for k, v in p.items() if k != "zingsniai"} | {"zingsniai": z})
    return {"pamokos": rez, "ateityje": ateityje, "patarimai": patarimai, "korteles": korteles}

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

TOL = 0.6          # mm - leidžiama paklaida koordinatėms
TOL_V = 0.015      # 1.5 % - leidžiama tūrio paklaida

# Tikslūs tūriai (apskaičiuoti iš anksto)
V_DEZE = 100 * 60 * 20
V_SUJUNGTA = V_DEZE + math.pi * 20 ** 2 * 40                  # 170265.5
V_SU_SKYLE = V_SUJUNGTA - 3 * math.sqrt(3) / 2 * 10 ** 2 * 60   # 154677.0
V_GALUTINIS = 158568.8                                        # + 2 briaunos be persidengimo su cilindru


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
    return f"nuo ({tf(round(x0,1))}, {tf(round(y0,1))}, {tf(round(z0,1))}) iki ({tf(round(x1,1))}, {tf(round(y1,1))}, {tf(round(z1,1))})"


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
            pastabos.append(f"dydis pagal {vardai[i]} yra {tf(round(dydis[i],1))}, o turi būti {tf(norimas[i])}")
    if not pastabos:
        for i in range(3):
            if abs(k["min"][i] - mn[i]) > TOL:
                pastabos.append(f"pradžia pagal {vardai[i]} yra {tf(round(k['min'][i],1))}, o turi būti {tf(mn[i])}")
    return "; ".join(pastabos) or "ribos beveik sutampa"


# ------------------------------------------------------------------ tikrinimai
def t_sluoksniai(b):
    doc = b.doc
    reikia = {"KONTURAS": 7, "ASYS": 1, "MATMENYS": 3}
    klaidos = []
    for vardas, spalva in reikia.items():
        try:
            sl = doc.Layers.Item(vardas)
        except Exception:
            klaidos.append(f"Nerandu sluoksnio {vardas}.")
            continue
        try:
            if int(sl.Color) != spalva:
                klaidos.append(f"Sluoksnio {vardas} spalva turi būti {spalva}.")
        except Exception:
            pass
    try:
        if not klaidos and doc.Layers.Item("ASYS").Linetype.upper() != "CENTER":
            klaidos.append("Sluoksnio ASYS linijos tipas turi būti CENTER (Load... → CENTER).")
    except Exception:
        pass
    try:
        if not klaidos and doc.ActiveLayer.Name.upper() != "KONTURAS":
            klaidos.append("Padaryk KONTURAS aktyviu (dukart spustelėk jį - atsiras žalia varnelė).")
    except Exception:
        pass
    return klaidos


def t_deze(b):
    ks = kunai(b)
    if not ks:
        return ["Brėžinyje nerandu nė vieno 3D kūno. Ar tikrai baigei BOX komandą (aukštis + Enter)?"]
    k = rasti(ks, (0, 0, 0), (100, 60, 20))
    if not k:
        a = artimiausias(ks, (0, 0, 0), (100, 60, 20))
        return [f"Radau dėžę {ribos_tekstas(a)}: {kas_ne_taip(a, (0,0,0), (100,60,20))}.",
                "Patarimas: ištrink ją (ERASE) ir bandyk iš naujo, koordinates rašyk su kableliais: 0,0,0"]
    if k["sluoksnis"].upper() != "KONTURAS":
        return [f"Dėžė nubraižyta sluoksnyje „{k['sluoksnis']}“, o turi būti KONTURAS. "
                "Pažymėk ją ir viršuje sluoksnių sąraše pasirink KONTURAS."]
    return []


def t_cilindras(b):
    ks = kunai(b)
    tikslas = ((30, 10, 20), (70, 50, 60))
    if rasti(ks, *tikslas):
        return []
    kiti = [k for k in ks if not ribos_atitinka(k, (0, 0, 0), (100, 60, 20))]
    if not kiti:
        return ["Nerandu cilindro. Ar įvedei CYLINDER ir visus tris atsakymus (centras, spindulys, aukštis)?"]
    a = artimiausias(kiti, *tikslas)
    return [f"Radau kūną {ribos_tekstas(a)}: {kas_ne_taip(a, *tikslas)}.",
            "Cilindro centras turi būti ant dėžės viršaus: 50,30,20 (z = 20!)."]


def t_sujungta(b):
    ks = kunai(b)
    if len(ks) > 1:
        return [f"Brėžinyje yra {len(ks)} atskiri kūnai - jie dar nesujungti. "
                "UNION → pažymėk dėžę IR cilindrą → Enter."]
    if not ks:
        return ["Nerandu kūnų - gal netyčia ištrynei? Spausk „Parodyk man“ ankstesniuose žingsniuose."]
    k = ks[0]
    if not ribos_atitinka(k, (0, 0, 0), (100, 60, 60)) or not turis_tinka(k, V_SUJUNGTA):
        return [f"Sujungtas kūnas {ribos_tekstas(k)} - formos neatitinka. Patikrink ankstesnius žingsnius."]
    return []


def t_prizme(b):
    ks = kunai(b)
    if len(ks) < 2:
        return ["Nerandu šešiakampės prizmės. POLYGON nubraižo tik plokščią šešiakampį - "
                "jį dar reikia ištempti EXTRUDE komanda (aukštis 60)."]
    for k in ks:
        dx, dy = k["max"][0] - k["min"][0], k["max"][1] - k["min"][1]
        cx, cy = (k["max"][0] + k["min"][0]) / 2, (k["max"][1] + k["min"][1]) / 2
        if abs(cx - 50) < 1 and abs(cy - 30) < 1 and sorted([round(dx, 1), round(dy, 1)]) in ([17.3, 20.0], [17.4, 20.0]):
            if abs(k["min"][2]) > TOL or abs(k["max"][2] - 60) > TOL:
                return [f"Prizmė yra, bet jos aukštis nuo {tf(round(k['min'][2],1))} iki {tf(round(k['max'][2],1))}. "
                        "Šešiakampį braižyk ant z = 0 ir ištempk 60 aukštyn."]
            return []
    mazi = [k for k in ks if k["max"][0] - k["min"][0] < 50]
    if mazi:
        k = mazi[0]
        return [f"Radau kūną {ribos_tekstas(k)}. Šešiakampio centras turi būti 50,30, "
                "o „Inscribed in circle“ spindulys - 10 (plotis 20 × 17,3)."]
    return ["Nerandu šešiakampės prizmės ties centru 50,30."]


def t_atimta(b):
    ks = kunai(b)
    if len(ks) > 1:
        return ["Vis dar yra atskiri kūnai. SUBTRACT: pirma pažymėk DETALĘ → Enter, "
                "tada pažymėk PRIZMĘ (ką išpjauti) → Enter."]
    if not ks:
        return ["Nerandu kūnų."]
    k = ks[0]
    if turis_tinka(k, V_SUJUNGTA - 0) and not turis_tinka(k, V_SU_SKYLE):
        return ["Tūris nepasikeitė - gal sujungei (UNION) vietoj atėmimo (SUBTRACT)? Atšauk: U."]
    if not turis_tinka(k, V_SU_SKYLE):
        return [f"Detalės tūris {tf(round(k['turis'] or 0))} mm³, tikėtasi apie {tf(round(V_SU_SKYLE))} mm³. "
                "Patikrink šešiakampį (spindulys 10, aukštis 60)."]
    return []


def t_pleistas(b):
    ks = kunai(b)
    tikslas = ((65, 26, 20), (90, 34, 50))
    if rasti(ks, *tikslas):
        return []
    kiti = [k for k in ks if k["max"][0] - k["min"][0] < 60]
    if not kiti:
        return ["Nerandu standumo briaunos. WEDGE: pirmas kampas 65,26,20, antras 90,34, aukštis 30."]
    a = artimiausias(kiti, *tikslas)
    return [f"Radau kūną {ribos_tekstas(a)}: {kas_ne_taip(a, *tikslas)}."]


def t_veidrodis(b):
    ks = kunai(b)
    desine = rasti(ks, (65, 26, 20), (90, 34, 50))
    kaire = rasti(ks, (10, 26, 20), (35, 34, 50))
    if not desine:
        return ["Dingo dešinioji briauna - MIRROR3D klausime „Delete source objects?“ reikėjo atsakyti No."]
    if not kaire:
        return ["Nerandu kairiosios briaunos (x nuo 10 iki 35). MIRROR3D plokštuma: YZ, taškas 50,30,0."]
    return []


def t_galutinis(b):
    ks = kunai(b)
    if len(ks) > 1:
        return [f"Dar yra {len(ks)} atskiri kūnai. UNION → pažymėk viską (galima rėmeliu) → Enter."]
    if not ks:
        return ["Nerandu kūnų."]
    k = ks[0]
    if not ribos_atitinka(k, (0, 0, 0), (100, 60, 60)):
        return [f"Detalė {ribos_tekstas(k)} - turi būti nuo (0,0,0) iki (100,60,60)."]
    if not turis_tinka(k, V_GALUTINIS):
        return [f"Tūris {tf(round(k['turis'] or 0))} mm³, tikėtasi apie {tf(round(V_GALUTINIS))} mm³."]
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
#  NAUJOS PAMOKOS: failas -> lapas -> 2D -> schema -> matmenys -> šriftai
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
        return ["Nepavyko perskaityti brėžinio nustatymų - ar atidarytas brėžinys?"]
    if int(m) != 1:
        return ["Šis brėžinys sukurtas iš imperinio (colių) šablono. Uždaryk jį ir sukurk naują iš acadiso.dwt."]
    if int(u) != 4:
        return [f"Brėžinio vienetai ne milimetrai (INSUNITS = {u}). Sukurk naują iš acadiso.dwt."]
    return []


def d_naujas(b):
    A.naujas_brezinys(b.acad, "acadiso.dwt")
    b.palaukti()
    b.kunas = None


def t_vienetai(b):
    lu, pr, u = kintamasis(b, "LUNITS"), kintamasis(b, "LUPREC"), kintamasis(b, "INSUNITS")
    kl = []
    if lu is not None and int(lu) != 2:
        kl.append("Length Type turi būti Decimal (dešimtainiai).")
    if u is not None and int(u) != 4:
        kl.append("Insertion scale turi būti Millimeters.")
    if pr is not None and int(pr) > 2:
        kl.append(f"Tikslumas dabar {pr} skaitmenys po kablelio - brėžiniams užtenka 0 arba 0.0.")
    return kl


def d_vienetai(b):
    for k, v in (("LUNITS", 2), ("INSUNITS", 4), ("LUPREC", 0)):
        b.doc.SetVariable(k, v)


def t_issaugota(b):
    doc = b.doc
    kelias = (doc.FullName or "")
    if not kelias:
        return ["Brėžinys dar neišsaugotas. Ctrl+Shift+S (SAVEAS) → įrašyk vardą → Save."]
    if not kelias.lower().endswith(".dwg"):
        return [f"Brėžinys išsaugotas kaip {os.path.splitext(kelias)[1]}, o reikia .dwg."]
    if "drawing" in os.path.basename(kelias).lower():
        return ["Duok failui prasmingą vardą, pvz. Pirmasis_brezinys.dwg, o ne Drawing1."]
    return []


def d_issaugoti(b):
    b.issaugoti(os.path.join(mano_aplankas(), "Pirmasis_brezinys"), "dwg")


def t_pdf(b):
    ap = [getattr(b.doc, "Path", ""), mano_aplankas()]
    if nauji_failai(ap, ".pdf"):
        return []
    return ["Neradau naujo PDF failo šalia brėžinio. PLOT → Printer: DWG To PDF.pc3 → OK → išsaugok."]


def d_pdf(b):
    b.issaugoti(os.path.join(mano_aplankas(), "Pirmasis_brezinys"), "pdf")


# ------------------------------------------------------------- 2. LAPAS
def t_a3(b):
    L = a3_lapas(b)
    if not L:
        return ["Neradau A3 lapo. LAYOUTWIZARD → vardas A3 → DWG To PDF.pc3 → ISO full bleed A3 (420 x 297) → Landscape → Title block: None → Viewports: None."]
    try:
        if "A3" not in (L.CanonicalMediaName or "").upper():
            return [f"Lapas „{L.Name}“ yra, bet popierius ne A3. Page Setup Manager → Modify → ISO full bleed A3."]
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
        return ["Pirma sukurk A3 lapą (ankstesnis žingsnis)."]
    if not staciakampis(objs, 20, 5, 415, 292):
        return ["Neradau rėmelio. Lape (ne Model!) įvesk RECTANG → 20,5 → 415,292."]
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
        return ["Pirma sukurk A3 lapą."]
    if not staciakampis(objs, 230, 5, 415, 45):
        return ["Neradau kampinio įrašo lentelės. RECTANG → 230,5 → 415,45 (185 × 40, apatiniame dešiniame kampe)."]
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
        return ["Pirma sukurk A3 lapą."]
    viduj = [t for t in tekstai(objs) if 229 <= t["p"][0] <= 416 and 4 <= t["p"][1] <= 46]
    if len(viduj) < 2:
        return [f"Kampiniame įraše radau {len(viduj)} tekstą(-us). Įrašyk bent darbo pavadinimą ir savo vardą (TEXT, aukštis 3.5 arba 5)."]
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
        return ["Neradau plokštės kontūro. RECTANG → 0,0 → 100,60."]
    if o["sluoksnis"].upper() != "KONTURAS":
        return [f"Kontūras nubraižytas sluoksnyje „{o['sluoksnis']}“, o turi būti KONTURAS."]
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
        return [f"Radau apskritimą centre ({c['c'][0]:g}, {c['c'][1]:g}) spinduliu {c['r']:g}. Reikia: centras 50,30, spindulys 15 (ø30)."]
    return ["Neradau apskritimo. CIRCLE → 50,30 → 15."]


def d_centras(b):
    b.ms.AddCircle(A.taskas(50, 30), 15)


def t_skyles(b):
    rasta = [c for c in apskritimai(objektai(b.ms), 5)]
    reikia = [(15, 15), (85, 15), (15, 45), (85, 45)]
    truksta = [p for p in reikia if not any(artima(c["c"][:2], p) for c in rasta)]
    if truksta:
        return ["Trūksta skylių ø10 taškuose: " + ", ".join(f"{x},{y}" for x, y in truksta) + ". CIRCLE → taškas → 5."]
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
        kl.append("Sluoksnyje ASYS neradau linijų. Pasirink sluoksnį ASYS ir braižyk LINE.")
    else:
        if not horiz:
            kl.append("Trūksta horizontalios ašies: LINE → -5,30 → 105,30.")
        if not vert:
            kl.append("Trūksta vertikalios ašies: LINE → 50,-5 → 50,65.")
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
        return ["Neradau plokštės polilinijos (RECTANG 0,0 → 100,60)."]
    pl = o["obj"]
    try:
        n = len(pl.Coordinates) // 2
        lankai = sum(1 for i in range(n) if abs(pl.GetBulge(i)) > 1e-6)
    except Exception:
        return ["Nepavyko perskaityti kontūro."]
    if lankai < 4:
        return [f"Suapvalinti kampai: {lankai} iš 4. FILLET → R (Radius) → 10 → P (Polyline) → spustelėk kontūrą."]
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
        return ["Neradau rezistoriaus stačiakampio. RECTANG → 5,-2 → 15,2."]
    lin = [o for o in objs if o["tipas"] == "AcDbLine" and abs(o["min"][1]) < 0.5 and abs(o["max"][1]) < 0.5]
    if len(lin) < 2:
        return ["Trūksta išvadų: LINE → 0,0 → 5,0 ir LINE → 15,0 → 20,0."]
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
        kl.append("Trūksta atributo POZ: ATTDEF → Tag: POZ, Prompt: Pozicinis žymuo, Default: R → taškas 7,4.")
    if "NUORODA" not in at:
        kl.append("Trūksta atributo NUORODA: ATTDEF → pažymėk Invisible → Tag: NUORODA → taškas 7,-7.")
    elif not (getattr(at["NUORODA"], "Invisible", False) or (int(getattr(at["NUORODA"], "Mode", 0)) & 1)):
        kl.append("Atributas NUORODA turi būti nematomas (Invisible).")
    return kl


def d_attdef(b):
    b.ms.AddAttribute(3.5, 0, "Pozicinis žymuo", A.taskas(7, 4), "POZ", "R")
    b.ms.AddAttribute(3.5, 1, "Nuoroda (parametrai)", A.taskas(7, -7), "NUORODA", "")


def t_blokas(b):
    try:
        blk = b.doc.Blocks.Item("REZISTORIUS")
    except Exception:
        return ["Neradau bloko REZISTORIUS. BLOCK → Name: REZISTORIUS → Base point 0,0 → Objects: pažymėk ženklą ir atributus → Delete → OK."]
    at = _atributai(blk)
    if "POZ" not in at or "NUORODA" not in at:
        return ["Blokas REZISTORIUS yra, bet jame trūksta atributų POZ ir NUORODA - pažymėk juos kuriant bloką."]
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
    for o in objektai(b.ms):        # ištrinam laisvą ženklą (kaip „Delete“ kuriant bloką)
        if o["max"][0] <= 21 and o["min"][1] >= -8 and o["max"][1] <= 8 and o["tipas"] != "AcDbBlockReference":
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
        return [f"Schemoje radau {len(r)} rezistorių. INSERT → REZISTORIUS → įstatyk 3 kartus, POZ: R1, R2, R3."]
    poz = [x.get("POZ", "") for x in r]
    if len(set(poz)) < len(poz) or any(p in ("", "R") for p in poz):
        return [f"Poziciniai žymenys: {', '.join(poz)}. Kiekvienas turi būti skirtingas: R1, R2, R3."]
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
    return ["Neradau aprašo lentelės. DATAEXTRACTION → naujas → pažymėk blokus → stulpeliai POZ, Name, Count, NUORODA → Insert table."]


def d_lentele(b):
    b._aprasas((150, 60))


# ------------------------------------------------------------- 5. MATMENYS
def t_plokste_yra(b):
    objs = objektai(b.ms)
    if not staciakampis(objs, 0, 0, 100, 60, tol=1.5) or not apskritimai(objs, 15):
        return ["Neradau plokštės iš 3 pamokos (100 × 60 su skyle ø30). Atidaryk tą brėžinį arba spausk „Parodyk man“."]
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
        return ["Neradau matmenų stiliaus ISO_MATMENYS. DIMSTYLE → New → vardas ISO_MATMENYS → Text height 3.5, Arrow size 3."]
    try:
        akt = b.doc.ActiveDimStyle.Name
    except Exception:
        akt = ""
    if akt.upper() != "ISO_MATMENYS":
        return ["Stilius yra, bet neaktyvus. DIMSTYLE → pažymėk ISO_MATMENYS → Set Current."]
    h = kintamasis(b, "DIMTXT")
    if h is not None and abs(float(h) - 3.5) > 0.05:
        return [f"Matmenų teksto aukštis {float(h):g}, o turi būti 3.5 (Text → Text height)."]
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
        return [f"Neradau matmens {verte:g}. {kaip}"]
    if m[0]["sluoksnis"].upper() != "MATMENYS":
        return [f"Matmuo {verte:g} yra sluoksnyje „{m[0]['sluoksnis']}“ - perkelk į MATMENYS."]
    return []


def t_ilgis(b):
    return _t_matmuo(b, "Rotated", 100, "Sluoksnis MATMENYS → DIMLINEAR → spustelėk du apatinius kampus → patrauk žemyn.")


def t_aukstis(b):
    return _t_matmuo(b, "Rotated", 60, "DIMLINEAR → du kairiosios kraštinės galai → patrauk kairėn.")


def t_skersmuo(b):
    return _t_matmuo(b, "Diametric", 30, "DIMDIAMETER → spustelėk didįjį apskritimą → padėk tekstą.")


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
        return ["Neradau teksto stiliaus ISO. STYLE → New → ISO → Font: isocp.shx → Apply."]
    if "isocp" not in (st.fontFile or "").lower():
        return [f"Stilius ISO naudoja šriftą „{st.fontFile}“, o reikia isocp.shx."]
    return []


def t_isolt(b):
    try:
        st = b.doc.TextStyles.Item("ISO_LT")
    except Exception:
        return ["Neradau stiliaus ISO_LT. STYLE → New → ISO_LT → Font: ISOCPEUR (su lietuviškomis raidėmis) → Oblique angle 15 → Apply."]
    try:
        sriftas = st.GetFont()[0]
    except Exception:
        sriftas = st.fontFile or ""
    if "isocpeur" not in str(sriftas).lower():
        return [f"Stilius ISO_LT naudoja „{sriftas}“, o reikia ISOCPEUR - jis turi ąčęėįšųūž."]
    if abs(math.degrees(float(st.ObliqueAngle)) - 15) > 1:
        return ["Nustatyk pasvirimą: Oblique angle 15 (ISO 3098 B tipas)."]
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
        return [f"Radau tekstą „{t['txt']}“ aukščio {t['h']:g}. Reikia aukščio 5 ir lietuviškų raidžių, pvz. „Brėžinys“."]
    return ["Neradau teksto stiliumi ISO_LT. Padaryk ISO_LT aktyvų → TEXT → taškas → aukštis 5 → „Brėžinys“."]


def d_tekstas(b):
    t = b.ms.AddText("Brėžinys", A.taskas(0, 80), 5)
    try:
        t.StyleName = "ISO_LT"
    except Exception:
        pass


# ------------------------------------------------------------- pamokų turinys: pamokos.json
# Tekstai (žingsniai, užuominos, testai, kortelės) - pamokos.json. Jį naudoja ir programėlė (app/).
# Čia - tik kas tikrina žingsnį ir kas jį parodo AutoCAD'e: žingsnio id -> (tikrinti, demo).
# Naujas žingsnis be įrašo čia veiks, tik nebus tikrinamas ir demonstruojamas.
TIKRINIMAS = {
    # failas
    "naujas": (t_naujas, d_naujas),
    "vienetai": (t_vienetai, d_vienetai),
    "dwg": (t_issaugota, d_issaugoti),
    "pdf": (t_pdf, d_pdf),
    # lapas
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


def viesai():
    """Pamokos be Python funkcijų - siuntimui į sąsają (ir programėlei)."""
    rez = []
    for p in PAMOKOS:
        z = [{k: v for k, v in s.items() if k not in ("tikrinti", "demo")} |
             {"tikrinama": s["tikrinti"] is not None, "demonstruojama": s["demo"] is not None}
             for s in p["zingsniai"]]
        rez.append({k: v for k, v in p.items() if k != "zingsniai"} | {"zingsniai": z})
    return {"pamokos": rez, "ateityje": ATEITYJE, "patarimai": PATARIMAI, "korteles": KORTELES}

"""
Brėžly pamokos: žingsniai, ką daryti AutoCAD'e, užuominos, tikrinimas ir demonstracijos.

Tikrinimas skaito tavo brėžinį (MODEL erdvę) per AutoCAD COM:
3D kūnų ribas (GetBoundingBox), tūrį (Volume) ir sluoksnį, sluoksnių savybes.
"""

import math
import os
import time

import pythoncom
import win32com.client

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


# ------------------------------------------------------------- pamokų aprašai
def _z(id, pav, xp, kodel, zingsniai, komandos, uzuominos, tikrinti, demo, tikslas=None):
    z = {"id": id, "pavadinimas": pav, "xp": xp, "kodel": kodel, "zingsniai": zingsniai,
         "komandos": komandos, "uzuominos": uzuominos, "tikrinti": tikrinti, "demo": demo}
    if tikslas:
        z["tikslas"] = tikslas
    return z


NAUJOS = [
  {"id": "failas", "pavadinimas": "Failas ir formatai", "trukme": "~10 min.",
   "aprasas": "Naujas brėžinys iš acadiso.dwt, vienetai, išsaugojimas DWG ir PDF - nuo to prasideda kiekvienas darbas.",
   "pabaiga": "Moki teisingai pradėti brėžinį ir jį išsaugoti DWG bei PDF formatu.",
   "zingsniai": [
     _z("naujas", "Naujas brėžinys iš acadiso.dwt", 10,
        "acadiso.dwt - metrinis šablonas: viskas milimetrais. acad.dwt - coliais, todėl brėžinyje matmenys būtų neteisingi.",
        ["Viršuje kairėje spausk A (Application) → New → Drawing.", "Sąraše pasirink acadiso.dwt → Open."],
        [["Command:", "NEW"], ["Select template:", "acadiso.dwt"]],
        ["Jei atsidaro be lango - įvesk STARTUP → 0 ir bandyk iš naujo.", "Šablonų aplankas atsidaro automatiškai - ieškok acadiso.dwt, ne acad.dwt."],
        t_naujas, d_naujas, "Metrinis brėžinys (mm)"),
     _z("vienetai", "Vienetai: UNITS", 10,
        "Vienetai nusako, ką reiškia skaičius 100. Mūsų brėžiniuose - 100 milimetrų, be nereikalingų skaitmenų po kablelio.",
        ["Įvesk UNITS. Nustatyk:"],
        [["Command:", "UNITS"], ["Length Type:", "Decimal"], ["Precision:", "0"], ["Insertion scale:", "Millimeters"], ["", "OK"]],
        ["Precision 0 reiškia sveikus skaičius - braižymo brėžiniams to užtenka."],
        t_vienetai, d_vienetai, "Decimal · 0 · Millimeters"),
     _z("dwg", "Išsaugok kaip DWG", 15,
        "DWG - pagrindinis AutoCAD formatas. Prasmingas failo vardas padeda rasti darbą po savaitės.",
        ["Spausk Ctrl+Shift+S (SAVEAS).", "Pasirink aplanką, įrašyk vardą Pirmasis_brezinys → Save."],
        [["Command:", "SAVEAS"], ["File name:", "Pirmasis_brezinys"], ["Files of type:", "AutoCAD 2018 Drawing (*.dwg)"]],
        ["Senesniam AutoCAD (pvz. mokykloje) rinkis AutoCAD 2013 Drawing.", "Ctrl+S vėliau tiesiog išsaugo pakeitimus."],
        t_issaugota, d_issaugoti, "Failas .dwg su tavo vardu"),
     _z("pdf", "Spausdink į PDF", 15,
        "Dėstytojui darbą dažnai reikia atiduoti PDF. Spausdintuvas DWG To PDF sukuria failą vietoj popieriaus.",
        ["Įvesk PLOT (arba Ctrl+P).", "Printer: DWG To PDF.pc3, Plot area: Extents, Fit to paper → OK → Save."],
        [["Command:", "PLOT"], ["Printer/plotter:", "DWG To PDF.pc3"], ["What to plot:", "Extents"], ["", "OK → Save"]],
        ["PDF išsaugok tame pačiame aplanke kaip DWG - taip lengviau rasti.", "Jei PDF tuščias - brėžinyje dar nieko nėra, tai normalu šiame žingsnyje."],
        t_pdf, d_pdf, "Naujas PDF failas"),
   ],
   "testas": [
     {"k": "Kurį šabloną rinktis brėžiniams milimetrais?", "v": ["acad.dwt", "acadiso.dwt", "acadiso3D.dwt tik 2D", "Nesvarbu"], "t": 1,
      "p": "acadiso.dwt - metrinis (ISO). acad.dwt - coliai."},
     {"k": "Kam naudojamas DXF formatas?", "v": ["Spausdinimui", "Brėžiniui atidaryti kitose CAD programose", "Tik 3D modeliams", "Nuotraukoms"], "t": 1,
      "p": "DXF - mainų formatas, jį atidaro daugelis CAD programų."},
     {"k": "Mokykloje senas AutoCAD neatidaro tavo failo. Ką daryti?", "v": ["Išsaugoti kaip PDF", "SAVEAS → senesnė DWG versija, pvz. 2013", "Pervadinti failą", "Nieko"], "t": 1,
      "p": "Naujesnės DWG versijos senesnėje programoje neatsidaro - išsaugok senesniu formatu."},
   ]},
  {"id": "lapas", "pavadinimas": "A3 lapas ir kampinis įrašas", "trukme": "~15 min.",
   "aprasas": "LAYOUTWIZARD, A3 formatas, rėmelis ir kampinio įrašo lentelė - lapas, ant kurio dėsi visus brėžinius.",
   "pabaiga": "Moki paruošti A3 lapą su rėmeliu ir kampiniu įrašu pagal reikalavimus.",
   "zingsniai": [
     _z("a3", "A3 lapas: LAYOUTWIZARD", 15,
        "Model erdvėje braižai tikrais dydžiais, o lapas (Layout / PAPER) - tai popierius, kurį spausdinsi. A3 = 420 × 297 mm.",
        ["Įvesk LAYOUTWIZARD ir eik per langus:"],
        [["Command:", "LAYOUTWIZARD"], ["Begin:", "A3"], ["Printer:", "DWG To PDF.pc3"], ["Paper size:", "ISO full bleed A3 (420 x 297)"],
         ["Orientation:", "Landscape"], ["Title block:", "None"], ["Define viewports:", "None"]],
        ["Apačioje atsiras skirtukas „A3“ - tai tavo lapas.", "Jei popieriaus sąraše nėra A3 - pirma pasirink spausdintuvą DWG To PDF."],
        t_a3, d_a3, "Lapas A3 (420 × 297)"),
     _z("remelis", "Rėmelis", 15,
        "Pagal standartą rėmelis kairėje 20 mm nuo krašto (segimui), kitose pusėse - 5 mm.",
        ["Būdamas lape A3 (ne Model!), sluoksnyje KONTURAS įvesk:"],
        [["Command:", "RECTANG"], ["Specify first corner:", "20,5"], ["Specify other corner:", "415,292"]],
        ["Patikrink, kad apačioje aktyvus skirtukas A3, o ne Model.", "420 - 5 = 415, 297 - 5 = 292."],
        t_remelis, d_remelis, "Rėmelis nuo (20,5) iki (415,292)"),
     _z("kampinis", "Kampinio įrašo lentelė", 15,
        "Kampinis įrašas - brėžinio „pasas“: kas braižė, kas tikrino, mastelis. Jis visada apatiniame dešiniame rėmelio kampe, 185 × 40.",
        ["Nubraižyk lentelės kontūrą:", "Vidines linijas nubraižyk LINE komanda pagal pavyzdį."],
        [["Command:", "RECTANG"], ["Specify first corner:", "230,5"], ["Specify other corner:", "415,45"]],
        ["415 - 185 = 230, 5 + 40 = 45.", "Įjunk OSNAP (F3) - linijos pritrauks prie kampų."],
        t_kampinis, d_kampinis, "Lentelė 185 × 40 kampe"),
     _z("uzpildyk", "Užpildyk kampinį įrašą", 10,
        "Neužpildytas kampinis įrašas - pirmas dalykas, ko pasiges dėstytojas.",
        ["Įrašyk darbo pavadinimą (aukštis 5) ir savo vardą (aukštis 2.5) į lentelės langelius."],
        [["Command:", "TEXT"], ["Specify start point:", "(spustelėk langelyje)"], ["Specify height:", "5"], ["Enter text:", "Detalė"]],
        ["Enter du kartus baigia TEXT komandą.", "Tekstą perkelti gali komanda MOVE."],
        t_uzpildyta, d_uzpildyti, "Bent 2 tekstai lentelėje"),
   ],
   "testas": [
     {"k": "Kiek milimetrų rėmelis nutolęs nuo kairiojo lapo krašto?", "v": ["5", "10", "20", "25"], "t": 2, "p": "Kairėje 20 mm segimui, kitur 5 mm."},
     {"k": "Kur dedamas kampinis įrašas?", "v": ["Viršuje kairėje", "Apačioje dešinėje", "Centre", "Bet kur"], "t": 1, "p": "Visada apatiniame dešiniame rėmelio kampe."},
     {"k": "Koks A3 lapo dydis?", "v": ["297 × 210", "420 × 297", "594 × 420", "500 × 300"], "t": 1, "p": "A3 = 420 × 297 mm, A4 = 210 × 297 mm."},
   ]},
  {"id": "2d", "pavadinimas": "2D brėžinys", "trukme": "~20 min.",
   "aprasas": "Sluoksniai, RECTANG, CIRCLE, ašys ir FILLET - nubraižysi plokštę su skylėmis.",
   "pabaiga": "Nubraižei 2D plokštę su skylėmis, ašimis ir suapvalintais kampais.",
   "zingsniai": [
     _z("sluoksniai2d", "Sukurk sluoksnius", 10,
        "Kontūras, ašys ir matmenys - skirtingi sluoksniai su skirtingomis linijomis, kaip reikalauja standartas.",
        ["LAYER → New Layer: KONTURAS (7), ASYS (1, linija CENTER), MATMENYS (3).", "Dukart spustelėk KONTURAS - jis taps aktyvus."],
        [["Command:", "LAYER"]],
        ["CENTER linijos tipą įkelk per Load...", "Spalvos numeris matomas lango apačioje."],
        t_sluoksniai, d_sluoksniai),
     _z("plokste", "Plokštės kontūras: RECTANG", 15,
        "Pradedam nuo 0,0 - taip lengviausia skaičiuoti kitas koordinates.",
        ["Sluoksnyje KONTURAS įvesk:"],
        [["Command:", "RECTANG"], ["Specify first corner:", "0,0"], ["Specify other corner:", "100,60"]],
        ["Koordinates rašyk su kableliu be tarpų.", "Dukart spustelėk pelės ratuką - matysi visą brėžinį."],
        t_plokste, d_plokste, "Stačiakampis 100 × 60"),
     _z("centras", "Skylė centre: CIRCLE", 15,
        "Centrinė skylė ø30. CIRCLE klausia spindulio, todėl įvedame pusę skersmens - 15.",
        ["Įvesk:"],
        [["Command:", "CIRCLE"], ["Specify center point:", "50,30"], ["Specify radius:", "15"]],
        ["Jei nori įvesti skersmenį - spausk D ir įvesk 30."],
        t_centras, d_centras, "Apskritimas ø30 centre"),
     _z("skyles", "4 tvirtinimo skylės", 15,
        "Skylės ø10 kampuose, 15 mm nuo kraštų.",
        ["Nubraižyk 4 apskritimus spinduliu 5:"],
        [["Command:", "CIRCLE"], ["Center:", "15,15"], ["Radius:", "5"], ["", "taip pat 85,15 · 15,45 · 85,45"]],
        ["Tuščias Enter (arba tarpas) pakartoja paskutinę komandą.", "Gali nubraižyti vieną ir nukopijuoti su COPY."],
        t_skyles, d_skyles, "4 skylės ø10"),
     _z("asys", "Ašys", 15,
        "Ašys rodo simetriją ir skylių centrus. Jos braižomos plona brūkšnine-taškine linija ir išsikiša už kontūro.",
        ["Pasirink sluoksnį ASYS ir nubraižyk dvi linijas:"],
        [["Command:", "LINE"], ["Specify first point:", "-5,30"], ["Specify next point:", "105,30"], ["Command:", "LINE"], ["Specify first point:", "50,-5"], ["Specify next point:", "50,65"]],
        ["Jei linija atrodo ištisinė - LTSCALE → 0.5.", "Ašys išsikiša 5 mm už kontūro."],
        t_asys, d_asys, "Horizontali ir vertikali ašis"),
     _z("fillet", "Suapvalink kampus: FILLET", 15,
        "Aštrūs kampai pavojingi ir negražūs. FILLET su parinktimi Polyline suapvalina visus 4 kampus iš karto.",
        ["Sluoksnyje KONTURAS įvesk:"],
        [["Command:", "FILLET"], ["Select first object or [Radius/Polyline]:", "R"], ["Specify fillet radius:", "10"],
         ["Select first object or [Radius/Polyline]:", "P"], ["Select 2D polyline:", "(spustelėk kontūrą)"]],
        ["Jei suapvalino tik vieną kampą - pamiršai P (Polyline). Atšauk: U.", "Spindulys 10 - kampai suapvalinti R10."],
        t_fillet, d_fillet, "4 kampai R10"),
   ],
   "testas": [
     {"k": "Kurį skaičių įvesti CIRCLE komandai, kai skylė ø30?", "v": ["30", "15", "60", "7.5"], "t": 1, "p": "CIRCLE klausia spindulio - pusė skersmens."},
     {"k": "Kokiame sluoksnyje braižomos ašys?", "v": ["KONTURAS", "MATMENYS", "ASYS", "0"], "t": 2, "p": "Ašys - atskirame sluoksnyje su CENTER linija."},
     {"k": "Kaip FILLET suapvalinti visus stačiakampio kampus iš karto?", "v": ["Spausti 4 kartus", "Parinktis P (Polyline)", "Parinktis T (Trim)", "Neįmanoma"], "t": 1, "p": "Polyline parinktis suapvalina visus polilinijos kampus."},
   ]},
  {"id": "schema", "pavadinimas": "Elektrinė schema su blokais", "trukme": "~25 min.",
   "aprasas": "Ženklas, atributai (ATTDEF), blokas (BLOCK), įterpimas (INSERT) ir aprašo lentelė (DATAEXTRACTION).",
   "pabaiga": "Moki kurti blokus su atributais ir sudaryti aprašo lentelę - tai pagrindas schemų darbui.",
   "zingsniai": [
     _z("naujas_sch", "Naujas brėžinys schemai", 5,
        "Schemą braižom švariame brėžinyje, kad nesusimaišytų su plokšte.",
        ["Sukurk naują brėžinį iš acadiso.dwt (kaip 1 pamokoje)."],
        [["Command:", "NEW"], ["Select template:", "acadiso.dwt"]],
        ["Ctrl+N - greitas naujas brėžinys."], None, d_naujas),
     _z("zenklas", "Rezistoriaus ženklas", 15,
        "Visi schemos ženklai vienodo ilgio - 20 mm. Rezistorius: stačiakampis 10 × 4 ir du išvadai.",
        ["Nubraižyk:"],
        [["Command:", "LINE"], ["Points:", "0,0 → 5,0"], ["Command:", "RECTANG"], ["Corners:", "5,-2 → 15,2"], ["Command:", "LINE"], ["Points:", "15,0 → 20,0"]],
        ["Ženklas ilgas 20: 5 + 10 + 5."],
        t_zenklas, d_zenklas, "Ženklas 20 × 4"),
     _z("attdef", "Atributai: ATTDEF", 20,
        "Atributas - laukelis bloke. POZ (R1, R2...) matomas schemoje, NUORODA (1 kΩ) - nematomas, bet patenka į aprašo lentelę.",
        ["Įvesk ATTDEF du kartus:"],
        [["ATTDEF 1:", "Tag: POZ · Prompt: Pozicinis žymuo · Default: R · taškas 7,4"],
         ["ATTDEF 2:", "pažymėk Invisible · Tag: NUORODA · taškas 7,-7"]],
        ["Tag - stulpelio vardas aprašo lentelėje.", "Invisible varnelė - kairėje lango pusėje (Mode)."],
        t_attdef, d_attdef, "Atributai POZ ir NUORODA"),
     _z("block", "Blokas: BLOCK", 20,
        "Blokas - ženklas, kurį nubraižai vieną kartą ir įterpi kiek nori. Pakeitus bloką, pasikeičia visi.",
        ["Įvesk BLOCK:"],
        [["Command:", "BLOCK"], ["Name:", "REZISTORIUS"], ["Base point:", "0,0"], ["Objects:", "(pažymėk ženklą ir abu atributus)"], ["", "Delete → OK"]],
        ["Base point 0,0 - kairysis išvadas, už jo „tempsi“ bloką.", "Delete - ženklas dingsta, bet blokas lieka atmintyje."],
        t_blokas, d_blokas, "Blokas REZISTORIUS su atributais"),
     _z("insert", "Įterpk 3 rezistorius: INSERT", 20,
        "Kiekvieną kartą įterpiant, AutoCAD paklaus atributų reikšmių.",
        ["INSERT → REZISTORIUS → padėk 3 kartus:"],
        [["Command:", "INSERT"], ["Name:", "REZISTORIUS"], ["Pozicinis žymuo:", "R1 (R2, R3)"], ["Nuoroda:", "1 kΩ"]],
        ["Jei atributų neklausia - ATTREQ → 1.", "Klaidingą reikšmę pataisysi dukart spustelėjęs ant bloko."],
        t_insert, d_insert, "R1, R2, R3"),
     _z("lentele", "Aprašo lentelė: DATAEXTRACTION", 25,
        "Aprašo lentelė sudaroma automatiškai iš blokų atributų - nereikia nieko perrašinėti ranka.",
        ["Įvesk DATAEXTRACTION ir eik per vedlį:"],
        [["Command:", "DATAEXTRACTION"], ["", "Create new → išsaugok .dxe"], ["Objects:", "tik REZISTORIUS"],
         ["Properties:", "Attribute (POZ, NUORODA)"], ["Output:", "Insert data extraction table"]],
        ["Count stulpelis - kiek tokių elementų.", "Lentelę padėk šalia schemos."],
        t_lentele, d_lentele, "Lentelė su rezistoriais"),
   ],
   "testas": [
     {"k": "Kodėl NUORODA atributas nustatomas Invisible?", "v": ["Kad neužimtų vietos schemoje, bet būtų lentelėje", "Kad jo nebūtų nieur", "Kad būtų raudonas", "Taip greičiau"], "t": 0,
      "p": "Nematomas schemoje, bet DATAEXTRACTION jį paima į aprašo lentelę."},
     {"k": "Ką daro BLOCK parinktis Delete?", "v": ["Ištrina bloką", "Ištrina pradinius objektus, blokas lieka atmintyje", "Ištrina atributus", "Nieko"], "t": 1,
      "p": "Objektai dingsta iš brėžinio, o blokas lieka - įterpsi jį INSERT."},
     {"k": "Kokio ilgio daromi schemos ženklai šioje pamokoje?", "v": ["10 mm", "15 mm", "20 mm", "50 mm"], "t": 2, "p": "Vienodas ilgis - laidus lengva sujungti."},
   ]},
  {"id": "matmenys", "pavadinimas": "Matmenys pagal standartą", "trukme": "~15 min.",
   "aprasas": "DIMSTYLE, DIMLINEAR, DIMDIAMETER - sužymėsi plokštės matmenis sluoksnyje MATMENYS.",
   "pabaiga": "Moki sukurti matmenų stilių ir sužymėti ilgius bei skersmenis.",
   "zingsniai": [
     _z("plokste_m", "Atsidaryk plokštę", 5,
        "Matmenis žymėsim 3 pamokos plokštei.",
        ["Atidaryk brėžinį su plokšte (OPEN) arba spausk „Parodyk man“ - nubraižysiu ją."],
        [["Command:", "OPEN"]], ["Plokštė: 100 × 60, centre ø30."], t_plokste_yra, d_plokste_yra),
     _z("dimstyle", "Matmenų stilius: DIMSTYLE", 20,
        "Matmenų stilius nustato teksto aukštį, rodykles ir tarpus. Pagal reikalavimus tekstas 3.5 mm.",
        ["DIMSTYLE → New → vardas ISO_MATMENYS → Continue:"],
        [["Symbols and Arrows:", "Arrow size 3"], ["Text:", "Text height 3.5 · Text placement: Above"], ["Primary Units:", "Precision 0"], ["", "OK → Set Current"]],
        ["Set Current - kad nauji matmenys naudotų šį stilių.", "Teksto stilius gali būti ISO_LT (6 pamoka)."],
        t_dimstyle, d_dimstyle, "ISO_MATMENYS aktyvus"),
     _z("ilgis", "Ilgis: DIMLINEAR 100", 15,
        "Linijinis matmuo - atstumas tarp dviejų taškų horizontaliai arba vertikaliai.",
        ["Pasirink sluoksnį MATMENYS. Įvesk:"],
        [["Command:", "DIMLINEAR"], ["First extension line origin:", "(apatinis kairys kampas)"], ["Second:", "(apatinis dešinys kampas)"], ["Dimension line location:", "(patrauk žemyn ~15)"]],
        ["Įjunk OSNAP (F3) - taškai pritrauks prie kampų.", "Suapvalintiems kampams naudok Endpoint ant lankų galų arba įvesk 0,0 ir 100,0."],
        t_ilgis, d_ilgis, "Matmuo 100"),
     _z("aukstis", "Aukštis: DIMLINEAR 60", 15,
        "Tas pats DIMLINEAR - tik pele traukiam į šoną, ir matmuo tampa vertikalus.",
        ["Įvesk DIMLINEAR dar kartą kairiajai kraštinei:"],
        [["Command:", "DIMLINEAR"], ["Points:", "0,0 → 0,60"], ["Location:", "(patrauk kairėn ~15)"]],
        ["Tarpas pakartoja paskutinę komandą."],
        t_aukstis, d_aukstis, "Matmuo 60"),
     _z("skersmuo", "Skersmuo: DIMDIAMETER", 15,
        "Skersmens matmuo automatiškai prideda ženklą ø.",
        ["Įvesk:"],
        [["Command:", "DIMDIAMETER"], ["Select arc or circle:", "(spustelėk ø30 apskritimą)"], ["Location:", "(padėk tekstą)"]],
        ["Mažoms skylėms parašyk 4x: DIMDIAMETER → M (Mtext) → 4x<>."],
        t_skersmuo, d_skersmuo, "Matmuo ø30"),
   ],
   "testas": [
     {"k": "Koks matmenų teksto aukštis šiuose brėžiniuose?", "v": ["2", "3.5", "7", "10"], "t": 1, "p": "3.5 mm - standartinis matmenų teksto aukštis."},
     {"k": "Kuria komanda žymimas vertikalus ilgis?", "v": ["DIMDIAMETER", "DIMLINEAR", "DIMRADIUS", "LINE"], "t": 1, "p": "DIMLINEAR - ir horizontalūs, ir vertikalūs matmenys."},
     {"k": "Kokiame sluoksnyje turi būti matmenys?", "v": ["KONTURAS", "ASYS", "MATMENYS", "0"], "t": 2, "p": "Atskiras sluoksnis - galima išjungti, keisti spalvą."},
   ]},
  {"id": "sriftai", "pavadinimas": "Šriftai ir tekstas", "trukme": "~10 min.",
   "aprasas": "Teksto stiliai pagal ISO 3098: isocp.shx ir ISOCPEUR su lietuviškomis raidėmis.",
   "pabaiga": "Moki sukurti ISO teksto stilius ir rašyti brėžinyje su lietuviškomis raidėmis.",
   "zingsniai": [
     _z("iso", "Teksto stilius ISO", 15,
        "Brėžiniuose naudojamas standartinis inžinerinis šriftas (ISO 3098), o ne Arial.",
        ["Įvesk STYLE → New → ISO:"],
        [["Command:", "STYLE"], ["New:", "ISO"], ["Font Name:", "isocp.shx"], ["", "Apply"]],
        ["Height palik 0 - aukštį pasirinksi rašydamas."],
        t_iso, d_sriftai, "Stilius ISO (isocp.shx)"),
     _z("isolt", "Stilius ISO_LT su lietuviškomis raidėmis", 20,
        "isocp.shx neturi ąčęėįšųūž. ISOCPEUR - tas pats ISO šriftas, bet su lietuviškomis raidėmis.",
        ["STYLE → New → ISO_LT:"],
        [["Font Name:", "ISOCPEUR"], ["Oblique Angle:", "15"], ["", "Apply → Set Current"]],
        ["Oblique 15° - pasvirasis ISO B tipo šriftas.", "Jei ISOCPEUR nėra - jis diegiamas kartu su AutoCAD, paieškok sąraše „isocpeur“."],
        t_isolt, d_sriftai, "Stilius ISO_LT (ISOCPEUR, 15°)"),
     _z("tekstas", "Parašyk „Brėžinys“", 15,
        "Patikrinsim, ar lietuviškos raidės matosi teisingai. Standartiniai aukščiai: 2.5, 3.5, 5, 7, 10.",
        ["Su aktyviu ISO_LT įvesk:"],
        [["Command:", "TEXT"], ["Specify start point:", "0,80"], ["Specify height:", "5"], ["Rotation:", "0"], ["Enter text:", "Brėžinys"]],
        ["Vietoj raidžių klaustukai? - stilius ne ISO_LT.", "Enter du kartus baigia TEXT."],
        t_tekstas, d_tekstas, "„Brėžinys“, aukštis 5, ISO_LT"),
   ],
   "testas": [
     {"k": "Kodėl isocp.shx netinka lietuviškam tekstui?", "v": ["Per mažas", "Neturi ąčęėįšųūž", "Per lėtas", "Tinka"], "t": 1, "p": "Naudok ISOCPEUR - jis turi lietuviškas raides."},
     {"k": "Kuris aukštis NĖRA standartinis?", "v": ["3.5", "5", "6", "7"], "t": 2, "p": "Standartiniai: 2.5, 3.5, 5, 7, 10, 14."},
     {"k": "Kokiu kampu pasviręs ISO B tipo šriftas?", "v": ["0°", "15°", "30°", "45°"], "t": 1, "p": "Oblique angle 15°."},
   ]},
]


# ------------------------------------------------------------------ pamokos
PAMOKOS = NAUJOS + [
  {
    "id": "pirmoji-3d",
    "pavadinimas": "Pirmoji 3D detalė",
    "aprasas": "BOX, CYLINDER, UNION, POLYGON, EXTRUDE, SUBTRACT, WEDGE, MIRROR3D - "
               "visos komandos iš praktinio darbo „Trimatis detalės modelis“.",
    "trukme": "~25 min.",
    "pabaiga": "Sukūrei pirmą tikrą 3D detalę - tokią pat kaip praktiniame darbe!",
    "zingsniai": [
      {"id": "pasiruosimas", "pavadinimas": "Pasiruošk darbo vietai", "xp": 5,
       "kodel": "3D modeliavimui AutoCAD turi atskirą darbo aplinką su 3D įrankiais. "
                "Izometrinis vaizdas leidžia matyti detalę iš karto iš trijų pusių.",
       "zingsniai": ["Atidaryk naują brėžinį iš šablono acadiso.dwt (milimetrai).",
                     "Apačioje dešinėje paspausk krumpliaratį ⚙ ir pasirink „3D Modeling“.",
                     "Viršuje: View → 3D Views → SE Isometric (arba ViewCube kampas)."],
       "komandos": [],
       "uzuominos": ["Krumpliaratis vadinasi „Workspace Switching“ - jis apatinėje juostoje.",
                     "Vaizdui gali įvesti komandą: -VIEW → SEISO"],
       "tikrinti": None, "demo": None},
      {"id": "sluoksniai", "pavadinimas": "Sukurk sluoksnius", "xp": 10,
       "kodel": "Sluoksniai - kaip skaidrės viena ant kitos. Kontūras, ašys ir matmenys turi skirtingas "
                "spalvas ir linijas, todėl brėžinys tvarkingas ir atitinka standartą.",
       "zingsniai": ["Įvesk LAYER ir spausk Enter - atsidarys Layer Properties Manager.",
                     "Mygtuku „New Layer“ sukurk: KONTURAS (spalva 7 - balta), ASYS (1 - raudona), MATMENYS (3 - žalia).",
                     "Sluoksniui ASYS paspausk ant „Continuous“ → Load... → CENTER → OK.",
                     "Dukart spustelėk KONTURAS, kad jis taptų aktyvus (žalia varnelė)."],
       "komandos": [["Command:", "LAYER"]],
       "uzuominos": ["Spalvos numeris rodomas paspaudus ant spalvos kvadratėlio - lango apačioje „Color: 7“.",
                     "Jei CENTER nėra sąraše - spausk Load..., susirask CENTER, pažymėk, OK."],
       "tikrinti": t_sluoksniai, "demo": d_sluoksniai},
      {"id": "box", "pavadinimas": "Pagrindas: BOX", "xp": 15,
       "kodel": "Kiekviena detalė prasideda nuo pagrindinio kūno. Pradėdami nuo taško 0,0,0 lengvai "
                "apskaičiuosime visas kitas koordinates.",
       "zingsniai": ["Įsitikink, kad aktyvus sluoksnis KONTURAS.",
                     "Įvesk BOX ir atsakyk į klausimus komandų eilutėje:"],
       "komandos": [["Command:", "BOX"], ["Specify first corner:", "0,0,0"],
                    ["Specify other corner:", "100,60,0"], ["Specify height:", "20"]],
       "uzuominos": ["Koordinates rašyk su kableliais be tarpų: 100,60,0",
                     "Jei pele spustelėsi ekrane vietoj įvedimo - dėžė atsiras ne ten. Tada ERASE ir iš naujo."],
       "tikslas": "Dėžė nuo (0,0,0) iki (100,60,20)",
       "tikrinti": t_deze, "demo": d_deze},
      {"id": "cylinder", "pavadinimas": "Cilindras: CYLINDER", "xp": 15,
       "kodel": "Cilindras stovės ant dėžės viršaus, todėl jo centro aukštis z = 20 - tiek, koks dėžės aukštis.",
       "zingsniai": ["Įvesk CYLINDER:"],
       "komandos": [["Command:", "CYLINDER"], ["Specify center point of base:", "50,30,20"],
                    ["Specify base radius:", "20"], ["Specify height:", "40"]],
       "uzuominos": ["Centras 50,30 - tai dėžės vidurys (100/2 = 50, 60/2 = 30).",
                     "Spindulys 20 reiškia skersmenį ø40."],
       "tikslas": "Cilindras ø40 nuo z=20 iki z=60",
       "tikrinti": t_cilindras, "demo": d_cilindras},
      {"id": "union", "pavadinimas": "Sujunk: UNION", "xp": 10,
       "kodel": "Kol kas tai du atskiri kūnai. UNION juos paverčia viena detale - kaip suklijuoti.",
       "zingsniai": ["Įvesk UNION, pele pažymėk dėžę ir cilindrą, spausk Enter."],
       "komandos": [["Command:", "UNION"], ["Select objects:", "(spustelėk dėžę ir cilindrą)"],
                    ["Select objects:", "Enter"]],
       "uzuominos": ["Po sujungimo, užvedus pelę, visa detalė pasišviečia kaip vienas objektas."],
       "tikslas": "Vienas kūnas, aukštis 60",
       "tikrinti": t_sujungta, "demo": d_sujungti},
      {"id": "polygon", "pavadinimas": "Šešiakampė prizmė: POLYGON + EXTRUDE", "xp": 20,
       "kodel": "Šešiakampę skylę darysime taip: nubraižysime šešiakampę prizmę ir vėliau ją „išpjausime“. "
                "POLYGON nubraižo plokščią figūrą, EXTRUDE ją ištempia į trečią matmenį.",
       "zingsniai": ["Nubraižyk šešiakampį:", "Tada ištempk jį į 60 aukštį:"],
       "komandos": [["Command:", "POLYGON"], ["Enter number of sides:", "6"],
                    ["Specify center of polygon:", "50,30,0"], ["Enter an option [Inscribed/Circumscribed]:", "I"],
                    ["Specify radius of circle:", "10"],
                    ["Command:", "EXTRUDE"], ["Select objects to extrude:", "(spustelėk šešiakampį) Enter"],
                    ["Specify height of extrusion:", "60"]],
       "uzuominos": ["Inscribed = šešiakampio kampai ant apskritimo (spindulys 10 iki kampo).",
                     "Jei šešiakampis neišsitempė - patikrink, ar EXTRUDE pasirinkai būtent jį, o ne detalę."],
       "tikslas": "Prizmė ties 50,30, aukštis 60",
       "tikrinti": t_prizme, "demo": d_prizme},
      {"id": "subtract", "pavadinimas": "Išpjauk: SUBTRACT", "xp": 20,
       "kodel": "SUBTRACT iš pirmojo objekto atima antrąjį. Svarbiausia - eilė: pirma IŠ KO, tada KĄ.",
       "zingsniai": ["Įvesk SUBTRACT. Pirma pažymėk detalę (Enter), tada prizmę (Enter)."],
       "komandos": [["Command:", "SUBTRACT"], ["Select solids... to subtract from:", "(detalė) Enter"],
                    ["Select solids... to subtract:", "(prizmė) Enter"]],
       "uzuominos": ["Jei detalė dingo, o liko prizmė - sumaišei eilę. Atšauk: U.",
                     "Pasuk vaizdą (Shift + vidurinis pelės mygtukas) - skylė turi matytis kiaurai."],
       "tikslas": "Viena detalė su šešiakampe kiauryme",
       "tikrinti": t_atimta, "demo": d_atimti},
      {"id": "wedge", "pavadinimas": "Standumo briauna: WEDGE", "xp": 20,
       "kodel": "Briauna sustiprina cilindro jungtį su pagrindu. WEDGE - pleištas: aukščiausias pirmojo kampo pusėje, "
                "nuolydis žemyn link antrojo kampo.",
       "zingsniai": ["Įvesk WEDGE:"],
       "komandos": [["Command:", "WEDGE"], ["Specify first corner:", "65,26,20"],
                    ["Specify other corner:", "90,34,20"], ["Specify height:", "30"]],
       "uzuominos": ["Briaunos storis 8: y nuo 26 iki 34 (30 - 4 ir 30 + 4).",
                     "x = 65 - briauna truputį įlenda į cilindrą, kad gerai susijungtų."],
       "tikslas": "Pleištas nuo (65,26,20) iki (90,34,50)",
       "tikrinti": t_pleistas, "demo": d_pleistas},
      {"id": "mirror", "pavadinimas": "Antra briauna: MIRROR3D", "xp": 20,
       "kodel": "Užuot braižę antrą briauną iš naujo, atspindime pirmąją per detalės vidurį. "
                "Veidrodžio plokštuma - YZ, einanti per x = 50.",
       "zingsniai": ["Įvesk MIRROR3D:"],
       "komandos": [["Command:", "MIRROR3D"], ["Select objects:", "(briauna) Enter"],
                    ["Specify first point of mirror plane [... YZ ...]:", "YZ"],
                    ["Specify point on YZ-plane:", "50,30,0"], ["Delete source objects? [Yes/No]:", "N"]],
       "uzuominos": ["YZ plokštuma stati ir statmena X ašiai - lygiai tokia, kokios reikia atspindžiui į kairę.",
                     "Atsakymas N (No) - kad liktų ir originali briauna."],
       "tikslas": "Dvi briaunos: dešinėje ir kairėje",
       "tikrinti": t_veidrodis, "demo": d_veidrodis},
      {"id": "final", "pavadinimas": "Galutinis UNION", "xp": 25,
       "kodel": "Paskutinis žingsnis - sujungti briaunas su detale. Po to detalė paruošta lapui ir pjūviams.",
       "zingsniai": ["Įvesk UNION ir pažymėk viską rėmeliu, Enter.",
                     "Pažiūrėk rezultatą: VSCURRENT → Conceptual."],
       "komandos": [["Command:", "UNION"], ["Select objects:", "(pažymėk viską) Enter"]],
       "uzuominos": ["Rėmelį tempk iš kairės į dešinę - pažymės viską, kas pilnai patenka į rėmelį."],
       "tikslas": "Viena detalė 100 × 60 × 60",
       "tikrinti": t_galutinis, "demo": d_galutinis},
    ],
    "testas": [
      {"k": "Kuria komanda iš vieno kūno išpjauni kitą?",
       "v": ["UNION", "SUBTRACT", "INTERSECT", "EXTRUDE"], "t": 1,
       "p": "SUBTRACT atima: pirma pažymi IŠ KO, tada KĄ."},
      {"k": "Ką reiškia POLYGON parinktis „Inscribed in circle“?",
       "v": ["Daugiakampio kampai yra ant apskritimo", "Apskritimas liečia daugiakampio kraštines",
             "Daugiakampis pasuktas 45°", "Daugiakampis tampa 3D"], "t": 0,
       "p": "Inscribed - įbrėžtas: kampai ant apskritimo. Circumscribed - apibrėžtas: kraštinės liečia apskritimą."},
      {"k": "Kodėl cilindro centras buvo 50,30,20, o ne 50,30,0?",
       "v": ["Taip gražiau", "Kad cilindras stovėtų ant dėžės viršaus (dėžės aukštis 20)",
             "AutoCAD neleidžia z = 0", "Kad būtų ø40"], "t": 1,
       "p": "Trečia koordinatė - aukštis Z. Dėžės viršus yra z = 20."},
      {"k": "MIRROR3D klausia „Delete source objects?“. Ką atsakyti, kad liktų abi briaunos?",
       "v": ["Yes", "No"], "t": 1, "p": "No - originalas lieka, atsiranda dar ir veidrodinė kopija."},
    ],
  },
]

ATEITYJE = [
    {"pavadinimas": "Pjūviai ir ketvirtinė išpjova", "aprasas": "SECTIONPLANE, VIEWBASE, VIEWSECTION"},
    {"pavadinimas": "Projekcijos iš 3D modelio", "aprasas": "VIEWBASE, VIEWPROJ, A3 lape"},
    {"pavadinimas": "Aksonometrija", "aprasas": "ISODRAFT, izometrinis apskritimas"},
]

PATARIMAI = [
    "Tarpo klavišas AutoCAD'e veikia kaip Enter - o tuščias tarpas pakartoja paskutinę komandą.",
    "Esc nutraukia bet kurią komandą. Užstrigai? Spausk Esc du kartus.",
    "U - atšaukia paskutinį veiksmą. Tai pats geriausias draugas mokantis!",
    "F8 įjungia ORTHO - linijos tik horizontalios ir vertikalios.",
    "Shift + vidurinis pelės mygtukas suka 3D vaizdą (orbit).",
    "Dukart spustelėk pelės ratuką - ZOOM Extents: parodo visą brėžinį.",
    "Komandų eilutėje užtenka pirmų raidžių: L = LINE, C = CIRCLE, EXT = EXTRUDE.",
    "VSCURRENT → C (Conceptual) parodo detalę spalvotą ir gražiai apšviestą.",
]


def pamoka(pid):
    for p in PAMOKOS:
        if p["id"] == pid:
            return p
    raise ValueError("Tokios pamokos nėra.")


# Komandų kortelės kartojimui be AutoCAD: (komanda, trumpinys, ką daro, pavyzdys, pamoka)
KORTELES = [
    ("NEW", "Ctrl+N", "Naujas brėžinys iš šablono. Mūsų brėžiniams - acadiso.dwt (milimetrai).", "NEW → acadiso.dwt", "failas"),
    ("UNITS", "UN", "Brėžinio vienetai ir tikslumas.", "UNITS → Decimal · 0 · Millimeters", "failas"),
    ("SAVEAS", "Ctrl+Shift+S", "Išsaugo brėžinį nauju vardu ar kitu formatu (DWG, DXF, senesnė versija).", "SAVEAS → Pirmasis_brezinys.dwg", "failas"),
    ("PLOT", "Ctrl+P", "Spausdina. Su DWG To PDF.pc3 sukuria PDF failą.", "PLOT → DWG To PDF.pc3 → Extents", "failas"),
    ("LAYOUTWIZARD", "", "Vedlys naujam lapui (Layout): spausdintuvas, popierius, orientacija.", "LAYOUTWIZARD → A3 → Landscape", "lapas"),
    ("RECTANG", "REC", "Stačiakampis pagal du priešingus kampus.", "RECTANG → 0,0 → 100,60", "2d"),
    ("LAYER", "LA", "Sluoksnių valdymas: kontūras, ašys, matmenys - skirtingos linijos ir spalvos.", "LAYER → New → KONTURAS", "2d"),
    ("LINE", "L", "Atkarpa (linija) tarp taškų. Enter baigia.", "LINE → -5,30 → 105,30", "2d"),
    ("CIRCLE", "C", "Apskritimas: centras ir spindulys (D - skersmuo).", "CIRCLE → 50,30 → 15", "2d"),
    ("FILLET", "F", "Suapvalina kampą. P (Polyline) - visus polilinijos kampus.", "FILLET → R → 10 → P", "2d"),
    ("COPY", "CO", "Nukopijuoja objektus iš vieno taško į kitą.", "COPY → objektas → bazinis taškas → naujas", "2d"),
    ("ATTDEF", "ATT", "Atributo apibrėžimas - laukelis bloke (pvz. POZ, NUORODA).", "ATTDEF → Tag: POZ", "schema"),
    ("BLOCK", "B", "Sukuria bloką iš objektų - ženklą, kurį galima įterpti daug kartų.", "BLOCK → REZISTORIUS → 0,0", "schema"),
    ("INSERT", "I", "Įterpia bloką ir paklausia atributų reikšmių.", "INSERT → REZISTORIUS → R1", "schema"),
    ("DATAEXTRACTION", "DX", "Ištraukia blokų atributus į lentelę - aprašo lentelė.", "DATAEXTRACTION → Insert table", "schema"),
    ("DIMSTYLE", "D", "Matmenų stilius: teksto aukštis, rodyklės, tikslumas.", "DIMSTYLE → ISO_MATMENYS → 3.5", "matmenys"),
    ("DIMLINEAR", "DLI", "Horizontalus arba vertikalus linijinis matmuo.", "DIMLINEAR → 0,0 → 100,0", "matmenys"),
    ("DIMDIAMETER", "DDI", "Skersmens matmuo su ženklu ø.", "DIMDIAMETER → apskritimas", "matmenys"),
    ("STYLE", "ST", "Teksto stilius: šriftas (isocp.shx, ISOCPEUR), pasvirimas.", "STYLE → ISO_LT → ISOCPEUR → 15°", "sriftai"),
    ("TEXT", "DT", "Vienos eilutės tekstas: taškas, aukštis, kampas.", "TEXT → 0,80 → 5 → 0 → Brėžinys", "sriftai"),
    ("BOX", "", "3D stačiakampis gretasienis (dėžė).", "BOX → 0,0,0 → 100,60,0 → 20", "pirmoji-3d"),
    ("CYLINDER", "CYL", "3D cilindras: pagrindo centras, spindulys, aukštis.", "CYLINDER → 50,30,0 → 15 → 40", "pirmoji-3d"),
    ("UNION", "UNI", "Sujungia kelis 3D kūnus į vieną.", "UNION → pažymėk kūnus → Enter", "pirmoji-3d"),
    ("SUBTRACT", "SU", "Iš vieno kūno atima kitą (skylės, grioveliai).", "SUBTRACT → iš ko → ką atimti", "pirmoji-3d"),
    ("EXTRUDE", "EXT", "Ištempia 2D kontūrą į 3D kūną.", "EXTRUDE → kontūras → aukštis", "pirmoji-3d"),
    ("MIRROR3D", "", "Veidrodinis atspindys 3D erdvėje per plokštumą.", "MIRROR3D → YZ → taškas", "pirmoji-3d"),
]


def viesai():
    """Pamokos be Python funkcijų - siuntimui į sąsają."""
    rez = []
    for p in PAMOKOS:
        z = [{k: v for k, v in s.items() if k not in ("tikrinti", "demo")} |
             {"tikrinama": s["tikrinti"] is not None, "demonstruojama": s["demo"] is not None}
             for s in p["zingsniai"]]
        rez.append({k: v for k, v in p.items() if k != "zingsniai"} | {"zingsniai": z})
    return {"pamokos": rez, "ateityje": ATEITYJE, "patarimai": PATARIMAI,
            "korteles": [dict(zip(("k", "trump", "ka", "pvz", "pamoka"), k)) for k in KORTELES]}

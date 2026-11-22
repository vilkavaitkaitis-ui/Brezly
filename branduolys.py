r"""
Brėžly Pilotas - AutoCAD valdymas per Python: 2D, 3D ir AI (nuotrauka arba tekstas).

Reikia:
    - Windows ir pilnas AutoCAD (ne LT)
    - Python 3
    - pip install pywin32
    - AI funkcijoms (nebūtina): pip install anthropic
      ir API raktas iš https://console.anthropic.com, įklijuotas į api_raktas.txt

Paleidimas (AutoCAD turi būti atidarytas):
    du kartus spausk PALEISTI.bat
    arba: python branduolys.py [detale_3d.txt]

Programoje parašyk "pagalba" - pamatysi visas komandas.
"""

import base64
import math
import os
import sys
import time

try:
    import pythoncom
    import win32com.client
    IMPORTO_KLAIDA = ""
except ImportError as _e:   # ne Windows: sąsają ir tikrinimą galima kurti bei testuoti be AutoCAD
    pythoncom = win32com = None
    IMPORTO_KLAIDA = str(_e) or _e.__class__.__name__   # Windows'e - sugadintas pywin32: parodoma būsenoje

VERSIJA = "1.4 (2026-11-09)"
MODELIS = "claude-sonnet-5-5"

# ---------------------------------------------------------------------------
# Komandų sąrašas: vardas -> (naudojimas, aprašymas, grupė)
# Iš jo sudaroma pagalba ir AI instrukcija.
# ---------------------------------------------------------------------------
KOMANDOS = {
    # 2D
    "linija":       ("linija x1 y1 x2 y2", "tiesi linija", "2D"),
    "apskritimas":  ("apskritimas x y r", "apskritimas", "2D"),
    "lankas":       ("lankas x y r pradzia pabaiga", "lankas, kampai laipsniais prieš laikrodžio rodyklę", "2D"),
    "staciakampis": ("staciakampis x y plotis aukstis", "stačiakampis nuo kairio apatinio kampo", "2D"),
    "daugiakampis": ("daugiakampis x1 y1 x2 y2 x3 y3 ...", "uždaras daugiakampis iš taškų", "2D"),
    "tekstas":      ("tekstas x y aukstis tekstas", "užrašas", "2D"),
    # 3D
    "naujas":       ("naujas", "pradėti naują 3D detalę", "3D"),
    "deze":         ("deze x y z plotis ilgis aukstis [kampas]", "stačiakampis gretasienis nuo kampo (x,y,z); kampas - pasukimas apie centrą", "3D"),
    "cilindras":    ("cilindras x y z r aukstis", "stačias cilindras, (x,y) centras, z apačia", "3D"),
    "cilindrasy":   ("cilindrasy x y0 z r ilgis", "gulintis cilindras išilgai Y ašies nuo y0", "3D"),
    "pleistas":     ("pleistas x y z plotis ilgis aukstis +x|-x", "nuožulnus kūnas; +x/-x - kurioje pusėje aukštoji dalis", "3D"),
    "sesiakampis":  ("sesiakampis x y z plotis_tarp_briaunu aukstis [kampas]", "stati šešiakampė prizmė, (x,y) centras; kampas 90 - plokšti šonai kairėje/dešinėje", "3D"),
    "profilis":     ("profilis y0 gylis x1 z1 x2 z2 ...", "daugiakampis XZ plokštumoje, ištemptas per Y", "3D"),
    "namas":        ("namas [x y plotis ilgis aukstis]", "3D namas su stogu ir durimis", "3D"),
    "vaizdas3d":    ("vaizdas3d", "pasukti vaizdą į 3D", "3D"),
    "vaizdas2d":    ("vaizdas2d", "grįžti į vaizdą iš viršaus", "3D"),
    "ketvirtine":   ("ketvirtine [atstumas]", "detalės kopija su ketvirtine išpjova šalia (aksonometrijai)", "3D"),
    # Elektrinės schemos
    "remelis":      ("remelis A4|A3|A2|A1|A0 [x y]", "lapo rėmelis MODEL erdvėje (paraštė kairėje 20, kitur 5)", "Lapai"),
    "remelis_a4":   ("remelis_a4", "A4 lapo rėmelis (tas pats kaip: remelis A4)", "Schemos"),
    "kampinis":     ("kampinis [darbo pavadinimas]", "kampinio įrašo blokas su atributais (išsaugomas ir kaip išorinis .dwg)", "Schemos"),
    "elementas":    ("elementas TIPAS x y kampas POZ [nuoroda]", "schemos ženklas-blokas; kontaktai (x,y) ir 20 mm toliau kampo kryptimi", "Schemos"),
    "laidas":       ("laidas x1 y1 x2 y2 [x3 y3 ...]", "jungiamasis laidas per taškus", "Schemos"),
    "mazgas":       ("mazgas x y", "laidų sujungimo taškas", "Schemos"),
    "aprasas":      ("aprasas [x y]", "elementų aprašo lentelė iš blokų atributų (numatyta - virš kampinio įrašo)", "Schemos"),
    "elementai":    ("elementai", "galimų ženklų (TIPAS) sąrašas", "Schemos"),
    # Lapai
    "lapas":        ("lapas A4|A3|A2|A1|A0 [lapo pavadinimas]", "lapas PAPER erdvėje (DWG To PDF), rėmelis ir kampinis įrašas", "Lapai"),
    "lapas_a3":     ("lapas_a3 [lapo pavadinimas]", "A3 lapas PAPER erdvėje (tas pats kaip: lapas A3)", "Lapai"),
    # Tvarka
    "sluoksnis":    ("sluoksnis vardas [spalva]", "sukurti/įjungti sluoksnį (spalva 1-255: 1 raudona, 3 žalia, 5 mėlyna)", "Tvarka"),
    "sluoksniai":   ("sluoksniai", "sukurti KONTURAS, ASYS, MATMENYS, NEMATOMOS sluoksnius", "Tvarka"),
    "sriftai":      ("sriftai", "ISO teksto stiliai (ISO, ISO_K, ISO_LT) ir matmenų stilius ISO_MATMENYS", "Tvarka"),
    "zoom":         ("zoom", "parodyti viską", "Tvarka"),
    "atsaukti":     ("atsaukti", "atšaukti paskutinį veiksmą", "Tvarka"),
    "isvalyti":     ("isvalyti", "ištrinti viską iš brėžinio (paklaus patvirtinimo)", "Tvarka"),
    # Failai
    "failas":       ("failas kelias\\iki\\komandos.txt", "įvykdyti komandas iš failo", "Failai"),
    "irasyti":      ("irasyti kelias\\iki\\failo.txt", "išsaugoti šios sesijos komandas į failą", "Failai"),
    "issaugoti":    ("issaugoti vardas[.dwg|.dxf|.pdf] [2018|2013|2010|2007|2004]", "išsaugoti brėžinį norimu formatu", "Failai"),
    "naujas_failas": ("naujas_failas [sablonas.dwt]", "naujas brėžinys iš šablono (numatyta acadiso.dwt)", "Failai"),
    # AI
    "foto":         ("foto kelias\\iki\\nuotraukos.jpg [pastaba]", "AI nubraižo pagal nuotrauką ar brėžinį", "AI"),
    "ai":           ("ai aprašymas laisvu tekstu", "AI nubraižo pagal aprašymą", "AI"),
    # Kita
    "komanda":      ("komanda <AutoCAD komanda>", "siųsti komandą tiesiai į AutoCAD", "Kita"),
    "pagalba":      ("pagalba", "šis sąrašas", "Kita"),
    "baigti":       ("baigti", "išeiti", "Kita"),
}

# Komandos, kurias gali naudoti AI ir kurios įrašomos į istoriją
BRAIZYMO = ({k for k, v in KOMANDOS.items() if v[2] in ("2D", "3D", "Schemos")}
            | {"sluoksnis", "sluoksniai", "lapas_a3", "lapas", "remelis"})
KUNAI = ("deze", "cilindras", "cilindrasy", "pleistas", "sesiakampis", "profilis")

# Sluoksniai pagal inžinerinės grafikos reikalavimus: vardas, spalva, linijos tipas, storis (0,01 mm)
STANDARTINIAI_SLUOKSNIAI = [
    ("KONTURAS", 7, "Continuous", 50),
    ("ASYS", 1, "CENTER", 18),
    ("MATMENYS", 3, "Continuous", 18),
    ("NEMATOMOS", 5, "HIDDEN", 25),
    ("BRUKSNIAI", 8, "Continuous", 18),      # pjūvių brūkšniavimas - plona linija
]


def pagalbos_tekstas():
    eilutes, grupe = [], None
    for vardas, (naud, apr, gr) in KOMANDOS.items():
        if gr != grupe:
            eilutes.append(f"\n--- {gr} ---")
            grupe = gr
        eilutes.append(f"  {naud:<44} {apr}")
    eilutes.append("\n3D komandos su minusu priekyje (pvz. -cilindras) IŠPJAUNA iš detalės.")
    eilutes.append("Kablelis skaičiuose tinka: 2,5 = 2.5")
    return "\n".join(eilutes)


# ---------------------------------------------------------------------------
# Elektrinių schemų ženklai. Visi 20 mm ilgio, kontaktai (0,0) ir (20,0).
# Primityvai: L linija x1 y1 x2 y2 | R stačiakampis x y plotis aukštis |
#             C apskritimas x y r | A lankas x y r nuo iki(°) | T tekstas x y h tekstas
# Reikšmė: (pusė aukščio, primityvai, pavadinimas aprašo lentelei)
# ---------------------------------------------------------------------------
SIMBOLIAI = {
    "REZISTORIUS": (2, [("L", 0, 0, 5, 0), ("L", 15, 0, 20, 0), ("R", 5, -2, 10, 4)],
                    "Rezistorius"),
    "KONDENSATORIUS": (4, [("L", 0, 0, 9, 0), ("L", 11, 0, 20, 0),
                           ("L", 9, -4, 9, 4), ("L", 11, -4, 11, 4)], "Kondensatorius"),
    "DIODAS": (3, [("L", 0, 0, 7, 0), ("L", 13, 0, 20, 0), ("L", 7, -3, 7, 3),
                   ("L", 7, 3, 13, 0), ("L", 7, -3, 13, 0), ("L", 13, -3, 13, 3)], "Diodas"),
    "LEMPUTE": (4, [("L", 0, 0, 6, 0), ("L", 14, 0, 20, 0), ("C", 10, 0, 4),
                    ("L", 7.17, 2.83, 12.83, -2.83), ("L", 7.17, -2.83, 12.83, 2.83)],
                "Lemputė"),
    "JUNGIKLIS": (4, [("L", 0, 0, 6, 0), ("L", 6, 0, 13.5, 4), ("L", 14, 0, 20, 0)],
                  "Jungiklis"),
    "SAUGIKLIS": (2, [("L", 0, 0, 20, 0), ("R", 5, -2, 10, 4)], "Saugiklis"),
    "RITE": (2, [("L", 0, 0, 4, 0), ("A", 6, 0, 2, 0, 180), ("A", 10, 0, 2, 0, 180),
                 ("A", 14, 0, 2, 0, 180), ("L", 16, 0, 20, 0)], "Induktyvumo ritė"),
    "MAITINIMAS": (5, [("L", 0, 0, 9, 0), ("L", 9, -5, 9, 5), ("L", 11, -2.5, 11, 2.5),
                       ("L", 11, 0, 20, 0)], "Galvaninis elementas"),
    "VARIKLIS": (5, [("L", 0, 0, 5, 0), ("L", 15, 0, 20, 0), ("C", 10, 0, 5),
                     ("T", 8.2, -1.75, 3.5, "M")], "Elektros variklis"),
}
TEKSTO_H = 3.5


def braizyti_primityvus(talpa, primityvai, dx=0.0, dy=0.0):
    """Nubraižo primityvus bloke arba ModelSpace."""
    for p in primityvai:
        t = p[0]
        if t == "L":
            talpa.AddLine(taskas(p[1] + dx, p[2] + dy), taskas(p[3] + dx, p[4] + dy))
        elif t == "R":
            x, y, w, h = p[1] + dx, p[2] + dy, p[3], p[4]
            kampai = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
            for (ax, ay), (bx, by) in zip(kampai, kampai[1:] + kampai[:1]):
                talpa.AddLine(taskas(ax, ay), taskas(bx, by))
        elif t == "C":
            talpa.AddCircle(taskas(p[1] + dx, p[2] + dy), p[3])
        elif t == "A":
            talpa.AddArc(taskas(p[1] + dx, p[2] + dy), p[3], math.radians(p[4]), math.radians(p[5]))
        elif t == "T":
            talpa.AddText(p[4], taskas(p[1] + dx, p[2] + dy), p[3])


# Lapų formatai: plotis, aukštis (mm), DWG To PDF popieriaus pavadinimas
FORMATAI = {
    "A4": (210, 297, "ISO_full_bleed_A4_(210.00_x_297.00_MM)"),
    "A3": (420, 297, "ISO_full_bleed_A3_(420.00_x_297.00_MM)"),
    "A2": (594, 420, "ISO_full_bleed_A2_(594.00_x_420.00_MM)"),
    "A1": (841, 594, "ISO_full_bleed_A1_(841.00_x_594.00_MM)"),
    "A0": (1189, 841, "ISO_full_bleed_A0_(1189.00_x_841.00_MM)"),
}


def formatas_is(args, numatytas):
    """Ištraukia formatą (A0-A4) iš argumentų. Grąžina (formatas, likę argumentai)."""
    for i, a in enumerate(args):
        if a.upper() in FORMATAI:
            return a.upper(), args[:i] + args[i + 1:]
    return numatytas, list(args)


# Brėžinių šablonai: pirmas - numatytasis
SABLONAI = [
    ("acadiso.dwt", "acadiso.dwt - metrinis, milimetrai (rekomenduojama)"),
    ("acadiso3D.dwt", "acadiso3D.dwt - metrinis 3D modeliavimui"),
    ("acad.dwt", "acad.dwt - coliai (imperinis)"),
]

# Išsaugojimo formatai: raktas -> (plėtinys, AcSaveAsType, aprašymas)
ISSAUGOJIMO_FORMATAI = {
    "dwg":     (".dwg", 64, "DWG (AutoCAD 2018 ir naujesni)"),
    "dwg2013": (".dwg", 60, "DWG 2013"),
    "dwg2010": (".dwg", 48, "DWG 2010"),
    "dwg2007": (".dwg", 36, "DWG 2007"),
    "dwg2004": (".dwg", 24, "DWG 2004 (seniems AutoCAD)"),
    "dxf":     (".dxf", 65, "DXF (kitoms CAD programoms)"),
    "pdf":     (".pdf", None, "PDF (spausdinimui)"),
}

# ISO teksto stiliai: vardas, šriftas, pasvirimas (°), ar TrueType
ISO_STILIAI = [
    ("ISO", "isocp.shx", 0, False),
    ("ISO_K", "isocp.shx", 15, False),          # pasvirasis (ISO 3098 B tipas)
    ("ISO_LT", "ISOCPEUR", 15, True),            # su lietuviškomis raidėmis
]
TEKSTO_AUKSCIAI = (2.5, 3.5, 5, 7, 10, 14)     # ISO 3098 rekomenduojami aukščiai, mm


def naujas_brezinys(acad, sablonas="acadiso.dwt"):
    """Sukuria naują brėžinį iš šablono. Grąžina dokumentą."""
    bandymai = [sablonas]
    if not os.path.isabs(sablonas):
        try:
            bandymai.append(os.path.join(acad.Preferences.Files.TemplateDwgPath, sablonas))
        except Exception:
            pass
    for kelias in bandymai:
        try:
            doc = kartoti(lambda: acad.Documents.Add(kelias))
            print(f"Naujas brėžinys iš šablono: {os.path.basename(kelias)}")
            return doc
        except Exception:
            continue
    print(f"  Šablono {sablonas} neradau - kuriu su numatytuoju šablonu.")
    return kartoti(lambda: acad.Documents.Add())


# Kampinio įrašo lentelė 185 x 40 (atskaitos taškas - apatinis kairys kampas)
KAMPINIS_GEOMETRIJA = [
    ("R", 0, 0, 185, 40), ("L", 65, 0, 65, 40),
    ("L", 0, 8, 65, 8), ("L", 0, 16, 65, 16), ("L", 0, 24, 65, 24), ("L", 0, 32, 65, 32),
    ("L", 20, 0, 20, 40), ("L", 45, 0, 45, 40),
    ("L", 65, 15, 185, 15), ("L", 105, 0, 105, 15), ("L", 145, 0, 145, 15),
    ("T", 1, 34.5, 2.5, "Pareigos"), ("T", 21, 34.5, 2.5, "Vardas, pavardė"),
    ("T", 46, 34.5, 2.5, "Data"), ("T", 1, 26.5, 2.5, "Braižė"), ("T", 1, 18.5, 2.5, "Tikrino"),
    ("T", 67, 11, 2.5, "Mastelis"), ("T", 107, 11, 2.5, "Lapas"), ("T", 147, 11, 2.5, "Grupė"),
]
# (žymė, raginimas, x, y, aukštis, numatyta reikšmė)
KAMPINIS_ATRIBUTAI = [
    ("PAVADINIMAS", "Darbo pavadinimas", 70, 25, 5, ""),
    ("BRAIZE", "Braižė (vardas, pavardė)", 21, 26, 3, ""),
    ("TIKRINO", "Tikrino (vardas, pavardė)", 21, 18, 3, ""),
    ("DATA", "Data", 46, 26, 2.5, ""),
    ("MASTELIS", "Mastelis", 67, 3, 3.5, "-"),
    ("LAPAS", "Lapas", 107, 3, 3.5, "1"),
    ("GRUPE", "Grupė", 147, 3, 3.5, ""),
]


# ---------------------------------------------------------------------------
# Pagalbinės funkcijos
# ---------------------------------------------------------------------------
def taskas(x, y, z=0.0):
    """AutoCAD COM nori taškų kaip double masyvo."""
    return win32com.client.VARIANT(
        pythoncom.VT_ARRAY | pythoncom.VT_R8, (float(x), float(y), float(z)))


def skaiciai(args, kiek, cmd):
    """Paverčia argumentus skaičiais; jei netinka - parodo, kaip teisingai."""
    try:
        if len(args) < kiek:
            raise ValueError
        return [float(a.replace(",", ".")) for a in args[:kiek]]
    except ValueError:
        raise ValueError(f"Reikia: {KOMANDOS[cmd][0]}") from None


def visi_skaiciai(args, cmd, poromis=True, min_kiek=6):
    try:
        reiksmes = [float(a.replace(",", ".")) for a in args]
    except ValueError:
        raise ValueError(f"Reikia: {KOMANDOS[cmd][0]}") from None
    if len(reiksmes) < min_kiek or (poromis and len(reiksmes) % 2):
        raise ValueError(f"Reikia: {KOMANDOS[cmd][0]}")
    return reiksmes


def programos_aplankas():
    """Aplankas su programos failais (.txt, api_raktas.txt). Veikia ir .exe versijoje."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


# AutoCAD užimtas ir atmeta kvietimą - tada verta palaukti ir pabandyti dar kartą
ATMESTA = (-2147418111, -2147417846)   # RPC_E_CALL_REJECTED, RPC_E_SERVERCALL_RETRYLATER


def atmesta(klaida):
    return bool(getattr(klaida, "args", None)) and klaida.args[0] in ATMESTA


def kartoti(f, bandymu=20, pauze=0.5):
    """Kviečia f(); jei AutoCAD užimtas - laukia ir bando iš naujo."""
    for i in range(bandymu):
        try:
            return f()
        except Exception as e:
            if atmesta(e) and i < bandymu - 1:
                time.sleep(pauze)
                continue
            raise


def _versiju_progid():
    """Įdiegtų AutoCAD versijų COM vardai, naujausi pirma, pvz. AutoCAD.Application.25.1 (2026), .25 (2025).
    Bendras „AutoCAD.Application“ rodo tik į paskutinę įdiegtą versiją - jei atidaryta kita, be šių neprisijungtume."""
    if _PROGID["sar"] is not None:
        return _PROGID["sar"]
    sar = []
    try:
        import winreg
        versijos = set()
        for sakn in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(sakn, r"SOFTWARE\Autodesk\AutoCAD") as k:
                    i = 0
                    while True:
                        try:
                            v = winreg.EnumKey(k, i)
                        except OSError:
                            break
                        i += 1
                        try:
                            versijos.add(tuple(int(x) for x in v.lstrip("Rr").split(".")[:2]))
                        except ValueError:
                            pass
            except OSError:
                pass
        for maj, *mn in sorted(versijos, reverse=True):
            for vardas in ([f"AutoCAD.Application.{maj}.{mn[0]}"] if mn and mn[0] else []) + [f"AutoCAD.Application.{maj}"]:
                try:
                    winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, vardas).Close()
                    sar.append(vardas)
                except OSError:
                    pass
    except ImportError:
        pass
    _PROGID["sar"] = sar
    return sar


_PROGID = {"sar": None}


def rasti_atidaryta():
    """Jau atidarytas AutoCAD (pats nepaleidžia). Klaida - paskutinė COM klaida (pagal ją paaiškinama priežastis)."""
    if win32com is None:
        raise RuntimeError("Trūksta pywin32: " + IMPORTO_KLAIDA)
    klaida = None
    for vardas in ["AutoCAD.Application"] + [v for v in _versiju_progid() if v != "AutoCAD.Application"]:
        try:
            return win32com.client.GetActiveObject(vardas)
        except Exception as e:
            # „Invalid class string“ (versija neįdiegta) mažiau svarbi nei „Operation unavailable“
            if klaida is None or com_kodas(klaida) == CO_E_CLASSSTRING:
                klaida = e
    raise klaida


# COM klaidų kodai, pagal kuriuos paaiškinama, kodėl neprisijungiama
MK_E_UNAVAILABLE = -2147221021      # 0x800401E3: AutoCAD neužsiregistravęs (kraunasi arba kitos teisės)
CO_E_CLASSSTRING = -2147221005      # 0x800401F3: AutoCAD.Application neregistruotas (LT / sugadintas diegimas)
REGDB_E_CLASSNOTREG = -2147221164   # 0x80040154
E_ACCESSDENIED = -2147024891        # 0x80070005
NUTRUKO = (-2147023174, -2147417848, -2147023170)   # RPC serveris nepasiekiamas / atsijungta (AutoCAD uždarytas)


def com_kodas(klaida):
    """COM klaidos HRESULT (neigiamas sveikasis) arba None."""
    a = getattr(klaida, "args", None) or ()
    return a[0] if a and isinstance(a[0], int) else getattr(klaida, "hresult", None)


def uztikrinti_brezini(acad):
    """Kad būtų aktyvus brėžinys: AutoCAD pradžios (Start) lange brėžinių nėra arba nė vienas neaktyvus."""
    n = kartoti(lambda: acad.Documents.Count)
    if n == 0:
        kartoti(lambda: acad.Documents.Add())
        return
    try:
        acad.ActiveDocument.Name
    except Exception as e:
        if atmesta(e):
            raise
        kartoti(lambda: acad.Documents.Item(n - 1).Activate())


def prisijungti(paleisti=True, brezinys=True):
    """Prisijungia prie atidaryto AutoCAD; jei jo nėra ir paleisti=True - paleidžia.
    paleisti=False, kai acad.exe jau veikia, bet nepasiekiamas (kitos teisės) - antro AutoCAD nekuriame.
    brezinys=True - pasirūpina aktyviu brėžiniu (False - kai jį tuoj atidarysime ar sukursime patys)."""
    if win32com is None:
        raise RuntimeError("Trūksta pywin32 paketo (" + IMPORTO_KLAIDA + "). Įdiek Brėžly iš naujo.")
    try:
        acad = rasti_atidaryta()
        print("Prisijungta prie atidaryto AutoCAD.")
    except Exception:
        if not paleisti:
            raise
        print("AutoCAD neatidarytas, paleidžiu (gali užtrukti iki minutės)...")
        try:
            acad = win32com.client.Dispatch("AutoCAD.Application")
        except Exception:
            raise RuntimeError("Nepavyko rasti AutoCAD. Ar įdiegtas pilnas AutoCAD (ne LT)?") from None
    kartoti(lambda: setattr(acad, "Visible", True), bandymu=120)
    if brezinys:
        uztikrinti_brezini(acad)
    try:
        print("AutoCAD versija:", acad.Version)
    except Exception:
        pass
    return acad


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------
def ai_instrukcija():
    sarasas = "\n".join(f"  {KOMANDOS[k][0]}   - {KOMANDOS[k][1]}"
                        for k in KOMANDOS if k in BRAIZYMO)
    return f"""Tu esi AutoCAD braižytojas. Paversk vartotojo užduotį brėžiniu.
Atsakyk TIK komandomis, po vieną eilutėje, be paaiškinimų ir be ``` ženklų.
Komentarus, jei reikia, rašyk eilutėse, prasidedančiose #.

Galimos komandos:
{sarasas}

Taisyklės:
- 1 vienetas = 1 mm, jei vartotojas nenurodo kitaip.
- 2D: x į dešinę, y į viršų. 3D: x plotis, y gylis, z aukštis.
- 3D komandos su minusu priekyje (pvz. -cilindras, -deze) išpjauna iš detalės (skylės, grioveliai).
- 3D detalę pradėk komanda naujas, pirma pridėk visus kūnus, tada išpjauk skyles, pabaigoje vaizdas3d.
- Jei brėžinyje yra keli vaizdai (iš priekio, iš viršaus) - pagal juos sumodeliuok vieną 3D detalę,
  nebent vartotojas prašo 2D.
- Naudok matmenis iš brėžinio. Trūkstamus įvertink pagal proporcijas.
- Elektrinei schemai: remelis_a4, kampinis <pavadinimas>, tada elementai ir laidai
  (lapas A4 210x297 mm, schemą dėk tarp y=130 ir y=280, x tarp 25 ir 200), pabaigoje aprasas.
  Ženklų tipai: {", ".join(SIMBOLIAI)}. Kiekvienas ženklas 20 mm ilgio:
  kampas 0 - kontaktai (x,y) ir (x+20,y); kampas 90 - (x,y) ir (x,y+20).
  Laidus vesk tik horizontaliai/vertikaliai, sujungimuose dėk mazgas.
  Poziciniai žymenys: R rezistoriai, C kondensatoriai, VD diodai, HL lemputės,
  SA jungikliai, FU saugikliai, L ritės, GB maitinimas, M varikliai.
- Ne daugiau kaip 150 komandų."""


def gauti_rakta():
    """API raktas: iš aplinkos kintamojo arba iš failo api_raktas.txt programos aplanke."""
    raktas = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if raktas:
        return raktas
    failas = os.path.join(programos_aplankas(), "api_raktas.txt")
    if os.path.exists(failas):
        with open(failas, encoding="utf-8") as f:
            for eilute in f:
                if eilute.strip().startswith("sk-"):
                    return eilute.strip()
    return None


def paklausti_ai(turinys):
    raktas = gauti_rakta()
    if not raktas:
        raise RuntimeError("Nėra API rakto. Atsidaryk api_raktas.txt programos aplanke, "
                           "įklijuok raktą (prasideda sk-ant-) ir išsaugok.")
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("Neįdiegtas paketas. Įvesk: pip install anthropic") from None
    klientas = anthropic.Anthropic(api_key=raktas)
    atsakymas = klientas.messages.create(
        model=MODELIS,
        max_tokens=8000,
        system=ai_instrukcija(),
        messages=[{"role": "user", "content": turinys}],
    )
    return "".join(b.text for b in atsakymas.content if b.type == "text")


NUOTRAUKOS = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}


def nuotrauka_ai(kelias):
    pletinys = os.path.splitext(kelias)[1].lower()
    if pletinys not in NUOTRAUKOS:
        raise ValueError("Tinka tik jpg, png, webp arba gif nuotraukos.")
    with open(kelias, "rb") as f:
        duomenys = base64.standard_b64encode(f.read()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64",
            "media_type": NUOTRAUKOS[pletinys], "data": duomenys}}


# ---------------------------------------------------------------------------
# Pagrindinė klasė
# ---------------------------------------------------------------------------
class Braizytojas:
    def __init__(self, acad):
        self.acad = acad
        self.kunas = None        # dabartinė 3D detalė
        self.istorija = []       # įvykdytos braižymo komandos
        self.remelio_vieta = None            # (x0, y0, plotis, aukštis) paskutinio rėmelio MODEL erdvėje
        self.kampinio_duomenys = {}          # PAVADINIMAS, BRAIZE, TIKRINO, GRUPE, MASTELIS ...
        # patvirtinimo klausimas (konsolėje - input, lange - dialogas)
        self.patvirtinti = lambda klausimas: input(klausimas + " (taip/ne): ").strip().lower() == "taip"

    def ribos(self):
        """Dabartinės 3D detalės ribos ((x0,y0,z0),(x1,y1,z1)) arba None."""
        if self.kunas is None:
            return None
        try:
            mn, mx = kartoti(lambda: self.kunas.GetBoundingBox())
            return tuple(mn), tuple(mx)
        except Exception:
            return None

    def turinio_ribos(self, nuo=0):
        """Visų MODEL erdvės objektų nuo indekso 'nuo' ribos ((x0,y0),(x1,y1)) arba None."""
        ms = self.ms
        mn, mx = [float("inf")] * 2, [float("-inf")] * 2
        for i in range(nuo, kartoti(lambda: ms.Count)):
            try:
                a, b = kartoti(lambda: ms.Item(i).GetBoundingBox())
            except Exception:
                continue
            mn = [min(mn[0], a[0]), min(mn[1], a[1])]
            mx = [max(mx[0], b[0]), max(mx[1], b[1])]
        if mn[0] == float("inf"):
            return None
        return tuple(mn), tuple(mx)

    def virsus(self):
        """Dabartinės 3D detalės viršaus aukštis (z) arba None."""
        if self.kunas is None:
            return None
        try:
            return kartoti(lambda: self.kunas.GetBoundingBox())[1][2]
        except Exception:
            return None

    @property
    def doc(self):
        return self.acad.ActiveDocument

    @property
    def ms(self):
        return self.doc.ModelSpace

    def palaukti(self, laikas=20):
        """Laukia, kol AutoCAD baigs vykdyti siųstas komandas."""
        pabaiga = time.time() + laikas
        while time.time() < pabaiga:
            try:
                if self.acad.GetAcadState().IsQuiescent:
                    return
            except Exception as e:
                if not atmesta(e):
                    return      # ši AutoCAD versija neturi būsenos tikrinimo
            time.sleep(0.1)

    def _siusti(self, komanda):
        kartoti(lambda: self.doc.SendCommand(komanda))
        self.palaukti()

    def isversti(self, eilute):
        """Sakinys žodžiais -> programos komandos. Komandos lieka tokios pačios."""
        if not hasattr(self, "_kalba"):
            import kalba
            self._kalba = kalba.Kalba(KOMANDOS.keys(), virsus=self.virsus, ribos=self.ribos)
        komandos = self._kalba.sakinys(eilute)
        if not komandos:
            raise ValueError(f"Nesupratau: '{eilute}'. Rašyk 'pagalba' arba žr. INSTRUKCIJA.txt")
        return komandos

    def vykdyti_zodziais(self, eilute, saltinis="ranka", gylis=0):
        """Vykdo komandą arba sakinį žodžiais (pvz. 'dėžė 100x60x20')."""
        eilute = eilute.strip()
        if not eilute or eilute.startswith("#"):
            return
        komandos = self.isversti(eilute)
        if komandos != [eilute] and saltinis == "ranka":
            print("  → " + " | ".join(komandos))
        for k in komandos:
            self.vykdyti_saugiai(k, saltinis, gylis)

    def vykdyti_saugiai(self, eilute, saltinis="ranka", gylis=0):
        """Kaip vykdyti, bet jei AutoCAD užimtas - palaukia ir bando dar kartą."""
        return kartoti(lambda: self.vykdyti(eilute, saltinis, gylis), bandymu=10)

    # ----- 3D pagalbinės -----
    def sukurti_3d(self, tipas, args, cmd):
        ms = self.ms
        if tipas == "deze":
            x, y, z, dx, dy, dz = skaiciai(args, 6, cmd)
            c = (x + dx / 2, y + dy / 2, z + dz / 2)
            kunas = ms.AddBox(taskas(*c), dx, dy, dz)
            if len(args) > 6:
                kampas = skaiciai(args[6:], 1, cmd)[0]
                if kampas:
                    kunas.Rotate3D(taskas(*c), taskas(c[0], c[1], c[2] + 1), math.radians(kampas))
            return kunas
        if tipas == "cilindras":
            x, y, z, r, h = skaiciai(args, 5, cmd)
            return ms.AddCylinder(taskas(x, y, z + h / 2), r, h)
        if tipas == "cilindrasy":
            x, y0, z, r, L = skaiciai(args, 5, cmd)
            c = (x, y0 + L / 2, z)
            kunas = ms.AddCylinder(taskas(*c), r, L)
            kunas.Rotate3D(taskas(*c), taskas(c[0] + 1, c[1], c[2]), math.pi / 2)
            return kunas
        if tipas == "sesiakampis":
            # Šešiakampis = 3 stačiakampių (kraštinė x atstumas tarp briaunų), pasuktų po 60°, sąjunga
            x, y, z, F, h = skaiciai(args, 5, cmd)
            posukis = skaiciai(args[5:], 1, cmd)[0] if len(args) > 5 else 0.0
            s = F / math.sqrt(3)
            c = (x, y, z + h / 2)
            dalys = []
            for kampas in (posukis, posukis + 60, posukis + 120):
                d = ms.AddBox(taskas(*c), s, F, h)
                if kampas:
                    d.Rotate3D(taskas(*c), taskas(x, y, c[2] + 1), math.radians(kampas))
                dalys.append(d)
            dalys[0].Boolean(0, dalys[1])
            dalys[0].Boolean(0, dalys[2])
            return dalys[0]
        if tipas == "pleistas":
            x, y, z, dx, dy, dz = skaiciai(args, 6, cmd)
            kur = args[6].lower() if len(args) > 6 else "+x"
            c = (x + dx / 2, y + dy / 2, z + dz / 2)
            kunas = ms.AddWedge(taskas(*c), dx, dy, dz)
            # svorio centras pasislinkęs į aukštąją pusę - pagal tai tikrinam kryptį
            if (kunas.Centroid[0] > c[0]) != (kur == "+x"):
                kunas.Rotate3D(taskas(*c), taskas(c[0], c[1], c[2] + 1), math.pi)
            return kunas
        # profilis
        if len(args) < 8:
            raise ValueError(f"Reikia: {KOMANDOS[cmd][0]}")
        y0, g = skaiciai(args, 2, cmd)
        koord = tuple(visi_skaiciai(args[2:], cmd))
        pl = ms.AddLightWeightPolyline(win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8, koord))
        pl.Closed = True
        reg = None
        for masyvas in (win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, [pl]),
                        [pl], (pl,)):
            try:
                reg = ms.AddRegion(masyvas)[0]
                break
            except Exception:
                continue
        if reg is None:
            pl.Delete()
            raise RuntimeError("profilis šiame AutoCAD neveikia - naudok pleistas/deze/cilindrasy")
        kunas = ms.AddExtrudedSolid(reg, g, 0.0)
        pl.Delete()
        reg.Delete()
        kunas.Rotate3D(taskas(0, 0, 0), taskas(1, 0, 0), math.pi / 2)
        kunas.Move(taskas(0, 0, 0), taskas(0, y0 + g, 0))
        return kunas

    def pridek(self, obj, atimti):
        if self.kunas is None:
            if atimti:
                obj.Delete()
                raise RuntimeError("Nėra iš ko išpjauti - pirma sukurk kūną.")
            self.kunas = obj
        else:
            self.kunas.Boolean(2 if atimti else 0, obj)  # 0 = sujungti, 2 = atimti

    # ----- komandų vykdymas -----
    def vykdyti(self, eilute, saltinis="ranka", gylis=0):
        """saltinis: 'ranka', 'failas' arba 'ai'."""
        eilute = eilute.strip()
        if not eilute or eilute.startswith("#"):
            return
        dalys = eilute.split()
        cmd, args = dalys[0].lower(), dalys[1:]
        atimti = cmd.startswith("-")
        bazine = cmd.lstrip("-")

        if bazine not in KOMANDOS:
            raise ValueError(f"Nežinoma komanda '{cmd}'. Rašyk 'pagalba'.")
        if atimti and bazine not in KUNAI:
            raise ValueError("Minusas tinka tik 3D kūnams: " + ", ".join(KUNAI) + ".")
        if saltinis == "ai" and bazine not in BRAIZYMO:
            raise ValueError(f"AI negali naudoti komandos '{cmd}'.")

        doc, ms = self.doc, self.ms

        # ---- 3D kūnai ----
        if bazine in KUNAI:
            self.pridek(self.sukurti_3d(bazine, args, bazine), atimti)
            if saltinis == "ranka":
                print(("Išpjauta: " if atimti else "Pridėta: ") + bazine)

        # ---- 2D ----
        elif cmd == "linija":
            x1, y1, x2, y2 = skaiciai(args, 4, cmd)
            ms.AddLine(taskas(x1, y1), taskas(x2, y2))
        elif cmd == "apskritimas":
            x, y, r = skaiciai(args, 3, cmd)
            ms.AddCircle(taskas(x, y), r)
        elif cmd == "lankas":
            x, y, r, a1, a2 = skaiciai(args, 5, cmd)
            ms.AddArc(taskas(x, y), r, math.radians(a1), math.radians(a2))
        elif cmd == "staciakampis":
            x, y, w, h = skaiciai(args, 4, cmd)
            self._uzdaras([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
        elif cmd == "daugiakampis":
            v = visi_skaiciai(args, cmd)
            self._uzdaras(list(zip(v[0::2], v[1::2])))
        elif cmd == "tekstas":
            x, y, h = skaiciai(args, 3, cmd)
            if len(args) < 4:
                raise ValueError(f"Reikia: {KOMANDOS[cmd][0]}")
            ms.AddText(" ".join(args[3:]), taskas(x, y), h)

        # ---- 3D kita ----
        elif cmd == "naujas":
            self.kunas = None
            if saltinis == "ranka":
                print("Pradedama nauja detalė.")
        elif cmd == "namas":
            self._namas(args)
        elif cmd == "vaizdas3d":
            self._siusti("_-VIEW _SEISO ")
            self._siusti("_VSCURRENT _C ")
        elif cmd == "ketvirtine":
            self._ketvirtine(skaiciai(args, 1, cmd)[0] if args else None)
        elif cmd == "vaizdas2d":
            self._siusti("_-VIEW _TOP ")
            self._siusti("_VSCURRENT _2 ")

        # ---- tvarka ----
        elif cmd == "sluoksnis":
            if not args:
                raise ValueError(f"Reikia: {KOMANDOS[cmd][0]}")
            sl = doc.Layers.Add(args[0])
            if len(args) > 1:
                sl.Color = int(skaiciai(args[1:], 1, cmd)[0])
            doc.ActiveLayer = sl
            if saltinis == "ranka":
                print(f"Aktyvus sluoksnis: {args[0]}")
        elif cmd == "sluoksniai":
            self._sluoksniai()

        # ---- schemos ----
        elif cmd in ("lapas", "lapas_a3"):
            fmt, likę = formatas_is(args, "A3")
            self._lapas(fmt, " ".join(likę) or f"{fmt}_Lapas")
        elif cmd in ("remelis", "remelis_a4"):
            fmt, likę = formatas_is(args, "A4")
            x0, y0 = skaiciai(likę, 2, "remelis") if len(likę) >= 2 else (0.0, 0.0)
            self._remelis(fmt, x0, y0)
        elif cmd == "kampinis":
            self._kampinis(" ".join(args))
        elif cmd == "elementas":
            self._elementas(args)
        elif cmd == "laidas":
            v = visi_skaiciai(args, cmd, min_kiek=4)
            taskai = list(zip(v[0::2], v[1::2]))
            for (ax, ay), (bx, by) in zip(taskai, taskai[1:]):
                ms.AddLine(taskas(ax, ay), taskas(bx, by))
        elif cmd == "mazgas":
            x, y = skaiciai(args, 2, cmd)
            d = 1.6
            pl = ms.AddLightWeightPolyline(win32com.client.VARIANT(
                pythoncom.VT_ARRAY | pythoncom.VT_R8, (x - d / 4, y, x + d / 4, y)))
            pl.SetBulge(0, 1.0)
            pl.SetBulge(1, 1.0)
            pl.Closed = True
            pl.ConstantWidth = d / 2
        elif cmd == "aprasas":
            vieta = skaiciai(args, 2, cmd) if args else None
            self._aprasas(vieta)
        elif cmd == "elementai":
            print("Galimi ženklai (TIPAS):")
            for k, v in SIMBOLIAI.items():
                print(f"  {k:<16} {v[2]}")
            return
        elif cmd == "zoom":
            pass  # zoom daromas pabaigoje
        elif cmd == "atsaukti":
            self._siusti("_U ")
            print("Atšaukta.")
        elif cmd == "isvalyti":
            if saltinis != "ranka":
                raise ValueError("isvalyti galima tik ranka.")
            if self.patvirtinti("Ištrinti VISKĄ iš brėžinio?"):
                for i in range(ms.Count - 1, -1, -1):
                    ms.Item(i).Delete()
                self.kunas = None
                print("Brėžinys išvalytas.")

        # ---- failai ----
        elif cmd == "failas":
            if gylis > 3:
                raise RuntimeError("Per daug įdėtų failų.")
            self._is_failo(" ".join(args).strip('"'), gylis)
        elif cmd == "irasyti":
            kelias = " ".join(args).strip('"')
            if not kelias:
                raise ValueError(f"Reikia: {KOMANDOS[cmd][0]}")
            with open(kelias, "w", encoding="utf-8") as f:
                f.write("\n".join(self.istorija) + "\n")
            print(f"Įrašyta {len(self.istorija)} komandų į {kelias}")
        elif cmd == "issaugoti":
            if not args:
                raise ValueError(f"Reikia: {KOMANDOS[cmd][0]}")
            versija = None
            if args[-1] in ("2018", "2013", "2010", "2007", "2004"):
                versija, args = args[-1], args[:-1]
            vardas = " ".join(args).strip('"')
            ext = os.path.splitext(vardas)[1].lower()
            raktas = {".dxf": "dxf", ".pdf": "pdf"}.get(ext, "dwg")
            if raktas == "dwg" and versija and versija != "2018":
                raktas = "dwg" + versija
            self.issaugoti(vardas, raktas)
        elif cmd == "naujas_failas":
            sablonas = " ".join(args).strip('"') or SABLONAI[0][0]
            naujas_brezinys(self.acad, sablonas)
            self.palaukti()
            self.kunas = None
            self.remelio_vieta = None
        elif cmd == "sriftai":
            self._sriftai()

        # ---- AI ----
        elif cmd == "foto":
            if not args:
                raise ValueError(f"Reikia: {KOMANDOS[cmd][0]}")
            kelias, pastaba = self._kelias_ir_pastaba(args)
            tekstas = "Nubraižyk tai, kas šioje nuotraukoje."
            if pastaba:
                tekstas += " Pastaba: " + pastaba
            self._ai([nuotrauka_ai(kelias), {"type": "text", "text": tekstas}])
        elif cmd == "ai":
            if not args:
                raise ValueError(f"Reikia: {KOMANDOS[cmd][0]}")
            self._ai(" ".join(args))

        elif cmd == "komanda":
            self._siusti(" ".join(args) + " ")
        elif cmd == "pagalba":
            print(pagalbos_tekstas())
            return

        if bazine in BRAIZYMO:
            self.istorija.append(eilute)
        if saltinis == "ranka":
            try:
                kartoti(self.acad.ZoomExtents)
            except Exception:
                pass

    # ----- vidinės -----
    def _uzdaras(self, taskai):
        for (ax, ay), (bx, by) in zip(taskai, taskai[1:] + taskai[:1]):
            self.ms.AddLine(taskas(ax, ay), taskas(bx, by))

    def _namas(self, args):
        if args:
            x, y, w, l, h = skaiciai(args, 5, "namas")
        else:
            x, y, w, l, h = 0, 0, 6000, 8000, 3000
        ms = self.ms
        ms.AddBox(taskas(x + w / 2, y + l / 2, h / 2), w, l, h)
        sk = h * 0.6
        A, B = taskas(x, y, h), taskas(x + w, y, h)
        C, D = taskas(x + w, y + l, h), taskas(x, y + l, h)
        R1, R2 = taskas(x + w / 2, y, h + sk), taskas(x + w / 2, y + l, h + sk)
        ms.Add3DFace(A, R1, R2, D)
        ms.Add3DFace(B, C, R2, R1)
        ms.Add3DFace(A, B, R1, R1)
        ms.Add3DFace(D, C, R2, R2)
        dw, dh, ds = w * 0.15, h * 0.67, w * 0.02
        ms.AddBox(taskas(x + w / 2, y - ds / 2, dh / 2), dw, ds, dh)
        self._siusti("_-VIEW _SEISO ")
        self._siusti("_VSCURRENT _C ")

    def issaugoti(self, vardas, raktas="dwg"):
        """Išsaugo brėžinį: raktas iš ISSAUGOJIMO_FORMATAI."""
        ext, tipas, aprasas = ISSAUGOJIMO_FORMATAI[raktas]
        kelias = os.path.abspath(vardas)
        if os.path.splitext(kelias)[1].lower() != ext:
            kelias += ext
        os.makedirs(os.path.dirname(kelias), exist_ok=True)
        doc = self.doc
        if raktas == "pdf":
            self._pdf(kelias)
            return kelias
        try:
            kartoti(lambda: doc.SaveAs(kelias, tipas))
        except Exception:
            if raktas != "dwg":
                raise
            kartoti(lambda: doc.SaveAs(kelias))
        self.palaukti()
        print(f"Išsaugota ({aprasas}): {kelias}")
        return kelias

    def _pdf(self, kelias):
        doc = self.doc
        try:
            doc.SetVariable("BACKGROUNDPLOT", 0)     # spausdinti iš karto, ne fone
        except Exception:
            pass
        lapas = doc.ActiveLayout
        try:
            lapas.ConfigName = "DWG To PDF.pc3"
            lapas.RefreshPlotDeviceInfo()
            if lapas.ModelType:                       # MODEL erdvė - viskas, ištempta į lapą
                lapas.PlotType = 1                    # acExtents
                lapas.StandardScale = 0               # acScaleToFit
                lapas.CenterPlot = True
            else:
                lapas.PlotType = 5                    # acLayout
        except Exception as e:
            print(f"  Spausdinimo nustatymų pakeisti nepavyko: {e}")
        if os.path.exists(kelias):
            os.remove(kelias)
        kartoti(lambda: doc.Plot.PlotToFile(kelias, "DWG To PDF.pc3"))
        self.palaukti(60)
        print(f"Išsaugota PDF: {kelias}")

    def _sriftai(self):
        """ISO teksto stiliai ir matmenų stilius pagal inžinerinės grafikos reikalavimus."""
        doc = self.doc
        for vardas, sriftas, pasvirimas, ttf in ISO_STILIAI:
            st = kartoti(lambda: doc.TextStyles.Add(vardas))
            try:
                if ttf:
                    try:
                        st.SetFont(sriftas, False, False, 186, 34)    # 186 - Baltijos koduotė (ąčęėįšųūž)
                    except Exception:
                        st.SetFont("Arial", False, False, 186, 34)
                        print(f"  Šrifto {sriftas} neradau - {vardas} naudos Arial.")
                else:
                    st.fontFile = sriftas
                st.Height = 0.0                    # aukštis renkamas kiekvienam tekstui
                st.Width = 1.0
                st.ObliqueAngle = math.radians(pasvirimas)
            except Exception as e:
                print(f"  Stiliaus {vardas} nustatyti iki galo nepavyko: {e}")
        try:
            doc.ActiveTextStyle = doc.TextStyles.Item("ISO_LT")
        except Exception:
            pass
        # Matmenų stilius
        kintamieji = [("DIMTXSTY", "ISO_LT"), ("DIMTXT", 3.5), ("DIMASZ", 3.0), ("DIMEXE", 2.0),
                      ("DIMEXO", 0.0), ("DIMGAP", 1.0), ("DIMDEC", 0), ("DIMADEC", 0), ("DIMLUNIT", 2),
                      ("DIMDSEP", "."), ("DIMTAD", 1), ("DIMTIH", 0), ("DIMTOH", 0), ("DIMCEN", 0.0),
                      ("DIMBLK", ""), ("DIMSCALE", 1.0)]
        for kint, reiksme in kintamieji:
            try:
                doc.SetVariable(kint, reiksme)
            except Exception:
                pass
        try:
            ds = kartoti(lambda: doc.DimStyles.Add("ISO_MATMENYS"))
            ds.CopyFrom(doc)
            doc.ActiveDimStyle = ds
            ms = "ir matmenų stilius ISO_MATMENYS"
        except Exception as e:
            ms = f"(matmenų stiliaus sukurti nepavyko: {e})"
        print("Sukurti teksto stiliai ISO (stačias), ISO_K (pasvirasis), ISO_LT (pasvirasis, su lietuviškomis "
              f"raidėmis; aktyvus) {ms}.")
        print("Rekomenduojami teksto aukščiai, mm: " + ", ".join(f"{h:g}" for h in TEKSTO_AUKSCIAI))

    def _sluoksniai(self):
        doc = self.doc
        for vardas, spalva, tipas, storis in STANDARTINIAI_SLUOKSNIAI:
            sl = doc.Layers.Add(vardas)
            sl.Color = spalva
            if tipas != "Continuous":
                try:
                    doc.Linetypes.Load(tipas, "acadiso.lin")
                except Exception:
                    pass  # jau įkeltas
                try:
                    sl.Linetype = tipas
                except Exception:
                    print(f"  Nepavyko nustatyti linijos tipo {tipas} sluoksniui {vardas}")
            try:
                sl.Lineweight = storis
            except Exception:
                pass
        doc.ActiveLayer = doc.Layers.Item("KONTURAS")
        print("Sukurti sluoksniai: " + ", ".join(s[0] for s in STANDARTINIAI_SLUOKSNIAI)
              + ". Aktyvus: KONTURAS")

    def _ketvirtine(self, atstumas):
        if self.kunas is None:
            raise RuntimeError("Nėra detalės - pirma sumodeliuok (pvz. failas detale_3d.txt).")
        mn, mx = self.kunas.GetBoundingBox()
        if atstumas is None:
            atstumas = (mx[0] - mn[0]) * 1.5
        kopija = self.kunas.Copy()
        cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
        # išpjaunamas ketvirtis, atsuktas į žiūrovą (priekis-dešinė)
        dx, dy, dz = mx[0] - cx + 1, cy - mn[1] + 1, mx[2] - mn[2] + 2
        ketvirtis = self.ms.AddBox(taskas(cx + dx / 2, cy - dy / 2, mn[2] - 1 + dz / 2), dx, dy, dz)
        kopija.Boolean(2, ketvirtis)
        kopija.Move(taskas(0, 0, 0), taskas(atstumas, 0, 0))
        print(f"Kopija su ketvirtine išpjova padėta {atstumas:g} vnt. į dešinę.")

    # ----- schemų pagalbinės -----
    def _blokas_yra(self, vardas):
        try:
            self.doc.Blocks.Item(vardas)
            return True
        except Exception:
            return False

    def _apibrezti_zenkla(self, tipas):
        if self._blokas_yra(tipas):
            return
        hw, primityvai, _ = SIMBOLIAI[tipas]
        b = self.doc.Blocks.Add(taskas(0, 0), tipas)
        braizyti_primityvus(b, primityvai)
        # Atributai: POZ - matomas schemoje, NUORODA - nematomas (tik aprašo lentelėje)
        b.AddAttribute(TEKSTO_H, 0, "Pozicinis žymuo", taskas(7, hw + 1.5), "POZ", "")
        b.AddAttribute(TEKSTO_H, 1, "Nuoroda (parametrai)", taskas(7, -hw - 5), "NUORODA", "")

    def _elementas(self, args):
        if len(args) < 5:
            raise ValueError(f"Reikia: {KOMANDOS['elementas'][0]}  (tipai: komanda elementai)")
        tipas = args[0].upper()
        if tipas not in SIMBOLIAI:
            raise ValueError(f"Nėra ženklo '{tipas}'. Galimi: " + ", ".join(SIMBOLIAI))
        x, y, kampas = skaiciai(args[1:], 3, "elementas")
        poz = args[4]
        nuoroda = " ".join(args[5:])
        self._apibrezti_zenkla(tipas)
        ref = self.ms.InsertBlock(taskas(x, y), tipas, 1.0, 1.0, 1.0, math.radians(kampas))
        hw = SIMBOLIAI[tipas][0]
        a = math.radians(kampas)
        cx, cy = x + 10 * math.cos(a), y + 10 * math.sin(a)
        tw = 0.75 * TEKSTO_H * len(poz)
        if abs(math.cos(a)) > 0.5:      # gulsčias - žymuo virš ženklo
            px, py = cx - tw / 2, cy + hw + 1.5
        else:                            # stačias - žymuo kairėje
            px, py = cx - hw - 2 - tw, cy - TEKSTO_H / 2
        for atr in ref.GetAttributes():
            if atr.TagString == "POZ":
                atr.TextString = poz
                atr.Rotation = 0.0
                atr.InsertionPoint = taskas(px, py)
            elif atr.TagString == "NUORODA":
                atr.TextString = nuoroda

    @staticmethod
    def _remelio_linijos(talpa, x0, y0, W, H):
        for taskai in ([(x0, y0), (x0 + W, y0), (x0 + W, y0 + H), (x0, y0 + H)],
                       [(x0 + 20, y0 + 5), (x0 + W - 5, y0 + 5), (x0 + W - 5, y0 + H - 5), (x0 + 20, y0 + H - 5)]):
            for (ax, ay), (bx, by) in zip(taskai, taskai[1:] + taskai[:1]):
                talpa.AddLine(taskas(ax, ay), taskas(bx, by))

    def _remelis(self, fmt, x0=0.0, y0=0.0):
        W, H, _ = FORMATAI[fmt]
        self._remelio_linijos(self.ms, x0, y0, W, H)
        self.remelio_vieta = (x0, y0, W, H)
        print(f"Rėmelis {fmt} ({W}x{H}) taške {x0:g} {y0:g}.")

    def _lapas(self, fmt, vardas):
        W, H, popierius = FORMATAI[fmt]
        doc = self.doc
        try:
            lapas = doc.Layouts.Item(vardas)
            print(f"Lapas {vardas} jau yra - naudoju jį.")
        except Exception:
            lapas = doc.Layouts.Add(vardas)
        doc.ActiveLayout = lapas
        try:
            lapas.ConfigName = "DWG To PDF.pc3"
            lapas.RefreshPlotDeviceInfo()
        except Exception:
            print("  Nepavyko pasirinkti DWG To PDF.pc3 - pasirink Page Setup Manager.")
        nustatymai = [
                      ("CanonicalMediaName", popierius),
                      ("PaperUnits", 1),          # milimetrai
                      ("StandardScale", 16)]      # 1:1
        for savybe, reiksme in nustatymai:
            try:
                setattr(lapas, savybe, reiksme)
            except Exception:
                print(f"  Nepavyko nustatyti {savybe} - pasitikrink Page Setup Manager.")
        ps = doc.PaperSpace
        # Ištrinami automatiniai vaizdo langai (užduotyje - None)
        for i in range(ps.Count - 1, -1, -1):
            try:
                obj = ps.Item(i)
                if obj.ObjectName == "AcDbViewport":
                    obj.Delete()
            except Exception:
                pass
        try:
            doc.ActiveLayer = doc.Layers.Item("KONTURAS")
        except Exception:
            pass
        # Lapo kraštas ir rėmelis (kairėje 20 mm, kitur 5 mm)
        self._remelio_linijos(ps, 0, 0, W, H)
        self._kampinis("", talpa=ps, vieta=(W - 5 - 185, 5))
        self._siusti("_ZOOM _E ")
        print(f"{fmt} lapas '{vardas}' paruoštas. Vaizdus dėk: Layout -> Base -> From Model Space.")

    def _kampinis(self, pavadinimas, talpa=None, vieta=None):
        import datetime
        vardas = "KAMPINIS_IRASAS"
        if not self._blokas_yra(vardas):
            b = self.doc.Blocks.Add(taskas(0, 0), vardas)
            braizyti_primityvus(b, KAMPINIS_GEOMETRIJA)
            for zyme, ragin, ax, ay, h, reiksme in KAMPINIS_ATRIBUTAI:
                b.AddAttribute(h, 0, ragin, taskas(ax, ay), zyme, reiksme)
        if vieta is None:
            if self.remelio_vieta:          # apatinis dešinys rėmelio kampas
                x0, y0, W, _H = self.remelio_vieta
                vieta = (x0 + W - 5 - 185, y0 + 5)
            else:
                vieta = (20, 5)
        ref = (talpa or self.ms).InsertBlock(taskas(*vieta), vardas, 1.0, 1.0, 1.0, 0.0)
        duomenys = dict(self.kampinio_duomenys)
        if pavadinimas:
            duomenys["PAVADINIMAS"] = pavadinimas
        duomenys.setdefault("DATA", datetime.date.today().strftime("%Y-%m-%d"))
        for atr in ref.GetAttributes():
            if duomenys.get(atr.TagString):
                atr.TextString = duomenys[atr.TagString]
        # Išorinis blokas (WBLOCK) - failas programos aplanke
        kelias = os.path.abspath("kampinis_irasas.dwg")
        try:
            if os.path.exists(kelias):
                try:
                    os.remove(kelias)
                except PermissionError:
                    raise RuntimeError("kampinis_irasas.dwg atidarytas kitur - uždaryk jį") from None
            self._siusti(f'_-WBLOCK "{kelias}" {vardas} ')
            print(f"Kampinis įrašas įkeltas ir išsaugotas kaip išorinis blokas: {kelias}")
        except Exception as e:
            print(f"Kampinis įrašas įkeltas, bet išorinio failo išsaugoti nepavyko: {e}")
        print("Langelius pildyk: du kartus spausk ant kampinio įrašo.")

    def _aprasas(self, vieta):
        # Surenkami visi schemos ženklai su atributais
        grupes = {}
        ms = self.ms
        for i in range(ms.Count):
            ent = ms.Item(i)
            if ent.ObjectName != "AcDbBlockReference" or not ent.HasAttributes:
                continue
            vardas = ent.EffectiveName
            if vardas not in SIMBOLIAI:
                continue
            atr = {a.TagString: a.TextString for a in ent.GetAttributes()}
            raktas = (vardas, atr.get("NUORODA", ""))
            grupes.setdefault(raktas, []).append(atr.get("POZ", ""))
        if not grupes:
            raise RuntimeError("Schemoje nėra ženklų (komanda elementas).")

        def poz_raktas(p):
            raides = "".join(c for c in p if c.isalpha())
            skaic = "".join(c for c in p if c.isdigit())
            return (raides, int(skaic) if skaic else 0)

        eilutes = []
        for (vardas, nuoroda), pozai in grupes.items():
            pozai.sort(key=poz_raktas)
            eilutes.append((", ".join(pozai), SIMBOLIAI[vardas][2], str(len(pozai)), nuoroda))
        eilutes.sort(key=lambda e: poz_raktas(e[0].split(",")[0]))

        aukstis = 8
        kiek = len(eilutes) + 2          # pavadinimas + antraštė + duomenys
        if vieta is None:
            if self.remelio_vieta:                # tiesiai virš kampinio įrašo
                x0, y0, W, _H = self.remelio_vieta
                vieta = (x0 + W - 5 - 185, y0 + 45 + kiek * aukstis)
            else:
                vieta = (20, 45 + kiek * aukstis)
        t = ms.AddTable(taskas(*vieta), kiek, 4, aukstis, 20)
        for i, plotis in enumerate((20, 110, 10, 45)):
            t.SetColumnWidth(i, plotis)
        try:
            t.SetTextHeight(1 | 2 | 4, TEKSTO_H)
        except Exception:
            pass
        t.SetText(0, 0, "ELEMENTŲ APRAŠAS")
        for j, antraste in enumerate(("Poz. žymuo", "Pavadinimas", "Kiekis", "Pastaba")):
            t.SetText(1, j, antraste)
        for i, e in enumerate(eilutes, start=2):
            for j, tekstas in enumerate(e):
                t.SetText(i, j, tekstas)
        print(f"Aprašo lentelė: {len(eilutes)} eilutės, {sum(len(p) for p in grupes.values())} elementai.")

    def _is_failo(self, kelias, gylis):
        with open(kelias, encoding="utf-8") as f:
            eilutes = f.readlines()
        self._daug(eilutes, "failas", gylis + 1)

    def _daug(self, eilutes, saltinis, gylis=0):
        gerai = klaidos = 0
        for nr, e in enumerate(eilutes, 1):
            e = e.strip()
            if not e or e.startswith("#") or e.startswith("```"):
                continue
            try:
                if saltinis == "ai":
                    self.vykdyti_saugiai(e, saltinis, gylis)
                else:
                    self.vykdyti_zodziais(e, saltinis, gylis)   # failuose irgi galima rašyti žodžiais
                gerai += 1
            except Exception as klaida:
                klaidos += 1
                print(f"  Praleista {nr} eil. '{e}': {klaida}")
        self.palaukti()
        try:
            kartoti(self.acad.ZoomExtents)
        except Exception:
            pass
        print(f"Įvykdyta: {gerai}, klaidų: {klaidos}")

    def _ai(self, turinys):
        print("Klausiu AI, palauk...")
        atsakymas = paklausti_ai(turinys)
        eilutes = atsakymas.splitlines()
        print(f"AI atsiuntė {len(eilutes)} eilučių. Braižau...")
        self._daug(eilutes, "ai")

    @staticmethod
    def _kelias_ir_pastaba(args):
        tekstas = " ".join(args)
        if tekstas.startswith('"'):
            pab = tekstas.find('"', 1)
            return tekstas[1:pab], tekstas[pab + 1:].strip()
        return args[0], " ".join(args[1:])


def main():
    import sys
    # Dirbam programos aplanke - tada failų vardus galima rašyti be kelio
    os.chdir(programos_aplankas())
    acad = prisijungti()
    b = Braizytojas(acad)
    print(f"Brėžly Pilotas {VERSIJA}")
    print("Brėžinys:", acad.ActiveDocument.Name)
    # Failai, nurodyti paleidžiant (pvz. python branduolys.py detale_3d.txt)
    for kelias in sys.argv[1:]:
        print(f"Vykdau {kelias}...")
        try:
            b.vykdyti_saugiai("failas " + kelias)
        except Exception as e:
            print("Klaida:", e)
    print("Rašyk komandą arba žodžiais (pvz.: dėžė 100x60x20). 'pagalba' - sąrašas, 'baigti' - išeiti.")
    while True:
        try:
            eilute = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if eilute.lower() in ("baigti", "exit", "q"):
            break
        try:
            b.vykdyti_zodziais(eilute)
        except Exception as e:
            print("Klaida:", e)
    print("Viso gero!")


if __name__ == "__main__":
    main()

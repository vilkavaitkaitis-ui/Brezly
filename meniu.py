"""
Brėžly Pilotas - žingsnių meniu:
  1) lapo formatas  ->  2) braižymo tipas  ->  3) paruošta detalė ARBA savi duomenys
Paleidimas: PALEISTI.bat (arba: python meniu.py)
"""

import glob
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)))

import branduolys as A          # noqa: E402

LINIJA = "=" * 56

# Paruoštos detalės pagal tipą: (failas, pavadinimas)
PARUOSTOS = {
    "3D": [("detale_zodziais.txt", "Detalė su cilindru ir nuožulniomis sienelėmis"),
           ("detale2_zodziais.txt", "Laikiklis su arka"),
           ("detale3_zodziais.txt", "Stovas su šešiakampiu"),
           ("detale4_zodziais.txt", "Namelio profilio prizmė su anga"),
           ("detale5_zodziais.txt", "Pagrindas su šešiakampe įvore (užduotis 3)")],
    "2D": [("detale_2d.txt", "Detalės vaizdai iš priekio ir iš viršaus")],
    "SCHEMA": [("schema_pvz.txt", "Elektrinė principinė schema")],
}
TIPAI = [("3D", "3D detalė (MODEL erdvė + lapas PAPER erdvėje)"),
         ("2D", "2D brėžinys (rėmelis MODEL erdvėje)"),
         ("SCHEMA", "Elektrinė schema (blokai, atributai, aprašo lentelė)")]
# Komandos, kurias meniu daro pats - iš paruoštų failų jos praleidžiamos
LAPO_KOMANDOS = {"remelis", "remelis_a4", "kampinis", "lapas", "lapas_a3", "aprasas",
                 "sluoksniai", "zoom", "vaizdas3d", "ketvirtine"}
NE_DETALES = {"api_raktas.txt", "INSTRUKCIJA.txt", "klaida.txt", "testas.txt", "detale_3d.txt"}


# Ką pasakyti AI pagal braižymo tipą (lapą ir rėmelį programa daro pati)
AI_TIPO_TEKSTAS = {
    "3D": "Sumodeliuok 3D detalę (tik kūnus, be lapo ir rėmelio).",
    "2D": "Nubraižyk 2D brėžinį (tik vaizdus, be rėmelio ir kampinio įrašo).",
    "SCHEMA": "Nubraižyk elektrinę schemą tarp x 25..200, y 130..280 "
              "(be rėmelio, kampinio įrašo ir aprašo lentelės).",
}


# ---------------------------------------------------------------- pagalbinės
def valyti():
    os.system("cls" if os.name == "nt" else "clear")


def antraste(zingsnis, tekstas, pasirinkta):
    valyti()
    print(LINIJA)
    print(f"  Brėžly Pilotas {A.VERSIJA}")
    print(LINIJA)
    if pasirinkta:
        print("  Pasirinkta: " + "  →  ".join(pasirinkta))
        print("-" * 56)
    print(f"  {zingsnis}. {tekstas}\n")


def rinktis(variantai, papildomi=(), atgal=True):
    """variantai - sąrašas (reikšmė, tekstas). Grąžina reikšmę, 'atgal' arba papildomo raktą."""
    for i, (_, tekstas) in enumerate(variantai, 1):
        print(f"   {i} - {tekstas}")
    if papildomi:
        print()
        for raktas, tekstas in papildomi:
            print(f"   {raktas} - {tekstas}")
    if atgal:
        print("   0 - Atgal")
    while True:
        ats = input("\n  Pasirink: ").strip().upper()
        if atgal and ats == "0":
            return "atgal"
        if ats.isdigit() and 1 <= int(ats) <= len(variantai):
            return variantai[int(ats) - 1][0]
        for raktas, _ in papildomi:
            if ats == raktas.upper():
                return raktas
        print("  Tokio pasirinkimo nėra, bandyk dar kartą.")


def taip(klausimas, numatyta=True):
    pr = "(T/n)" if numatyta else "(t/N)"
    ats = input(f"  {klausimas} {pr}: ").strip().lower()
    if not ats:
        return numatyta
    return ats[0] in "ty"


def kelias_is(ivestis):
    return ivestis.strip().strip('"').strip("'").strip()


def pasirinkti_sablona():
    """Grąžina šablono kelią arba None (tęsti atidarytame brėžinyje)."""
    print("\n  Brėžinys:")
    for i, (_, aprasas) in enumerate(A.SABLONAI, 1):
        print(f"   {i} - Naujas iš {aprasas}")
    savas = len(A.SABLONAI) + 1
    print(f"   {savas} - Naujas iš savo šablono (.dwt)")
    print(f"   {savas + 1} - Tęsti jau atidarytame brėžinyje")
    while True:
        ats = input("  Pasirink [Enter = 1, acadiso.dwt]: ").strip()
        if not ats:
            return A.SABLONAI[0][0]
        if ats.isdigit():
            n = int(ats)
            if 1 <= n <= len(A.SABLONAI):
                return A.SABLONAI[n - 1][0]
            if n == savas:
                kelias = kelias_is(input("  Šablono kelias (įtempk .dwt failą): "))
                if kelias:
                    return kelias
                continue
            if n == savas + 1:
                return None
        print("  Tokio pasirinkimo nėra.")


def pasirinkti_issaugojima(numatytas_vardas):
    """Grąžina (vardas, formato raktas) arba None."""
    print("\n  Išsaugoti failą:")
    raktai = list(A.ISSAUGOJIMO_FORMATAI)
    for i, r in enumerate(raktai, 1):
        print(f"   {i} - {A.ISSAUGOJIMO_FORMATAI[r][2]}")
    print("   0 - Nesaugoti")
    ats = input("  Pasirink [Enter = 1, DWG]: ").strip() or "1"
    if ats == "0" or not ats.isdigit() or not 1 <= int(ats) <= len(raktai):
        return None
    raktas = raktai[int(ats) - 1]
    vardas = kelias_is(input(f"  Failo vardas [{numatytas_vardas}]: ")) or numatytas_vardas
    if not os.path.isabs(vardas) and not os.path.dirname(vardas):
        vardas = os.path.join("brezinai", vardas)
    return vardas, raktas


def failo_vardas(tekstas):
    vardas = "".join(c if c.isalnum() or c in "-_" else "_" for c in tekstas.strip())
    return (vardas.strip("_") or "brezinys")[:40]


# ---------------------------------------------------------------- vykdymas
class Darbas:
    def __init__(self):
        self.b = None

    def prisijungti(self):
        if self.b is None:
            print("\n  Jungiamasi prie AutoCAD...")
            self.b = A.Braizytojas(A.prisijungti())
        return self.b

    def vykdyti_eilutes(self, eilutes, saltinis="failas"):
        """Vykdo eilutes (žodžiai arba komandos), praleidžia lapo komandas - jas daro meniu."""
        b = self.b
        gerai = klaidos = 0
        for nr, e in enumerate(eilutes, 1):
            e = e.strip()
            if not e or e.startswith("#") or e.startswith("```"):
                continue
            try:
                komandos = b.isversti(e)
            except Exception as klaida:
                klaidos += 1
                print(f"  Praleista {nr} eil. '{e}': {klaida}")
                continue
            for k in komandos:
                if k.split()[0].lower() in LAPO_KOMANDOS:
                    continue
                try:
                    b.vykdyti_saugiai(k, saltinis)
                    gerai += 1
                except Exception as klaida:
                    klaidos += 1
                    print(f"  Praleista {nr} eil. '{k}': {klaida}")
        b.palaukti()
        print(f"  Įvykdyta: {gerai}, klaidų: {klaidos}")
        return klaidos

    def rasyti_pats(self):
        print("\n  Rašyk po vieną veiksmą eilutėje (žodžiais arba komandomis).")
        print("  Pvz.: plokštė 100x60x20 | cilindras ø40 aukštis 60 taške 50 30 | skylė ø10 taške 12 12")
        print("  'atsauk' - atšaukti, 'pagalba' - visos komandos, tuščia eilutė arba 'baigta' - baigti.\n")
        while True:
            e = input("  > ").strip()
            if not e or e.lower() in ("baigta", "baigti", "gatava", "q"):
                break
            if e.lower() == "pagalba":
                print(A.pagalbos_tekstas())
                continue
            self.vykdyti_eilutes([e], "ranka")

    def is_failo(self):
        print("\n  Įtempk .txt failą pele į šį langą arba įrašyk jo kelią/pavadinimą ir spausk Enter.")
        kelias = kelias_is(input("  Failas: "))
        if not kelias:
            return False
        if not os.path.exists(kelias) and os.path.exists(kelias + ".txt"):
            kelias += ".txt"
        try:
            with open(kelias, encoding="utf-8") as f:
                eilutes = f.readlines()
        except Exception as e:
            print(f"  Nepavyko atidaryti: {e}")
            return False
        self.vykdyti_eilutes(eilutes)
        return True

    def per_ai(self, tipas, fmt):
        if not A.gauti_rakta():
            print("\n  AI reikia API rakto: įklijuok jį į api_raktas.txt (žr. INSTRUKCIJA.txt).")
            input("  Enter - grįžti...")
            return False
        print("\n  1 - Nuotrauka / brėžinys (įtempk failą)")
        print("  2 - Aprašymas žodžiais")
        budas = input("  Pasirink: ").strip()
        tipo_tekstas = AI_TIPO_TEKSTAS[tipas]
        if budas == "1":
            kelias = kelias_is(input("  Nuotrauka: "))
            pastaba = input("  Pastaba AI (galima tuščia): ").strip()
            turinys = [A.nuotrauka_ai(kelias),
                       {"type": "text", "text": tipo_tekstas + (" Pastaba: " + pastaba if pastaba else "")}]
        else:
            aprasymas = input("  Aprašymas: ").strip()
            if not aprasymas:
                return False
            turinys = tipo_tekstas + " Užduotis: " + aprasymas
        print("  Klausiu AI, palauk...")
        atsakymas = A.paklausti_ai(turinys)
        self.vykdyti_eilutes(atsakymas.splitlines(), "ai")
        return True

    # ---------- lapo įforminimas ----------
    def paruosti_brezini(self):
        """Šablonas + nebūtini ISO šriftai. Grąžina True, jei sukurtas naujas brėžinys."""
        b = self.b
        sablonas = pasirinkti_sablona()
        if sablonas:
            A.naujas_brezinys(b.acad, sablonas)
            b.palaukti()
        b.kunas = None
        b.remelio_vieta = None
        if taip("Sukurti ISO šriftus ir matmenų stilių?", numatyta=False):
            b.vykdyti_saugiai("sriftai")
        return bool(sablonas)

    def issaugoti(self, numatytas_vardas):
        while True:
            pas = pasirinkti_issaugojima(numatytas_vardas)
            if not pas:
                return
            try:
                self.b.issaugoti(*pas)
            except Exception as e:
                print(f"  Išsaugoti nepavyko: {e}")
            if not taip("Išsaugoti dar ir kitu formatu?", numatyta=False):
                return

    def naujas_failas(self):
        """Tuščias užduoties failas: šablonas, šriftai, sluoksniai, lapas su rėmeliu ir kampiniu įrašu."""
        b = self.prisijungti()
        antraste("N", "Naujas failas", ["šablonas → šriftai → formatas → išsaugojimas"])
        self.paruosti_brezini()
        b.vykdyti_saugiai("sluoksniai")
        print("\n  Lapo formatas:")
        formatai = [(k, f"{k}  ({w}x{h} mm)") for k, (w, h, _) in A.FORMATAI.items()]
        formatai.append(("BE", "Be lapo"))
        fmt = rinktis(formatai, atgal=False)
        if fmt != "BE":
            print("\n   1 - Lapas PAPER erdvėje (3D užduotims, Layout)")
            print("   2 - Rėmelis MODEL erdvėje (2D brėžiniams, schemoms)")
            vieta = input("  Pasirink [Enter = 1]: ").strip() or "1"
            pav = input("\n  Darbo pavadinimas: ").strip() or "Brėžinys"
            self.kampinio_duomenys(pav, fmt, "1:1", klausti_pavadinimo=False)
            if vieta == "2":
                b.vykdyti_saugiai(f"remelis {fmt}")
                b.vykdyti_saugiai("kampinis")
                b.vykdyti_saugiai("zoom")
            else:
                b.vykdyti_saugiai(f"lapas {fmt} {fmt}_Lapas")
        else:
            pav = "Brezinys"
        self.issaugoti(failo_vardas(pav))
        input("\n  Enter - grįžti į meniu...")

    def kampinio_duomenys(self, pavadinimas, fmt, mastelis, klausti_pavadinimo=True):
        print("\n  Kampinio įrašo duomenys (Enter - palikti tuščią):")
        if klausti_pavadinimo:
            pavadinimas = input(f"    Darbo pavadinimas [{pavadinimas}]: ").strip() or pavadinimas
        d = {"PAVADINIMAS": pavadinimas,
             "BRAIZE": input("    Braižė (vardas, pavardė): ").strip(),
             "TIKRINO": input("    Tikrino: ").strip(),
             "GRUPE": input("    Grupė: ").strip(),
             "MASTELIS": mastelis, "LAPAS": "1"}
        self.b.kampinio_duomenys = {k: v for k, v in d.items() if v}

    def iforminti(self, tipas, fmt, nuo, pavadinimas, kampinis=None, ketvirtine=None):
        """kampinis - kampinio įrašo duomenys (None - paklausti konsolėje);
        ketvirtine - ar daryti ketvirtinę išpjovą (None - paklausti)."""
        b = self.b
        if fmt is None:
            if tipas == "3D":
                b.vykdyti_saugiai("vaizdas3d")
            b.vykdyti_saugiai("zoom")
            return
        if kampinis is None:
            self.kampinio_duomenys(pavadinimas, fmt, "1:1")
        else:
            d = {"PAVADINIMAS": pavadinimas, "MASTELIS": "1:1", "LAPAS": "1"}
            d.update({k: v for k, v in kampinis.items() if v})
            b.kampinio_duomenys = d
        if tipas == "3D":
            if ketvirtine is None and b.kunas is not None:
                ketvirtine = taip("Padaryti kopiją su ketvirtine išpjova (aksonometrijai)?")
            if ketvirtine and b.kunas is not None:
                b.vykdyti_saugiai("ketvirtine")
            b.vykdyti_saugiai("vaizdas3d")
            b.vykdyti_saugiai(f"lapas {fmt} {fmt}_Lapas")
            print("\n  Toliau lape: Layout → Base → From Model Space (vaizdai), Section (pjūvis),")
            print("  ašys sluoksnyje ASYS, matmenys sluoksnyje MATMENYS, Plot → PDF.")
            return
        # 2D ir schema: rėmelis aplink nubraižytą turinį MODEL erdvėje
        W, H, _ = A.FORMATAI[fmt]
        ribos = b.turinio_ribos(nuo)
        apacia = 45 + (90 if tipas == "SCHEMA" else 0)     # vieta kampiniam įrašui (+ aprašui)
        if ribos is None:
            x0, y0 = 0.0, 0.0
        else:
            (ax, ay), (bx, by) = ribos
            if bx - ax > W - 35 or by - ay > H - apacia - 15:
                print(f"\n  DĖMESIO: brėžinys ({bx - ax:.0f}x{by - ay:.0f}) netelpa į {fmt} - rinkis didesnį formatą.")
            x0 = (ax + bx) / 2 - (20 + W - 5) / 2
            y0 = (ay + by) / 2 - (apacia + H - 5) / 2
            if tipas == "SCHEMA" and fmt == "A4" and abs(x0) < 30 and abs(y0) < 60:
                x0, y0 = 0.0, 0.0          # paruoštos schemos koordinatės jau pritaikytos A4
        b.vykdyti_saugiai(f"remelis {fmt} {x0:g} {y0:g}")
        b.vykdyti_saugiai("kampinis")
        if tipas == "SCHEMA":
            try:
                b.vykdyti_saugiai("aprasas")
            except Exception as e:
                print(f"  Aprašo lentelės nepadariau: {e}")
        b.vykdyti_saugiai("zoom")
        print("\n  Spausdinimas: Plot → DWG To PDF.pc3, Plot area: Window (pažymėk rėmelį), Scale 1:1.")


# ---------------------------------------------------------------- meniu
def main():
    try:
        import zenklas
        zenklas.rodyti(A.VERSIJA.split()[0])
    except Exception:
        pass
    d = Darbas()
    zingsnis, fmt, tipas = 1, None, None
    while True:
        try:
            if zingsnis == 1:
                antraste(1, "Lapo formatas", [])
                formatai = [(k, f"{k}  ({w}x{h} mm)" + ("  stačias" if k == "A4" else "  gulsčias"))
                            for k, (w, h, _) in A.FORMATAI.items()]
                formatai.append(("BE", "Be lapo (tik braižyti)"))
                ats = rinktis(formatai, papildomi=[("N", "Naujas tuščias failas (šablonas, formatas, šriftai, išsaugojimas)"),
                                                   ("T", "Testas (ar viskas veikia)"),
                                                   ("L", "Atidaryti programą su langu"),
                                                   ("Q", "Išeiti")], atgal=False)
                if ats == "Q":
                    return
                if ats == "N":
                    d.naujas_failas()
                    continue
                if ats == "T":
                    b = d.prisijungti()
                    b.vykdyti_zodziais("failas testas.txt")
                    input("\n  Enter - grįžti į meniu...")
                    continue
                if ats == "L":
                    if os.name != "nt":
                        print("  Tik Windows.")
                    elif os.path.exists("Brezly Pilotas.exe"):
                        os.startfile("Brezly Pilotas.exe")
                    else:
                        os.startfile("PROGRAMA.bat")
                    continue
                fmt = None if ats == "BE" else ats
                zingsnis = 2

            elif zingsnis == 2:
                antraste(2, "Braižymo tipas", [fmt or "be lapo"])
                ats = rinktis(TIPAI)
                if ats == "atgal":
                    zingsnis = 1
                    continue
                tipas = ats
                zingsnis = 3

            elif zingsnis == 3:
                tipo_pav = dict(TIPAI)[tipas].split(" (")[0]
                antraste(3, "Ką braižyti?", [fmt or "be lapo", tipo_pav])
                variantai = [(("P", f), f"Paruošta: {pav}") for f, pav in PARUOSTOS[tipas]]
                zinomi = {f for sar in PARUOSTOS.values() for f, _ in sar} | NE_DETALES
                mano = sorted(f for f in glob.glob("*.txt") if f not in zinomi)
                variantai += [(("P", f), f"Mano failas: {f}") for f in mano]
                variantai += [(("RASYTI", None), "Pagal mano duomenis: rašysiu žodžiais čia"),
                              (("FAILAS", None), "Pagal mano duomenis: iš .txt failo (įtempk)"),
                              (("AI", None), "Pagal mano duomenis: nuotrauka arba aprašymas → AI")]
                ats = rinktis(variantai)
                if ats == "atgal":
                    zingsnis = 2
                    continue
                budas, failas = ats

                b = d.prisijungti()
                d.paruosti_brezini()
                b.vykdyti_saugiai("sluoksniai")
                if tipas == "3D":
                    b.vykdyti_saugiai("naujas")
                nuo = A.kartoti(lambda: b.ms.Count)
                pavadinimas = {"3D": "Detalė", "2D": "Detalės brėžinys", "SCHEMA": "Elektrinė principinė schema"}[tipas]

                print()
                ok = True
                if budas == "P":
                    with open(failas, encoding="utf-8") as f:
                        d.vykdyti_eilutes(f.readlines())
                    pavadinimas = dict(PARUOSTOS[tipas]).get(failas, pavadinimas)
                elif budas == "RASYTI":
                    d.rasyti_pats()
                elif budas == "FAILAS":
                    ok = d.is_failo()
                else:
                    ok = d.per_ai(tipas, fmt)
                if ok:
                    d.iforminti(tipas, fmt, nuo, pavadinimas)
                    d.issaugoti(failo_vardas(b.kampinio_duomenys.get("PAVADINIMAS", pavadinimas)))
                print(f"\n{LINIJA}\n  Baigta.")
                if taip("Braižyti dar vieną?"):
                    zingsnis = 1
                else:
                    return
        except KeyboardInterrupt:
            print("\n  Nutraukta.")
            zingsnis = 1
        except Exception as e:
            print(f"\n  Klaida: {e}")
            input("  Enter - grįžti į meniu...")
            zingsnis = 1


if __name__ == "__main__":
    main()

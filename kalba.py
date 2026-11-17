"""
Lietuviškų sakinių supratimas: "nubraižyk dėžę 100x60x20" -> "deze 0 0 0 100 60 20".
Veikia be interneto ir be API. Ko nesupranta - grąžina kaip nesuprastą
(jei yra API raktas, langas tai perduoda AI).
"""

import re

LT = str.maketrans("ąčęėįšųūžĄČĘĖĮŠŲŪŽ", "aceeisuuzACEEISUUZ")
SK = r"-?\d+(?:\.\d+)?"          # skaičius (trupmena su tašku)

# Elektriniai ženklai: raktažodis -> (TIPAS, raidinis kodas)
ZENKLAI = [
    ("rezistor", "REZISTORIUS", "R"), ("varz", "REZISTORIUS", "R"),
    ("kondensator", "KONDENSATORIUS", "C"),
    ("diod", "DIODAS", "VD"),
    ("lemput", "LEMPUTE", "HL"), ("lempa", "LEMPUTE", "HL"),
    ("jungikl", "JUNGIKLIS", "SA"), ("jungtuk", "JUNGIKLIS", "SA"),
    ("saugikl", "SAUGIKLIS", "FU"),
    ("rite", "RITE", "L"), ("ritė", "RITE", "L"), ("induktyv", "RITE", "L"),
    ("baterij", "MAITINIMAS", "GB"), ("maitinim", "MAITINIMAS", "GB"),
    ("akumuliator", "MAITINIMAS", "GB"), ("galvanin", "MAITINIMAS", "GB"),
    ("varikl", "VARIKLIS", "M"),
]
NUORODA = re.compile(r"\d+(?:[.,]\d+)?\s*(?:k|M|m|µ|u|n|p)?\s*(?:Ω|om[ua]?s?\b|ohm|kΩ|V\b|A\b|F\b|W\b|H\b)"
                     r"(?:\s*;\s*\d+(?:[.,]\d+)?\s*(?:k|M|m)?\s*(?:V|A|W)\b)?"
                     r"|\b\d?[A-Z]{1,3}\d{3,}[A-Z]?\b")
POZ = re.compile(r"\b(R|C|VD|HL|SA|FU|L|GB|M)\d+\b")


def normalizuoti(tekstas):
    t = tekstas.translate(LT).lower()
    # "50,30" ir "50,30,10" - AutoCAD stiliaus taškas -> skaičiai per tarpą
    t = re.sub(r"(?<=\d),(?=-?\d)", " ", t)
    return t


def skaidyti_sakinius(tekstas):
    """Kiekviena eilutė, ';' arba '. ' - atskiras veiksmas. Taip pat 'tada', 'po to'."""
    eilutes = [e for e in tekstas.splitlines() if not e.strip().startswith("#")]
    dalys = re.split(r"\n|;|\.\s+|\btada\b|\bpo to\b", "\n".join(eilutes))
    return [d.strip(" .,\t") for d in dalys if d.strip(" .,\t")]


class Kalba:
    def __init__(self, zinomos_komandos, virsus=lambda: None, ribos=lambda: None):
        """zinomos_komandos - programos komandų vardai; virsus() - detalės viršaus aukštis arba None;
        ribos() - detalės ribos ((x0,y0,z0),(x1,y1,z1)) arba None."""
        self.zinomos = set(zinomos_komandos)
        self.virsus = virsus
        self.ribos = ribos
        self.skaitikliai = {}

    # ----- pagalbinės -----
    @staticmethod
    def _f(x):
        return f"{float(x):g}"

    def _zymeta(self, t, raktai):
        """Ieško 'raktas 40' / 'raktas=40'. Grąžina (reikšmė, tekstas be jos)."""
        m = re.search(rf"(?:{raktai})[^\W\d]*\s*[=:]?\s*({SK})", t)
        if not m:
            return None, t
        return float(m.group(1)), t[:m.start()] + " " + t[m.end():]

    def _issinagrineti(self, t):
        """Ištraukia žymėtus dydžius ir likusius skaičius."""
        r = {}
        # "100x60x20" - matmenys. Jei sakinyje yra "y 30", tai "x 12" su tarpais - koordinatė.
        if re.search(rf"\by\s*=?\s*{SK}", t):
            m = re.search(rf"({SK})(?:[x×*]|\s*[×*]\s*)({SK})(?:(?:[x×*]|\s*[×*]\s*)({SK}))?", t)
        else:
            m = re.search(rf"({SK})\s*[x×*]\s*({SK})(?:\s*[x×*]\s*({SK}))?", t)
        if m:
            r["matmenys"] = [float(g) for g in m.groups() if g is not None]
            t = t[:m.start()] + " " + t[m.end():]
        for vardas, raktai in [
            ("d", r"ø|⌀|skersm|diametr|\bd(?=\s*=?\s*\d)"),
            ("r", r"spindul|\br(?=\s*=?\s*\d)"),
            ("tarp", r"tarp briaun\w*|plotis tarp\w*"),
            ("aukstis", r"auks|aukst|\bh(?=\s*=?\s*\d)"),
            ("ilgis", r"ilg"),
            ("plotis", r"plot"),
            ("gylis", r"gyl"),
            ("storis", r"stor"),
            ("kampas", r"\bkamp|\bpasuk"),
        ]:
            v, t = self._zymeta(t, raktai)
            if v is not None:
                r[vardas] = v
        m = re.search(rf"(?:task\w*|centr\w*|ties|vieto\w*|koordinat\w*|padek\w*\s+ties)\s*\(?\s*({SK})\s+({SK})(?:\s+({SK}))?", t)
        if m:
            r["vieta"] = [float(g) for g in m.groups() if g is not None]
            t = t[:m.start()] + " " + t[m.end():]
        for asis in "xyz":
            m = re.search(rf"\b{asis}\s*=?\s*({SK})", t)
            if m:
                r[asis] = float(m.group(1))
                t = t[:m.start()] + " " + t[m.end():]
        r["likę"] = [float(s) for s in re.findall(SK, t)]
        return r

    def _vieta(self, r, kiek=2, numatyta=0.0):
        v = list(r.get("vieta", []))
        for i, a in enumerate("xyz"):
            if a in r:
                while len(v) <= i:
                    v.append(numatyta)
                v[i] = r[a]
        while len(v) < kiek:
            v.append(numatyta)
        return v[:kiek]

    def _spindulys(self, r):
        if "r" in r:
            return r["r"]
        if "d" in r:
            return r["d"] / 2
        return None

    def _poz(self, kodas):
        self.skaitikliai[kodas] = self.skaitikliai.get(kodas, 0) + 1
        return f"{kodas}{self.skaitikliai[kodas]}"

    @staticmethod
    def _ar_skaicius(z):
        try:
            float(z.replace(",", "."))
            return True
        except ValueError:
            return False

    def _ar_komanda(self, cmd, likę):
        """Ar eilutė jau parašyta programos komandų kalba (o ne žodžiais)?"""
        if cmd in ("failas", "irasyti", "issaugoti", "komanda", "ai", "foto", "sluoksnis", "lapas_a3"):
            return True
        if cmd == "elementas":
            return bool(likę) and likę[0].isupper()
        if cmd == "tekstas":
            return len(likę) >= 4 and all(self._ar_skaicius(z) for z in likę[:3])
        if cmd == "kampinis":
            return False
        return all(self._ar_skaicius(z) or z.lower() in ("+x", "-x") for z in likę)

    # ----- pagrindinė -----
    def versti(self, tekstas):
        """Grąžina (komandų sąrašas, nesuprasti sakiniai)."""
        komandos, nesuprasta = [], []
        for sakinys in skaidyti_sakinius(tekstas):
            try:
                k = self.sakinys(sakinys)
            except Exception:
                k = None
            if k:
                komandos.extend(k)
            else:
                nesuprasta.append(sakinys)
        return komandos, nesuprasta

    def sakinys(self, originalas):
        zodziai = originalas.split()
        pirmas = zodziai[0].lower() if zodziai else ""
        if pirmas.lstrip("-") in self.zinomos and self._ar_komanda(pirmas.lstrip("-"), zodziai[1:]):
            return [originalas]                 # jau programos komanda

        # elektrinio ženklo nuoroda (1 kΩ, 12 V) ir pozicinis žymuo - prieš skaičius
        nuoroda = ""
        poz_m = POZ.search(originalas)
        be_poz = POZ.sub(" ", originalas)
        n = NUORODA.search(be_poz)
        if n:
            nuoroda = n.group(0).strip()
            be_poz = be_poz[:n.start()] + " " + be_poz[n.end():]
        tekstas_kab = re.search(r"[\"„“'](.+?)[\"“”']", originalas)

        t = normalizuoti(be_poz)
        r = self._issinagrineti(t)
        L, f = r["likę"], self._f
        has = lambda *zodziai: any(z in t for z in zodziai)

        # ---- valdymas ----
        if has("atsauk", "anuliuok", "grazink"):
            return ["atsaukti"]
        if has("isvalyk", "istrink viska", "isvalyti"):
            return ["isvalyti"]
        if has("nauj") and has("detal"):
            return ["naujas"]
        if has("sluoksni") and not has("sluoksnis ", "sluoksni "):
            return ["sluoksniai"]
        if has("sluoksn"):
            m = re.search(r"sluoksn\w*\s+([A-Za-z_][\w-]*)", originalas.translate(LT), re.I)
            if m:
                return ["sluoksnis " + m.group(1).upper()]
            return ["sluoksniai"]
        if has("ketvirtin"):
            return ["ketvirtine"]
        fmt_m = re.search(r"\ba\s?([0-4])\b", t)
        if has("remel"):
            return [f"remelis A{fmt_m.group(1) if fmt_m else 4}"]
        if re.search(r"\blap(as|a|o|e|ui)\b|lakst|format", t) or (fmt_m and not L):
            return [f"lapas A{fmt_m.group(1) if fmt_m else 3}"]
        if has("kampin"):
            if tekstas_kab:
                pav = tekstas_kab.group(1)
            else:
                pav = re.sub(r"(?i)\b(kampin\w*|įraš\w*|iras\w*|lentel\w*|įkelk|ikelk|sukurk|uzrasas|užrašas)\b",
                             " ", originalas)
                pav = " ".join(pav.split())
            return [f"kampinis {pav}".strip()]
        if has("apras", "specifikacij"):
            return ["aprasas"]
        if has("3d vaiz", "izometr", "aksonometr", "pasuk vaizd") or (t.strip() in ("3d", "rodyk 3d", "parodyk 3d")):
            return ["vaizdas3d"]
        if has("is virsaus", "2d vaizd", "plano vaizd"):
            return ["vaizdas2d"]
        if has("issaugok", "issaugoti", "irasyk faila", "eksportuok"):
            m = re.search(r"([\w.-]+\.(?:dwg|dxf|pdf))", originalas, re.I)
            if m:
                vardas = m.group(1)
            else:
                ext = ".pdf" if has("pdf") else ".dxf" if has("dxf") else ".dwg"
                vardas = "brezinys" + ext
            versija = re.search(r"\b(2018|2013|2010|2007|2004)\b", t)
            return [f"issaugoti {vardas}" + (f" {versija.group(1)}" if versija else "")]
        if has("sriftai", "sriftus", "srifta", "teksto stil", "matmenu stil"):
            return ["sriftai"]
        if has("nauj") and has("fail", "brezin", "dokument"):
            m = re.search(r"([\w.-]+\.dwt)", originalas, re.I)
            return ["naujas_failas" + (f" {m.group(1)}" if m else "")]
        if has("parodyk viska", "zoom", "priartink"):
            return ["zoom"]

        # ---- elektriniai ženklai ----
        for raktas, tipas, kodas in ZENKLAI:
            if raktas.translate(LT) in t:
                x, y = self._vieta(r, 2) if ("vieta" in r or "x" in r) else (L + [0, 0])[:2]
                kampas = r.get("kampas")
                if kampas is None:
                    kampas = 90 if has("vertikal", "stac", "statm") else 0
                poz = poz_m.group(0) if poz_m else self._poz(kodas)
                return [f"elementas {tipas} {f(x)} {f(y)} {f(kampas)} {poz} {nuoroda}".strip()]
        if has("laid", "sujunk"):
            if len(L) >= 4 and len(L) % 2 == 0:
                return ["laidas " + " ".join(f(v) for v in L)]
            return None
        if has("mazg"):
            x, y = self._vieta(r, 2) if "vieta" in r else (L + [0, 0])[:2]
            return [f"mazgas {f(x)} {f(y)}"]

        # ---- kampų suapvalinimas: "suapvalink kampus r10" ----
        if has("suapvalin", "apvalin", "apvalus kamp", "apvalius kamp") and has("kamp"):
            rad = self._spindulys(r) or (L[0] if L else None)
            rb = self.ribos()
            if rad is None or rb is None:
                return None
            (x0, y0, z0), (x1, y1, _z1) = rb
            hh = r.get("aukstis") or r.get("storis") or (self.virsus() - z0)
            kom = []
            for kx, ky, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
                dx = kx if sx > 0 else kx - rad
                dy = ky if sy > 0 else ky - rad
                kom.append(f"-deze {f(dx)} {f(dy)} {f(z0)} {f(rad)} {f(rad)} {f(hh)}")
                kom.append(f"cilindras {f(kx + sx * rad)} {f(ky + sy * rad)} {f(z0)} {f(rad)} {f(hh)}")
            return kom

        # ---- išpjovos: skylė, griovelis ----
        if has("skyl", "ispjau", "isgrez", "kiaur", "griovel", "iskirp", "tunel", "ileid", "zenkl"):
            virsus = self.virsus()
            if has("gul", "horizont", "tunel", "isilgai"):
                # gulinti skylė išilgai Y: per visą detalės ilgį
                rad = self._spindulys(r) or (L[0] if L else None)
                if rad is None:
                    return None
                rb = self.ribos()
                x, y0, z = self._vieta(r, 3, numatyta=None) if "vieta" in r else (None, None, None)
                x = 0 if x is None else x
                z = 0 if z is None else z
                if y0 is None:
                    y0 = (rb[0][1] - 1) if rb else -1
                ilgis = r.get("ilgis") or (((rb[1][1] - rb[0][1]) + 2) if rb else 1000)
                return [f"-cilindrasy {f(x)} {f(y0)} {f(z)} {f(rad)} {f(ilgis)}"]
            if has("griovel") or (has("ispjau", "iskirp") and r.get("matmenys")):
                m = r.get("matmenys") or L[:3]
                if len(m) < 3:
                    return None
                x, y, z = self._vieta(r, 3, numatyta=None) if "vieta" in r else (L[3:] + [None] * 3)[:3]
                x = 0 if x is None else x
                y = 0 if y is None else y
                if z is None:
                    z = (virsus - m[2]) if virsus is not None else 0
                return [f"-deze {f(x)} {f(y)} {f(z)} {f(m[0])} {f(m[1])} {f(m[2] + 1)}"]
            x, y = self._vieta(r, 2) if ("vieta" in r or "x" in r) else (None, None)
            # gylis matuojamas nuo paviršiaus: "taške 30 30 10" - paviršius z=10, kitaip - detalės viršus
            pavirsius = r["vieta"][2] if len(r.get("vieta", [])) == 3 else r.get("z", virsus)
            if "gylis" in r and pavirsius is not None:
                z0, h = pavirsius - r["gylis"], r["gylis"] + 1
            else:
                z0, h = -1, ((virsus + 2) if virsus is not None else 1000)
            if has("kvadrat"):
                a = r.get("plotis") or (r.get("matmenys") or [None])[0]
                rest = list(L)
                if a is None and rest:
                    a = rest.pop(0)
                if a is None:
                    return None
                if x is None:
                    x, y = (rest + [0, 0])[:2]
                kampas = r.get("kampas", 0)
                return [f"-deze {f(x - a / 2)} {f(y - a / 2)} {f(z0)} {f(a)} {f(a)} {f(h)} {f(kampas)}"]
            if has("sesiakamp"):
                F = r.get("tarp") or r.get("d") or (L[0] if L else None)
                rest = L[1:] if ("tarp" not in r and "d" not in r) else L
                if x is None:
                    x, y = (rest + [0, 0])[:2]
                aukstis = (virsus + 2) if virsus is not None else 1000
                posukis = f" {f(r['kampas'])}" if r.get("kampas") else ""
                return [f"-sesiakampis {f(x)} {f(y)} -1 {f(F)} {f(aukstis)}{posukis}"] if F else None
            rad = self._spindulys(r)
            rest = L
            if rad is None and L:
                rad, rest = L[0] / 2, L[1:]      # "skylė 10" - skersmuo
            if rad is None:
                return None
            if x is None:
                x, y = (rest + [0, 0])[:2]
            return [f"-cilindras {f(x)} {f(y)} {f(z0)} {f(rad)} {f(h)}"]

        # ---- 3D kūnai ----
        if has("nam"):
            m = r.get("matmenys")
            if m and len(m) == 3:
                x, y = self._vieta(r, 2)
                return [f"namas {f(x)} {f(y)} {f(m[0])} {f(m[1])} {f(m[2])}"]
            return ["namas"]
        if has("cilindr", "veleno", "velen"):
            rad = self._spindulys(r)
            h = r.get("aukstis") or r.get("ilgis")
            rest = list(L)
            if rad is None and rest:
                rad = rest.pop(0)
            if h is None and rest:
                h = rest.pop(0)
            if rad is None or h is None:
                return None
            x, y, z = self._vieta(r, 3) if ("vieta" in r or "x" in r) else (rest + [0, 0, 0])[:3]
            if has("gul", "horizont"):
                return [f"cilindrasy {f(x)} {f(y)} {f(z)} {f(rad)} {f(h)}"]
            return [f"cilindras {f(x)} {f(y)} {f(z)} {f(rad)} {f(h)}"]
        if has("sesiakamp"):
            F = r.get("tarp") or r.get("d")
            h = r.get("aukstis")
            rest = list(L)
            if F is None and rest:
                F = rest.pop(0)
            if h is None and rest:
                h = rest.pop(0)
            if F is None or h is None:
                return None
            x, y, z = self._vieta(r, 3) if ("vieta" in r or "x" in r) else (rest + [0, 0, 0])[:3]
            posukis = f" {f(r['kampas'])}" if r.get("kampas") else ""
            return [f"sesiakampis {f(x)} {f(y)} {f(z)} {f(F)} {f(h)}{posukis}"]
        if has("pleist", "briaun", "wedge", "nuozul"):
            m = r.get("matmenys") or [r.get("ilgis"), r.get("storis") or r.get("plotis"), r.get("aukstis")]
            if None in m or len(m) < 3:
                if len(L) >= 6:
                    return [f"pleistas {' '.join(f(v) for v in L[:6])} {'-x' if has('kair') else '+x'}"]
                return None
            x, y, z = self._vieta(r, 3)
            kryptis = "-x" if has("kair", "-x") else "+x"
            return [f"pleistas {f(x)} {f(y)} {f(z)} {f(m[0])} {f(m[1])} {f(m[2])} {kryptis}"]
        if has("dez", "prizm", "box", "gretasien", "plokst", "pagrind", "kalad", "blok"):
            m = r.get("matmenys")
            if not m:
                trys = [r.get("plotis") or r.get("ilgis"), r.get("ilgis") if r.get("plotis") else None,
                        r.get("aukstis") or r.get("storis")]
                if r.get("plotis") and r.get("ilgis"):
                    trys = [r["ilgis"], r["plotis"], r.get("aukstis") or r.get("storis")]
                if all(v is not None for v in trys):
                    m = trys
            rest = list(L)
            if not m:
                if len(rest) >= 6:
                    return ["deze " + " ".join(f(v) for v in rest[:6])]
                if len(rest) >= 3:
                    m, rest = rest[:3], rest[3:]
                else:
                    return None
            if len(m) == 2:
                m = m + [r.get("aukstis") or r.get("storis") or (rest.pop(0) if rest else 10)]
            x, y, z = self._vieta(r, 3) if ("vieta" in r or "x" in r) else (rest + [0, 0, 0])[:3]
            return [f"deze {f(x)} {f(y)} {f(z)} {f(m[0])} {f(m[1])} {f(m[2])}"]

        # ---- 2D ----
        if has("tekst", "uzras", "parasyk"):
            if not tekstas_kab:
                return None
            x, y = self._vieta(r, 2) if ("vieta" in r or "x" in r) else (L + [0, 0])[:2]
            h = r.get("aukstis", 5)
            return [f"tekstas {f(x)} {f(y)} {f(h)} {tekstas_kab.group(1)}"]
        if has("kvadrat"):
            a = (r.get("matmenys") or [None])[0] or r.get("plotis") or (L[0] if L else None)
            if a is None:
                return None
            rest = L[1:] if not r.get("matmenys") and "plotis" not in r else L
            x, y = self._vieta(r, 2) if ("vieta" in r or "x" in r) else (rest + [0, 0])[:2]
            return [f"staciakampis {f(x)} {f(y)} {f(a)} {f(a)}"]
        if has("apskritim", "skritul") or re.search(r"\brat(as|a)\b", t):
            rad = self._spindulys(r)
            rest = list(L)
            if rad is None:
                if len(rest) >= 3:
                    return [f"apskritimas {f(rest[0])} {f(rest[1])} {f(rest[2])}"]
                if rest:
                    rad = rest.pop(0)
                else:
                    return None
            x, y = self._vieta(r, 2) if ("vieta" in r or "x" in r) else (rest + [0, 0])[:2]
            return [f"apskritimas {f(x)} {f(y)} {f(rad)}"]
        if has("lank"):
            if len(L) >= 5:
                return ["lankas " + " ".join(f(v) for v in L[:5])]
            return None
        if has("staciakamp", "rectang"):
            m = r.get("matmenys")
            rest = list(L)
            if not m:
                if r.get("plotis") and (r.get("aukstis") or r.get("ilgis")):
                    m = [r["plotis"], r.get("aukstis") or r.get("ilgis")]
                elif len(rest) >= 4:
                    return ["staciakampis " + " ".join(f(v) for v in rest[:4])]
                elif len(rest) >= 2:
                    m, rest = rest[:2], rest[2:]
                else:
                    return None
            x, y = self._vieta(r, 2) if ("vieta" in r or "x" in r) else (rest + [0, 0])[:2]
            return [f"staciakampis {f(x)} {f(y)} {f(m[0])} {f(m[1])}"]
        if has("linij", "atkarp", "tiese"):
            if len(L) >= 4:
                return ["linija " + " ".join(f(v) for v in L[:4])]
            if "ilgis" in r:
                x, y = self._vieta(r, 2)
                if has("vertikal", "stac"):
                    return [f"linija {f(x)} {f(y)} {f(x)} {f(y + r['ilgis'])}"]
                return [f"linija {f(x)} {f(y)} {f(x + r['ilgis'])} {f(y)}"]
            return None
        if has("daugiakamp", "trikamp"):
            if len(L) >= 6 and len(L) % 2 == 0:
                return ["daugiakampis " + " ".join(f(v) for v in L)]
            return None
        return None


PAVYZDZIAI = """# Rašyk po vieną veiksmą eilutėje. Pavyzdžiai:
sukurk sluoksnius
nauja detalė
dėžė 100x60x20
cilindras ø40 aukštis 60 taške 50 30
šešiakampė skylė 24 taške 50 30
skylė ø10 taške 12 12
skylė ø10 taške 88 12
briauna 20x8x30 taške 12 26 20
ketvirtinė išpjova
3D vaizdas
"""

PAVYZDZIAI_SCHEMA = """sukurk sluoksnius
rėmelis A4
kampinis įrašas "Elektrinė schema"
baterija 12 V taške 40 200 vertikali
jungiklis taške 55 250
rezistorius 1 kΩ taške 105 250
lemputė 12 V taške 140 205 vertikali
laidas 40 220 40 250 55 250
laidas 75 250 105 250
laidas 125 250 140 250 140 225
laidas 140 205 140 180 40 180 40 200
aprašo lentelė
"""

PAVYZDZIAI_2D = """apskritimas ø50 taške 0 0
kvadratas 40 taške -20 -20
stačiakampis 100x60 taške -50 -80
linija 0 0 100 100
tekstas "Labas" taške 0 60 aukštis 8
"""

PAVYZDZIAI_BREZINYS = """sukurk sluoksnius
nauja detalė
plokštė 100x80x10
suapvalink kampus r10
blokas 100x40x30 taške 0 20 0
dėžė 56x40x40 taške 22 20 30
briauna 22x40x40 taške 0 20 30, aukštoji pusė dešinėje
briauna 22x40x40 taške 78 20 30, aukštoji pusė kairėje
cilindras ø50 aukštis 70 taške 50 40
griovelis 30x82x30 taške 35 -1 40
skylė ø40 gylis 40 taške 50 40
šešiakampė skylė 26 taške 50 40
gulinti skylė r10 taške 50 -1 0
skylė ø10 taške 10 10
skylė ø10 taške 90 10
skylė ø10 taške 10 70
skylė ø10 taške 90 70
3D vaizdas
"""

PAVYZDZIAI_LAIKIKLIS = """sukurk sluoksnius
nauja detalė
plokštė 80x60x10 taške 30 0 0
cilindras r30 aukštis 10 taške 30 30
cilindras r30 aukštis 10 taške 110 30
blokas 40x60x60 taške 50 0 0
gulintis cilindras r20 ilgis 60 taške 70 0 60
griovelis 20x62x60 taške 60 -1 -1
gulinti skylė r10 taške 70 -1 60
kvadratinė skylė 10 taške 70 30 pasukta 45
skylė ø10 taške 30 30
skylė ø10 taške 110 30
įleidimas ø20 gylis 5 taške 30 30 10
įleidimas ø20 gylis 5 taške 110 30 10
3D vaizdas
"""

PAVYZDZIAI_STOVAS = """sukurk sluoksnius
nauja detalė
cilindras ø100 aukštis 20 taške 50 30
išpjauk 100x21x22 taške 0 -21 -1
išpjauk 100x21x22 taške 0 60 -1
griovelis 30x62x10 taške 35 -1 -1
šešiakampis 52 aukštis 10 taške 50 30 20
cilindras ø40 aukštis 65 taške 50 30 20
briauna 14x6x50 taške 17 27 20, aukštoji pusė dešinėje
briauna 14x6x50 taške 69 27 20, aukštoji pusė kairėje
skylė ø30 taške 50 30
gulinti skylė r5 taške 50 -1 70
skylė ø10 taške 10 30
skylė ø10 taške 90 30
3D vaizdas
"""

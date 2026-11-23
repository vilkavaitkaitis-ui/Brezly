"""
Tikslo paveikslėliai: kiekvienam 2D žingsniui SVG „taip turi atrodyti“.

Jie gaunami iš tų pačių „Parodyk man“ demonstracijų (pamokos.py d_ funkcijos), paleistų netikrame
AutoCAD, kuris nieko nebraižo - tik užrašo, kas nubraižyta. Pilka - ankstesnių žingsnių brėžinys,
oranžinė - šio žingsnio nauja dalis. Pasikeitus pamokoms paveikslėliai sugeneruojami iš naujo.

  python irankiai/paveiksleliai.py             -> paveiksleliai/<žingsnis>.svg ir paveiksleliai/en/<žingsnis>.svg
  python irankiai/paveiksleliai.py --tikrinti  -> klaida, jei failai pasenę (testams)

3D žingsniai (BOX, SUBTRACT, VIEWBASE...) paveikslėlio negauna - jų demonstracija pati kuria kūnus AutoCAD'e.
"""
import contextlib
import io
import math
import os
import sys
import types

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SAKNIS)
os.environ.setdefault("BREZLY_DUOMENYS", os.path.join(SAKNIS, "isvestis", "paveiksleliu_duomenys"))

import branduolys as A      # noqa: E402
import pamokos              # noqa: E402
import vertimas             # noqa: E402

APLANKAS = os.path.join(SAKNIS, "paveiksleliai")
SENA, NAUJA = "#111111", "#e2362b"           # brėžinio lape: juoda - jau nubraižyta, raudona - šis žingsnis
SLUOKSNIAI = ("KONTURAS", "ASYS", "MATMENYS", "TEKSTAS", "BRUKSNINE", "NEMATOMOS", "BRUKSNIAI")


class Nera(Exception):
    """Netikras AutoCAD šito nemoka - žingsnis paveikslėlio negaus."""


# ---------------------------------------------------------------- netikras AutoCAD
class Obj:
    def __init__(self, talpa, rusis, ObjectName, **d):
        self.talpa, self.rusis, self.ObjectName = talpa, rusis, ObjectName
        self.Layer = talpa.doc.sluoksnis
        self.Closed, self.bulge, self.StyleName, self.TextString, self.TagString = False, {}, "Standard", "", ""
        self.__dict__.update(d)

    def SetBulge(self, i, k):
        self.bulge[i] = k

    def GetBulge(self, i):
        return self.bulge.get(i, 0.0)

    # COM savybės, kurias skaito tikrinimas (pamokos.py)
    @property
    def Coordinates(self):
        return tuple(v for p in self.__dict__.get("v", []) for v in p)

    @property
    def StartPoint(self):
        return self.__dict__["p1"] + (0.0,)

    @property
    def EndPoint(self):
        return self.__dict__["p2"] + (0.0,)

    @property
    def Center(self):
        return self.__dict__["c"] + (0.0,)

    @property
    def Radius(self):
        return self.__dict__["r"]

    @property
    def Height(self):
        return self.__dict__["h"]

    @property
    def InsertionPoint(self):
        return self.__dict__["p"] + (0.0,)

    @property
    def Measurement(self):
        return self.__dict__.get("matas", 0.0)

    @property
    def NumberOfLoops(self):
        return len(self.__dict__.get("kilpos", []))

    def AppendOuterLoop(self, objs):
        self.kilpos.append([p for o in objs for p in o.taskai()])

    def Evaluate(self):
        pass

    def Delete(self):
        self.talpa.sar.remove(self)

    def GetBoundingBox(self):
        xs, ys = zip(*self.taskai()) if self.taskai() else ((0,), (0,))
        return (min(xs), min(ys), 0), (max(xs), max(ys), 0)

    def taskai(self):
        r = self.__dict__
        if self.rusis == "pl":
            return list(r["v"])
        if self.rusis == "linija":
            return [r["p1"], r["p2"]]
        if self.rusis == "matmuo" and r["budas"] == "spindulys":      # su užrašu „R10“ už lanko
            (cx, cy), (px, py) = r["p1"], r["p2"]
            d = math.dist(r["p1"], r["p2"]) or 1
            return [r["p1"], (px + (px - cx) / d * 18, py + (py - cy) / d * 18)]
        if self.rusis == "matmuo":                      # su matmens linijos vieta ir užrašu
            return [r["p1"], r["p2"]] + ([r["vieta"]] if "vieta" in r else [])
        if self.rusis == "apskritimas":
            (x, y), R = r["c"], r["r"]
            return [(x - R, y - R), (x + R, y + R)]
        if self.rusis == "lankas":
            (x, y), R = r["c"], r["r"]
            ap = (r["a1"] - r["a0"]) % (2 * math.pi)
            return [(x + R * math.cos(r["a0"] + ap * i / 24), y + R * math.sin(r["a0"] + ap * i / 24)) for i in range(25)]
        if self.rusis == "bruksniai":
            return [p for k in r["kilpos"] for p in k]
        if self.rusis == "elipse":
            (x, y), R = r["c"], math.hypot(*r["maj"])
            return [(x - R, y - R), (x + R, y + R)]
        if self.rusis in ("tekstas", "atributas"):
            (x, y), h = r["p"], r["h"]
            return [(x, y), (x + 0.75 * h * len(self.rodomas()), y + h)]
        if self.rusis == "blokas":
            return [(x + r["p"][0], y + r["p"][1]) for o in r["blk"].sar for (x, y) in o.taskai()]
        return []

    def rodomas(self):
        return self.TextString if self.rusis == "tekstas" or self.TextString else self.TagString

    def GetAttributes(self):
        return self.atributai


def _xy(p):
    return (float(p[0]), float(p[1]))


class Talpa:
    def __init__(self, doc, vardas):
        self.doc, self.vardas, self.sar = doc, vardas, []

    def _naujas(self, *a, **k):
        o = Obj(self, *a, **k)
        self.sar.append(o)
        return o

    @property
    def Count(self):
        return len(self.sar)

    def Item(self, i):
        return self.sar[i]

    def AddLine(self, a, b):
        return self._naujas("linija", "AcDbLine", p1=_xy(a), p2=_xy(b))

    def AddCircle(self, c, r):
        return self._naujas("apskritimas", "AcDbCircle", c=_xy(c), r=float(r))

    def AddArc(self, c, r, a0, a1):
        return self._naujas("lankas", "AcDbArc", c=_xy(c), r=float(r), a0=float(a0), a1=float(a1),
                            StartAngle=float(a0), EndAngle=float(a1))

    def AddHatch(self, tipas, rastas, asociatyvus):
        return self._naujas("bruksniai", "AcDbHatch", PatternName=rastas, kilpos=[])

    def AddDimRadial(self, c, p, ilgis):
        return self._naujas("matmuo", "AcDbRadialDimension", p1=_xy(c), p2=_xy(p), budas="spindulys",
                            matas=math.dist(_xy(c), _xy(p)))

    def AddLightWeightPolyline(self, koord):
        k = [float(v) for v in koord]
        return self._naujas("pl", "AcDbPolyline", v=list(zip(k[0::2], k[1::2])))

    def AddText(self, t, p, h):
        return self._naujas("tekstas", "AcDbText", TextString=t, p=_xy(p), h=float(h))

    def AddEllipse(self, c, maj, santykis):
        return self._naujas("elipse", "AcDbEllipse", c=_xy(c), maj=_xy(maj), k=float(santykis))

    def AddAttribute(self, h, rezimas, klausimas, p, zyme, numatyta):
        return self._naujas("atributas", "AcDbAttributeDefinition", h=float(h), p=_xy(p), TagString=zyme,
                            TextString=numatyta)

    def AddDimRotated(self, a, b, vieta, kampas):
        u = (math.cos(float(kampas)), math.sin(float(kampas)))
        return self._naujas("matmuo", "AcDbRotatedDimension", p1=_xy(a), p2=_xy(b), vieta=_xy(vieta),
                            kampas=float(kampas), budas="pasuktas", matas=abs((b[0] - a[0]) * u[0] + (b[1] - a[1]) * u[1]))

    def AddDimAligned(self, a, b, vieta):
        return self._naujas("matmuo", "AcDbAlignedDimension", p1=_xy(a), p2=_xy(b), vieta=_xy(vieta), budas="lygiagretus",
                            matas=math.dist(_xy(a), _xy(b)))

    def AddDimDiametric(self, a, b, ilgis):
        return self._naujas("matmuo", "AcDbDiametricDimension", p1=_xy(a), p2=_xy(b), budas="skersmuo",
                            matas=math.dist(_xy(a), _xy(b)))

    def InsertBlock(self, p, vardas, sx=1, sy=1, sz=1, kampas=0):
        blk = self.doc.Blocks.Item(vardas)
        attr = [types.SimpleNamespace(TagString=a.TagString, TextString=a.TextString, p=a.p, h=a.h)
                for a in blk.sar if a.rusis == "atributas"]
        return self._naujas("blokas", "AcDbBlockReference", p=_xy(p), blk=blk, atributai=attr)

    def __getattr__(self, vardas):          # AddBox, AddTable... - nemokam
        if vardas.startswith("Add"):
            raise Nera(vardas)
        raise AttributeError(vardas)


class Sluoksnis:
    def __init__(self, vardas):
        self.Name = vardas


class Sluoksniai:
    def __init__(self):
        self.d = {}

    def Item(self, vardas):
        if vardas not in self.d:
            raise KeyError(vardas)
        return self.d[vardas]

    def Add(self, vardas):
        return self.d.setdefault(vardas, Sluoksnis(vardas))


class Lapas:
    def __init__(self, doc, vardas, modelis=False):
        self.Name, self.ModelType, self.CanonicalMediaName, self.ConfigName = vardas, modelis, "", ""
        self.Block = doc.ModelSpace if modelis else Talpa(doc, vardas)

    def RefreshPlotDeviceInfo(self):
        pass


class Lapai:
    def __init__(self, doc):
        self.sar = [Lapas(doc, "Model", True)]
        self.doc = doc

    @property
    def Count(self):
        return len(self.sar)

    def Item(self, k):
        if isinstance(k, int):
            return self.sar[k]
        for L in self.sar:
            if L.Name == k:
                return L
        raise KeyError(k)

    def Add(self, vardas):
        L = Lapas(self.doc, vardas)
        self.sar.append(L)
        return L


class Blokai:
    def __init__(self, doc):
        self.doc, self.d = doc, {}

    def Item(self, vardas):
        return self.d[vardas]

    def Add(self, p, vardas):
        return self.d.setdefault(vardas, Talpa(self.doc, vardas))


class Dok:
    def __init__(self):
        self.Name, self.sluoksnis, self.kintamieji = "Drawing1.dwg", "0", {}
        self.ModelSpace = Talpa(self, "Model")
        self.Layers, self.Layouts, self.Blocks = Sluoksniai(), Lapai(self), Blokai(self)
        self._lapas = self.Layouts.Item("Model")

    @property
    def ActiveLayer(self):
        return self.Layers.Add(self.sluoksnis)

    @ActiveLayer.setter
    def ActiveLayer(self, sl):
        self.sluoksnis = sl.Name

    @property
    def ActiveLayout(self):
        return self._lapas

    @ActiveLayout.setter
    def ActiveLayout(self, L):
        self._lapas = L

    @property
    def PaperSpace(self):
        return self._lapas.Block

    def SetVariable(self, k, v):
        self.kintamieji[k] = v

    def GetVariable(self, k):
        return self.kintamieji.get(k, 0)


class Braizytojas:
    def __init__(self):
        self.doc = Dok()
        self.acad = types.SimpleNamespace(ZoomExtents=lambda: None, ActiveDocument=self.doc)
        self.kunas = None

    @property
    def ms(self):
        return self.doc.ModelSpace

    def vykdyti_saugiai(self, eilute, *a, **k):
        if eilute == "sluoksniai":
            for s in SLUOKSNIAI:
                self.doc.Layers.Add(s)
            self.doc.sluoksnis = "KONTURAS"         # kaip tikrame: po sluoksnių aktyvus KONTURAS
            return
        raise Nera(eilute)

    def _sriftai(self):
        pass

    def issaugoti(self, *a, **k):
        pass

    def palaukti(self, *a, **k):
        pass

    def __getattr__(self, vardas):
        raise Nera(vardas)


# ---------------------------------------------------------------- SVG
def _ribos(objs):
    t = [p for o in objs for p in o.taskai()]
    if not t:
        return None
    xs, ys = zip(*t)
    return min(xs), min(ys), max(xs), max(ys)


def _f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


class Piesinys:
    def __init__(self, ribos):
        x0, y0, x1, y1 = ribos
        m = 0.08 * max(x1 - x0, y1 - y0, 20)
        self.x0, self.y1 = x0 - m, y1 + m
        self.w, self.h = (x1 - x0) + 2 * m, (y1 - y0) + 2 * m
        self.mastelis = max(self.w, self.h) / 100      # rodyklių, tekstų dydžiui
        self.el = []

    def p(self, x, y):
        return x - self.x0, self.y1 - y

    def linija(self, a, b, spalva, storis, bruks=None):
        (x1, y1), (x2, y2) = self.p(*a), self.p(*b)
        d = f' stroke-dasharray="{bruks}"' if bruks else ""
        self.el.append(f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" stroke="{spalva}" '
                       f'stroke-width="{storis}" vector-effect="non-scaling-stroke"{d}/>')

    def tekstas(self, t, p, h, spalva, kampas=0, vidurys=False):
        x, y = self.p(*p)
        rot = f' transform="rotate({_f(-kampas)} {_f(x)} {_f(y)})"' if kampas else ""
        anch = ' text-anchor="middle"' if vidurys else ""
        t = t.replace("&", "&amp;").replace("<", "&lt;")
        self.el.append(f'<text x="{_f(x)}" y="{_f(y)}" font-size="{_f(h)}" fill="{spalva}"{anch}{rot}>{t}</text>')

    def rodykle(self, galas, kryptis, spalva):
        ilg = 2.2 * self.mastelis
        ux, uy = kryptis
        n = math.hypot(ux, uy) or 1
        ux, uy = ux / n, uy / n
        a = (galas[0] - ux * ilg - uy * ilg * 0.3, galas[1] - uy * ilg + ux * ilg * 0.3)
        b = (galas[0] - ux * ilg + uy * ilg * 0.3, galas[1] - uy * ilg - ux * ilg * 0.3)
        pts = " ".join(f"{_f(x)},{_f(y)}" for x, y in (self.p(*galas), self.p(*a), self.p(*b)))
        self.el.append(f'<polygon points="{pts}" fill="{spalva}"/>')

    def matmuo(self, o, spalva):
        r = o.__dict__
        if r["budas"] == "spindulys":
            c, p = r["p1"], r["p2"]
            u = ((p[0] - c[0]) / (math.dist(c, p) or 1), (p[1] - c[1]) / (math.dist(c, p) or 1))
            galas = (p[0] + u[0] * 6 * self.mastelis, p[1] + u[1] * 6 * self.mastelis)
            self.linija(c, galas, spalva, 1)
            self.rodykle(p, u, spalva)
            self.tekstas(f"R{math.dist(c, p):.0f}", (galas[0] + self.mastelis, galas[1]), 3.2 * self.mastelis, spalva)
            return
        if r["budas"] == "skersmuo":
            a, b = r["p1"], r["p2"]
            self.linija(a, b, spalva, 1)
            self.rodykle(a, (a[0] - b[0], a[1] - b[1]), spalva)
            self.rodykle(b, (b[0] - a[0], b[1] - a[1]), spalva)
            d = math.dist(a, b)
            self.tekstas(f"⌀{d:.0f}", ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + self.mastelis), 3.2 * self.mastelis,
                         spalva, vidurys=True)
            return
        a, b, v = r["p1"], r["p2"], r["vieta"]
        if r["budas"] == "pasuktas":
            u = (math.cos(r["kampas"]), math.sin(r["kampas"]))
        else:
            u = (b[0] - a[0], b[1] - a[1])
            n = math.hypot(*u) or 1
            u = (u[0] / n, u[1] / n)
        nrm = (-u[1], u[0])
        # matmens linija eina per vietą, lygiagreti u; taškai projektuojami į ją
        da = (v[0] - a[0]) * nrm[0] + (v[1] - a[1]) * nrm[1]
        db = (v[0] - b[0]) * nrm[0] + (v[1] - b[1]) * nrm[1]
        a2 = (a[0] + nrm[0] * da, a[1] + nrm[1] * da)
        b2 = (b[0] + nrm[0] * db, b[1] + nrm[1] * db)
        isk = 1.2 * self.mastelis
        for p, q, d in ((a, a2, da), (b, b2, db)):
            s = 1 if d >= 0 else -1
            self.linija(p, (q[0] + nrm[0] * isk * s, q[1] + nrm[1] * isk * s), spalva, 1)
        self.linija(a2, b2, spalva, 1)
        self.rodykle(a2, (a2[0] - b2[0], a2[1] - b2[1]), spalva)
        self.rodykle(b2, (b2[0] - a2[0], b2[1] - a2[1]), spalva)
        ilgis = abs((b[0] - a[0]) * u[0] + (b[1] - a[1]) * u[1])
        kampas = math.degrees(math.atan2(u[1], u[0]))
        if kampas > 90 or kampas <= -90:
            kampas -= 180 if kampas > 0 else -180
        s = 1 if (da + db) >= 0 else -1
        vid = ((a2[0] + b2[0]) / 2 + nrm[0] * self.mastelis * s, (a2[1] + b2[1]) / 2 + nrm[1] * self.mastelis * s)
        self.tekstas(f"{ilgis:.0f}", vid, 3.2 * self.mastelis, spalva, kampas=kampas, vidurys=True)

    def objektas(self, o, spalva, dx=0.0, dy=0.0):
        r = o.__dict__
        asis = o.Layer == "ASYS"
        storis = 1 if (asis or o.Layer == "MATMENYS") else 1.8
        bruks = "12 3 2 3" if asis else None
        if o.rusis == "linija":
            self.linija((r["p1"][0] + dx, r["p1"][1] + dy), (r["p2"][0] + dx, r["p2"][1] + dy), spalva, storis, bruks)
        elif o.rusis == "pl":
            v = [(x + dx, y + dy) for x, y in r["v"]]
            if not v:
                return
            pts = v + ([v[0]] if o.Closed else [])
            x, y = self.p(*pts[0])
            d = [f"M{_f(x)} {_f(y)}"]
            for i in range(len(pts) - 1):
                (x1, y1), k = self.p(*pts[i + 1]), o.bulge.get(i, 0)
                if k:
                    th = 4 * math.atan(abs(k))
                    R = math.dist(pts[i], pts[i + 1]) / (2 * math.sin(th / 2))
                    d.append(f"A{_f(R)} {_f(R)} 0 {1 if th > math.pi else 0} {0 if k > 0 else 1} {_f(x1)} {_f(y1)}")   # y apverstas: prieš laikrodį = 0
                else:
                    d.append(f"L{_f(x1)} {_f(y1)}")
            self.el.append(f'<path d="{" ".join(d)}" fill="none" stroke="{spalva}" stroke-width="{storis}" '
                           f'vector-effect="non-scaling-stroke" stroke-linejoin="round"/>')
        elif o.rusis == "lankas":
            ap = (r["a1"] - r["a0"]) % (2 * math.pi)
            (x0, y0) = self.p(r["c"][0] + dx + r["r"] * math.cos(r["a0"]), r["c"][1] + dy + r["r"] * math.sin(r["a0"]))
            (x1, y1) = self.p(r["c"][0] + dx + r["r"] * math.cos(r["a0"] + ap), r["c"][1] + dy + r["r"] * math.sin(r["a0"] + ap))
            self.el.append(f'<path d="M{_f(x0)} {_f(y0)} A{_f(r["r"])} {_f(r["r"])} 0 {1 if ap > math.pi else 0} 0 {_f(x1)} {_f(y1)}" '
                           f'fill="none" stroke="{spalva}" stroke-width="{storis}" vector-effect="non-scaling-stroke"/>')
        elif o.rusis == "bruksniai":
            for k in r["kilpos"]:
                xs, ys = zip(*k)
                x0, y0, x1, y1 = min(xs) + dx, min(ys) + dy, max(xs) + dx, max(ys) + dy
                zingsn = 3.0
                c = x0 - (y1 - y0)                      # 45° linijos y - x = konst., apkarpytos iki stačiakampio
                while c <= x1:
                    a = (max(x0, c), max(x0, c) - c + y0)
                    if a[1] > y1:
                        c += zingsn
                        continue
                    bx = min(x1, c + (y1 - y0))
                    b2 = (bx, bx - c + y0)
                    if b2[0] > a[0]:
                        self.linija(a, b2, spalva, 0.8)
                    c += zingsn
        elif o.rusis == "apskritimas":
            x, y = self.p(r["c"][0] + dx, r["c"][1] + dy)
            d = f' stroke-dasharray="{bruks}"' if bruks else ""
            self.el.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{_f(r["r"])}" fill="none" stroke="{spalva}" '
                           f'stroke-width="{storis}" vector-effect="non-scaling-stroke"{d}/>')
        elif o.rusis == "elipse":
            x, y = self.p(r["c"][0] + dx, r["c"][1] + dy)
            R = math.hypot(*r["maj"])
            kamp = -math.degrees(math.atan2(r["maj"][1], r["maj"][0]))
            self.el.append(f'<ellipse cx="{_f(x)}" cy="{_f(y)}" rx="{_f(R)}" ry="{_f(R * r["k"])}" '
                           f'transform="rotate({_f(kamp)} {_f(x)} {_f(y)})" fill="none" stroke="{spalva}" '
                           f'stroke-width="{storis}" vector-effect="non-scaling-stroke"/>')
        elif o.rusis in ("tekstas", "atributas"):
            self.tekstas(o.rodomas(), (r["p"][0] + dx, r["p"][1] + dy), r["h"], spalva)
        elif o.rusis == "matmuo":
            self.matmuo(o, spalva)
        elif o.rusis == "blokas":
            bx, by = r["p"]
            for v in r["blk"].sar:
                if v.rusis != "atributas":
                    self.objektas(v, spalva, bx, by)
            for a in r["atributai"]:
                self.tekstas(a.TextString, (a.p[0] + bx, a.p[1] + by), a.h, spalva)

    def svg(self, pavadinimas):
        t = pavadinimas.replace("&", "&amp;").replace("<", "&lt;")
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_f(self.w)} {_f(self.h)}" '
                f'font-family="IBM Plex Sans, Segoe UI, sans-serif" role="img" aria-label="{t}">'
                f'<title>{t}</title>' + "".join(self.el) + "</svg>\n")


def piesti(senos, naujos, pavadinimas, lape=False):
    """Senos - pilkai, naujos - oranžiškai. Kai nauja dalis maža A3 lape - priartinta prie jos."""
    visu = _ribos(senos + naujos)
    nr = _ribos(naujos)
    if not visu or not nr:
        return None
    vplot = max(visu[2] - visu[0], visu[3] - visu[1], 1)
    nplot = max(nr[2] - nr[0], nr[3] - nr[1], 1)
    ribos = visu
    if lape and nplot / vplot < 0.3:           # pvz. kampinio įrašo tekstai A3 lape
        c = ((nr[0] + nr[2]) / 2, (nr[1] + nr[3]) / 2)
        pus = nplot * 0.9
        ribos = (c[0] - pus, c[1] - pus * 0.6, c[0] + pus, c[1] + pus * 0.6)
    pie = Piesinys(ribos)
    for o in senos:
        pie.objektas(o, SENA)
    for o in naujos:
        pie.objektas(o, NAUJA)
    return pie.svg(pavadinimas)


# ---------------------------------------------------------------- generavimas
def _talpos(b):
    return [b.doc.ModelSpace] + [L.Block for L in b.doc.Layouts.sar if not L.ModelType] + list(b.doc.Blocks.d.values())


def generuoti(kalba):
    """{žingsnio id: svg} pasirinkta kalba."""
    vertimas.nustatyti(kalba)
    senas = (A.taskas, pamokos.win32com, pamokos.pythoncom)
    A.taskas = lambda x, y, z=0: (x, y, z)
    pamokos.win32com = types.SimpleNamespace(client=types.SimpleNamespace(VARIANT=lambda t, v: v))
    pamokos.pythoncom = types.SimpleNamespace(VT_ARRAY=0, VT_R8=0, VT_DISPATCH=0)
    rez = {}
    try:
        for p in pamokos.PAMOKOS:
            b = Braizytojas()
            for z in p["zingsniai"]:
                pries = {id(t): list(t.sar) for t in _talpos(b)}
                if z.get("demo") is None:
                    continue
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        z["demo"](b)
                except Exception:                 # 3D, AutoCAD komandos ir pan. - be paveikslėlio
                    continue
                geriausia = None
                for t in _talpos(b):
                    if t.vardas in b.doc.Blocks.d:      # bloko apibrėžimas - ne brėžinyje
                        continue
                    naujos = [o for o in t.sar if o not in pries.get(id(t), [])]
                    if naujos and (geriausia is None or len(naujos) > len(geriausia[1])):
                        geriausia = ([o for o in t.sar if o in pries.get(id(t), [])], naujos, t is not b.doc.ModelSpace)
                if geriausia:
                    svg = piesti(geriausia[0], geriausia[1], z["pavadinimas"], lape=geriausia[2])
                    if svg:
                        rez[z["id"]] = svg
    finally:
        A.taskas, pamokos.win32com, pamokos.pythoncom = senas
        vertimas.nustatyti("lt")
    return rez


def failai():
    """{santykinis kelias: turinys} - visi paveikslėliai abiem kalbomis."""
    rez = {f"{i}.svg": s for i, s in generuoti("lt").items()}
    for i, s in generuoti("en").items():
        if rez.get(f"{i}.svg") != s:
            rez[f"en/{i}.svg"] = s
    return rez


def main(argv):
    nauji = failai()
    if "--tikrinti" in argv:
        pasene = [k for k, v in nauji.items()
                  if not os.path.exists(os.path.join(APLANKAS, k))
                  or open(os.path.join(APLANKAS, k), encoding="utf-8").read() != v]
        if pasene:
            raise SystemExit("Pasenę paveikslėliai (paleisk irankiai/paveiksleliai.py): " + ", ".join(pasene))
        print(f"Paveikslėliai atnaujinti ({len(nauji)}).")
        return
    if os.path.isdir(APLANKAS):
        for sakn, _, vardai in os.walk(APLANKAS):
            for v in vardai:
                if v.endswith(".svg"):
                    os.remove(os.path.join(sakn, v))
    for k, v in nauji.items():
        kelias = os.path.join(APLANKAS, k)
        os.makedirs(os.path.dirname(kelias), exist_ok=True)
        with open(kelias, "w", encoding="utf-8", newline="\n") as f:
            f.write(v)
    print(f"Paveikslėliai: {len(nauji)} → {APLANKAS}")
    print("  " + ", ".join(sorted(k for k in nauji if "/" not in k)))


if __name__ == "__main__":
    main(sys.argv[1:])

"""1.2 pamokos: „Tikslus braižymas“, „Redagavimas“, „Masyvai“, „2D pjūvis“ ir DIMRADIUS.
Netikrame AutoCAD (irankiai/paveiksleliai.py): „Parodyk man“ nubraižo -> tikrinimas priima;
tipinės klaidos -> suprantamas paaiškinimas. Paleisti: python -m unittest discover -s testai"""
import contextlib
import io
import json
import math
import os
import re
import sys
import types
import unittest

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SAKNIS)
sys.path.insert(0, os.path.join(SAKNIS, "irankiai"))
import pamokos as P          # noqa: E402
import paveiksleliai as PV   # noqa: E402

NAUJOS = ("tikslumas", "redagavimas", "masyvai", "bruksniavimas")


class Netikras(unittest.TestCase):
    def setUp(self):
        self._senas = (P.A.taskas, P.win32com, P.pythoncom)
        P.A.taskas = lambda x, y, z=0.0: (float(x), float(y), float(z))
        P.win32com = types.SimpleNamespace(client=types.SimpleNamespace(VARIANT=lambda t, v: v))
        P.pythoncom = types.SimpleNamespace(VT_ARRAY=0, VT_R8=0, VT_DISPATCH=0)

    def tearDown(self):
        P.A.taskas, P.win32com, P.pythoncom = self._senas

    def b(self):
        b = PV.Braizytojas()
        b.doc.kintamieji.update(MEASUREMENT=1, INSUNITS=4)
        return b

    def iki(self, pid, zid):
        """Brėžinys, kuriame „Parodyk man“ atlikti visi žingsniai iki zid (be jo)."""
        b = self.b()
        for z in P.pamoka(pid)["zingsniai"]:
            if z["id"] == zid:
                return b
            self.demo(b, z)
        raise KeyError(zid)

    @staticmethod
    def demo(b, z):
        if z["demo"]:
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    z["demo"](b)
            except PV.Nera:
                pass
            except AttributeError:            # NEW netikrame AutoCAD
                if z["id"] not in ("tk-naujas",):
                    raise

    def zingsnis(self, pid, zid):
        return next(z for z in P.pamoka(pid)["zingsniai"] if z["id"] == zid)

    def klaida(self, pid, zid, b, kas):
        kl = self.zingsnis(pid, zid)["tikrinti"](b)
        self.assertTrue(kl, f"{zid}: tikėjausi klaidos")
        self.assertIn(kas, " ".join(kl))


class DemonstracijaPriimama(Netikras):
    def test_kiekvienas_zingsnis(self):
        for pid in NAUJOS + ("matmenys",):
            b = self.b()
            for z in P.pamoka(pid)["zingsniai"]:
                self.demo(b, z)
                if z["tikrinti"] and z["id"] != "dimstyle":         # DIMSTYLE netikrame AutoCAD nėra
                    with self.subTest(zingsnis=z["id"]):
                        self.assertEqual(z["tikrinti"](b), [])

    def test_tuscias_brezinys_nepriimamas(self):
        for pid in NAUJOS:
            for z in P.pamoka(pid)["zingsniai"]:
                if z["tikrinti"] and z["id"] != "tk-naujas":
                    with self.subTest(zingsnis=z["id"]):
                        self.assertTrue(z["tikrinti"](self.b()))


class TipinesKlaidos(Netikras):
    def test_osnap_isjungtas_ir_truksta(self):
        b = self.b()
        b.doc.SetVariable("OSMODE", 55 | 16384)
        self.klaida("tikslumas", "tk-osnap", b, "F3")
        b.doc.SetVariable("OSMODE", 1 | 2)
        self.klaida("tikslumas", "tk-osnap", b, "Center")

    def test_rombas_is_akies(self):
        b = self.iki("tikslumas", "tk-rombas")
        P._pl(b.ms, [(0, 0), (80, 0), (80, 50), (0, 50)])
        b.ms.AddLine((40, 0, 0), (80, 26, 0))           # ne per vidurį
        self.klaida("tikslumas", "tk-rombas", b, "Midpoint")

    def test_polar_netinkamas_kampas(self):
        b = self.iki("tikslumas", "tk-polar")
        b.ms.AddLine((80, 50, 0), (80 + 40 * math.cos(math.radians(45)), 50 + 40 * math.sin(math.radians(45)), 0))
        self.klaida("tikslumas", "tk-polar", b, "45°")

    def test_plotas_staciakampio(self):
        b = self.iki("tikslumas", "tk-plotas")
        b.ms.AddText("S = 4000", (85, 5, 0), 3.5)
        self.klaida("tikslumas", "tk-plotas", b, "stačiakampio")

    def test_chamfer_be_polyline(self):
        b = self.iki("redagavimas", "rd-chamfer")
        self.klaida("redagavimas", "rd-chamfer", b, "CHAMFER")

    def test_trim_ne_ta_puse(self):
        b = self.iki("redagavimas", "rd-trim")
        for o in list(b.ms.sar):
            if o.ObjectName == "AcDbCircle":
                o.Delete()
        b.ms.AddArc((25, 40, 0), 6, 3 * math.pi / 2, math.pi / 2)      # dešinė pusė vietoj kairės
        b.ms.AddArc((55, 40, 0), 6, math.pi / 2, 3 * math.pi / 2)
        self.klaida("redagavimas", "rd-trim", b, "ne ta pusė")

    def test_mirror_istrintas_originalas(self):
        b = self.iki("redagavimas", "rd-mirror")
        for o in list(b.ms.sar):
            if o.ObjectName == "AcDbArc":
                o.Delete()
        self.zingsnis("redagavimas", "rd-mirror")["demo"](b)
        self.klaida("redagavimas", "rd-mirror", b, "Erase source objects")

    def test_pcd_ne_tas_sluoksnis(self):
        b = self.iki("masyvai", "ms-pcd")
        b.ms.AddCircle((0, 0, 0), 35)
        self.klaida("masyvai", "ms-pcd", b, "ASYS")

    def test_susietas_masyvas(self):
        b = self.iki("masyvai", "ms-masyvas")
        b.ms._naujas("blokas", "AcDbBlockReference", p=(0, 0), blk=PV.Talpa(b.doc, "*U1"), atributai=[])
        self.klaida("masyvai", "ms-masyvas", b, "EXPLODE")

    def test_rotate_nepasuktos(self):
        b = self.iki("masyvai", "ms-rotate")
        self.klaida("masyvai", "ms-rotate", b, "ROTATE")

    def test_hatch_ir_kiauryme(self):
        b = self.iki("bruksniavimas", "bk-hatch")
        h = b.ms.AddHatch(1, "ANSI31", False)
        h.Layer = "BRUKSNIAI"
        h.AppendOuterLoop([P._pl(b.ms, [(0, -20), (50, -20), (50, 20), (0, 20)])])
        self.klaida("bruksniavimas", "bk-hatch", b, "kiaurymę")

    def test_hatch_rastas_ir_viena_sienele(self):
        b = self.iki("bruksniavimas", "bk-hatch")
        h = b.ms.AddHatch(1, "SOLID", False)
        h.Layer = "BRUKSNIAI"
        h.AppendOuterLoop([P._pl(b.ms, [(0, 10), (50, 10), (50, 20), (0, 20)])])
        self.klaida("bruksniavimas", "bk-hatch", b, "ANSI31")
        h.PatternName = "ANSI31"
        self.klaida("bruksniavimas", "bk-hatch", b, "apatinės")


class Turinys(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(SAKNIS, "pamokos.json"), encoding="utf-8") as f:
            self.d = json.load(f)
        with open(os.path.join(SAKNIS, "pamokos_en.json"), encoding="utf-8") as f:
            self.e = json.load(f)

    def test_visi_zingsniai_tikrinami_ir_demonstruojami(self):
        for pid in NAUJOS:
            for z in P.pamoka(pid)["zingsniai"]:
                self.assertIn(z["id"], P.TIKRINIMAS)
                self.assertIsNotNone(z["tikrinti"], z["id"])
                self.assertIsNotNone(z["demo"], z["id"])

    def test_angliskai_tas_pats_kiekis(self):
        for p in self.d["pamokos"]:
            ep = self.e["pamokos"][p["id"]]
            self.assertEqual(len(ep["testas"]), len(p["testas"]), p["id"])
            for z in p["zingsniai"]:
                ez = ep["zingsniai"].get(z["id"])
                self.assertIsNotNone(ez, f"{p['id']}/{z['id']} - nėra EN")
                for k in ("zingsniai", "komandos", "uzuominos"):
                    self.assertEqual(len(ez.get(k, z.get(k, []))), len(z.get(k, [])), f"{z['id']}.{k}")
                if p["id"] not in NAUJOS:
                    continue
                for (pl, il), (pe, ie) in zip(z.get("komandos", []), ez.get("komandos", [])):
                    if not pl.startswith("("):
                        self.assertEqual(pl, pe, z["id"])            # AutoCAD raginimai angliški abiem kalbom
                    if re.fullmatch(r"[A-Z0-9@,.<\-]+", il):
                        self.assertEqual(il, ie, z["id"])            # komandos ir koordinatės sutampa

    def test_korteles_ir_patarimai(self):
        k = {x["k"] for x in self.d["korteles"]}
        for c in ("OSNAP", "TRIM", "OFFSET", "MIRROR", "CHAMFER", "ARRAYPOLAR", "ROTATE", "HATCH", "PLINE", "DIMRADIUS", "MOVE", "ZOOM"):
            self.assertIn(c, k)
            self.assertIn(c, self.e["korteles"])
        ids = {p["id"] for p in self.d["pamokos"]}
        for x in self.d["korteles"]:
            self.assertIn(x["pamoka"], ids, x["k"])
        self.assertEqual(len(self.d["patarimai"]), len(self.e["patarimai"]))

    def test_dazniausios_klaidos_patarimuose(self):
        t = " ".join(self.d["patarimai"])
        for zodis in ("sluoksnyje 0", "Defpoints", "EXPLODE", "1:1", "Ctrl+S"):
            self.assertIn(zodis, t)


if __name__ == "__main__":
    unittest.main()

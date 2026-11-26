"""1.5 bandomoji funkcija: brėžinio iššūkiai ir peržiūra.
Netikrame AutoCAD (irankiai/paveiksleliai.py) nubraižoma teisinga detalė bet kurioje vietoje -> priimama;
tipinės klaidos -> suprantamos pastabos; komandų žurnalas -> seka ir patarimai."""
import json
import math
import os
import sys
import unittest

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SAKNIS)
sys.path.insert(0, os.path.join(SAKNIS, "irankiai"))
import issukiai as I         # noqa: E402
import issukiai_gen as G     # noqa: E402
import paveiksleliai as PV   # noqa: E402
import vertimas              # noqa: E402


def braizyti(b, geom, dx=0.0, dy=0.0, praleisti=(), keisti=None):
    """Iššūkio geometrija į netikrą AutoCAD (pastumta per dx, dy)."""
    for n, g in enumerate(geom):
        if n in praleisti:
            continue
        if keisti and n in keisti:
            g = keisti[n]
        if "l" in g:
            x1, y1, x2, y2 = g["l"]
            b.ms.AddLine((x1 + dx, y1 + dy, 0), (x2 + dx, y2 + dy, 0))
        elif "a" in g:
            cx, cy, r, a0, a1 = g["a"]
            b.ms.AddArc((cx + dx, cy + dy, 0), r, math.radians(a0), math.radians(a1))
        else:
            cx, cy, r = g["c"]
            b.ms.AddCircle((cx + dx, cy + dy, 0), r)


class Duomenys(unittest.TestCase):
    def test_failas_atnaujintas(self):
        with open(I.FAILAS, encoding="utf-8") as f:
            self.assertEqual(f.read(), G.turinys(), "paleisk python irankiai/issukiai_gen.py")

    def test_laukai(self):
        for i in I.sarasas("lt") + I.sarasas("en"):
            for k in ("id", "nr", "pav", "aprasas", "lyg", "tikslas", "xp", "kom", "geom", "matmenys"):
                self.assertIn(k, i)
            r = I.ribos([I.is_json(g) for g in i["geom"]])
            self.assertAlmostEqual(r[0], 0, delta=0.2, msg=i["id"])           # ribos - iš taškų (lankai apytiksliai)
            self.assertAlmostEqual(r[1], 0, delta=0.2, msg=i["id"])

    def test_surinkime(self):
        import surinkti
        self.assertIn("issukiai.py", surinkti.MODULIAI)
        self.assertIn("issukiai.json", surinkti.DUOMENYS)


class Tikrinimas(unittest.TestCase):
    def setUp(self):
        vertimas.nustatyti("lt")

    def tearDown(self):
        vertimas.nustatyti("lt")

    def test_teisinga_bet_kurioje_vietoje(self):
        for i in I.sarasas():
            for dx, dy in ((0, 0), (137.25, -42.5), (-1000, 2500)):
                with self.subTest(issukis=i["id"], vieta=(dx, dy)):
                    b = PV.Braizytojas()
                    braizyti(b, i["geom"], dx, dy)
                    pastabos, _ = I.tikrinti(i["id"], b)
                    self.assertEqual(pastabos, [])

    def test_tuscias(self):
        pastabos, _ = I.tikrinti("plokstele", PV.Braizytojas())
        self.assertIn("nieko nėra", pastabos[0])

    def test_staciakampis_polilinija_ir_dalimis(self):
        b = PV.Braizytojas()
        b.ms.AddLightWeightPolyline((10, 10, 90, 10, 90, 60, 10, 60)).Closed = True
        b.ms.AddLine((10, 10, 0), (40, 10, 0))                 # dalis kraštinės dar kartą - netrukdo
        b.ms.AddCircle((25, 35, 0), 5)
        b.ms.AddCircle((75, 35, 0), 5)
        pastabos, faktai = I.tikrinti("plokstele", b)
        self.assertEqual(pastabos, [])
        self.assertEqual(faktai["tipai"]["AcDbPolyline"], 1)

    def test_uzapvalinta_polilinija_su_lankais(self):
        b = PV.Braizytojas()
        k = math.tan(math.radians(90) / 4)                     # 90° lanko bulge
        pl = b.ms.AddLightWeightPolyline((10, 0, 90, 0, 100, 10, 100, 50, 90, 60, 10, 60, 0, 50, 0, 10))
        pl.Closed = True
        for j in (1, 3, 5, 7):
            pl.SetBulge(j, k)
        for x, y in ((15, 15), (85, 15), (15, 45), (85, 45)):
            b.ms.AddCircle((x, y, 0), 4)
        self.assertEqual(I.tikrinti("uzapvalinta", b)[0], [])

    def test_skersmuo_vietoj_spindulio(self):
        i = I.issukis("plokstele")
        b = PV.Braizytojas()
        braizyti(b, i["geom"], 5, 5, keisti={5: {"c": [65, 25, 10]}})
        pastabos, _ = I.tikrinti("plokstele", b)
        self.assertTrue(any("Trūksta" in p and "⌀10" in p and "spindulio" in p for p in pastabos), pastabos)

    def test_truksta_skyles(self):
        i = I.issukis("flansas")
        b = PV.Braizytojas()
        braizyti(b, i["geom"], praleisti=(3,))
        pastabos, _ = I.tikrinti("flansas", b)
        self.assertTrue(any("Trūksta: apskritimas ⌀8" in p for p in pastabos), pastabos)

    def test_netiksliai(self):
        i = I.issukis("kampuotis")
        b = PV.Braizytojas()
        braizyti(b, i["geom"], keisti={0: {"l": [0, 0, 70.8, 0]}, 1: {"l": [70.8, 0, 70, 15]}})
        pastabos, _ = I.tikrinti("kampuotis", b)
        self.assertTrue(any(p.startswith("Beveik!") for p in pastabos), pastabos)

    def test_lieka_nenukirpta(self):
        i = I.issukis("griovelis")
        b = PV.Braizytojas()
        braizyti(b, i["geom"])
        b.ms.AddCircle((30, 25, 0), 6)                         # griovelio apskritimai nenukirpti
        b.ms.AddCircle((60, 25, 0), 6)
        pastabos, _ = I.tikrinti("griovelis", b)
        self.assertTrue(any("nereikalingų objektų (2)" in p for p in pastabos), pastabos)

    def test_pagalbines_linijos_netikrinamos(self):
        i = I.issukis("svirtis")
        b = PV.Braizytojas()
        braizyti(b, i["geom"])
        b.doc.sluoksnis = "PAGALBINIS"
        b.ms.AddLine((0, 20, 0), (130, 20, 0))
        b.ms.AddCircle((20, 20, 0), 20)
        self.assertEqual(I.tikrinti("svirtis", b)[0], [])

    def test_kitas_mastelis(self):
        b = PV.Braizytojas()
        braizyti(b, [{"l": [a * 2 for a in g["l"]]} if "l" in g else {"c": [g["c"][0] * 2, g["c"][1] * 2, g["c"][2] * 2]}
                     for g in I.issukis("plokstele")["geom"]])
        pastabos, _ = I.tikrinti("plokstele", b)
        self.assertIn("160 × 100", pastabos[0])

    def test_anglu_kalba(self):
        vertimas.nustatyti("en")
        pastabos, _ = I.tikrinti("plokstele", PV.Braizytojas())
        self.assertIn("empty", pastabos[0])

    def test_faktai_tarpai_ir_dubliai(self):
        b = PV.Braizytojas()
        braizyti(b, I.issukis("plokstele")["geom"])
        b.ms.AddLine((0, 0, 0), (80, 0, 0))                    # dublis
        b.ms.AddLine((80.2, 0, 0), (90, 0, 0))                 # tarpas 0.2
        _, f = I.tikrinti("plokstele", b)
        self.assertEqual(f["dubliai"], 1)
        self.assertGreaterEqual(f["tarpai"], 1)


class Perziura(unittest.TestCase):
    def test_seka_ir_permatomos(self):
        ev = [(0, "b", "LINE"), (3, "b", "ZOOM"), (4, "e", "ZOOM"), (9, "e", "LINE"), (10, "b", "_CIRCLE"),
              (14, "b", "ERASE"), (15, "e", "ERASE")]
        sk = I.seka([(t, r, I.normalizuoti(v)) for t, r, v in ev])
        self.assertEqual([s["k"] for s in sk], ["LINE", "ZOOM", "CIRCLE", "ERASE"])
        self.assertEqual(sk[0]["tr"], 9)
        self.assertEqual(sk[2]["tr"], 4)            # nebaigtas CIRCLE baigiasi prasidėjus ERASE

    def test_patarimai_pradedanciajam(self):
        ir = I.pavyzdinis_irasas("plokstele")
        f = {"tipai": {"AcDbLine": 4, "AcDbCircle": 2}, "tarpai": 0, "dubliai": 0, "apskritimai": {5.0: 2}}
        r = I.perziura("plokstele", ir, f, 260)
        tipai = [p["tipas"] for p in r["patarimai"]]
        for t in ("rectang", "copy", "osnap"):
            self.assertIn(t, tipai)
        self.assertEqual(r["zvaigzdes"], 1)
        self.assertEqual(r["komandos"][0]["k"], "LINE")

    def test_be_zurnalo(self):
        r = I.perziura("flansas", {"ivykiai": []}, {"tipai": {"AcDbCircle": 6}, "apskritimai": {4.0: 4}}, 100)
        self.assertEqual(r["zvaigzdes"], 3)
        self.assertTrue(r["pastaba"])
        self.assertTrue(r["patarimai"])

    def test_osnap(self):
        sk = [{"k": "LINE", "t": 5, "tr": 4}]
        self.assertTrue(I._osnap_isjungtas({"kintamieji": [(0, "OSMODE", 4133), (2, "OSMODE", 4133 + 16384)]}, sk))
        self.assertFalse(I._osnap_isjungtas({"kintamieji": [(0, "OSMODE", 4133 + 16384), (2, "OSMODE", 4133)]}, sk))

    def test_irasas_be_windows(self):
        I.IRASAS.pradeti("plokstele")
        I.IRASAS.ivykis("b", "_LINE")
        I.IRASAS.ivykis("e", "LINE")
        I.IRASAS.ivykis("b", "QSAVE")
        r = I.IRASAS.sustabdyti()
        self.assertEqual([e[2] for e in r["ivykiai"]], ["LINE", "LINE"])


if __name__ == "__main__":
    unittest.main()

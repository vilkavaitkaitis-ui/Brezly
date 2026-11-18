"""8-10 pamokų tikrinimas su netikru AutoCAD (COM objektų imitacija): demonstracija nubraižo -> tikrinimas priima,
tipinės klaidos -> suprantamas paaiškinimas. Paleisti: python -m unittest discover -s testai"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pamokos as P     # noqa: E402


class Obj:
    def __init__(self, tipas, mn=(0, 0, 0), mx=(0, 0, 0), **kw):
        self.ObjectName, self._mn, self._mx, self.Layer = tipas, mn, mx, "0"
        self.__dict__.update(kw)

    def GetBoundingBox(self):
        return self._mn, self._mx


class Talpa(list):
    Count = property(len)

    def Item(self, i):
        return self[i]

    def AddLine(self, p, q):
        self.append(Obj("AcDbLine", StartPoint=p, EndPoint=q))

    def AddEllipse(self, c, ax, santykis):
        r = math.hypot(ax[0], ax[1])
        self.append(Obj("AcDbEllipse", Center=c, MajorAxis=ax, MajorRadius=r, MinorRadius=r * santykis))

    def AddDimAligned(self, p, q, t):
        self.append(Obj("AcDbAlignedDimension", Measurement=math.hypot(q[0] - p[0], q[1] - p[1])))


class Lapas:
    def __init__(self, vardas, objektai=(), modelis=False, popierius="ISO_full_bleed_A3_(420.00_x_297.00_MM)"):
        self.Name, self.ModelType, self.Block, self.CanonicalMediaName = vardas, modelis, Talpa(objektai), popierius


class Lapai(list):
    Count = property(len)

    def Item(self, i):
        return self[i]


class Doc:
    def __init__(self, lapai=(), kintamieji=None):
        self.Layouts = Lapai([Lapas("Model", modelis=True)] + list(lapai))
        self._k = kintamieji or {}

    def GetVariable(self, v):
        return self._k[v]

    def SetVariable(self, v, x):
        self._k[v] = x


class B:
    def __init__(self, objektai=(), lapai=(), kintamieji=None):
        self.ms, self.doc = Talpa(objektai), Doc(lapai, kintamieji)


def kunas(turis, mn=P.DETALE_MIN, mx=P.DETALE_MAX):
    return Obj("AcDb3dSolid", mn, mx, Volume=turis)


class Bendra(unittest.TestCase):
    def setUp(self):
        self._taskas = P.A.taskas
        P.A.taskas = lambda x, y, z=0.0: (float(x), float(y), float(z))      # be pywin32

    def tearDown(self):
        P.A.taskas = self._taskas


class Pjuviai(Bendra):
    def test_ispjovos_turis_suskaiciuotas_tiksliai(self):
        """Skaitinis integravimas: atimamas ketvirtis iš 7 pamokos detalės."""
        # briaunos (x 65..90, y 26..34, aukštis 30·(90-x)/25 - aukštesnė prie cilindro) dalis cilindro viduje;
        # cilindras siekia tik x <= 70, todėl integruojam x 65..70 (vidurio taškų metodas, be numpy)
        nx, ny = 500, 800
        dx, dy = 5 / nx, 8 / ny
        viduje = 0.0
        for i in range(nx):
            x = 65 + (i + 0.5) * dx
            h = 30 * (90 - x) / 25
            n_in = sum(1 for j in range(ny) if (x - 50) ** 2 + (26 + (j + 0.5) * dy - 30) ** 2 <= 400)
            viduje += h * n_in * dx * dy
        lauke = 25 * 8 * 30 / 2 - viduje
        sesiak = 3 * math.sqrt(3) / 2 * 10 ** 2
        galutinis = 100 * 60 * 20 + math.pi * 20 ** 2 * 40 - sesiak * 60 + 2 * lauke
        self.assertAlmostEqual(galutinis, P.V_GALUTINIS, delta=1)
        ispjauta = 50 * 30 * 20 + math.pi * 20 ** 2 * 40 / 4 + lauke / 2 - sesiak / 4 * 60
        self.assertAlmostEqual(galutinis - ispjauta, P.V_ISPJOVA, delta=1)

    def test_detale(self):
        self.assertEqual(P.t_detale3d(B([kunas(P.V_GALUTINIS)])), [])
        self.assertEqual(P.t_detale3d(B([kunas(P.V_ISPJOVA)])), [], "detalė jau su išpjova irgi tinka")
        self.assertIn("Neradau", P.t_detale3d(B())[0])

    def test_ispjova(self):
        self.assertEqual(P.t_ispjova(B([kunas(P.V_ISPJOVA)])), [])
        self.assertIn("dar neišpjautas", P.t_ispjova(B([kunas(P.V_GALUTINIS)]))[0])
        dvi = B([kunas(P.V_GALUTINIS), kunas(50 * 30 * 60, P.ISPJOVA_MIN, P.ISPJOVA_MAX)])
        self.assertIn("SUBTRACT", P.t_ispjova(dvi)[0])
        self.assertIn("Tūris", P.t_ispjova(B([kunas(100000)]))[0])

    def test_plokstuma_ir_vaizdai(self):
        self.assertTrue(P.t_plokstuma(B()))
        self.assertEqual(P.t_plokstuma(B([Obj("AcDbSection")])), [])
        self.assertTrue(P.t_vaizdas(B(lapai=[Lapas("Layout1")])))
        su_vaizdu = B(lapai=[Lapas("Layout1", [Obj("AcDbViewBorder")])])
        self.assertEqual(P.t_vaizdas(su_vaizdu), [])
        self.assertIn("VIEWSECTION", P.t_pjuvis(su_vaizdu)[0])
        su_pjuviu = B(lapai=[Lapas("Layout1", [Obj("AcDbViewBorder"), Obj("AcDbViewBorder"), Obj("AcDbSectionSymbol")])])
        self.assertEqual(P.t_pjuvis(su_pjuviu), [])


class Projekcijos(Bendra):
    def test_vaizdu_skaicius_a3_lape(self):
        def b(n, lapas="A3"):
            return B(lapai=[Lapas(lapas, [Obj("AcDbViewBorder") for _ in range(n)])])
        self.assertTrue(P.t_pr_priekis(b(0)))
        self.assertEqual(P.t_pr_priekis(b(1)), [])
        self.assertIn("vaizdų: 2, reikia 3", P.t_pr_projekcijos(b(2))[0])
        self.assertEqual(P.t_pr_projekcijos(b(3)), [])
        self.assertEqual(P.t_pr_aksonometrija(b(4)), [])
        kitame = B(lapai=[Lapas("A3", []), Lapas("Layout1", [Obj("AcDbViewBorder")], popierius="Letter")])
        self.assertIn("kitame lape", P.t_pr_priekis(kitame)[0])
        self.assertIn("A3", P.t_pr_priekis(B(lapai=[Lapas("Layout1", popierius="Letter")]))[0])


class Aksonometrija(Bendra):
    def test_demonstracijos_praeina_tikrinima(self):
        b = B(kintamieji={"SNAPSTYL": 0})
        self.assertTrue(P.t_isodraft(b))
        for d, t in ((P.d_isodraft, P.t_isodraft), (P.d_iso_deze, P.t_iso_deze),
                     (P.d_iso_apskritimas, P.t_iso_apskritimas), (P.d_iso_matmuo, P.t_iso_matmuo)):
            d(b)
            self.assertEqual(t(b), [], d.__name__)

    def test_komandu_eilute_nubraizo_dezes_briaunas(self):
        """Tiksliai tie taškai, kuriuos pamoka liepia įvesti LINE komandoje."""
        b, p = B(), (100.0, 50.0)
        for ilgis, kampas in ((60, 30), (30, 90), (40, 150), (60, 210), (30, 270), (40, 330), (30, 90), (60, 30)):
            q = P._iso_taskas(p, ilgis, kampas)
            b.ms.AddLine(p, q)
            p = q
        self.assertTrue(P.t_iso_deze(b), "be antros LINE trūksta vienos briaunos")
        b.ms.AddLine((100.0, 80.0), P._iso_taskas((100.0, 80.0), 40, 150))
        self.assertEqual(P.t_iso_deze(b), [])

    def test_izoapskritimo_klaidos(self):
        c = P.ISO_CENTRAS
        apskr = B([Obj("AcDbCircle", Center=c, Radius=10.0)])
        self.assertIn("Isocircle", P.t_iso_apskritimas(apskr)[0])
        kaire = B()
        kaire.ms.AddEllipse(c, (P.ISO_DIDZ * math.cos(math.radians(60)), P.ISO_DIDZ * math.sin(math.radians(60))), P.ISO_MAZ / P.ISO_DIDZ)
        self.assertIn("F5", P.t_iso_apskritimas(kaire)[0])
        maza = B()
        maza.ms.AddEllipse(c, (P.ISO_DIDZ / 2, 0), P.ISO_MAZ / P.ISO_DIDZ)
        self.assertIn("spinduliu 10", P.t_iso_apskritimas(maza)[0])
        toli = B()
        toli.ms.AddEllipse((0, 0, 0), (P.ISO_DIDZ, 0), P.ISO_MAZ / P.ISO_DIDZ)
        self.assertIn("centre", P.t_iso_apskritimas(toli)[0])


if __name__ == "__main__":
    unittest.main()

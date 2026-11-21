"""
„Kur klaida?“ (parodo AutoCAD'e, kas nubraižyta šiame žingsnyje) ir mirktelėjimas - su netikru AutoCAD.
"""

import os
import sys
import types
import unittest

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SAKNIS)
os.environ.setdefault("BREZLY_DUOMENYS", os.path.join(SAKNIS, "isvestis", "testu_duomenys"))

import branduolys as A      # noqa: E402
import brezly as B          # noqa: E402
import serveris as P        # noqa: E402


class Obj:
    def __init__(self, h, mn, mx):
        self.Handle, self._mn, self._mx, self.paryskinta = h, mn, mx, False

    def GetBoundingBox(self):
        return self._mn, self._mx

    def Highlight(self, t):
        self.paryskinta = t


class Talpa:
    def __init__(self, objs=()):
        self.sar = list(objs)

    @property
    def Count(self):
        return len(self.sar)

    def Item(self, i):
        return self.sar[i]


class Dok:
    def __init__(self, vardas="Drawing1.dwg"):
        self.Name, self.seed, self.ActiveSpace = vardas, "20", 1
        self.ModelSpace, self.PaperSpace = Talpa(), Talpa()

    def GetVariable(self, v):
        return {"HANDSEED": self.seed}[v]


class Dokai:
    def __init__(self, doc):
        self.doc = doc

    @property
    def Count(self):
        return 1

    def Item(self, i):
        return self.doc


class Acad:
    def __init__(self):
        self.ActiveDocument = Dok()
        self.Documents = Dokai(self.ActiveDocument)
        self.Visible, self.langas = True, None

    def ZoomWindow(self, a, b):
        self.langas = (tuple(a)[:2], tuple(b)[:2])


class KurKlaida(unittest.TestCase):
    def setUp(self):
        self.senas = (A.win32com, A.taskas, P.BUSENA["darbas"].b, dict(B._ZINGSNIO_PRADZIA))
        self.acad = Acad()
        A.win32com = types.SimpleNamespace(client=types.SimpleNamespace(GetActiveObject=lambda v: self.acad))
        A.taskas = lambda x, y, z=0: (x, y, z)
        P.BUSENA["darbas"].b = A.Braizytojas(self.acad)
        B._ZINGSNIO_PRADZIA.clear()
        self.duom = {"pamoka": "kampinis-irasas", "zingsnis": 1}

    def tearDown(self):
        A.win32com, A.taskas, P.BUSENA["darbas"].b, z = self.senas
        B._ZINGSNIO_PRADZIA.clear()
        B._ZINGSNIO_PRADZIA.update(z)

    def test_paryskina_tik_sio_zingsnio_objektus(self):
        doc = self.acad.ActiveDocument
        senas = Obj("1F", (0, 0, 0), (500, 500, 0))                  # nubraižytas anksčiau
        doc.ModelSpace.sar.append(senas)
        B.zingsnio_pradzia(self.duom)                                  # HANDSEED = 20
        naujas = [Obj("20", (230, 5, 0), (295, 45, 0)), Obj("2A", (295, 20, 0), (415, 20, 0))]
        doc.ModelSpace.sar += naujas
        r = B.kur_klaida(self.duom)
        self.assertEqual(r, {"ok": True, "kiek": 2})
        self.assertTrue(all(o.paryskinta for o in naujas))
        self.assertFalse(senas.paryskinta)
        (x0, y0), (x1, y1) = self.acad.langas
        self.assertLess(x0, 230)
        self.assertGreater(x1, 415)
        self.assertLess(y0, 5)
        self.assertGreater(y1, 45)

    def test_grizus_prie_zingsnio_pradzia_islieka(self):
        B.zingsnio_pradzia(self.duom)
        self.acad.ActiveDocument.ModelSpace.sar.append(Obj("21", (0, 0, 0), (10, 10, 0)))
        self.acad.ActiveDocument.seed = "30"
        B.zingsnio_pradzia(self.duom)                                  # tas pats brėžinys - senoji pradžia
        self.assertEqual(B.kur_klaida(self.duom)["kiek"], 1)

    def test_ne_toje_erdveje(self):
        B.zingsnio_pradzia(self.duom)
        doc = self.acad.ActiveDocument
        doc.ModelSpace.sar.append(Obj("21", (0, 0, 0), (10, 10, 0)))
        doc.ActiveSpace = 0                                            # žiūri į lapą
        r = B.kur_klaida(self.duom)
        self.assertEqual(r["kiek"], 0)
        self.assertIn("Model", r["pranesimas"])

    def test_nieko_nenubraizyta_ir_nezinoma_pradzia(self):
        self.assertIn("Nežinau", B.kur_klaida(self.duom)["pranesimas"])
        B.zingsnio_pradzia(self.duom)
        self.assertIn("nieko nenubraižei", B.kur_klaida(self.duom)["pranesimas"])

    def test_kitas_breziny_pradzia_is_naujo(self):
        B.zingsnio_pradzia(self.duom)
        kitas = Dok("Kampinis_irasas.dwg")
        kitas.seed = "40"
        self.acad.ActiveDocument = kitas
        self.assertIn("Nežinau", B.kur_klaida(self.duom)["pranesimas"])
        B.zingsnio_pradzia(self.duom)
        kitas.ModelSpace.sar.append(Obj("41", (0, 0, 0), (10, 10, 0)))
        self.assertEqual(B.kur_klaida(self.duom)["kiek"], 1)

    def test_mirkteleti_ne_windows(self):
        if B.WINDOWS:
            self.skipTest("Windows - tikras langas")
        self.assertEqual(B.mirkteleti({}), {"ok": False})

    def test_greitos_uzklausos(self):
        self.assertIn("/api/mirkteleti", B.BrezlyTvarkykle.GREITI)
        self.assertNotIn("/api/kur_klaida", B.BrezlyTvarkykle.GREITI)     # AutoCAD - per AutoCAD giją


if __name__ == "__main__":
    unittest.main()

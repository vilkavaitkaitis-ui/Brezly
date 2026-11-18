"""
Ryšys su AutoCAD (serveris.busena / prisijungti) su netikrais COM objektais - veikia ir be Windows.
Tikrinama, kad Brėžly prisijungia ir tada, kai AutoCAD rodo tik pradžios (Start) langą, yra užimtas,
atidaryta kita AutoCAD versija, o kai neprisijungia - pasako kodėl.
"""

import os
import sys
import types
import unittest

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SAKNIS)
os.environ.setdefault("BREZLY_DUOMENYS", os.path.join(SAKNIS, "isvestis", "testu_duomenys"))

import branduolys as A      # noqa: E402
import serveris as P        # noqa: E402

E_FAIL = -2147467259
RPC_E_CALL_REJECTED = -2147418111
RPC_S_SERVER_UNAVAILABLE = -2147023174


class ComKlaida(Exception):
    """Kaip pywintypes.com_error: args = (hresult, tekstas, excepinfo, argerr)."""
    def __init__(self, kodas, tekstas="klaida"):
        super().__init__(kodas, tekstas, None, None)


class Dok:
    def __init__(self, acad, vardas):
        self.acad, self.Name = acad, vardas

    def Activate(self):
        self.acad.aktyvus = self


class Dokai:
    def __init__(self, acad, vardai):
        self.acad = acad
        self.sar = [Dok(acad, v) for v in vardai]
        self.klaida = None
        self.prideta = 0

    @property
    def Count(self):
        if self.klaida:
            raise self.klaida
        return len(self.sar)

    def Item(self, i):
        return self.sar[i]

    def Add(self):
        self.prideta += 1
        d = Dok(self.acad, f"Drawing{len(self.sar) + 1}.dwg")
        self.sar.append(d)
        self.acad.aktyvus = d
        return d


class Acad:
    """Netikras AutoCAD. aktyvus=None - aktyvus pradžios (Start) skirtukas."""
    Version = "25.1"

    def __init__(self, vardai=(), aktyvus=True):
        self.Visible = False
        self.Documents = Dokai(self, vardai)
        self.aktyvus = self.Documents.sar[-1] if (aktyvus and self.Documents.sar) else None

    @property
    def ActiveDocument(self):
        if self.Documents.klaida:
            raise self.Documents.klaida
        if self.aktyvus is None:
            raise ComKlaida(E_FAIL, "No active document")
        return self.aktyvus


class Rysys(unittest.TestCase):
    def setUp(self):
        self.senas = (A.win32com, A.IMPORTO_KLAIDA, P.acad_procesai, P.pakeltas, A._PROGID["sar"], P.BUSENA["darbas"].b)
        self.objektai = {}          # ProgID -> Acad arba klaida
        self.paleista = []

        def gauti(vardas):
            o = self.objektai.get(vardas, ComKlaida(A.CO_E_CLASSSTRING, "Invalid class string"))
            if isinstance(o, Exception):
                raise o
            return o

        def paleisti(vardas):
            self.paleista.append(vardas)
            return Acad()
        A.win32com = types.SimpleNamespace(client=types.SimpleNamespace(GetActiveObject=gauti, Dispatch=paleisti))
        A.IMPORTO_KLAIDA = ""
        A._PROGID["sar"] = []
        P.acad_procesai = lambda: [4242] if any(not isinstance(o, Exception) or A.com_kodas(o) == A.MK_E_UNAVAILABLE
                                                for o in self.objektai.values()) else []
        P.pakeltas = lambda pid=None: None
        P.BUSENA["darbas"].b = None

    def tearDown(self):
        (A.win32com, A.IMPORTO_KLAIDA, P.acad_procesai, P.pakeltas, A._PROGID["sar"], P.BUSENA["darbas"].b) = self.senas

    def test_iprastas_brezinys(self):
        self.objektai["AutoCAD.Application"] = Acad(["Drawing1.dwg"])
        r = P.busena({})
        self.assertTrue(r["prisijungta"])
        self.assertEqual(r["brezinys"], "Drawing1.dwg")

    def test_pradzios_langas_be_breziniu(self):
        """Ką tik atidarytas AutoCAD rodo pradžios langą be brėžinių - tai ne „neprijungtas“."""
        acad = Acad([])
        self.objektai["AutoCAD.Application"] = acad
        r = P.busena({})
        self.assertTrue(r["prisijungta"])
        self.assertTrue(r["be_brezinio"])
        self.assertEqual(acad.Documents.prideta, 0, "būsenos tikrinimas pats brėžinių nekuria")
        # „Naujas“ / tikrinimas - sukuriamas brėžinys
        self.assertTrue(P.prisijungti({})["ok"])
        self.assertEqual(acad.Documents.prideta, 1)
        self.assertEqual(P.busena({})["brezinys"], "Drawing1.dwg")

    def test_aktyvus_pradzios_skirtukas(self):
        """Brėžiniai atidaryti, bet aktyvus pradžios skirtukas - ActiveDocument meta klaidą."""
        acad = Acad(["Velenas.dwg"], aktyvus=False)
        self.objektai["AutoCAD.Application"] = acad
        r = P.busena({})
        self.assertTrue(r["prisijungta"])
        self.assertEqual(r["brezinys"], "Velenas.dwg")
        b = P.braizytojas()                       # tikrinant - brėžinys suaktyvinamas
        self.assertEqual(b.acad.ActiveDocument.Name, "Velenas.dwg")

    def test_uzimtas_neatjungia(self):
        acad = Acad(["Drawing1.dwg"])
        self.objektai["AutoCAD.Application"] = acad
        P.busena({})
        acad.Documents.klaida = ComKlaida(RPC_E_CALL_REJECTED, "Call was rejected by callee.")
        r = P.busena({})
        self.assertTrue(r["prisijungta"])
        self.assertTrue(r["uzimtas"])
        self.assertEqual(r["brezinys"], "Drawing1.dwg")
        self.assertIsNotNone(P.BUSENA["darbas"].b, "užimtas AutoCAD - ryšys paliekamas")

    def test_kita_autocad_versija(self):
        """Įdiegti 2025 ir 2026, atidarytas 2025: bendras vardas jo neranda, versijos vardas - randa."""
        self.objektai["AutoCAD.Application"] = ComKlaida(A.MK_E_UNAVAILABLE, "Operation unavailable")
        self.objektai["AutoCAD.Application.25"] = Acad(["Drawing1.dwg"])
        A._PROGID["sar"] = ["AutoCAD.Application.25.1", "AutoCAD.Application.25"]
        r = P.busena({})
        self.assertTrue(r["prisijungta"], r)

    def test_autocad_paleistas_kaip_administratorius(self):
        self.objektai["AutoCAD.Application"] = ComKlaida(A.MK_E_UNAVAILABLE, "Operation unavailable")
        P.pakeltas = lambda pid=None: pid is not None          # AutoCAD - administratorius, Brėžly - ne
        r = P.busena({})
        self.assertFalse(r["prisijungta"])
        self.assertEqual(r["priezastis"], "teises_acad")
        self.assertIn("administratori", r["paaiskinimas"])
        self.assertIn("0x800401e3", r["klaida"])
        # „Jungtis“ - antro AutoCAD nepaleidžia, o pasako kodėl
        p = P.prisijungti({})
        self.assertFalse(p["ok"])
        self.assertEqual(p["priezastis"], "teises_acad")
        self.assertEqual(self.paleista, [])

    def test_brezly_paleistas_kaip_administratorius(self):
        self.objektai["AutoCAD.Application"] = ComKlaida(A.MK_E_UNAVAILABLE, "Operation unavailable")
        P.pakeltas = lambda pid=None: pid is None
        self.assertEqual(P.busena({})["priezastis"], "teises_brezly")

    def test_dar_kraunasi(self):
        self.objektai["AutoCAD.Application"] = ComKlaida(A.MK_E_UNAVAILABLE, "Operation unavailable")
        self.assertEqual(P.busena({})["priezastis"], "kraunasi")

    def test_neatidarytas_ir_paleidimas(self):
        r = P.busena({})
        self.assertFalse(r["prisijungta"])
        self.assertEqual(r["priezastis"], "neatidarytas")
        self.assertTrue(P.prisijungti({})["ok"])            # AutoCAD neveikia - paleidžiamas
        self.assertEqual(self.paleista, ["AutoCAD.Application"])

    def test_autocad_perkrautas(self):
        senas = Acad(["Senas.dwg"])
        self.objektai["AutoCAD.Application"] = senas
        P.busena({})
        senas.Documents.klaida = ComKlaida(RPC_S_SERVER_UNAVAILABLE, "The RPC server is unavailable.")
        self.objektai["AutoCAD.Application"] = Acad(["Naujas.dwg"])
        r = P.busena({})
        self.assertTrue(r["prisijungta"])
        self.assertEqual(r["brezinys"], "Naujas.dwg")

    def test_be_pywin32(self):
        A.win32com, A.IMPORTO_KLAIDA = None, "DLL load failed while importing pywintypes"
        r = P.busena({})
        self.assertFalse(r["prisijungta"])
        self.assertEqual(r["priezastis"], "pywin32")
        self.assertIn("pywin32", r["paaiskinimas"])
        self.assertFalse(P.prisijungti({})["ok"])

    def test_konsoles_isvestis_lietuviskame_windows(self):
        """tasklist išvestis OEM koduote (pvz. cp775) neturi nulaužti būsenos."""
        txt = P.dekoduoti('"acad.exe","4242","Console","1","812 345 K"\r\n'.encode("cp775") + bytes(range(128, 256)))
        self.assertIn('"acad.exe","4242"', txt)


if __name__ == "__main__":
    unittest.main()

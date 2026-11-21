"""
Greitis: AutoCAD darbai eina per vieną AutoCAD giją, o sąsaja (failai, progresas, būsena) atsako iškart,
net kai AutoCAD užimtas (atidarytas dialogas) ar vyksta ilgas tikrinimas. Automatinis tikrinimas nelaukia
užimto AutoCAD ir neperskaito nepasikeitusio brėžinio.
"""

import json
import os
import sys
import threading
import time
import types
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SAKNIS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("BREZLY_DUOMENYS", os.path.join(SAKNIS, "isvestis", "testu_duomenys"))

import branduolys as A      # noqa: E402
import brezly as B          # noqa: E402
import serveris as P        # noqa: E402
from test_rysys import Acad, ComKlaida, RPC_E_CALL_REJECTED   # noqa: E402


class Busena:
    IsQuiescent = True


class Greitis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.senas = (A.win32com, P.acad_procesai, P.pakeltas, B.aplinka, P.BUSENA["darbas"].b)
        cls.acad = Acad(["Drawing1.dwg"])
        cls.acad.GetAcadState = lambda: Busena
        doc = cls.acad.Documents.sar[0]
        doc.GetVariable = lambda v: {"HANDSEED": "1A2", "LOCALE": "LTH"}[v]
        doc.ModelSpace = type("MS", (), {"Count": 0})()
        doc.ActiveLayout = type("L", (), {"Name": "Model"})()
        A.win32com = types.SimpleNamespace(client=types.SimpleNamespace(GetActiveObject=lambda v: cls.acad,
                                                                         Dispatch=lambda v: cls.acad))
        P.acad_procesai = lambda: [1]
        P.pakeltas = lambda pid=None: None
        B.aplinka = lambda _=None: {"ok": True, "windows": True, "pilnas_idiegtas": True, "lt_idiegtas": False,
                                    "pilnas_veikia": True, "lt_veikia": False}
        P.BUSENA["darbas"].b = None
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), B.BrezlyTvarkykle)
        cls.srv.daemon_threads = True
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        (A.win32com, P.acad_procesai, P.pakeltas, B.aplinka, P.BUSENA["darbas"].b) = cls.senas

    def setUp(self):
        self.acad.Documents.klaida = None
        B._AUTO.update(raktas=None, pirstas=None, rez=None)

    def uzklausa(self, kelias, duom=None):
        t = time.time()
        req = urllib.request.Request(self.url + kelias, json.dumps(duom).encode() if duom is not None else None,
                                     {"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=30).read()
        return time.time() - t, (json.loads(r) if kelias.startswith("/api/") else r)

    def test_sasaja_nelaukia_uzimto_autocad(self):
        self.uzklausa("/api/busena", {})                     # prisijungta, būsena įsiminta
        rez = {}
        P.COM.vykdyti(lambda: None)
        threading.Thread(target=lambda: rez.update(ilgas=P.COM.vykdyti(lambda: time.sleep(1.5) or "baigta"))).start()
        time.sleep(0.2)
        self.assertTrue(P.COM.uzimta())
        for kelias, duom in (("/brezly.js", None), ("/api/progresas", {}), ("/api/info", {}),
                             ("/api/busena", {}), ("/api/tikrinti", {"pamoka": "kampinis-irasas", "zingsnis": 0, "tyliai": True})):
            t, r = self.uzklausa(kelias, duom)
            self.assertLess(t, 0.5, f"{kelias} laukė {t:.2f} s, kol AutoCAD gija užimta")
        self.assertTrue(self.uzklausa("/api/busena", {})[1]["prisijungta"], "būsena - iš atminties")
        self.assertEqual(self.uzklausa("/api/tikrinti", {"pamoka": "kampinis-irasas", "zingsnis": 0, "tyliai": True})[1],
                         {"ok": True, "laukia": True})
        time.sleep(1.6)
        self.assertEqual(rez["ilgas"], "baigta")

    def test_automatinis_nelaukia_dialogo(self):
        self.uzklausa("/api/busena", {})
        self.acad.Documents.klaida = ComKlaida(RPC_E_CALL_REJECTED, "Call was rejected by callee.")
        t, r = self.uzklausa("/api/tikrinti", {"pamoka": "kampinis-irasas", "zingsnis": 0, "tyliai": True})
        self.assertEqual(r, {"ok": True, "laukia": True})
        self.assertLess(t, 0.4, "anksčiau automatinis tikrinimas laukdavo ~10 s ir užšaldydavo visą Brėžly")
        t, r = self.uzklausa("/api/tikrinti", {"pamoka": "kampinis-irasas", "zingsnis": 0})
        self.assertLess(t, 3, "„Patikrinti“ užimto AutoCAD laukia ~2 s, ne 10 s")
        self.assertFalse(r["ok"])
        self.assertIn("užimtas", r["klaida"])

    def test_nepasikeitusio_breziniu_neperskaito(self):
        self.uzklausa("/api/busena", {})
        kiek = {"n": 0}
        z = B.pamokos.pamoka("kampinis-irasas")["zingsniai"][0]
        senas = z["tikrinti"]
        z["tikrinti"] = lambda b: kiek.update(n=kiek["n"] + 1) or ["dar ne"]
        try:
            duom = {"pamoka": "kampinis-irasas", "zingsnis": 0, "tyliai": True}
            for _ in range(3):
                r = self.uzklausa("/api/tikrinti", duom)[1]
                self.assertFalse(r["teisingai"])
            self.assertEqual(kiek["n"], 1, "brėžinys nepasikeitė - perskaitytas tik kartą")
            self.acad.Documents.sar[0].GetVariable = lambda v: {"HANDSEED": "1B0", "LOCALE": "LTH"}[v]   # naujas objektas
            self.uzklausa("/api/tikrinti", duom)
            self.assertEqual(kiek["n"], 2)
            self.uzklausa("/api/tikrinti", {"pamoka": "kampinis-irasas", "zingsnis": 0})              # rankinis - visada
            self.assertEqual(kiek["n"], 3)
        finally:
            z["tikrinti"] = senas
            self.acad.Documents.sar[0].GetVariable = lambda v: {"HANDSEED": "1A2", "LOCALE": "LTH"}[v]


if __name__ == "__main__":
    unittest.main()

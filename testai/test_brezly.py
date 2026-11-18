"""
Brėžly testai be AutoCAD (veikia Windows, Linux ir GitHub Actions).
Paleisti: python -m unittest discover -s testai -v
"""

import json
import os
import subprocess
import sys
import threading
import unittest
import urllib.request
from http.server import HTTPServer

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SAKNIS)
sys.path.insert(0, os.path.join(SAKNIS, "irankiai"))
os.environ.setdefault("BREZLY_DUOMENYS", os.path.join(SAKNIS, "isvestis", "testu_duomenys"))

import pamokos      # noqa: E402
import praktika     # noqa: E402


class Pamokos(unittest.TestCase):
    def test_zingsniu_id_unikalus(self):
        ids = [z["id"] for p in pamokos.PAMOKOS for z in p["zingsniai"]]
        self.assertEqual(len(ids), len(set(ids)), "žingsnių id turi nesikartoti - pagal juos randamas tikrinimas")

    def test_tikrinimo_zodyne_nera_pasenusiu_id(self):
        ids = {z["id"] for p in pamokos.PAMOKOS for z in p["zingsniai"]}
        self.assertEqual(set(pamokos.TIKRINIMAS) - ids, set(), "pamokos.TIKRINIMAS yra žingsnių, kurių nėra pamokos.json")

    def test_zingsniai_turi_privalomus_laukus(self):
        for p in pamokos.PAMOKOS:
            for k in ("id", "pavadinimas", "aprasas", "zingsniai", "testas"):
                self.assertIn(k, p, p.get("id"))
            for z in p["zingsniai"]:
                for k in ("id", "pavadinimas", "xp", "kodel", "zingsniai", "komandos", "uzuominos"):
                    self.assertIn(k, z, f'{p["id"]}/{z.get("id")}')

    def test_testo_atsakymai_galimi(self):
        for p in pamokos.PAMOKOS:
            for q in p["testas"]:
                self.assertTrue(0 <= q["t"] < len(q["v"]), q["k"])

    def test_korteliu_pamokos_egzistuoja(self):
        ids = {p["id"] for p in pamokos.PAMOKOS}
        for k in pamokos.KORTELES:
            self.assertIn(k["pamoka"], ids, k["k"])

    def test_viesai_be_funkciju(self):
        json.dumps(pamokos.viesai())        # turi būti paverčiama JSON (be Python funkcijų)


class Praktika(unittest.TestCase):
    def test_kiekvienai_uzduociai_yra_failai(self):
        for u in praktika.SARASAS:
            for galune in (".svg", ".pdf", ".dxf", "_ruosinys.dxf"):
                self.assertIsNotNone(praktika.failas(u["id"] + galune), u["id"] + galune)

    def test_failas_neleidzia_iseiti_is_aplanko(self):
        self.assertIsNone(praktika.failas("../brezly.py"))
        self.assertIsNone(praktika.failas("uzduotys.json"))

    def test_tikrinimas_su_netikru_autocad(self):
        """Imituojam AutoCAD COM objektus: geras brėžinys - be pastabų, skersmuo vietoj spindulio - pastaba."""
        class Obj:
            def __init__(self, tipas, **kw):
                self.ObjectName = tipas
                self.__dict__.update(kw)

        class MS(list):
            Count = property(len)

            def Item(self, i):
                return self[i]

        class B:
            def __init__(self, objektai):
                self.ms = MS(objektai)
                self.acad = type("A", (), {"ActiveDocument": type("D", (), {"Name": "U1_Tarpine_mano.dwg"})})

        def kartoti(f, **_):
            return f()
        geras = [Obj("AcDbCircle", Radius=20.0)] + [Obj("AcDbCircle", Radius=5.0) for _ in range(4)] + \
                [Obj("AcDbLine") for _ in range(4)] + [Obj("AcDbArc") for _ in range(4)]
        self.assertEqual(praktika.tikrinti("U1_Tarpine", B(geras), kartoti), [])
        blogas = [Obj("AcDbCircle", Radius=40.0)] + geras[1:]
        pastabos = praktika.tikrinti("U1_Tarpine", B(blogas), kartoti)
        self.assertTrue(any("tai skersmuo" in p for p in pastabos), pastabos)

    def test_lisp_atitinka_uzduotis(self):
        import generuoti
        _, pasikeite = generuoti.lisp_atnaujintas(generuoti.uzduotys())
        self.assertFalse(pasikeite, "lisp/Brezly.lsp pasenęs - paleisk: python irankiai/generuoti.py")


class Naujienos(unittest.TestCase):
    def test_versijos_nuo_naujausios(self):
        with open(os.path.join(SAKNIS, "naujienos.json"), encoding="utf-8") as f:
            v = json.load(f)["versijos"]
        sk = [tuple(int(x) for x in n["versija"].split(".")) for n in v]
        self.assertEqual(sk, sorted(sk, reverse=True), "naujienos.json: naujausia versija turi būti pirma")
        for n in v:
            for k in ("versija", "pavadinimas", "punktai"):
                self.assertIn(k, n)

    def test_release_aprasas(self):
        import naujienos
        self.assertIn("Naujas inžinerinis dizainas", naujienos.tekstas("0.9"))
        self.assertEqual(naujienos.tekstas("99.9"), "")


class Serveris(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import brezly
        cls.srv = HTTPServer(("127.0.0.1", 0), brezly.BrezlyTvarkykle)
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def gauti(self, kelias):
        with urllib.request.urlopen(self.url + kelias, timeout=5) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()

    def test_sasaja_ir_jos_failai(self):
        st, tipas, html = self.gauti("/")
        self.assertEqual(st, 200)
        self.assertIn("text/html", tipas)
        for v in ("brezly.css", "brezly.js"):
            self.assertIn(v.encode(), html)
            self.assertEqual(self.gauti("/" + v)[0], 200)

    def test_info_turi_pamokas_ir_praktika(self):
        d = json.loads(self.gauti("/api/info")[2])
        self.assertTrue(d["ok"])
        self.assertEqual(len(d["pamokos"]), len(pamokos.PAMOKOS))
        self.assertEqual([u["id"] for u in d["praktika"]], [u["id"] for u in praktika.SARASAS])

    def test_praktikos_brezinys(self):
        st, tipas, _ = self.gauti("/praktika/U1_Tarpine.svg")
        self.assertEqual((st, tipas), (200, "image/svg+xml"))

    def test_kodas_nepasiekiamas(self):
        for k in ("/brezly.py", "/../brezly.py", "/testavimas.json", "/praktika/../brezly.py"):
            with self.assertRaises(urllib.error.HTTPError, msg=k):
                self.gauti(k)


class ProgresoPerkelimas(unittest.TestCase):
    def setUp(self):
        import brezly
        self.b = brezly
        self.b.progresas({"S": {"xp": 120, "atlikta": {"failas": ["a", "b"]}, "praktika": {"U1_Tarpine": "2026-11-10"},
                                "zenkleliai": ["pirmas"], "vardas": "Robis"}, "nustatymai": {"tema": "dark"}})

    def test_eksportas_ir_importas(self):
        r = self.b.progresas_eksportuoti({})
        self.assertTrue(r["ok"])
        self.assertEqual(r["santrauka"]["xp"], 120)
        with open(r["kelias"], encoding="utf-8") as f:
            turinys = f.read()
        self.b.progresas({"S": {"xp": 5, "atlikta": {}, "praktika": {}}})
        perziura = self.b.progresas_importuoti({"turinys": turinys})
        self.assertEqual((perziura["dabar"]["xp"], perziura["failas"]["xp"]), (5, 120))
        self.assertEqual(self.b.progresas({})["S"]["xp"], 5, "be patvirtinimo nieko nekeičia")
        self.assertTrue(self.b.progresas_importuoti({"turinys": turinys, "patvirtinta": True})["ok"])
        self.assertEqual(self.b.progresas({})["S"]["xp"], 120)

    def test_svetimas_failas(self):
        for t in ("", "nesąmonė", '{"a": 1}', '{"S": {"be_xp": 1}}'):
            self.assertFalse(self.b.progresas_importuoti({"turinys": t})["ok"], t)

    def test_destytojo_ataskaita(self):
        r = self.b.destytojo_ataskaita({"vardas": "Vardenis Pavardenis", "html": "<!doctype html><p>x</p>"})
        self.assertTrue(r["ok"] and os.path.exists(r["kelias"]))
        self.assertFalse(self.b.destytojo_ataskaita({"html": "<script>"})["ok"])


class Surinkimas(unittest.TestCase):
    def test_visi_failai_yra(self):
        import surinkti
        surinkti.patikrinti()

    def test_programeles_tikrinimas(self):
        """app/tikrinimas.js su pavyzdiniais DXF (reikia Node.js; jei nėra - praleidžiama)."""
        try:
            r = subprocess.run(["node", os.path.join(SAKNIS, "testai", "tikrinimas.test.js")],
                               capture_output=True, text=True, timeout=60)
        except FileNotFoundError:
            self.skipTest("nėra Node.js")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()

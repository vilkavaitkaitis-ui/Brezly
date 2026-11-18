"""Anglų kalba: pamokos_en.json atitinka pamokos.json, užduotys ir pastabos išverstos, lietuvių kalba nepaliesta."""
import json
import os
import re
import sys
import unittest

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SAKNIS)
import pamokos      # noqa: E402
import praktika     # noqa: E402
import vertimas     # noqa: E402

LT_RAIDES = re.compile(r"[ąčęėįšųūžĄČĘĖĮŠŲŪŽ]")
LEIDZIAMA = ("Brėžinys", "ąčęėįšųūž", "Brėžly", "„Brėžinys“")       # sąmoningai lietuviški (6 pamoka)


def be_leidziamu(t):
    for x in LEIDZIAMA:
        t = t.replace(x, "")
    return t


class Pamokos(unittest.TestCase):
    def setUp(self):
        self.en = pamokos.viesai("en")

    def test_visos_pamokos_ir_zingsniai_isversti(self):
        for p in self.en["pamokos"]:
            for k in ("pavadinimas", "aprasas", "pabaiga"):
                self.assertFalse(LT_RAIDES.search(be_leidziamu(p.get(k, ""))), f"{p['id']}.{k}: {p.get(k)}")
            for z in p["zingsniai"]:
                tekstas = json.dumps({k: z.get(k) for k in pamokos.ZINGSNIO_TEKSTAI}, ensure_ascii=False)
                self.assertFalse(LT_RAIDES.search(be_leidziamu(tekstas)), f"{p['id']}/{z['id']}: {tekstas[:200]}")
            for q in p["testas"]:
                self.assertFalse(LT_RAIDES.search(be_leidziamu(json.dumps(q, ensure_ascii=False))), q["k"])

    def test_teisingi_atsakymai_ir_xp_is_lietuvisko(self):
        lt = pamokos.viesai("lt")
        for p_lt, p_en in zip(lt["pamokos"], self.en["pamokos"]):
            self.assertEqual([(z["id"], z["xp"]) for z in p_lt["zingsniai"]], [(z["id"], z["xp"]) for z in p_en["zingsniai"]])
            self.assertEqual([q["t"] for q in p_lt["testas"]], [q["t"] for q in p_en["testas"]])
            self.assertEqual([len(q["v"]) for q in p_lt["testas"]], [len(q["v"]) for q in p_en["testas"]], p_lt["id"])

    def test_lietuviskai_nepasikeite(self):
        self.assertEqual(pamokos.viesai("lt")["pamokos"][0]["pavadinimas"], "Failas ir formatai")

    def test_korteles_ir_patarimai(self):
        for k in self.en["korteles"]:
            self.assertFalse(LT_RAIDES.search(be_leidziamu(k["ka"] + k["pvz"])), k["k"])
        self.assertEqual(len(self.en["patarimai"]), len(pamokos.PATARIMAI))


class Uzduotys(unittest.TestCase):
    def test_visos_uzduotys_turi_anglu_tekstus(self):
        for u in praktika.sarasas("en"):
            self.assertFalse(LT_RAIDES.search(u["pav"] + u["uzd"] + "".join(u["z"])), u["id"])
            self.assertEqual(len(u["z"]), len(next(x for x in praktika.SARASAS if x["id"] == u["id"])["z"]))


class Pastabos(unittest.TestCase):
    def tearDown(self):
        vertimas.nustatyti("lt")

    def test_tikrinimo_pastabos_angliskai(self):
        vertimas.nustatyti("en")
        b = type("B", (), {"ms": type("T", (list,), {"Count": property(len), "Item": lambda s, i: s[i]})(),
                           "doc": None})()
        pastabos = pamokos.t_deze(b) + pamokos.t_iso_deze(b)
        self.assertTrue(pastabos)
        for p in pastabos:
            self.assertFalse(LT_RAIDES.search(p), p)
        vertimas.nustatyti("lt")
        self.assertIn("nerandu", pamokos.t_deze(b)[0])

    def test_kode_nera_pastabu_be_vertimo(self):
        """Kiekvienas pranešimas su lietuviškomis raidėmis tikrinimo funkcijose turi būti tr(...) viduje."""
        import ast
        for failas in ("pamokos.py", "praktika.py"):
            medis = ast.parse(open(os.path.join(SAKNIS, failas), encoding="utf-8").read())
            for fn in ast.walk(medis):
                if not (isinstance(fn, ast.FunctionDef) and (fn.name.startswith("t_") or fn.name in ("tikrinti", "_viena_detale", "_a3_vaizdai"))):
                    continue
                for r in [n for n in ast.walk(fn) if isinstance(n, ast.Return) and isinstance(n.value, ast.List)]:
                    for el in r.value.elts:
                        if isinstance(el, (ast.Constant, ast.JoinedStr)):
                            self.fail(f"{failas}:{el.lineno} {fn.name}: pranešimas be tr(lt, en)")


class Sasaja(unittest.TestCase):
    def test_zodynas(self):
        with open(os.path.join(SAKNIS, "sasaja_en.json"), encoding="utf-8") as f:
            d = json.load(f)["tekstai"]
        self.assertGreater(len(d), 200)
        for lt, en in d.items():
            self.assertEqual(lt.count("#"), en.count("#"), lt)
            self.assertEqual(lt.count("{}"), en.count("{}"), lt)


if __name__ == "__main__":
    unittest.main()

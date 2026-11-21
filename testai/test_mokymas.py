"""1.1 mokymosi įrankiai: tikslo paveikslėliai, žinynas (terminai LT-EN, standartų atmintinė),
komandų eilutės treniruoklis (mokymas.js), egzamino režimas ir silpnos vietos (brezly.js)."""
import json
import os
import re
import subprocess
import sys
import unittest

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SAKNIS)
sys.path.insert(0, os.path.join(SAKNIS, "irankiai"))
import pamokos      # noqa: E402

_LT = re.compile(r"[ąčęėįšųūžĄČĘĖĮŠŲŪŽ]")


class LT_RAIDES:        # programos vardas „Brėžly“ - leidžiamas ir angliškame tekste
    @staticmethod
    def search(t):
        return _LT.search(t.replace("Brėžly", ""))


def skaityti(f):
    with open(os.path.join(SAKNIS, f), encoding="utf-8") as x:
        return x.read()


class Paveiksleliai(unittest.TestCase):
    def test_atnaujinti(self):
        r = subprocess.run([sys.executable, os.path.join(SAKNIS, "irankiai", "paveiksleliai.py"), "--tikrinti"],
                           capture_output=True, text=True, timeout=120, cwd=SAKNIS)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_pamokose_nuorodos_i_esamus_failus(self):
        for kalba in ("lt", "en"):
            pav = [z["pav"] for p in pamokos.viesai(kalba)["pamokos"] for z in p["zingsniai"] if z.get("pav")]
            self.assertGreaterEqual(len(pav), 20, kalba)
            for k in pav:
                self.assertTrue(k.startswith("paveiksleliai/"), k)
                self.assertTrue(os.path.exists(os.path.join(SAKNIS, k)), k)
        en = {z["id"]: z.get("pav") for p in pamokos.viesai("en")["pamokos"] for z in p["zingsniai"]}
        self.assertEqual(en["ki-tekstas"], "paveiksleliai/en/ki-tekstas.svg")     # tekstas brėžinyje - angliškas

    def test_svg_be_iskarpu(self):
        for v in os.listdir(os.path.join(SAKNIS, "paveiksleliai")):
            if v.endswith(".svg"):
                s = skaityti(os.path.join("paveiksleliai", v))
                self.assertTrue(s.startswith("<svg") and s.rstrip().endswith("</svg>"), v)
                self.assertNotIn("<script", s, v)


class Zinynas(unittest.TestCase):
    def setUp(self):
        self.d = json.loads(skaityti("zinynas.json"))

    def test_terminai(self):
        t = self.d["terminai"]
        self.assertGreaterEqual(len(t), 50)
        self.assertEqual(len({x["lt"] for x in t}), len(t), "pasikartojantys terminai")
        for x in t:
            for k in ("lt", "en", "ka", "ka_en"):
                self.assertTrue(x.get(k), f"{x.get('lt')}: nėra {k}")
            self.assertFalse(LT_RAIDES.search(x["en"] + x["ka_en"]), x["lt"])
            if "komanda" in x:
                self.assertRegex(x["komanda"], r"^-?[A-Z0-9]+$")

    def test_atmintine(self):
        a = self.d["atmintine"]
        self.assertGreaterEqual(len(a), 6)
        for s in a:
            self.assertTrue(s["pavadinimas"] and s["pavadinimas_en"] and s["eilutes"])
            self.assertFalse(LT_RAIDES.search(s["pavadinimas_en"] + s.get("pastaba_en", "")), s["pavadinimas"])
            for e in s["eilutes"]:
                self.assertIn(len(e), (2, 4), e)
                if len(e) == 4:
                    self.assertFalse(LT_RAIDES.search(e[2] + e[3]), e)
                else:
                    self.assertFalse(LT_RAIDES.search(e[0] + e[1]), e)      # vienodi abiem kalbom
        formatai = dict(a[0]["eilutes"])
        self.assertEqual(formatai["A4"], "210 × 297 mm")
        self.assertEqual(formatai["A3"], "297 × 420 mm")


class Treniruoklis(unittest.TestCase):
    """mokymas.js logika per Node.js: kiekvienas įvedamas atsakymas priimamas, trumpiniai ir parinktys veikia."""

    def test_atsakymai(self):
        js = r"""
global.window = globalThis; require(process.argv[1] + "/mokymas.js");
const M = window.Mokymas._vidus, fs = require("fs");
const d = JSON.parse(fs.readFileSync(process.argv[1] + "/pamokos.json", "utf8"));
const b = M.baseinas(d.pamokos), al = M.trumpiniai(d.korteles), klaidos = [];
let n = 0;
b.forEach(x => x.ir.forEach(e => { if (e.rusis === "info") return; n++;
  if (!M.tinka(e.rusis === "enter" ? "" : e.iv, e, al)) klaidos.push(x.raktas + ": " + e.iv); }));
const e = (pr, iv) => ({ pr, iv, rusis: M.rusis(pr, iv) });
const T = [[e("Command:", "LINE"), "l", true], [e("Command:", "LINE"), "_line", true], [e("Command:", "LINE"), "pline", false],
  [e("Command:", "RECTANG"), "rec", true], [e("Specify first corner:", "0,0"), "0, 0", true], [e("Specify first corner:", "0,0"), "0,0,0", false],
  [e("Specify next point:", "@60<30"), "@60<30.0", true], [e("Specify next point:", "@60<30"), "60<30", false],
  [e("Select first object or [Radius/Polyline]:", "R"), "radius", true], [e("Select first object or [Radius/Polyline]:", "R"), "p", false],
  [e("Enter text:", "Detalė"), "detale", true], [e("Specify next point:", "(Enter)"), "", true], [e("Command:", "-VIEW"), "view", false]];
T.forEach(([x, a, l]) => { if (M.tinka(a, x, al) !== l) klaidos.push("tinka(" + a + ", " + x.iv + ") != " + l); });
if (M.rusis("Length Type:", "Decimal") !== "info" || M.rusis("Points:", "0,0 → 0,60") !== "info") klaidos.push("dialogai - ne info");
console.log(JSON.stringify({ zingsniai: b.length, ivedami: n, klaidos }));
"""
        try:
            r = subprocess.run(["node", "-e", js, SAKNIS], capture_output=True, text=True, timeout=60)
        except FileNotFoundError:
            self.skipTest("nėra Node.js")
        self.assertEqual(r.returncode, 0, r.stderr)
        rez = json.loads(r.stdout)
        self.assertEqual(rez["klaidos"], [])
        self.assertGreaterEqual(rez["zingsniai"], 40)
        self.assertGreaterEqual(rez["ivedami"], 120)


class Integracija(unittest.TestCase):
    def test_failai_programoje_ir_programeleje(self):
        import surinkti
        import brezly
        for f in ("mokymas.js", "zinynas.json"):
            self.assertIn(f, surinkti.DUOMENYS)
            self.assertIn(f, brezly.BrezlyTvarkykle.FAILAI)
        self.assertIn("paveiksleliai", surinkti.APLANKAI)
        h = skaityti("brezly.html")
        self.assertLess(h.index('src="mokymas.js"'), h.index('src="brezly.js"'))
        self.assertIn('src="mokymas.js"', skaityti(os.path.join("app", "index.html")))
        g = skaityti(os.path.join("irankiai", "generuoti.py"))
        self.assertIn('"mokymas.js", "zinynas.json"', g)
        w = skaityti(os.path.join(".github", "workflows", "programele.yml"))
        for f in ("mokymas.js", "zinynas.json", "paveiksleliai/**"):
            self.assertIn(f, w)

    def test_nauji_skyriai(self):
        js = skaityti("brezly.js")
        for x in ("const Egzaminas=", "const Silpnos=", "function trenPaleisti(", "function rodytiZinyna(",
                  'Silpnos.pazymeti("b")', 'Silpnos.pazymeti("u")', 'Silpnos.pazymeti("d")', 'Silpnos.pazymeti("k")'):
            self.assertIn(x, js)
        self.assertIn('data-v="zinynas"', skaityti("brezly.html"))
        app = skaityti(os.path.join("app", "index.html"))
        for x in ('["zinynas","Žinynas"]', 'sk === "treniruoklis"', "XP_TRENIRUOTE"):
            self.assertIn(x, app)

    def test_anglu_vertimai(self):
        t = json.loads(skaityti("sasaja_en.json"))["tekstai"]
        for k in ("Žinynas", "⌨ Komandų eilutė", "🎯 Silpnos vietos", "⏱ Egzamino režimas", "Pradėti egzaminą",
                  "✔ Baigti ir patikrinti", "✓ Įskaityta", "✗ Neįskaityta", "šis žingsnis", "jau nubraižyta",
                  "✗ Nepavykę tikrinimai: #", "Rekomenduojama: # min", "Egzaminas · {}"):
            self.assertIn(k, t)
            self.assertFalse(LT_RAIDES.search(t[k]), k)


if __name__ == "__main__":
    unittest.main()

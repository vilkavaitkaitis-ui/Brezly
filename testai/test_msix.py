"""
Microsoft Store (MSIX) versija: manifestas, versijos numeris ir programos elgesys pakete
(be savo atnaujinimų, nerašo į programos aplanką). Veikia ir be Windows.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.dom.minidom

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SAKNIS, "irankiai"))

import msix     # noqa: E402


class Manifestas(unittest.TestCase):
    def test_versija_store_formatu(self):
        self.assertEqual(msix.versija4("1.0.1"), "1.0.1.0")
        self.assertEqual(msix.versija4("1.0"), "1.0.0.0")
        self.assertEqual(msix.versija4("v2"), "2.0.0.0")
        with open(os.path.join(SAKNIS, "naujienos.json"), encoding="utf-8") as f:
            naujausia = json.load(f)["versijos"][0]["versija"]
        self.assertEqual(msix.versija4("0.0.0-bandymas"), msix.versija4(naujausia))

    def test_manifestas_tvarkingas(self):
        t = {"tapatybe": "12345Vardas.Brezly", "leidejas": 'CN=ABC-123, O="Vardas & Co"', "vardas": "Vardas <V>"}
        d = xml.dom.minidom.parseString(msix.manifestas(t, "1.0.1.0").encode("utf-8"))
        idt = d.getElementsByTagName("Identity")[0]
        self.assertEqual(idt.getAttribute("Name"), "12345Vardas.Brezly")
        self.assertEqual(idt.getAttribute("Publisher"), t["leidejas"])
        self.assertEqual(idt.getAttribute("Version"), "1.0.1.0")
        self.assertEqual(d.getElementsByTagName("PublisherDisplayName")[0].firstChild.data, "Vardas <V>")
        app = d.getElementsByTagName("Application")[0]
        self.assertEqual(app.getAttribute("Executable"), "Brezly.exe")
        self.assertEqual(app.getAttribute("EntryPoint"), "Windows.FullTrustApplication")
        self.assertIn("runFullTrust", [c.getAttribute("Name") for c in d.getElementsByTagName("rescap:Capability")])
        for laukas in ("Square150x150Logo", "Square44x44Logo"):
            failas = d.getElementsByTagName("uap:VisualElements")[0].getAttribute(laukas).split("\\")[-1]
            self.assertIn(failas, [i[0] for i in msix.IKONOS])

    def test_bloga_tapatybe_atmetama(self):
        senas = dict(os.environ)
        try:
            os.environ["MSIX_TAPATYBE"] = "Brėžly su tarpais"
            with self.assertRaises(SystemExit):
                msix.tapatybe()
            os.environ["MSIX_TAPATYBE"], os.environ["MSIX_LEIDEJAS"] = "Vardas.Brezly", "Vardas"
            with self.assertRaises(SystemExit):
                msix.tapatybe()
        finally:
            os.environ.clear()
            os.environ.update(senas)


class Pakete(unittest.TestCase):
    """Brėžly, paleistas iš MSIX: atnaujinimus tvarko Store, failus rašo į Dokumentai\\Brezly."""

    def _paleisti(self, supakuota):
        kodas = ("import json, brezly as B;"
                 "print(json.dumps({'url': B.ATNAUJINIMU_URL, 'rasomas': B.RASOMAS_APLANKAS, 'duom': B.DUOM,"
                 "'programa': B.PROGRAMOS_APLANKAS, 'atn': B.atnaujinimai({}), 'atnaujinti': B.atnaujinti({}) if "
                 + ("True" if supakuota else "False") + " else None}))")
        with tempfile.TemporaryDirectory() as duom:
            env = dict(os.environ, BREZLY_SUPAKUOTA="1" if supakuota else "0", BREZLY_DUOMENYS=duom,
                       BREZLY_ATNAUJINIMAI="https://example.invalid/atnaujinimai.json")
            r = subprocess.run([sys.executable, "-c", kodas], cwd=SAKNIS, env=env, capture_output=True, text=True,
                               encoding="utf-8", timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            return json.loads(r.stdout.strip().splitlines()[-1])

    def test_pakete_be_savo_atnaujinimu(self):
        d = self._paleisti(True)
        self.assertEqual(d["url"], "")
        self.assertEqual(d["atn"], {"ok": True, "yra": False, "parduotuve": True})
        self.assertFalse(d["atnaujinti"]["ok"])
        self.assertIn("Microsoft Store", d["atnaujinti"]["klaida"])
        self.assertEqual(d["rasomas"], d["duom"])

    def test_iprastai_kaip_anksciau(self):
        d = self._paleisti(False)
        self.assertTrue(d["url"].startswith("https://"))
        self.assertEqual(d["rasomas"], d["programa"])


if __name__ == "__main__":
    unittest.main()

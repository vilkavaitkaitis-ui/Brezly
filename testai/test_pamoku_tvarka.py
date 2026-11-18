"""
Pamokų tvarka: kiekviena pamoka eina po tų, kuriomis remiasi, o tekstuose pamokos
minimos pavadinimu, ne numeriu (kad pakeitus tvarką nuorodos nesugestų).
"""

import json
import os
import re
import unittest

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# pamoka -> pamokos, kurių įgūdžių ar failų jai reikia
REMIASI = {
    "2d": ["failas"],
    "sriftai": ["failas"],
    "matmenys": ["2d", "sriftai"],          # matmenys plokštei iš 2D, teksto stilius ISO_LT
    "lapas": ["sriftai"],                   # kampinio įrašo tekstas
    "pirmoji-3d": ["2d"],
    "projekcijos": ["pirmoji-3d", "lapas"],  # vaizdai iš 3D detalės A3 lape
    "aksonometrija": ["matmenys"],          # DIMALIGNED + Oblique
    "pjuviai": ["pirmoji-3d", "projekcijos"],  # VIEWBASE jau pažįstamas
    "schema": ["sriftai"],                  # atributai - tekstas
}


def _ikelti(failas):
    with open(os.path.join(SAKNIS, failas), encoding="utf-8") as f:
        return json.load(f)


class Tvarka(unittest.TestCase):
    def test_kiekviena_po_tu_kuriomis_remiasi(self):
        ids = [p["id"] for p in _ikelti("pamokos.json")["pamokos"]]
        for pamoka, reikia in REMIASI.items():
            for r in reikia:
                self.assertLess(ids.index(r), ids.index(pamoka), f"{r} turi būti prieš {pamoka}: {ids}")

    def test_angliska_tvarka_sutampa(self):
        ids = [p["id"] for p in _ikelti("pamokos.json")["pamokos"]]
        self.assertEqual(list(_ikelti("pamokos_en.json")["pamokos"]), ids)

    def test_tekstuose_pamokos_ne_numeriais(self):
        """„7 pamokos detalė“ sugenda pakeitus tvarką - minimas pavadinimas."""
        blogai = re.compile(r"\b\d+(-\d+)?\s+pamok|\bpamok\w*\s+\d|\blessons?\s+\d", re.I)
        for failas in ("pamokos.json", "pamokos_en.json"):
            for tekstas in re.findall(r'"((?:[^"\\]|\\.)*)"', open(os.path.join(SAKNIS, failas), encoding="utf-8").read()):
                self.assertIsNone(blogai.search(tekstas), f"{failas}: {tekstas}")
        with open(os.path.join(SAKNIS, "pamokos.py"), encoding="utf-8") as f:
            for i, eil in enumerate(f, 1):
                self.assertIsNone(blogai.search(eil), f"pamokos.py:{i}: {eil.strip()}")


if __name__ == "__main__":
    unittest.main()

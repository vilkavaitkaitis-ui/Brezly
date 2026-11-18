"""
Release aprašas iš naujienos.json (naudoja GitHub surinkimas, kai laukelis „Kas naujo“ tuščias).

  python irankiai/naujienos.py 1.0              -> tekstas versijai 1.0 (tuščias, jei jos naujienose nėra)
  python irankiai/naujienos.py 1.0 failas.txt   -> tą patį į failą (UTF-8; PowerShell'iui saugiau nei konsolė)
"""
import json
import os
import re
import sys

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tekstas(versija):
    with open(os.path.join(SAKNIS, "naujienos.json"), encoding="utf-8") as f:
        for n in json.load(f)["versijos"]:
            if n["versija"] == versija.strip().lstrip("vV") and n.get("punktai"):
                punktai = [re.sub(r"<[^>]+>", "", p) for p in n["punktai"]]      # be HTML žymių
                return "\n".join([n["pavadinimas"], ""] + [f"- {p}" for p in punktai])
    return ""


if __name__ == "__main__":
    t = tekstas(sys.argv[1] if len(sys.argv) > 1 else "")
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(t)
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(t)

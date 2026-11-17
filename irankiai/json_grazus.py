"""Įskaitomas JSON: žodynai po vieną raktą eilutėje, trumpi sąrašai - vienoje eilutėje.
Naudoja irankiai/generuoti.py; rankomis redaguotą failą galima „sutvarkyti“: python irankiai/json_grazus.py failas.json"""
import json
import sys

PLOTIS = 110


def _vienoje(x):
    return json.dumps(x, ensure_ascii=False)


def grazus(x, gylis=0):
    tarpai = " " * gylis
    if isinstance(x, dict):
        if not x:
            return "{}"
        eil = [f'{tarpai} {_vienoje(k)}: {grazus(v, gylis + 1)}' for k, v in x.items()]
        return "{\n" + ",\n".join(eil) + "\n" + tarpai + "}"
    if isinstance(x, list):
        vienoje = _vienoje(x)
        if len(vienoje) + gylis <= PLOTIS and not any(isinstance(v, dict) for v in x):
            return vienoje
        eil = [f"{tarpai} {grazus(v, gylis + 1)}" for v in x]
        return "[\n" + ",\n".join(eil) + "\n" + tarpai + "]"
    return _vienoje(x)


def irasyti(kelias, duom):
    with open(kelias, "w", encoding="utf-8", newline="\n") as f:
        f.write(grazus(duom) + "\n")


if __name__ == "__main__":
    for k in sys.argv[1:]:
        with open(k, encoding="utf-8") as f:
            irasyti(k, json.load(f))

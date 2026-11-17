"""
Brėžly: failai, kurie kuriami iš vieno šaltinio (pamokos.json ir praktika/uzduotys.json).

  python irankiai/generuoti.py              - atnaujina lisp/Brezly.lsp užduočių sąrašą ir sukuria svetainę
                                              isvestis/svetaine: atsisiuntimo puslapis + programele/
  python irankiai/generuoti.py --tikrinti   - tik patikrina, ar lisp/Brezly.lsp atnaujintas (GitHub Actions)

Išbandyti: python -m http.server -d isvestis/svetaine 8000  ->  http://localhost:8000 (programėlė - /programele/)
"""

import hashlib
import json
import os
import re
import shutil
import sys

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SAKNIS)

UZDUOTYS = os.path.join(SAKNIS, "praktika", "uzduotys.json")
LISP = os.path.join(SAKNIS, "lisp", "Brezly.lsp")
APP = os.path.join(SAKNIS, "app")
SVETAINES_SALTINIS = os.path.join(SAKNIS, "svetaine")
SVETAINE = os.path.join(SAKNIS, "isvestis", "svetaine")          # -> gh-pages
PROGRAMELE = os.path.join(SVETAINE, "programele")

LISP_PRADZIA = ";;; <uzduotys> - GENERUOJAMA is praktika/uzduotys.json (python irankiai/generuoti.py), ranka nekeisti"
LISP_PABAIGA = ";;; </uzduotys>"


def uzduotys():
    with open(UZDUOTYS, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ AutoCAD priedas (LISP)
# AutoLISP eilutės - tik ASCII (kitaip AutoCAD rodo „?“ priklausomai nuo Windows kodų lentelės)
_ASCII = str.maketrans({"ą": "a", "č": "c", "ę": "e", "ė": "e", "į": "i", "š": "s", "ų": "u", "ū": "u", "ž": "z",
                        "Ą": "A", "Č": "C", "Ę": "E", "Ė": "E", "Į": "I", "Š": "S", "Ų": "U", "Ū": "U", "Ž": "Z",
                        "ø": "D", "Ø": "D", "×": "x", "≈": "apie", "³": "3", "²": "2", "·": "-", "–": "-", "—": "-",
                        "„": "'", "“": "'", "”": "'", "°": " laipsniu", " ": " "})


def lisp_tekstas(s):
    s = str(s).replace("→", "->").translate(_ASCII)
    if any(ord(c) > 126 for c in s):
        raise ValueError(f"LISP tekste liko ne ASCII simbolių: {s!r} - papildyk _ASCII lentelę")
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _sk(x):
    return f"{float(x):.1f}" if float(x) == round(float(x), 1) else f"{float(x):g}"


def lisp_blokas(d):
    eil = [LISP_PRADZIA, "(setq *br:uzd*", " (list"]
    for u in sorted(d["uzduotys"], key=lambda u: u["nr"]):
        t = u.get("tikrinimas", {})
        taisykles = [f'(list "R" {_sk(r)} {k})' for r, k in t.get("apskritimai", {}).items()]
        taisykles += [f'(list "T" "{tp}" {k})' for tp, k in t.get("tipai", {}).items()]
        if t.get("turis"):
            taisykles += ['(list "T" "3DSOLID" 1)',
                          f'(list "TURIS" {_sk(t["turis"])} {_sk(d["tolerancija"]["turis"] * 100)})']
        if t.get("dydis"):
            taisykles.append(f'(list "DYDIS" {_sk(t["dydis"][0])} {_sk(t["dydis"][1])})')
        eil += [f'  (list {lisp_tekstas(u["id"])} {lisp_tekstas(u["pav"])} {lisp_tekstas(u["fmt"])} {lisp_tekstas(u["d"])} '
                f'{int(u["min"])} {int(u["xp"])}',
                f'   {lisp_tekstas(u["uzd"])}',
                f'   {lisp_tekstas(", ".join(u["kom"]))}',
                "   (list " + "\n         ".join(lisp_tekstas(z) for z in u["z"]) + ")",
                "   (list " + " ".join(taisykles) + "))", ""]
    eil[-1] = " ))"
    eil.append(LISP_PABAIGA)
    return "\n".join(eil)


def lisp_atnaujintas(d):
    """Grąžina (naujas_tekstas, ar_pasikeitė)."""
    with open(LISP, encoding="ascii", newline="") as f:
        senas = f.read()
    nl = "\r\n" if "\r\n" in senas else "\n"
    tekstas = senas.replace("\r\n", "\n")
    m = re.search(re.escape(LISP_PRADZIA) + r".*?" + re.escape(LISP_PABAIGA), tekstas, re.S)
    if not m:
        raise ValueError(f"lisp/Brezly.lsp nerasta žymė „{LISP_PRADZIA[:14]}...“")
    naujas = (tekstas[:m.start()] + lisp_blokas(d) + tekstas[m.end():]).replace("\n", nl)
    return naujas, naujas != senas


# ------------------------------------------------------------------ programėlė (PWA)
def svetaine(d):
    """Atsisiuntimo puslapis (svetaine/) su skaičiais iš pamokų ir užduočių + programėlė programele/."""
    import pamokos      # be pywin32 importuojasi (AutoCAD nereikia)
    if os.path.exists(SVETAINE):
        shutil.rmtree(SVETAINE)
    shutil.copytree(SVETAINES_SALTINIS, SVETAINE)
    for ikona in ("icon-192.png", "icon-512.png"):
        shutil.copy2(os.path.join(APP, ikona), SVETAINE)
    zym = {"{{PAMOKOS}}": len(pamokos.PAMOKOS), "{{ZINGSNIAI}}": sum(len(p["zingsniai"]) for p in pamokos.PAMOKOS),
           "{{UZDUOTYS}}": len(d["uzduotys"]), "{{VERSIJA}}": _versija()}
    kelias = os.path.join(SVETAINE, "index.html")
    with open(kelias, encoding="utf-8") as f:
        s = f.read()
    for k, v in zym.items():
        s = s.replace(k, str(v))
    with open(kelias, "w", encoding="utf-8") as f:
        f.write(s)
    open(os.path.join(SVETAINE, ".nojekyll"), "w").close()      # GitHub Pages: rodyti failus kaip yra
    return programele(d, pamokos)


def _versija():
    try:
        with open(os.path.join(SAKNIS, "versija.txt"), encoding="utf-8") as f:
            return f.read().strip().lstrip("vV") or "naujausia"
    except OSError:
        return "naujausia"


def programele(d, pamokos):
    shutil.copytree(APP, PROGRAMELE)
    with open(os.path.join(PROGRAMELE, "pamokos.json"), "w", encoding="utf-8") as f:
        json.dump(pamokos.viesai(), f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(PROGRAMELE, "uzduotys.js"), "w", encoding="utf-8") as f:
        f.write("/* GENERUOJAMA iš praktika/uzduotys.json (irankiai/generuoti.py) */\nwindow.BREZLY_UZDUOTYS = "
                + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + ";\n")
    os.makedirs(os.path.join(PROGRAMELE, "praktika"), exist_ok=True)
    for u in d["uzduotys"]:
        for galune in (".pdf", ".svg", "_ruosinys.dxf"):
            shutil.copy2(os.path.join(SAKNIS, "praktika", u["id"] + galune), os.path.join(PROGRAMELE, "praktika"))
    # talpykla (sw.js): visų failų sąrašas ir versija pagal turinį - pasikeitus failams telefonai gauna naujus
    failai, h = [], hashlib.sha256()
    for sakn, _, vardai in sorted(os.walk(PROGRAMELE)):
        for v in sorted(vardai):
            kelias = os.path.join(sakn, v)
            rel = os.path.relpath(kelias, PROGRAMELE).replace(os.sep, "/")
            if rel == "sw.js":
                continue
            failai.append(rel)
            with open(kelias, "rb") as f:
                h.update(rel.encode() + f.read())
    sw = os.path.join(PROGRAMELE, "sw.js")
    with open(sw, encoding="utf-8") as f:
        s = f.read()
    s = re.sub(r'const VERSIJA = "[^"]*";', f'const VERSIJA = "brezly-programele-{h.hexdigest()[:10]}";', s, count=1)
    s = re.sub(r"const FAILAI = \[.*?\];", "const FAILAI = " + json.dumps(["./"] + failai, indent=1) + ";", s,
               count=1, flags=re.S)
    with open(sw, "w", encoding="utf-8") as f:
        f.write(s)
    return len(failai)


def main():
    d = uzduotys()
    naujas, pasikeite = lisp_atnaujintas(d)
    if "--tikrinti" in sys.argv:
        if pasikeite:
            print("KLAIDA: lisp/Brezly.lsp neatnaujintas pagal praktika/uzduotys.json. Paleisk: python irankiai/generuoti.py")
            sys.exit(1)
        print("lisp/Brezly.lsp atitinka praktika/uzduotys.json")
        return
    if pasikeite:
        with open(LISP, "w", encoding="ascii", newline="") as f:
            f.write(naujas)
        print("Atnaujinta: lisp/Brezly.lsp")
    n = svetaine(d)
    print(f"Svetainė: {os.path.relpath(SVETAINE, SAKNIS)} (atsisiuntimo puslapis + programele/, {n} failai)")


if __name__ == "__main__":
    main()

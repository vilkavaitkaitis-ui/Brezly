"""
Brėžly: failai, kurie kuriami iš vieno šaltinio (pamokos.json ir praktika/uzduotys.json).

  python irankiai/generuoti.py              - atnaujina lisp/Brezly.lsp užduočių sąrašą
                                              ir sukuria svetainę aplanke isvestis/svetaine
                                              (svetaine/ -> /, programėlė app/ -> /programele/)
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
SVETAINE = os.path.join(SAKNIS, "isvestis", "svetaine")          # -> gh-pages (https://vilkavaitkaitis-ui.github.io/Brezly/)

NAUJIENOS = os.path.join(SAKNIS, "naujienos.json")
LISP_PRADZIA = ";;; <uzduotys> - GENERUOJAMA is praktika/uzduotys.json (python irankiai/generuoti.py), ranka nekeisti"
LISP_PABAIGA = ";;; </uzduotys>"


def versija():
    """Naujausia versija iš naujienos.json - ji įrašoma į AutoCAD priedą."""
    with open(NAUJIENOS, encoding="utf-8") as f:
        return json.load(f)["versijos"][0]["versija"]


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
    tekstas = tekstas[:m.start()] + lisp_blokas(d) + tekstas[m.end():]
    v = versija()
    tekstas = re.sub(r'^(;;;\s+Versija ).*$', lambda m_: m_.group(1) + v, tekstas, count=1, flags=re.M)
    tekstas = re.sub(r'\(setq \*br:ver\* "[^"]*"\)', f'(setq *br:ver* "{v}")', tekstas, count=1)
    naujas = tekstas.replace("\n", nl)
    return naujas, naujas != senas


# ------------------------------------------------------------------ programėlė (PWA)
def programele(d, PROGRAMELE):
    import pamokos      # be pywin32 importuojasi (AutoCAD nereikia)
    if os.path.exists(PROGRAMELE):
        shutil.rmtree(PROGRAMELE)
    shutil.copytree(APP, PROGRAMELE)
    shutil.copytree(os.path.join(SAKNIS, "sriftai"), os.path.join(PROGRAMELE, "sriftai"))     # šriftai be Google Fonts
    shutil.copytree(os.path.join(SAKNIS, "paveiksleliai"), os.path.join(PROGRAMELE, "paveiksleliai"))   # tikslo paveikslėliai
    for f in ("mokymas.js", "zinynas.json"):          # žinynas ir komandų treniruoklis - bendri su programa
        shutil.copy2(os.path.join(SAKNIS, f), PROGRAMELE)
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
    s = re.sub(r'const VERSIJA = "[^"]*";', f'const VERSIJA = "brezly-app-{h.hexdigest()[:10]}";', s, count=1)
    s = re.sub(r"const FAILAI = \[.*?\];", "const FAILAI = " + json.dumps(["./"] + failai, indent=1) + ";", s,
               count=1, flags=re.S)
    with open(sw, "w", encoding="utf-8") as f:
        f.write(s)
    open(os.path.join(PROGRAMELE, ".nojekyll"), "w").close()      # GitHub Pages: rodyti failus kaip yra
    return len(failai)


def personazai():
    """Personažų SVG iš brezly.js (per node irankiai/personazai.js). Be node - tušti (svetainė veikia ir be jų)."""
    import subprocess
    try:
        r = subprocess.run(["node", os.path.join(SAKNIS, "irankiai", "personazai.js")], capture_output=True, text=True,
                           encoding="utf-8", timeout=60, check=True)
        return json.loads(r.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        print(f"ĮSPĖJIMAS: personažai nesugeneruoti ({e}) - reikia Node.js")
        return {"personazai": [], "robis_dziaug": ""}


def pagrindinio_zymes(d, pamokos, html):
    """Pagrindinio puslapio sąrašai: pamokų lentelė, ruošiamos pamokos, užduočių kortelės, personažai, mini pamoka."""
    e = html.escape
    sarasas = "\n".join(
        f'        <div class="eil"><span class="nr">{i + 1}</span><span class="pv">{e(p["pavadinimas"])}</span>'
        f'<span class="sk">{len(p["zingsniai"])}</span></div>'
        for i, p in enumerate(pamokos.PAMOKOS))
    ateityje = "\n".join(
        f'        <div class="eil ateit"><span class="nr">–</span><span class="pv">{e(a["pavadinimas"])}'
        f'<span>{e(a["aprasas"])}</span></span><span class="sk">netrukus</span></div>'
        for a in pamokos.ATEITYJE)
    uzd = sorted(d["uzduotys"], key=lambda u: u["nr"])
    korteles = "\n".join(
        f'        <div class="plytele"><div class="vaizdas"><span class="didelis" aria-hidden="true">{u["nr"]}</span>'
        f'<span class="fmt">{e(u["fmt"])} · {e(u["d"])}</span>'
        f'<img src="praktika/{e(u["id"])}.svg" alt="Užduoties „{e(u["pav"])}“ brėžinys" loading="lazy"></div>'
        f'<div class="apac"><b>{e(u["pav"])}</b><span>~{int(u["min"])} min · <em>+{int(u["xp"])} XP</em></span>'
        f'<span class="kom">{e(" · ".join(k.split(" ")[0] for k in u["kom"][:4]))}</span></div></div>'
        for u in uzd)
    pers = personazai()
    ps = pers["personazai"]
    tamsus = ("#111111", "#1f4fd1", "#e2362b")
    kortos = "\n".join(
        f'        <div class="pers"><div class="vaizdas" style="background:{p["fonas"]}">'
        f'<i style="color:{"#f7f5f0" if p["fonas"] in tamsus else "#111111"}">{i + 1:02d}</i>{p["svg"]}</div>'
        f'<div class="apie"><b>{e(p["vardas"])}</b><span>{e(p["forma"])}</span><small>{e(p["txt"])}</small></div></div>'
        for i, p in enumerate(ps))
    pirma = pamokos.PAMOKOS[0]
    zingsniai = [{"pavadinimas": z["pavadinimas"], "xp": z["xp"], "kodel": z.get("kodel", "")} for z in pirma["zingsniai"]]
    return {"{{PAMOKU_SARASAS}}": sarasas, "{{ATEITYJE_SARASAS}}": ateityje, "{{UZDUOCIU_KORTELES}}": korteles,
            "{{PERSONAZAI}}": kortos, "{{PERS_SK}}": len(ps) or "–",
            "{{ROBIS}}": pers["robis_dziaug"], "{{ROBIO_VARDAS}}": e(ps[0]["vardas"]) if ps else "Brėžly",
            "{{PIRMA_PAV}}": e(pirma["pavadinimas"]), "{{UZD1_XP}}": int(uzd[0]["xp"]),
            "{{PIRMA_PAMOKA}}": json.dumps(zingsniai, ensure_ascii=False).replace("</", "<\\/")}


# praktikos brėžinio miniatiūra svetainei: Bauhaus spalvos, apkarpyta iki detalės (be rėmelio, užduoties teksto ir kampinio įrašo)
_SPALVOS = {'stroke="#0f766e"': 'stroke="#1f4fd1"', 'fill="#0f766e"': 'fill="#1f4fd1"',      # matmenys - mėlyna
            'stroke="#d11a1a"': 'stroke="#e2362b"', 'stroke="#1d4ed8"': 'stroke="#1f4fd1"'}    # ašys - raudona


def _taskai(el):
    """Apytiksliai: visi elemento koordinačių taškai (x, y)."""
    a = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', el))
    f = lambda k: float(a[k])
    try:
        if el.startswith("<line"):
            return [(f("x1"), f("y1")), (f("x2"), f("y2"))]
        if el.startswith("<circle"):
            return [(f("cx") - f("r"), f("cy") - f("r")), (f("cx") + f("r"), f("cy") + f("r"))]
        if el.startswith("<ellipse"):
            return [(f("cx") - f("rx"), f("cy") - f("ry")), (f("cx") + f("rx"), f("cy") + f("ry"))]
        if el.startswith("<rect"):
            x, y = float(a.get("x", 0)), float(a.get("y", 0))
            return [(x, y), (x + f("width"), y + f("height"))]
        if el.startswith("<text"):
            return [(f("x"), f("y"))]
        sk = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", a.get("points") or a.get("d") or "")]
        return list(zip(sk[0::2], sk[1::2]))
    except (KeyError, ValueError):
        return []


def praktikos_miniatiura(saltinis, tikslas):
    with open(saltinis, encoding="utf-8") as f:
        s = f.read()
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', s)
    plotis = float(m.group(1))
    s = re.sub(r'<rect width="[\d.]+" height="[\d.]+" fill="#ffffff"/>', "", s, count=1)    # popierius
    xs, ys = [], []
    for el in re.findall(r"<(?:line|circle|ellipse|rect|text|polygon|path)\b[^>]*>", s):
        t = _taskai(el)
        if t and all(21 < x < plotis - 6 and 21 < y < 250 for x, y in t):     # tik brėžinio laukas
            xs += [x for x, _ in t]
            ys += [y for _, y in t]
    for k, v in _SPALVOS.items():
        s = s.replace(k, v)
    if xs:
        x0, y0 = max(min(xs) - 10, 20.8), max(min(ys) - 10, 21)          # rėmelis (x=20, y=5) ir užduoties tekstas lieka už kadro
        x1, y1 = min(max(xs) + 12, plotis - 5.6), min(max(ys) + 8, 251)
        s = re.sub(r'<svg [^>]*>', f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.1f} {y0:.1f} {x1 - x0:.1f} {y1 - y0:.1f}">', s, count=1)
    with open(tikslas, "w", encoding="utf-8") as f:
        f.write(s)



# ------------------------------------------------------------------ svetainė (pagrindinis puslapis + demo/)
def svetaine(d):
    """svetaine/ su skaičiais ir sąrašais iš pamokų bei užduočių; programėlė - programele/ (jei įjungta)."""
    import html
    import pamokos      # be pywin32 importuojasi (AutoCAD nereikia)
    kur = SVETAINE
    if os.path.exists(kur):
        shutil.rmtree(kur)
    shutil.copytree(SVETAINES_SALTINIS, kur)
    for ikona in ("icon-192.png", "icon-512.png"):
        shutil.copy2(os.path.join(APP, ikona), kur)
    shutil.copytree(os.path.join(SAKNIS, "sriftai"), os.path.join(kur, "sriftai"),       # šriftai be Google Fonts
                    ignore=shutil.ignore_patterns("*.txt", "IBMPlexSans*", "IBMPlexSansCondensed*"))
    with open(os.path.join(SVETAINES_SALTINIS, "demo", "forma.json"), encoding="utf-8") as f:
        forma = json.load(f)
    with open(os.path.join(SVETAINES_SALTINIS, "nustatymai.json"), encoding="utf-8") as f:
        nust = json.load(f)
    siusti = forma.get("formsubmit", "").strip()
    budas = "formsubmit" if siusti else "google"
    registracija = bool(siusti or forma.get("forma"))
    zym = {"{{PAMOKOS}}": len(pamokos.PAMOKOS), "{{ZINGSNIAI}}": sum(len(p["zingsniai"]) for p in pamokos.PAMOKOS),
           "{{UZDUOTYS}}": len(d["uzduotys"]), "{{VERSIJA}}": versija(),
           "{{ATEITYJE}}": "\n".join(f'        <li><b>{html.escape(x["pavadinimas"])}</b><span>{html.escape(x["aprasas"])}</span></li>'
                                     for x in pamokos.ATEITYJE),
           **pagrindinio_zymes(d, pamokos, html),
           "{{FORMA}}": forma["forma"] or "{{FORMA}}", "{{FORMSUBMIT}}": siusti or "{{FORMSUBMIT}}",
           "{{LAUKAI}}": json.dumps(forma["laukai"]), "{{BUDAS}}": budas}
    # <!--ZYME-->...<!--/ZYME--> blokai paliekami arba išmetami pagal nustatymus
    blokai = {"ATIDARYTA": nust["atsisiuntimas"], "UZDARYTA": not nust["atsisiuntimas"], "PROGRAMELE": nust["programele"],
              "REGISTRACIJA": registracija, "BE_REGISTRACIJOS": not registracija}
    for sakn, _, vardai in os.walk(kur):
        for v in vardai:
            if v.endswith(".html"):
                kelias = os.path.join(sakn, v)
                with open(kelias, encoding="utf-8") as f:
                    s = f.read()
                for zyme, rodyti in blokai.items():
                    s = re.sub(rf"<!--{zyme}-->\n?(.*?)<!--/{zyme}-->\n?", (lambda m: m.group(1)) if rodyti else "", s, flags=re.S)
                for k, reiksme in zym.items():
                    if reiksme != k:
                        s = s.replace(k, str(reiksme))
                s = s.replace(' data-netlify="true" netlify-honeypot="gudrus"', "")
                with open(kelias, "w", encoding="utf-8") as f:
                    f.write(s)
    os.makedirs(os.path.join(kur, "praktika"), exist_ok=True)
    for u in d["uzduotys"]:
        praktikos_miniatiura(os.path.join(SAKNIS, "praktika", u["id"] + ".svg"), os.path.join(kur, "praktika", u["id"] + ".svg"))
    os.remove(os.path.join(kur, "demo", "forma.json"))
    os.remove(os.path.join(kur, "nustatymai.json"))
    open(os.path.join(kur, ".nojekyll"), "w").close()      # GitHub Pages: rodyti failus kaip yra
    if not nust["programele"]:
        return 0
    return programele(d, os.path.join(kur, "programele"))


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
    print(f"Svetainė: {os.path.relpath(SVETAINE, SAKNIS)} (programėlė programele/ - {n} failai)")


if __name__ == "__main__":
    main()

"""Brėžinio iššūkių (1.5, bandomoji funkcija) duomenys -> issukiai.json.

Geometrija čia skaičiuojama tiksliai (liestinės, užapvalinimai), JSON faile - tik primityvai:
  {"l": [x1, y1, x2, y2]}            linija
  {"a": [cx, cy, r, a0, a1]}         lankas prieš laikrodžio rodyklę nuo a0 iki a1 (laipsniais)
  {"c": [cx, cy, r]}                 apskritimas
Visų detalių kairysis apatinis kampas (ribų pradžia) - 0,0.
Matmenys brėžiniui: h/v (horizontalus/vertikalus), d (išnaša su tekstu prie apskritimo ar lanko).
Paleisti: python irankiai/issukiai_gen.py   (--tikrinti - tik patikrina, ar failas atnaujintas)"""
import json
import math
import os
import sys

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILAS = os.path.join(SAKNIS, "issukiai.json")


def r6(v):
    return round(v, 6) + 0.0


def L(x1, y1, x2, y2):
    return {"l": [r6(x1), r6(y1), r6(x2), r6(y2)]}


def A(cx, cy, r, a0, a1):
    return {"a": [r6(cx), r6(cy), r6(r), r6(a0 % 360), r6(a1 % 360)]}


def C(cx, cy, r):
    return {"c": [r6(cx), r6(cy), r6(r)]}


def kryzius(cx, cy, r):
    k = r + 4
    return [[r6(cx - k), r6(cy), r6(cx + k), r6(cy)], [r6(cx), r6(cy - k), r6(cx), r6(cy + k)]]


def h(x1, y1, x2, y2, y, txt):
    return {"t": "h", "a": [x1, y1], "b": [x2, y2], "y": y, "txt": txt}


def v(x1, y1, x2, y2, x, txt):
    return {"t": "v", "a": [x1, y1], "b": [x2, y2], "x": x, "txt": txt}


def d(cx, cy, r, kampas, txt, ilgis=11):
    return {"t": "d", "c": [r6(cx), r6(cy)], "r": r6(r), "kampas": kampas, "txt": txt, "ilgis": ilgis}


def suapvalintas(w, hh, r):
    """Stačiakampis w x hh su R r kampais."""
    return [L(r, 0, w - r, 0), A(w - r, r, r, 270, 360), L(w, r, w, hh - r), A(w - r, hh - r, r, 0, 90),
            L(w - r, hh, r, hh), A(r, hh - r, r, 90, 180), L(0, hh - r, 0, r), A(r, r, r, 180, 270)]


def staciakampis(w, hh):
    return [L(0, 0, w, 0), L(w, 0, w, hh), L(w, hh, 0, hh), L(0, hh, 0, 0)]


def issukiai():
    I = []
    # 1. Plokštelė su dviem skylėmis
    I.append({"id": "plokstele", "pav": "Plokštelė", "lyg": 1, "tikslas": 150, "xp": 30,
              "aprasas": "Stačiakampė plokštelė su dviem vienodomis skylėmis.",
              "kom": ["RECTANG", "CIRCLE", "COPY"], "patarimai": ["rectang", "copy", "mirror"],
              "geom": staciakampis(80, 50) + [C(15, 25, 5), C(65, 25, 5)],
              "asys": kryzius(15, 25, 5) + kryzius(65, 25, 5),
              "matmenys": [h(0, 0, 80, 0, -14, "80"), v(80, 0, 80, 50, 94, "50"), h(0, 50, 15, 25, 62, "15"),
                           h(65, 25, 80, 50, 62, "15"), v(0, 0, 15, 25, -12, "25"), d(15, 25, 5, 140, "2× ⌀10", 24)],
              "en": {"pav": "Small plate", "aprasas": "A rectangular plate with two identical holes."}})
    # 2. Kampuotis (L formos)
    I.append({"id": "kampuotis", "pav": "Kampuotis", "lyg": 1, "tikslas": 180, "xp": 35,
              "aprasas": "L formos kronšteinas su skylėmis abiejose lentynose.",
              "kom": ["LINE", "CIRCLE", "COPY"], "patarimai": ["pline", "copy"],
              "geom": [L(0, 0, 70, 0), L(70, 0, 70, 15), L(70, 15, 15, 15), L(15, 15, 15, 50), L(15, 50, 0, 50),
                       L(0, 50, 0, 0), C(55, 7.5, 4), C(7.5, 35, 4)],
              "asys": kryzius(55, 7.5, 4) + kryzius(7.5, 35, 4),
              "matmenys": [h(0, 0, 70, 0, -14, "70"), v(0, 0, 0, 50, -14, "50"), v(70, 0, 70, 15, 82, "15"),
                           h(0, 50, 15, 50, 62, "15"), h(55, 7.5, 70, 0, -28, "15"), v(7.5, 35, 0, 50, -28, "15"),
                           d(55, 7.5, 4, 55, "2× ⌀8")],
              "en": {"pav": "Angle bracket", "aprasas": "An L-shaped bracket with a hole in each flange."}})
    # 3. Flanšas
    c = (40, 40)
    skyles = [C(c[0] + 30 * math.cos(math.radians(a)), c[1] + 30 * math.sin(math.radians(a)), 4) for a in (45, 135, 225, 315)]
    asys = [[r6(c[0] - 46), c[1], r6(c[0] + 46), c[1]], [c[0], r6(c[1] - 46), c[0], r6(c[1] + 46)]]
    for s in skyles:
        x, y, _ = s["c"]
        asys += [[r6(c[0] + (x - c[0]) * 0.8), r6(c[1] + (y - c[1]) * 0.8), r6(c[0] + (x - c[0]) * 1.2), r6(c[1] + (y - c[1]) * 1.2)]]
    I.append({"id": "flansas", "pav": "Flanšas", "lyg": 2, "tikslas": 180, "xp": 40,
              "aprasas": "Apvalus flanšas: 4 skylės tolygiai išdėstytos ant ⌀60 apskritimo.",
              "kom": ["CIRCLE", "ARRAYPOLAR"], "patarimai": ["pcd", "copy"],
              "geom": [C(*c, 40), C(*c, 15)] + skyles,
              "asys": asys, "asys_apsk": [[c[0], c[1], 30]],
              "matmenys": [d(*c, 40, 120, "⌀80"), d(*c, 15, 200, "⌀30"),
                           d(c[0] + 30 * math.cos(math.radians(45)), c[1] + 30 * math.sin(math.radians(45)), 4, 40, "4× ⌀8"),
                           d(*c, 30, 290, "⌀60")],
              "en": {"pav": "Flange", "aprasas": "A round flange: 4 holes evenly spaced on a ⌀60 circle."}})
    # 4. Užapvalinta plokštė
    sk4 = [C(15, 15, 4), C(85, 15, 4), C(15, 45, 4), C(85, 45, 4)]
    I.append({"id": "uzapvalinta", "pav": "Užapvalinta plokštė", "lyg": 2, "tikslas": 240, "xp": 45,
              "aprasas": "Plokštė su R10 kampais ir keturiomis tvirtinimo skylėmis.",
              "kom": ["RECTANG", "FILLET", "CIRCLE", "ARRAYRECT"], "patarimai": ["rectang", "fillet", "copy", "mirror"],
              "geom": suapvalintas(100, 60, 10) + sk4,
              "asys": [a for s in sk4 for a in kryzius(s["c"][0], s["c"][1], 4)],
              "matmenys": [h(0, 0, 100, 0, -14, "100"), v(100, 0, 100, 60, 126, "60"), h(15, 15, 85, 15, -28, "70"),
                           v(85, 15, 85, 45, 112, "30"), h(0, 60, 15, 45, 72, "15"), v(0, 0, 15, 15, -14, "15"),
                           d(15, 45, 4, 135, "4× ⌀8"), d(90, 50, 10, 45, "R10")],
              "en": {"pav": "Rounded plate", "aprasas": "A plate with R10 corners and four mounting holes."}})
    # 5. Plokštė su grioveliu
    I.append({"id": "griovelis", "pav": "Plokštė su grioveliu", "lyg": 3, "tikslas": 300, "xp": 55,
              "aprasas": "Plokštė su ilgu grioveliu viduryje ir dviem skylėmis.",
              "kom": ["RECTANG", "CIRCLE", "LINE", "TRIM"], "patarimai": ["rectang", "griovelis", "copy", "mirror"],
              "geom": staciakampis(90, 50) + [A(30, 25, 6, 90, 270), A(60, 25, 6, 270, 90), L(30, 31, 60, 31),
                                               L(30, 19, 60, 19), C(10, 40, 3), C(80, 40, 3)],
              "asys": kryzius(30, 25, 6) + kryzius(60, 25, 6) + kryzius(10, 40, 3) + kryzius(80, 40, 3) + [[20, 25, 70, 25]],
              "matmenys": [h(0, 0, 30, 25, -14, "30"), h(30, 25, 60, 25, -14, "30"), h(60, 25, 90, 0, -14, "30"),
                           h(0, 0, 90, 0, -28, "90"), v(90, 0, 90, 50, 104, "50"), v(0, 0, 30, 25, -14, "25"),
                           v(0, 0, 10, 40, -28, "40"), h(0, 50, 10, 40, 62, "10"), h(80, 40, 90, 50, 62, "10"),
                           d(60, 25, 6, 30, "R6"), d(10, 40, 3, 150, "2× ⌀6")],
              "en": {"pav": "Slotted plate", "aprasas": "A plate with a long slot in the middle and two holes."}})
    # 6. Svirtis: dvi stebulės sujungtos liestinėmis
    c1, c2, R1, R2 = (20, 20), (100, 20), 20, 12
    fi = math.degrees(math.acos((R1 - R2) / (c2[0] - c1[0])))
    p = lambda cc, r, a: (cc[0] + r * math.cos(math.radians(a)), cc[1] + r * math.sin(math.radians(a)))
    I.append({"id": "svirtis", "pav": "Svirtis", "lyg": 3, "tikslas": 360, "xp": 60,
              "aprasas": "Dvi stebulės, sujungtos liestinėmis linijomis.",
              "kom": ["CIRCLE", "LINE + Tangent", "TRIM"], "patarimai": ["tan", "mirror"],
              "geom": [A(*c1, R1, fi, 360 - fi), A(*c2, R2, -fi, fi), L(*p(c1, R1, fi), *p(c2, R2, fi)),
                       L(*p(c1, R1, -fi), *p(c2, R2, -fi)), C(*c1, 10), C(*c2, 5)],
              "asys": [[2, 20, 116, 20], [20, 2, 20, 38], [100, 6, 100, 34]],
              "matmenys": [h(20, 20, 100, 20, -12, "80"), d(*c1, R1, 140, "R20"), d(*c2, R2, 50, "R12"),
                           d(*c1, 10, 225, "⌀20"), d(*c2, 5, 300, "⌀10")],
              "en": {"pav": "Lever", "aprasas": "Two bosses joined by tangent lines."}})
    for nr, i in enumerate(I, 1):
        i["nr"] = nr
    return I


def turinys():
    d = {"_": "Sugeneruota irankiai/issukiai_gen.py - ranka nekeisti.",
         "tolerancija": {"padetis": 0.3, "beveik": 2.0}, "issukiai": issukiai()}
    return json.dumps(d, ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    t = turinys()
    if "--tikrinti" in sys.argv:
        with open(FAILAS, encoding="utf-8") as f:
            if f.read() != t:
                sys.exit("issukiai.json pasenęs - paleisk python irankiai/issukiai_gen.py")
        print("issukiai.json atnaujintas")
    else:
        with open(FAILAS, "w", encoding="utf-8", newline="\n") as f:
            f.write(t)
        print("Sukurta: issukiai.json")

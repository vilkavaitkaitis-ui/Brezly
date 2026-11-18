"""
Pavyzdiniai praktikos atsakymai U4, U6, U7 su tikrais AutoCAD objektais (DXF R2010).

Seni pavyzdžiai buvo DXF R12, kuriame nėra HATCH ir ELLIPSE, o schemos ženklai buvo atskiros linijos,
todėl tikrinimas (praktika.py, app/tikrinimas.js) atidaryto pavyzdžio nepriimdavo. Šis įrankis:
  U4 - pjūvio A-A brūkšniuotė -> HATCH ANSI31 (apskritimas ø30 su grioveliu 8×4)
  U6 - izoapskritimas (72 taškų polilinija) -> ELLIPSE (kaip ISODRAFT + ELLIPSE Isocircle)
  U7 - elektros ženklai -> blokai BATERIJA, JUNGIKLIS, REZISTORIUS, LEMPUTE su atributais POZ ir VERTE;
       jungimo taškų SOLID viršūnių tvarka pataisyta (buvo „smėlio laikrodis“)

Reikia ezdxf:  pip install ezdxf
Paleisti:      python irankiai/pavyzdziai.py         (perrašo praktika/U4_Velenas.dxf, U6_..., U7_...)
Šaltinis - tie patys failai R12 formatu (git istorijoje iki šio įrankio).
"""

import math
import os
import re
import sys

import ezdxf
from ezdxf.addons import Importer

SAKNIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRAKTIKA = os.path.join(SAKNIS, "praktika")
VERSIJA = "R2010"           # UTF-8: lietuviškos raidės ir Ω be kodų lentelių


def unicode_tekstas(t):
    """AutoCAD R12 kodai \\U+03A9 -> tikri simboliai (R2010 failas yra UTF-8)."""
    return re.sub(r"\\U\+([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), t)


def perkelti(senas):
    """Naujas R2010 dokumentas su visais seno brėžinio objektais, sluoksniais, stiliais ir antrašte."""
    naujas = ezdxf.new(VERSIJA, units=ezdxf.units.MM)
    imp = Importer(senas, naujas)
    imp.import_tables()
    imp.import_modelspace()
    imp.finalize()
    for k in ("$LTSCALE", "$LIMMIN", "$LIMMAX", "$EXTMIN", "$EXTMAX", "$TEXTSTYLE", "$CLAYER", "$DIMSCALE"):
        if k in senas.header:
            naujas.header[k] = senas.header[k]
    naujas.header["$INSUNITS"] = 4          # mm
    naujas.header["$MEASUREMENT"] = 1       # metrinė sistema
    for e in naujas.modelspace().query("TEXT"):
        e.dxf.text = unicode_tekstas(e.dxf.text)
    return naujas


def u4(doc):
    """Pjūvis A-A: brūkšniuotės linijos -> HATCH ANSI31 ribose (lankas R15 be griovelio + 3 griovelio linijos)."""
    msp = doc.modelspace()
    for e in list(msp.query('LINE[layer=="BRUKSNIUOTE"]')):
        msp.delete_entity(e)
    lankas = next(e for e in msp.query("ARC") if abs(e.dxf.radius - 15) < 1e-6)
    c, r = lankas.dxf.center, lankas.dxf.radius
    a1, a2 = lankas.dxf.start_angle, lankas.dxf.end_angle         # 105.47° -> 74.53° (prieš laikrodžio rodyklę)
    p_pab = (c.x + r * math.cos(math.radians(a2)), c.y + r * math.sin(math.radians(a2)))
    p_prad = (c.x + r * math.cos(math.radians(a1)), c.y + r * math.sin(math.radians(a1)))
    dugnas = c.y + r - 4                                          # griovelio gylis 4
    h = msp.add_hatch(dxfattribs={"layer": "BRUKSNIUOTE", "color": 256})
    h.set_pattern_fill("ANSI31", scale=1.0, angle=0.0)
    kelias = h.paths.add_edge_path()
    kelias.add_arc((c.x, c.y), r, a1, a2, ccw=True)
    kelias.add_line(p_pab, (p_pab[0], dugnas))
    kelias.add_line((p_pab[0], dugnas), (p_prad[0], dugnas))
    kelias.add_line((p_prad[0], dugnas), p_prad)
    return "HATCH ANSI31 pjūvyje A-A"


def u6(doc):
    """Izoapskritimas ø14 (2:1) viršutinėje plokštumoje: polilinija -> ELLIPSE."""
    msp = doc.modelspace()
    pl = next(e for e in msp.query("POLYLINE") if e.is_closed)
    taskai = [(v.dxf.location.x, v.dxf.location.y) for v in pl.vertices]
    cx = (max(p[0] for p in taskai) + min(p[0] for p in taskai)) / 2
    cy = (max(p[1] for p in taskai) + min(p[1] for p in taskai)) / 2
    d = 14 * 2                                          # ø14 mastelis 2:1
    didz = d * math.sqrt(1.5) / 2                       # izometrijoje didžioji pusašė d·√(3/2)/2
    maz = d * math.sqrt(0.5) / 2                        #             mažoji d·√(1/2)/2
    tolimiausias = max(taskai, key=lambda p: math.hypot(p[0] - cx, p[1] - cy))
    kampas = math.atan2(tolimiausias[1] - cy, tolimiausias[0] - cx)
    if abs(math.hypot(tolimiausias[0] - cx, tolimiausias[1] - cy) - didz) > 0.05:
        raise ValueError("U6: polilinija nebeatitinka izoapskritimo ø14 2:1 - patikrink brėžinį")
    msp.add_ellipse((cx, cy), major_axis=(didz * math.cos(kampas), didz * math.sin(kampas)), ratio=maz / didz,
                    dxfattribs={"layer": pl.dxf.layer, "color": 256})
    msp.delete_entity(pl)
    return f"ELLIPSE centras ({cx:.2f}; {cy:.2f}), pusašės {didz:.2f} ir {maz:.2f}"


# U7: kiekvienas ženklas - bazinis taškas, ženklo objektai (sluoksnis, tipas, taškai) ir atributai
ZENKLAI = {
    "BATERIJA": {"bazes": [((40, 200), {"POZ": "G1", "VERTE": "9 V"})],
                 "objektai": [("KONTURAS", "LINE", (34, 202), (46, 202)), ("REMELIS", "LINE", (37, 198), (43, 198)),
                              ("REMELIS", "LINE", (37, 198.2), (43, 198.2)), ("TEKSTAS", "TEXT", (44, 205), "+")],
                 "atributai": {"POZ": (26, 202), "VERTE": (26, 196)}},
    "JUNGIKLIS": {"bazes": [((65, 230), {"POZ": "S1"})],
                  "objektai": [("KONTURAS", "CIRCLE", (65, 230), 0.8), ("KONTURAS", "CIRCLE", (80, 230), 0.8),
                               ("KONTURAS", "LINE", (65, 230), (79, 236))],
                  "atributai": {"POZ": (70, 239)}},
    "REZISTORIUS": {"bazes": [((110, 230), {"POZ": "R1", "VERTE": "1 kΩ"})],
                    "objektai": [("KONTURAS", "LINE", (105, 228), (115, 228)), ("KONTURAS", "LINE", (115, 228), (115, 232)),
                                 ("KONTURAS", "LINE", (115, 232), (105, 232)), ("KONTURAS", "LINE", (105, 232), (105, 228))],
                    "atributai": {"POZ": (106, 236), "VERTE": (105, 222)}},
    "LEMPUTE": {"bazes": [((140, 200), {"POZ": "H1", "VERTE": "6 V"}), ((170, 200), {"POZ": "H2", "VERTE": "6 V"})],
                "objektai": [("KONTURAS", "CIRCLE", (140, 200), 5.0),
                             ("KONTURAS", "LINE", (136.46, 196.46), (143.54, 203.54)),
                             ("KONTURAS", "LINE", (136.46, 203.54), (143.54, 196.46))],
                "atributai": {"POZ": (146, 202), "VERTE": (146, 196.5)}},
}
UZKLAUSOS = {"POZ": "Pozicija (pvz. R1)", "VERTE": "Vardinė reikšmė (pvz. 1 kΩ)"}


def _artimas(a, b, tol=0.02):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def _rasti(msp, sluoksnis, tipas, a, b, poslinkis=(0, 0)):
    """Ženklo objektas modelio erdvėje (pirmo ženklo koordinatės + poslinkis kitiems įterpimams)."""
    a = (a[0] + poslinkis[0], a[1] + poslinkis[1])
    for e in msp.query(f'{tipas}[layer=="{sluoksnis}"]'):
        if tipas == "LINE":
            b2 = (b[0] + poslinkis[0], b[1] + poslinkis[1])
            s, f = (e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)
            if (_artimas(s, a) and _artimas(f, b2)) or (_artimas(s, b2) and _artimas(f, a)):
                return e
        elif tipas == "CIRCLE":
            if _artimas((e.dxf.center.x, e.dxf.center.y), a) and abs(e.dxf.radius - b) < 1e-3:
                return e
        elif tipas == "TEXT":
            if _artimas((e.dxf.insert.x, e.dxf.insert.y), a) and e.dxf.text == b:
                return e
    raise ValueError(f"U7: nerastas {tipas} {sluoksnis} ties {a}")


def _tekstas(msp, xy, poslinkis, tekstas):
    for e in msp.query('TEXT[layer=="TEKSTAS"]'):
        if _artimas((e.dxf.insert.x, e.dxf.insert.y), (xy[0] + poslinkis[0], xy[1] + poslinkis[1]), 0.05) and e.dxf.text == tekstas:
            return e
    raise ValueError(f"U7: nerastas tekstas „{tekstas}“")


def u7(doc):
    msp = doc.modelspace()
    stilius = next(iter(msp.query("TEXT"))).dxf.style
    n = 0
    for vardas, z in ZENKLAI.items():
        (bx, by), _ = z["bazes"][0]
        blk = doc.blocks.new(vardas, base_point=(0, 0))
        for sl, tipas, a, b in z["objektai"]:
            e = _rasti(msp, sl, tipas, a, b)
            if tipas == "LINE":
                blk.add_line((a[0] - bx, a[1] - by), (b[0] - bx, b[1] - by), dxfattribs={"layer": sl})
            elif tipas == "CIRCLE":
                blk.add_circle((a[0] - bx, a[1] - by), b, dxfattribs={"layer": sl})
            else:
                blk.add_text(b, dxfattribs={"layer": sl, "height": e.dxf.height, "style": e.dxf.style,
                                            "insert": (a[0] - bx, a[1] - by)})
        for zyme, (ax, ay) in z["atributai"].items():
            blk.add_attdef(zyme, (ax - bx, ay - by), dxfattribs={"layer": "TEKSTAS", "height": 3.5, "style": stilius,
                                                                  "prompt": UZKLAUSOS[zyme]})
        for (ix, iy), reiksmes in z["bazes"]:
            pos = (ix - bx, iy - by)
            for sl, tipas, a, b in z["objektai"]:
                msp.delete_entity(_rasti(msp, sl, tipas, a, b, pos))
            for zyme, tekstas in reiksmes.items():
                ax, ay = z["atributai"][zyme]
                senas = _tekstas(msp, (ax, ay), pos, tekstas)
                msp.delete_entity(senas)
            ref = msp.add_blockref(vardas, (ix, iy), dxfattribs={"layer": "KONTURAS"})
            ref.add_auto_attribs(reiksmes)
            n += 1
    # SOLID viršūnės eina 0-1-3-2: stačiakampiui reikia sukeisti 3-ią ir 4-ą, kitaip piešiamas „smėlio laikrodis“
    for e in msp.query("SOLID"):
        v = [e.dxf.vtx0, e.dxf.vtx1, e.dxf.vtx2, e.dxf.vtx3]
        if len({(p.x, p.y) for p in v}) == 4:
            e.dxf.vtx2, e.dxf.vtx3 = v[3], v[2]
    return f"{len(ZENKLAI)} blokai, {n} įterpimai (INSERT) su atributais POZ, VERTE; jungimo taškai pataisyti"


def main():
    for uid, f in (("U4_Velenas", u4), ("U6_Izometrija", u6), ("U7_Schema", u7)):
        kelias = os.path.join(PRAKTIKA, uid + ".dxf")
        senas = ezdxf.readfile(kelias)
        if senas.dxfversion != "AC1009":
            print(f"{uid}: jau {senas.dxfversion} - praleidžiama (perdaryti galima tik iš R12 originalo)")
            continue
        doc = perkelti(senas)
        aprasas = f(doc)
        audit = doc.audit()
        if audit.has_errors:
            audit.print_error_report()
            sys.exit(f"{uid}: DXF klaidos")
        doc.saveas(kelias)
        print(f"{uid}: {VERSIJA} - {aprasas}")


if __name__ == "__main__":
    main()

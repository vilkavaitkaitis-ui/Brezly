"""
Brėžly brėžinio iššūkiai ir brėžinio peržiūra (1.5, bandomoji funkcija - įjungiama Nustatymuose).

Iššūkis: rodomas tik detalės brėžinys su matmenimis. Mokinys braižo AutoCAD'e bet kurioje vietoje,
tikrinimas palygina nubraižytą geometriją (linijas, lankus, apskritimus) su teisinga - nesvarbu, kur
detalė nubraižyta ir iš kiek dalių sudėta linija. Pagalbinės linijos (sluoksniai ASYS, PAGALBINIS,
DEFPOINTS ar ne ištisinis linijos tipas), matmenys ir tekstai netikrinami.

Peržiūra (kaip šachmatų partijos peržiūra): kol vyksta iššūkis, atskiroje gijoje įrašomos AutoCAD komandos
(dokumento įvykiai BeginCommand / EndCommand / SysVarChanged; jei įvykių prijungti nepavyksta - kas 0,3 s
skaitomas kintamasis CMDNAMES). Pabaigoje - komandų laikai ir patarimai, kaip nubraižyti greičiau ir tiksliau.
"""

import json
import math
import os
import re
import sys
import threading
import time

from vertimas import tr

try:
    import pythoncom
    import win32com.client
except ImportError:          # ne Windows: tikrinimas ir peržiūra veikia su netikru AutoCAD (testai)
    pythoncom = win32com = None

APLANKAS = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
FAILAS = os.path.join(APLANKAS, "issukiai.json")
with open(FAILAS, encoding="utf-8") as _f:
    _DUOM = json.load(_f)
ISSUKIAI = {i["id"]: i for i in _DUOM["issukiai"]}
TOL = _DUOM["tolerancija"]["padetis"]          # mm - kiek gali skirtis taškai
BEVEIK = _DUOM["tolerancija"]["beveik"]        # mm - „beveik teisingai, tik netiksliai“
MAKS_OBJEKTU = 400
NETIKRINAMI_SLUOKSNIAI = re.compile(r"ASY|ASI[SE]|CENT|PAGALB|DEFPOINTS|MATM|DIM|TEKST|TEXT", re.I)
ISTISINIAI = ("", "BYLAYER", "BYBLOCK", "CONTINUOUS", "ISTISINE")


def sarasas(kalba="lt"):
    """Iššūkiai sąsajai (pasirinkta kalba)."""
    return [{**i, **i.get("en", {})} if kalba == "en" else i for i in _DUOM["issukiai"]]


def issukis(uid):
    if uid not in ISSUKIAI:
        raise ValueError(tr("Nežinomas iššūkis", "Unknown challenge"))
    return ISSUKIAI[uid]


# ================================================================== geometrija
# Primityvai: ("s", p, q) atkarpa, ("a", c, r, a0, a1) lankas prieš laikrodžio rodyklę (radianais), ("c", c, r) apskritimas
def is_json(g):
    if "l" in g:
        x1, y1, x2, y2 = g["l"]
        return ("s", (x1, y1), (x2, y2))
    if "a" in g:
        cx, cy, r, a0, a1 = g["a"]
        return ("a", (cx, cy), r, math.radians(a0), math.radians(a1))
    cx, cy, r = g["c"]
    return ("c", (cx, cy), r)


def _apimtis(e):
    return (e[4] - e[3]) % (2 * math.pi) or 2 * math.pi


def taskai(e, zingsnis=2.0, maks=60):
    if e[0] == "s":
        (x1, y1), (x2, y2) = e[1], e[2]
        n = min(maks, max(2, math.ceil(math.dist(e[1], e[2]) / zingsnis)))
        return [(x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n) for i in range(n + 1)]
    (cx, cy), r = e[1], e[2]
    if e[0] == "a":
        a0, ap = e[3], _apimtis(e)
        n = min(maks, max(3, math.ceil(r * ap / zingsnis)))
        return [(cx + r * math.cos(a0 + ap * i / n), cy + r * math.sin(a0 + ap * i / n)) for i in range(n + 1)]
    n = min(maks, max(8, math.ceil(2 * math.pi * r / zingsnis)))
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def atstumas(p, e):
    if e[0] == "s":
        (x1, y1), (x2, y2) = e[1], e[2]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - x1) * dx + (p[1] - y1) * dy) / L2))
        return math.hypot(p[0] - x1 - t * dx, p[1] - y1 - t * dy)
    c, r = e[1], e[2]
    d = math.dist(p, c)
    if e[0] == "c":
        return abs(d - r)
    kampas = math.atan2(p[1] - c[1], p[0] - c[0])
    if (kampas - e[3]) % (2 * math.pi) <= _apimtis(e) + 1e-9:
        return abs(d - r)
    galai = [(c[0] + r * math.cos(a), c[1] + r * math.sin(a)) for a in (e[3], e[4])]
    return min(math.dist(p, g) for g in galai)


def ribos(elementai):
    xs, ys = [], []
    for e in elementai:
        for x, y in taskai(e, 4.0, 24):
            xs.append(x)
            ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def pastumti(e, dx, dy):
    if e[0] == "s":
        return ("s", (e[1][0] - dx, e[1][1] - dy), (e[2][0] - dx, e[2][1] - dy))
    return (e[0], (e[1][0] - dx, e[1][1] - dy)) + tuple(e[2:])


def _bulge_lankas(p, q, bulge):
    """Polilinijos lanko segmentas -> ("a", c, r, a0, a1)."""
    th = 4 * math.atan(bulge)
    ch = math.dist(p, q)
    if ch == 0:
        return None
    r = abs(ch / (2 * math.sin(th / 2)))
    hh = (ch / 2) / math.tan(th / 2)
    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    nx, ny = -(q[1] - p[1]) / ch, (q[0] - p[0]) / ch
    c = (mx + hh * nx, my + hh * ny)
    ap, aq = math.atan2(p[1] - c[1], p[0] - c[0]), math.atan2(q[1] - c[1], q[0] - c[0])
    return ("a", c, r, ap, aq) if bulge > 0 else ("a", c, r, aq, ap)


def _sluoksnio_tipas(doc, vardas, talpa):
    if vardas not in talpa:
        try:
            talpa[vardas] = str(doc.Layers.Item(vardas).Linetype).upper()
        except Exception:
            talpa[vardas] = ""
    return talpa[vardas]


def nuskaityti(b, kartoti=None):
    """AutoCAD MODEL erdvė -> (primityvai, faktai). faktai - peržiūrai: kiek kokių objektų, tarpai, dubliai."""
    k = kartoti or (lambda f, **_: f())
    ms = b.ms
    try:
        doc = b.doc
    except Exception:
        doc = None
    n = k(lambda: ms.Count)
    prim, tipai, tipu_talpa, galai, atkarpos = [], {}, {}, [], []
    for i in range(min(n, MAKS_OBJEKTU * 2)):
        try:
            o = k(lambda: ms.Item(i))
            t = o.ObjectName
        except Exception:
            continue
        if t not in ("AcDbLine", "AcDbPolyline", "AcDbArc", "AcDbCircle"):
            continue
        sl = str(getattr(o, "Layer", "") or "")
        if NETIKRINAMI_SLUOKSNIAI.search(sl):
            continue
        lt = str(getattr(o, "Linetype", "BYLAYER") or "BYLAYER").upper()
        if lt == "BYLAYER" and doc is not None:
            lt = _sluoksnio_tipas(doc, sl, tipu_talpa)
        if lt not in ISTISINIAI:
            continue
        tipai[t] = tipai.get(t, 0) + 1
        try:
            if t == "AcDbLine":
                p, q = tuple(o.StartPoint)[:2], tuple(o.EndPoint)[:2]
                prim.append(("s", p, q))
                galai += [p, q]
                atkarpos.append((p, q))
            elif t == "AcDbCircle":
                prim.append(("c", tuple(o.Center)[:2], float(o.Radius)))
            elif t == "AcDbArc":
                c, r, a0, a1 = tuple(o.Center)[:2], float(o.Radius), float(o.StartAngle), float(o.EndAngle)
                e = ("a", c, r, a0, a1)
                prim.append(e)
                galai += [(c[0] + r * math.cos(a0), c[1] + r * math.sin(a0)), (c[0] + r * math.cos(a1), c[1] + r * math.sin(a1))]
            else:
                kd = list(o.Coordinates)
                v = list(zip(kd[0::2], kd[1::2]))
                uzd = bool(o.Closed)
                for j in range(len(v) - (0 if uzd else 1)):
                    p, q = v[j], v[(j + 1) % len(v)]
                    try:
                        bl = float(o.GetBulge(j))
                    except Exception:
                        bl = 0.0
                    if abs(bl) < 1e-9:
                        prim.append(("s", p, q))
                        atkarpos.append((p, q))
                    else:
                        lk = _bulge_lankas(p, q, bl)
                        if lk:
                            prim.append(lk)
                if not uzd and v:
                    galai += [v[0], v[-1]]
        except Exception:
            continue
    # galai, kurie beveik susiliečia, bet nesujungti (be OSNAP)
    tarpai = []
    for x in range(len(galai)):
        for y in range(x + 1, len(galai)):
            dd = math.dist(galai[x], galai[y])
            if 1e-4 < dd < 0.5:
                tarpai.append(dd)
    dubliai = sum(1 for x in range(len(atkarpos)) for y in range(x + 1, len(atkarpos))
                  if (math.dist(atkarpos[x][0], atkarpos[y][0]) < 0.01 and math.dist(atkarpos[x][1], atkarpos[y][1]) < 0.01)
                  or (math.dist(atkarpos[x][0], atkarpos[y][1]) < 0.01 and math.dist(atkarpos[x][1], atkarpos[y][0]) < 0.01))
    spinduliai = {}
    for e in prim:
        if e[0] == "c":
            spinduliai[round(e[2], 2)] = spinduliai.get(round(e[2], 2), 0) + 1
    faktai = {"tipai": tipai, "tarpai": len(tarpai), "tarpas_maks": max(tarpai) if tarpai else 0.0,
              "dubliai": dubliai, "apskritimai": spinduliai}
    return prim[:MAKS_OBJEKTU], faktai


def _blogiausias(e, kiti):
    """Didžiausias e taškų atstumas iki artimiausio kito elemento."""
    blog = 0.0
    for p in taskai(e):
        d = min((atstumas(p, k) for k in kiti), default=1e9)
        if d > blog:
            blog = d
            if blog > BEVEIK * 4:
                break
    return blog


def _taskai_pagal(lauk, akt, dx, dy, imtis=None):
    """Kiek laukiamų taškų padengia nubraižyti (pastumti per dx, dy) - greitas sulyginimo įvertinimas."""
    akt2 = [pastumti(e, dx, dy) for e in akt]
    tsk = [p for e in lauk for p in taskai(e, 6.0, 8)]
    if imtis and len(tsk) > imtis:
        tsk = tsk[:: max(1, len(tsk) // imtis)]
    return sum(1 for p in tsk if min((atstumas(p, k) for k in akt2), default=1e9) <= TOL) / max(1, len(tsk))


def sulygiuoti(lauk, akt):
    """Kur nubraižyta detalė: poslinkis (dx, dy), kurį atėmus nubraižyta sutampa su laukiama."""
    rl, ra = ribos(lauk), ribos(akt)
    kandidatai = [(ra[0] - rl[0], ra[1] - rl[1])]
    # pagal apskritimus (to paties spindulio) ir pagal kontūro kampą
    for e in lauk:
        if e[0] == "c":
            for a in akt:
                if a[0] == "c" and abs(a[2] - e[2]) <= 0.1:
                    kandidatai.append((a[1][0] - e[1][0], a[1][1] - e[1][1]))
            break
    kampai = [e[1] for e in lauk if e[0] == "s"] + [e[2] for e in lauk if e[0] == "s"]
    if kampai:
        k0 = min(kampai, key=lambda p: (p[0] + p[1]))
        for a in akt:
            if a[0] == "s":
                for p in (a[1], a[2]):
                    kandidatai.append((p[0] - k0[0], p[1] - k0[1]))
    mat, geriausias, taskas = set(), kandidatai[0], -1.0
    for dx, dy in kandidatai[:400]:
        raktas = (round(dx, 2), round(dy, 2))
        if raktas in mat:
            continue
        mat.add(raktas)
        s = _taskai_pagal(lauk, akt, dx, dy, imtis=40)
        if s > taskas:
            geriausias, taskas = (dx, dy), s
            if s >= 0.999:
                break
    return geriausias


def _aprasas(e):
    if e[0] == "s":
        return tr(f"linija {math.dist(e[1], e[2]):.4g} mm (nuo {e[1][0]:.4g}, {e[1][1]:.4g})",
                  f"line {math.dist(e[1], e[2]):.4g} mm (from {e[1][0]:.4g}, {e[1][1]:.4g})")
    if e[0] == "a":
        return tr(f"lankas R{e[2]:.4g}", f"arc R{e[2]:.4g}")
    return tr(f"apskritimas ⌀{2 * e[2]:.4g} (centras {e[1][0]:.4g}, {e[1][1]:.4g})",
              f"circle ⌀{2 * e[2]:.4g} (centre {e[1][0]:.4g}, {e[1][1]:.4g})")


def palyginti(lauk, akt):
    """Pastabų sąrašas (tuščias - viskas teisingai). Koordinatės - nuo detalės kairio apatinio kampo."""
    if not akt:
        return [tr("Brėžinyje dar nieko nėra - braižyk detalę pagal brėžinį (bet kurioje vietoje).",
                   "The drawing is still empty - draw the part as shown (anywhere you like).")]
    dx, dy = sulygiuoti(lauk, akt)
    akt0 = [pastumti(e, dx, dy) for e in akt]
    pastabos = []
    rl, ra = ribos(lauk), ribos(akt0)
    lw, lh, aw, ah = rl[2] - rl[0], rl[3] - rl[1], ra[2] - ra[0], ra[3] - ra[1]
    if abs(aw - lw) > BEVEIK or abs(ah - lh) > BEVEIK:
        p = tr(f"Detalės dydis {aw:.4g} × {ah:.4g} mm, o turi būti {lw:.4g} × {lh:.4g} mm.",
               f"The part is {aw:.4g} × {ah:.4g} mm but should be {lw:.4g} × {lh:.4g} mm.")
        for kart, kodel in ((2, tr("gal įvedei skersmenį vietoj spindulio ar padvigubinai matmenį?", "did you type a diameter instead of a radius, or double a dimension?")),
                            (10, tr("gal braižei centimetrais?", "did you draw in centimetres?")),
                            (25.4, tr("gal braižei coliais?", "did you draw in inches?"))):
            if lw and any(abs(aw / lw - k) < 0.03 for k in (kart, 1 / kart)):
                p += " " + kodel[0].upper() + kodel[1:]
                break
        pastabos.append(p)
    truksta, beveik = [], []
    for e in lauk:
        d = _blogiausias(e, akt0)
        if d > BEVEIK:
            truksta.append(e)
        elif d > TOL:
            beveik.append(d)
    lieka, lieka_beveik = 0, []
    for e in akt0:
        d = _blogiausias(e, lauk)
        if d > BEVEIK:
            lieka += 1
        elif d > TOL:
            lieka_beveik.append(d)
    for e in truksta[:4]:
        p = tr("Trūksta: ", "Missing: ") + _aprasas(e) + "."
        if e[0] == "c":
            for a in akt0:
                if a[0] == "c" and math.dist(a[1], e[1]) <= BEVEIK and abs(a[2] - 2 * e[2]) <= 0.1:
                    p += tr(f" Radau ⌀{2 * a[2]:.4g} tame pačiame centre - CIRCLE prašo spindulio: įvesk {e[2]:.4g} (arba D ir {2 * e[2]:.4g}).",
                            f" Found ⌀{2 * a[2]:.4g} at the same centre - CIRCLE asks for the radius: type {e[2]:.4g} (or D and {2 * e[2]:.4g}).")
        pastabos.append(p)
    if len(truksta) > 4:
        pastabos.append(tr(f"Ir dar {len(truksta) - 4} trūkstamos dalys.", f"And {len(truksta) - 4} more missing parts."))
    if beveik or lieka_beveik:
        mx = max(beveik + lieka_beveik)
        pastabos.append(tr(f"Beveik! Kai kurios linijos nukrypsta iki {mx:.2g} mm. Įvesk matmenis klaviatūra (@80,0) ir naudok OSNAP (F3) - leidžiama paklaida {TOL:g} mm.",
                           f"Almost! Some lines are off by up to {mx:.2g} mm. Type the dimensions (@80,0) and use OSNAP (F3) - the allowed error is {TOL:g} mm."))
    if lieka:
        pastabos.append(tr(f"Liko nereikalingų objektų ({lieka}) - nukirpk TRIM arba ištrink. Pagalbines linijas perkelk į sluoksnį PAGALBINIS - jų netikrinu.",
                           f"There are unneeded objects left ({lieka}) - TRIM or erase them. Move construction lines to a layer named PAGALBINIS - I don't check it."))
    return pastabos


def tikrinti(uid, b, kartoti=None):
    """-> (pastabos, faktai)"""
    i = issukis(uid)
    akt, faktai = nuskaityti(b, kartoti)
    return palyginti([is_json(g) for g in i["geom"]], akt), faktai


# ================================================================== komandų įrašymas
NEDOMINA = {"", "REGEN", "REDRAW", "QSAVE", "SAVE", "SAVEAS", "NEW", "QNEW", "CLOSE", "OPEN", "GRIP_POPUP", "COMMANDLINE"}


def normalizuoti(vardas):
    v = str(vardas or "").strip().upper().lstrip("_-+'.")
    return v


class Irasas:
    """Vieno iššūkio komandų žurnalas: ivykiai [(t, "b"|"e", KOMANDA)], kintamieji [(t, VARDAS, reiksme)]."""

    def __init__(self):
        self.uzraktas = threading.Lock()
        self.sustoti = threading.Event()
        self.gija = None
        self.isvalyti()

    def isvalyti(self):
        self.uid, self.t0, self.budas, self.klaida = None, time.time(), "nera", ""
        self.ivykiai, self.kintamieji = [], []

    def pradeti(self, uid):
        self.sustabdyti()
        with self.uzraktas:
            self.isvalyti()
            self.uid = uid
        if pythoncom is None:
            return
        self.sustoti = threading.Event()
        self.gija = threading.Thread(target=self._ciklas, args=(self.sustoti,), name="Komandos", daemon=True)
        self.gija.start()

    def ivykis(self, rusis, vardas):
        v = normalizuoti(vardas)
        if v in NEDOMINA:
            return
        with self.uzraktas:
            self.ivykiai.append((round(time.time() - self.t0, 2), rusis, v))

    def kintamasis(self, vardas, reiksme):
        try:
            reiksme = int(reiksme)
        except Exception:
            return
        with self.uzraktas:
            self.kintamieji.append((round(time.time() - self.t0, 2), str(vardas).upper(), reiksme))

    def sustabdyti(self):
        if self.gija and self.gija.is_alive():
            self.sustoti.set()
            self.gija.join(1.5)
        self.gija = None
        with self.uzraktas:
            return {"uid": self.uid, "budas": self.budas, "klaida": self.klaida,
                    "ivykiai": list(self.ivykiai), "kintamieji": list(self.kintamieji)}

    # --- AutoCAD gija: savas COM ryšys ir žinučių ciklas (įvykiams reikia)
    def _ciklas(self, sustoti):
        pythoncom.CoInitialize()
        laikyti = None
        try:
            import branduolys as A
            acad = A.rasti_atidaryta()
            doc = acad.ActiveDocument
            try:
                self.kintamasis("OSMODE", doc.GetVariable("OSMODE"))
            except Exception:
                pass
            try:
                laikyti = win32com.client.WithEvents(doc, DokumentoIvykiai)
                self.budas = "ivykiai"
            except Exception as e:
                self.budas, self.klaida = "apklausa", f"WithEvents: {e}"
            pries, osm_t = [], 0.0
            while not sustoti.is_set() and time.time() - self.t0 < 3600:
                if self.budas == "ivykiai":
                    pythoncom.PumpWaitingMessages()
                    time.sleep(0.05)
                    continue
                try:
                    dab = [normalizuoti(x) for x in str(doc.GetVariable("CMDNAMES")).split("'") if x.strip()]
                    bendra = 0
                    while bendra < min(len(pries), len(dab)) and pries[bendra] == dab[bendra]:
                        bendra += 1
                    for v in reversed(pries[bendra:]):
                        self.ivykis("e", v)
                    for v in dab[bendra:]:
                        self.ivykis("b", v)
                    pries = dab
                    if time.time() - osm_t > 1.0:
                        osm_t = time.time()
                        v = int(doc.GetVariable("OSMODE"))
                        if not self.kintamieji or self.kintamieji[-1][2] != v:
                            self.kintamasis("OSMODE", v)
                except Exception:
                    pass            # AutoCAD užimtas - kitą kartą
                time.sleep(0.3)
        except Exception as e:
            self.budas, self.klaida = "nera", str(e)
        finally:
            laikyti = None
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


IRASAS = Irasas()


class DokumentoIvykiai:
    """AutoCAD dokumento įvykiai (win32com.client.WithEvents)."""

    def OnBeginCommand(self, CommandName):
        IRASAS.ivykis("b", CommandName)

    def OnEndCommand(self, CommandName):
        IRASAS.ivykis("e", CommandName)

    def OnSysVarChanged(self, SysvarName, newVal):
        if str(SysvarName).upper() in ("OSMODE", "ORTHOMODE", "AUTOSNAP"):
            IRASAS.kintamasis(SysvarName, newVal)


# ================================================================== peržiūra
PIESIMO = {"LINE", "CIRCLE", "ARC", "PLINE", "RECTANG", "MOVE", "COPY", "OFFSET", "FILLET", "CHAMFER", "MIRROR", "ROTATE",
           "ARRAYPOLAR", "ARRAYRECT", "XLINE", "POLYGON"}


def seka(ivykiai):
    """Įvykiai -> [{k, t, tr}] (pradžia ir trukmė s). Neužbaigtos komandos baigiamos kitos pradžioje."""
    rez, stekas = [], []
    for t, rusis, v in ivykiai:
        if rusis == "b":
            if stekas and v not in ("ZOOM", "PAN") and stekas[-1][0] not in ("ZOOM", "PAN"):
                k, t0 = stekas.pop()            # nauja (ne permatoma) komanda - ankstesnė baigėsi
                rez.append({"k": k, "t": t0, "tr": round(t - t0, 2)})
            stekas.append((v, t))
        else:
            for i in range(len(stekas) - 1, -1, -1):
                if stekas[i][0] == v:
                    k, t0 = stekas.pop(i)
                    rez.append({"k": k, "t": t0, "tr": round(t - t0, 2)})
                    break
    for k, t0 in stekas:
        rez.append({"k": k, "t": t0, "tr": 0.0})
    return sorted(rez, key=lambda x: x["t"])


def _osnap_isjungtas(irasas, sk):
    """Ar braižymo komandos vyko išjungus OSNAP (OSMODE bitas 16384 arba be jokio režimo)."""
    kin = [(t, v) for t, n, v in irasas.get("kintamieji", []) if n == "OSMODE"]
    if not kin:
        return False

    def busena(t):
        v = kin[0][1]
        for tt, vv in kin:
            if tt <= t:
                v = vv
        return bool(v & 16384) or not (v & 16383)
    return any(busena(s["t"] + s["tr"] / 2) for s in sk if s["k"] in PIESIMO and s["k"] not in ("MOVE",))


def _laikas(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def perziura(uid, irasas, faktai, sekundes):
    i = issukis(uid)
    sk = seka(irasas.get("ivykiai", []))
    yra_zurnalas = bool(sk)
    kiek, laikai = {}, {}
    for s in sk:
        kiek[s["k"]] = kiek.get(s["k"], 0) + 1
        laikai[s["k"]] = round(laikai.get(s["k"], 0) + s["tr"], 1)
    K = lambda v: kiek.get(v, 0)
    tipai = faktai.get("tipai", {})
    tikslas = i["tikslas"]
    zv = 3 if sekundes <= tikslas else 2 if sekundes <= tikslas * 1.5 else 1
    pat, flag = [], set(i.get("patarimai", []))

    def p(tipas, lt, en):
        pat.append({"tipas": tipas, "tekstas": tr(lt, en)})

    linijos = max(K("LINE"), tipai.get("AcDbLine", 0))
    if "rectang" in flag and linijos >= 4 and K("RECTANG") == 0:
        p("rectang", f"Stačiakampį braižei linijomis ({linijos} × LINE). RECTANG (REC) nubraižo jį per du spustelėjimus: kampas → @plotis,aukštis.",
          f"You drew the rectangle with lines ({linijos} × LINE). RECTANG (REC) does it in two clicks: corner → @width,height.")
    if "pline" in flag and tipai.get("AcDbLine", 0) >= 6 and tipai.get("AcDbPolyline", 0) == 0:
        p("pline", "Kontūrą sudėjai iš atskirų linijų. PLINE (C - uždaryti) nubraižo jį vienu objektu - tada OFFSET ir AREA veikia iškart.",
          "You built the outline from separate lines. PLINE (C to close) draws it as one object - then OFFSET and AREA work straight away.")
    vienodu = max((v for v in faktai.get("apskritimai", {}).values()), default=0)
    if "copy" in flag and yra_zurnalas and vienodu >= 2 and K("CIRCLE") >= vienodu and not (K("COPY") or K("ARRAYPOLAR") or K("ARRAYRECT") or K("ARRAY") or K("MIRROR")):
        p("copy", f"{vienodu} vienodus apskritimus braižei po vieną. Nubraižyk vieną ir COPY (CO); ratu - ARRAYPOLAR, eilėmis - ARRAYRECT.",
          f"You drew {vienodu} identical circles one by one. Draw one and COPY (CO) it; in a ring - ARRAYPOLAR, in rows - ARRAYRECT.")
    if "pcd" in flag and yra_zurnalas and K("ARRAYPOLAR") == 0 and K("ARRAY") == 0:
        p("pcd", "Skylės ant apskritimo - darbas ARRAYPOLAR: pasirink skylę → centras → 4 vnt. Koordinačių skaičiuoti nereikia.",
          "Holes on a circle are a job for ARRAYPOLAR: pick the hole → centre → 4 items. No coordinates to calculate.")
    if "fillet" in flag and yra_zurnalas and K("FILLET") == 0 and (K("ARC") or tipai.get("AcDbArc", 0)):
        p("fillet", "Užapvalinimus braižei lankais. FILLET (F → R 10 → dvi kraštinės) padaro kampą akimirksniu, o RECTANG su parinktimi Fillet - visus 4 iškart.",
          "You drew the rounds as arcs. FILLET (F → R 10 → two edges) makes a corner instantly, and RECTANG with the Fillet option does all 4 at once.")
    if "griovelis" in flag and (K("ARC") >= 2 or tipai.get("AcDbArc", 0) >= 2) and K("TRIM") == 0 and sekundes > tikslas:
        p("griovelis", "Griovelis greičiau: 2 apskritimai R6 + 2 liestinės linijos (OSNAP Quadrant) → TRIM vidines puses.",
          "A faster slot: 2 circles R6 + 2 tangent lines (OSNAP Quadrant) → TRIM the inner halves.")
    if "tan" in flag and sekundes > tikslas:
        p("tan", "Liestinę tarp dviejų apskritimų brėžk LINE su Tangent: Shift + dešinys pelės mygtukas → Tangent ant abiejų apskritimų, tada TRIM.",
          "Draw the tangent between two circles with LINE and Tangent: Shift + right-click → Tangent on both circles, then TRIM.")
    if "mirror" in flag and yra_zurnalas and K("MIRROR") == 0 and sekundes > tikslas:
        p("mirror", "Detalė simetriška - nubraižyk pusę ir MIRROR (MI) per vidurio liniją.",
          "The part is symmetrical - draw one half and MIRROR (MI) it about the centre line.")
    if _osnap_isjungtas(irasas, sk):
        p("osnap", "OSNAP buvo išjungtas (F3), kai braižei - taškus gaudei akimis. Įjunk F3: Endpoint, Center, Tangent.",
          "OSNAP was off (F3) while you drew - you were aiming by eye. Turn on F3: Endpoint, Center, Tangent.")
    if faktai.get("tarpai"):
        p("tarpai", f"{faktai['tarpai']} galai beveik susiliečia, bet nesujungti (tarpas iki {faktai['tarpas_maks']:.2f} mm). Su OSNAP Endpoint taip nenutinka.",
          f"{faktai['tarpai']} ends nearly touch but are not joined (gap up to {faktai['tarpas_maks']:.2f} mm). OSNAP Endpoint prevents this.")
    if faktai.get("dubliai"):
        p("dubliai", f"{faktai['dubliai']} linijos nubrėžtos du kartus viena ant kitos. OVERKILL jas išvalo.",
          f"{faktai['dubliai']} lines are drawn twice on top of each other. OVERKILL cleans them up.")
    taisymai = K("U") + K("UNDO") + K("ERASE")
    if taisymai >= 4:
        p("taisymai", f"Daug taisymų: UNDO × {K('U') + K('UNDO')}, ERASE × {K('ERASE')}. Prieš braižydamas pažiūrėk į matmenis ir nuspręsk, nuo kurio taško pradėsi.",
          f"Lots of corrections: UNDO × {K('U') + K('UNDO')}, ERASE × {K('ERASE')}. Look at the dimensions first and decide where to start.")
    if K("ZOOM") + K("PAN") >= 8:
        p("zoom", f"ZOOM/PAN × {K('ZOOM') + K('PAN')}. Suk pelės ratuką (artinti), laikyk jį nuspaustą (stumti), du kartus spustelk ratuką - visa detalė ekrane.",
          f"ZOOM/PAN × {K('ZOOM') + K('PAN')}. Roll the mouse wheel (zoom), hold it down (pan), double-click it - the whole part on screen.")
    ilgiausia = max(((k, t) for k, t in laikai.items() if k not in ("ZOOM", "PAN")), key=lambda x: x[1], default=None)
    if ilgiausia and sekundes and ilgiausia[1] >= 20 and ilgiausia[1] >= sekundes * 0.3:
        p("ilgiausia", f"Ilgiausiai užtruko {ilgiausia[0]} - {_laikas(ilgiausia[1])} iš {_laikas(sekundes)}.",
          f"{ilgiausia[0]} took the longest - {_laikas(ilgiausia[1])} of {_laikas(sekundes)}.")
    pastaba = ""
    if not yra_zurnalas:
        pastaba = tr("Komandų sąrašo šį kartą nesurinkau - patarimai tik pagal brėžinį.",
                     "I couldn't collect the command list this time - tips are based on the drawing only.")
    if not pat:
        p("svaru", "Švarus darbas - patarimų neturiu. Pabandyk pagerinti laiką!",
          "Clean work - no tips from me. Try to beat your time!")
    komandos = sorted(({"k": k, "kiek": kiek[k], "laikas": laikai[k]} for k in kiek), key=lambda x: -x["laikas"])
    return {"laikas": round(sekundes, 1), "tikslas": tikslas, "zvaigzdes": zv, "komandos": komandos[:12],
            "seka": sk[:80], "patarimai": pat[:6], "budas": irasas.get("budas", "nera"), "pastaba": pastaba}


def pavyzdinis_irasas(uid):
    """Imitacijai (kūrėjo režimas be AutoCAD): tipiškas pradedančiojo įrašas."""
    ev, t = [], 1.0

    def kom(k, tr_, tarpas=1.5):
        nonlocal t
        ev.append((round(t, 2), "b", k))
        t += tr_
        ev.append((round(t, 2), "e", k))
        t += tarpas
    for k, d in (("LINE", 34), ("ZOOM", 2), ("LINE", 12), ("ERASE", 4), ("LINE", 18), ("CIRCLE", 16), ("U", 1),
                 ("CIRCLE", 9), ("CIRCLE", 11), ("ZOOM", 2), ("PAN", 3), ("TRIM", 22)):
        kom(k, d)
    return {"uid": uid, "budas": "imitacija", "klaida": "", "ivykiai": ev, "kintamieji": [(0.0, "OSMODE", 16384 + 4133)]}

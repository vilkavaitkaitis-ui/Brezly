"""
Brėžly Pilotas - programa su grafine sąsaja.

Paleidžia mažą vietinį serverį (tik šiame kompiuteryje) ir atidaro sąsają atskirame
programos lange (Microsoft Edge "app" režimu, be naršyklės juostų).
Uždarius langą, programa po kelių sekundžių išsijungia pati.

Paleidimas: PROGRAMA.bat arba nuoroda "Brėžly Pilotas" (po IDIEGTI.bat).
"""

import contextlib
import glob
import io
import os
import traceback

import serveris as S            # bendras serveris, langas ir AutoCAD ryšys (kartu su Brėžly)
import branduolys as A          # noqa: E402
import kalba                    # noqa: E402
import meniu as M               # noqa: E402

S.BUSENA["darbas"] = M.Darbas()     # Pilotui ryšio laikiklis su braižymo veiksmais
BUSENA = S.BUSENA
braizytojas, prisijungti, busena, ping = S.braizytojas, S.prisijungti, S.busena, S.ping
TIPO_PAVADINIMAI = {"3D": "Detalė", "2D": "Detalės brėžinys", "SCHEMA": "Elektrinė principinė schema"}


# ------------------------------------------------------------------ pagalbinės
def mano_failai():
    zinomi = {f for sar in M.PARUOSTOS.values() for f, _ in sar} | M.NE_DETALES
    return sorted(f for f in glob.glob("*.txt") if f not in zinomi)


def info():
    return {
        "versija": A.VERSIJA.split()[0], "langas": dict(S.LANGAS),
        "formatai": [{"id": k, "w": w, "h": h} for k, (w, h, _) in A.FORMATAI.items()],
        "tipai": [{"id": i, "pav": p.split(" (")[0], "aprasas": p.split(" (")[1].rstrip(")") if " (" in p else ""}
                  for i, p in M.TIPAI],
        "sablonai": [{"id": i, "pav": p} for i, p in A.SABLONAI],
        "issaugojimas": [{"id": k, "ext": v[0], "pav": v[2]} for k, v in A.ISSAUGOJIMO_FORMATAI.items()],
        "paruostos": {t: [{"failas": f, "pav": p} for f, p in sar] for t, sar in M.PARUOSTOS.items()},
        "mano": mano_failai(),
        "ai": A.gauti_rakta() is not None,
        "pavyzdziai": {"3D": kalba.PAVYZDZIAI_BREZINYS, "2D": kalba.PAVYZDZIAI_2D,
                       "SCHEMA": kalba.PAVYZDZIAI_SCHEMA},
    }


def saugus_failas(vardas):
    """Leidžia skaityti tik .txt failus iš programos aplanko."""
    vardas = os.path.basename(vardas or "")
    if not vardas.lower().endswith(".txt") or not os.path.exists(vardas):
        raise ValueError("Tokio failo nėra.")
    return vardas


# ------------------------------------------------------------------ veiksmai
class Ribos:
    """Sekame detalės ribas peržiūrai - kad skylių gylis ir kampų suapvalinimas būtų kaip braižant."""
    def __init__(self):
        self.r = None

    def virsus(self):
        return self.r[1][2] if self.r else None

    def ribos(self):
        return self.r

    def prideti(self, komanda):
        dalys = komanda.split()
        cmd = dalys[0].lower()
        if cmd == "naujas":
            self.r = None
            return
        if cmd.startswith("-"):
            return
        try:
            v = [float(x) for x in dalys[1:7] if x.lower() not in ("+x", "-x")]
        except ValueError:
            return
        if cmd in ("deze", "pleistas") and len(v) >= 6:
            d = ((v[0], v[1], v[2]), (v[0] + v[3], v[1] + v[4], v[2] + v[5]))
        elif cmd == "cilindras" and len(v) >= 5:
            d = ((v[0] - v[3], v[1] - v[3], v[2]), (v[0] + v[3], v[1] + v[3], v[2] + v[4]))
        elif cmd == "cilindrasy" and len(v) >= 5:
            d = ((v[0] - v[3], v[1], v[2] - v[3]), (v[0] + v[3], v[1] + v[4], v[2] + v[3]))
        elif cmd == "sesiakampis" and len(v) >= 5:
            rr = v[3] / 3 ** 0.5
            d = ((v[0] - rr, v[1] - rr, v[2]), (v[0] + rr, v[1] + rr, v[2] + v[4]))
        else:
            return
        if self.r is None:
            self.r = d
        else:
            self.r = (tuple(map(min, self.r[0], d[0])), tuple(map(max, self.r[1], d[1])))


def perziura(duom):
    rb = Ribos()
    k = kalba.Kalba(A.KOMANDOS.keys(), virsus=rb.virsus, ribos=rb.ribos)
    kom, nes = [], []
    for sakinys in kalba.skaidyti_sakinius(duom.get("tekstas", "")):
        try:
            rez = k.sakinys(sakinys)
        except Exception:
            rez = None
        if not rez:
            nes.append(sakinys)
            continue
        for c in rez:
            kom.append(c)
            rb.prideti(c)
    return {"ok": True, "komandos": kom, "nesuprasta": nes}


def failo_turinys(duom):
    vardas = saugus_failas(duom.get("vardas"))
    with open(vardas, encoding="utf-8") as f:
        return {"ok": True, "tekstas": f.read()}


def vykdyti(duom):
    d = BUSENA["darbas"]
    buf = io.StringIO()
    klaidos_pries = 0
    with contextlib.redirect_stdout(buf):
        b = braizytojas()
        tipas = duom.get("tipas", "3D")
        fmt = duom.get("fmt") or None
        saltinis = duom.get("saltinis", {})
        if duom.get("sablonas"):
            A.naujas_brezinys(b.acad, duom["sablonas"])
            b.palaukti()
        b.kunas = None
        b.remelio_vieta = None
        if duom.get("sriftai"):
            b.vykdyti_saugiai("sriftai")
        b.vykdyti_saugiai("sluoksniai")
        if tipas == "3D":
            b.vykdyti_saugiai("naujas")
        nuo = A.kartoti(lambda: b.ms.Count)
        pavadinimas = TIPO_PAVADINIMAI.get(tipas, "Brėžinys")

        budas = saltinis.get("budas")
        if budas == "paruosta":
            vardas = saugus_failas(saltinis.get("failas"))
            with open(vardas, encoding="utf-8") as f:
                klaidos_pries = d.vykdyti_eilutes(f.readlines())
            pavadinimas = dict((x, y) for sar in M.PARUOSTOS.values() for x, y in sar).get(vardas, pavadinimas)
        elif budas == "tekstas":
            klaidos_pries = d.vykdyti_eilutes(saltinis.get("tekstas", "").splitlines())
        elif budas == "ai":
            turinys_tekstas = M.AI_TIPO_TEKSTAS[tipas]
            if saltinis.get("tekstas"):
                turinys_tekstas += " Užduotis: " + saltinis["tekstas"]
            pav = saltinis.get("paveikslas")
            if pav:
                turinys = [{"type": "image", "source": {"type": "base64", "media_type": pav["media"],
                                                         "data": pav["data"]}},
                           {"type": "text", "text": turinys_tekstas}]
            else:
                turinys = turinys_tekstas
            print("Klausiu AI, palauk...")
            atsakymas = A.paklausti_ai(turinys)
            klaidos_pries = d.vykdyti_eilutes(atsakymas.splitlines(), "ai")
        else:
            raise ValueError("Nepasirinktas turinys.")

        kampinis = {k: v for k, v in (duom.get("kampinis") or {}).items() if v}
        if kampinis.get("PAVADINIMAS"):
            pavadinimas = kampinis["PAVADINIMAS"]
        d.iforminti(tipas, fmt, nuo, pavadinimas, kampinis=kampinis,
                    ketvirtine=bool(duom.get("ketvirtine")))
    return {"ok": True, "log": buf.getvalue(), "klaidos": klaidos_pries,
            "vardas": M.failo_vardas(pavadinimas)}


def issaugoti(duom):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        b = braizytojas()
        vardas = duom.get("vardas") or "brezinys"
        if not os.path.isabs(vardas) and not os.path.dirname(vardas):
            vardas = os.path.join("brezinai", vardas)
        kelias = b.issaugoti(vardas, duom.get("formatas", "dwg"))
    return {"ok": True, "log": buf.getvalue(), "kelias": kelias}


def komanda(duom):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        b = braizytojas()
        tekstas = duom.get("tekstas", "").strip()
        if tekstas == "isvalyti":
            b.patvirtinti = lambda klausimas: True       # sąsaja jau paklausė
        b.vykdyti_zodziais(tekstas)
    return {"ok": True, "log": buf.getvalue()}


def atidaryti_aplanka(_):
    os.makedirs("brezinai", exist_ok=True)
    if os.name == "nt":
        os.startfile(os.path.abspath("brezinai"))
    return {"ok": True}


VEIKSMAI = {"/api/info": lambda _: info(), "/api/prisijungti": prisijungti, "/api/busena": busena, "/api/perziura": perziura,
            "/api/failas": failo_turinys, "/api/vykdyti": vykdyti, "/api/issaugoti": issaugoti,
            "/api/komanda": komanda, "/api/aplankas": atidaryti_aplanka, "/api/ping": ping}


# ------------------------------------------------------------------ serveris
class Tvarkykle(S.Tvarkykle):
    HTML = "ui.html"
    IKONA = "robotas.ico"
    VEIKSMAI = VEIKSMAI


def main():
    S.main(Tvarkykle, 8731)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open("klaida.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise

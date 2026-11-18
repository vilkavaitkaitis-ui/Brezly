# Brėžly 📐

**Tavo braižymo mokymosi draugas.** Tu braižai AutoCAD'e, o Brėžly veda žingsnis po žingsnio, tikrina brėžinį ir padeda.

## ⬇ Atsisiųsti

**[Atsisiuntimo puslapis](https://vilkavaitkaitis-ui.github.io/Brezly/)** · **[Programėlė naršyklėje](https://vilkavaitkaitis-ui.github.io/Brezly/programele/)** (veikia ir kai Windows blokuoja .exe)

**[Brezly_Setup.exe – naujausia versija](../../releases/latest/download/Brezly_Setup.exe)**

1. Atsisiųsk ir paleisk `Brezly_Setup.exe` (administratoriaus teisių nereikia).
2. Jei Windows parodo „Windows apsaugojo jūsų kompiuterį“ – spausk **Daugiau informacijos → Vis tiek paleisti**.
3. Atsidaryk AutoCAD (pilną, ne LT) ir Brėžly.

Naujos versijos įsidiegia pačios – Brėžly pasiūlys atnaujinti.

## Kas viduje

- 7 pamokos (38 žingsniai) – nuo failo iki pirmosios 3D detalės
- 8 praktikos užduotys: 2D A4 ir 3D A3 lapuose, su automatiniu tikrinimu
- XP, lygiai, ženkleliai ir 8 personažai

Reikia: Windows 10/11 ir AutoCAD (pilna versija). Progresas saugomas `Dokumentai\Brezly`.

---
Brėžly – nepriklausoma programa, nesusijusi su Autodesk, Inc. AutoCAD® yra Autodesk, Inc. prekės ženklas.

## Jei Windows blokuoja .exe (Smart App Control)

Naudok **AutoCAD priedą** – jo Windows neblokuoja, nes jį paleidžia pats AutoCAD:

**[Brezly.lsp – AutoCAD priedas](../../releases/latest/download/Brezly.lsp)**

1. Atsisiųsk `Brezly.lsp` ir nutempk jį į atidarytą AutoCAD langą → **Load Once** (arba **Always Load**).
2. Įrašyk komandą `BREZLY`.
3. Kad kraustųsi kiekvieną kartą: `APPLOAD` → **Startup Suite** → **Contents…** → **Add** → `Brezly.lsp`.

Komandos: `BREZLY` (praktikos langas), `BRLAPAS` (lapo rėmelis), `TIKRINK` (patikrinti).

**Jei naršyklė neleidžia atsisiųsti `.lsp`:** atsisiųsk [Brezly.txt](../../releases/latest/download/Brezly.txt)
ir AutoCAD komandų eilutėje įrašyk `(load (getfiled "Brezly" "" "txt" 0))` → pasirink atsisiųstą failą.

## Kūrėjams

| Kas | Kur |
|---|---|
| Programa (Windows) | `brezly.py` – veiksmai, `serveris.py` – vietinis serveris, langas, ryšys su AutoCAD (bendras su Pilotu) |
| Sąsaja | `brezly.html` + `brezly.css` + `brezly.js` |
| Pamokų tekstai | `pamokos.json` (naudoja ir programa, ir programėlė) |
| Pamokų tikrinimas AutoCAD'e | `pamokos.py` – žodynas `TIKRINIMAS`: žingsnio id → (tikrinti, parodyti) |
| Praktikos užduotys ir taisyklės | `praktika/uzduotys.json` (naudoja programa, programėlė ir AutoCAD priedas) |
| Atsisiuntimo puslapis | `svetaine/index.html` → https://vilkavaitkaitis-ui.github.io/Brezly/ |
| Programėlė (PWA) | `app/` → `/Brezly/programele/`; abu skelbiami automatiškai į `gh-pages` |
| AutoCAD priedas | `lisp/Brezly.lsp` – užduočių blokas generuojamas |
| Brėžly Pilotas (sena programa) | `programa.py`, `ui.html`, `meniu.py`, `kalba.py`, `langas.py` |

**Pakeitei pamoką ar užduotį?** Redaguok `pamokos.json` arba `praktika/uzduotys.json`, tada:

```
python irankiai/generuoti.py                 # atnaujina lisp/Brezly.lsp ir sukuria isvestis/svetaine
python -m unittest discover -s testai -v     # testai (AutoCAD nereikia; veikia ir ne Windows)
```

Svetainę ir programėlę galima išbandyti: `python -m http.server -d isvestis/svetaine 8000` → http://localhost:8000 (programėlė – `/programele/`).
Sąsają be AutoCAD: `python brezly.py` (ne Windows – be AutoCAD ryšio, bet visi langai veikia).

**Išleidimas.** Actions → „Brėžly diegimo programa“ → Run workflow su versija (pvz. `1.0`):
testai → `Brezly_Setup.exe`, `Brezly_programa.zip`, `Brezly.lsp` → Release, įdiegtos programos pasiūlo atnaujinti.
Svetainė ir programėlė pasiskelbia pačios („Brėžly programėlė“), kai `main` šakoje pasikeičia `svetaine/`, `app/`, `pamokos.json` ar `praktika/`.
Į surinkimą įtraukiami failai išvardyti vienoje vietoje – `irankiai/surinkti.py`.

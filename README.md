# Brėžly 📐

**Tavo braižymo mokymosi draugas.** Tu braižai AutoCAD'e, o Brėžly veda žingsnis po žingsnio, tikrina brėžinį ir padeda.

## ⬇ Atsisiųsti

**[Brėžly programėlė – atidaryk ir spausk „Įdiegti“](https://vilkavaitkaitis-ui.github.io/Brezly/)** (veikia ir kai Windows blokuoja .exe)

**[Brezly_Setup.exe – naujausia versija](../../releases/latest/download/Brezly_Setup.exe)**

1. Atsisiųsk ir paleisk `Brezly_Setup.exe` (administratoriaus teisių nereikia).
2. Jei Windows parodo „Windows apsaugojo jūsų kompiuterį“ – spausk **Daugiau informacijos → Vis tiek paleisti**.
3. Atsidaryk AutoCAD (pilną, ne LT) ir Brėžly.

Naujos versijos įsidiegia pačios – Brėžly pasiūlys atnaujinti.

## Kas viduje

- 15 pamokų (81 žingsnis) – nuo kampinio įrašo ir tikslaus braižymo (OSNAP, sekimas), redagavimo (TRIM, OFFSET, MIRROR, masyvai) ir 2D pjūvio iki 3D detalės, projekcijų, pjūvių ir A3 lapo
- 8 praktikos užduotys: 2D A4 ir 3D A3 lapuose, su automatiniu tikrinimu
- Egzamino režimas su laikmačiu, „Mano silpnos vietos“, komandų eilutės treniruoklis
- Žinynas: inžinerinės grafikos terminai LT–EN ir standartų atmintinė; 2D žingsniuose – paveikslėlis „taip turi atrodyti“
- XP, lygiai, ženkleliai ir 8 personažai
- Dizainas „Brėžinys yra sąsaja“: pamokos žingsniai – pozicijos brėžinio lape, šviesi ir tamsi tema

Reikia: Windows 10/11 ir AutoCAD (pilna versija). Progresas saugomas `Dokumentai\Brezly`.

Privatumas: Brėžly apie tave nieko nesiunčia – [privatumo politika](PRIVATUMAS.md). Licencija: [MIT](LICENSE)
(šriftai IBM Plex, Archivo ir Space Mono – [SIL OFL](sriftai/OFL.txt), [Archivo](sriftai/OFL-Archivo.txt), [Space Mono](sriftai/OFL-SpaceMono.txt)).

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
| Pamokų tekstai | `pamokos.json` (naudoja ir programa, ir programėlė); anglų kalba - `pamokos_en.json` |
| Pamokų tikrinimas AutoCAD'e | `pamokos.py` – žodynas `TIKRINIMAS`: žingsnio id → (tikrinti, parodyti) |
| Praktikos užduotys ir taisyklės | `praktika/uzduotys.json` (naudoja programa, programėlė ir AutoCAD priedas; anglų tekstai - laukas `en`) |
| Kalba | `vertimas.py` - `tr("lietuviškai", "English")` tikrinimo pastaboms; `sasaja_en.json` - sąsajos žodynas |
| Versija ir „Kas naujo“ | `naujienos.json` - naujausia viršuje; iš jos ir AutoCAD priedo versija, ir Release aprašas |
| Pavyzdiniai DXF | `irankiai/pavyzdziai.py` (reikia `pip install ezdxf`) |
| Programėlė (PWA) | `app/` – šaltinis; skelbiama automatiškai į `gh-pages` |
| Žinynas ir komandų treniruoklis | `zinynas.json` + `mokymas.js` (bendri programai ir programėlei) |
| Tikslo paveikslėliai | `paveiksleliai/` – generuoja `python irankiai/paveiksleliai.py` iš „Parodyk man“ demonstracijų |
| AutoCAD priedas | `lisp/Brezly.lsp` – užduočių blokas generuojamas |
| Brėžly Pilotas (sena programa) | `programa.py`, `ui.html`, `meniu.py`, `kalba.py`, `langas.py` |

**Pakeitei pamoką ar užduotį?** Redaguok `pamokos.json` arba `praktika/uzduotys.json`, tada:

```
python irankiai/paveiksleliai.py             # tikslo paveikslėliai (jei keitei 2D žingsnius)
python irankiai/generuoti.py                 # atnaujina lisp/Brezly.lsp ir sukuria isvestis/programele
python -m unittest discover -s testai -v     # testai (AutoCAD nereikia; veikia ir ne Windows)
```

Programėlę galima išbandyti: `python -m http.server -d isvestis/programele 8000` → http://localhost:8000.
Sąsają be AutoCAD: `python brezly.py` (ne Windows – be AutoCAD ryšio, bet visi langai veikia).

**Prieš išleidžiant** - `PATIKRA.md` (15 min. su AutoCAD).

**Išleidimas.** Actions → „Brėžly diegimo programa“ → Run workflow su versija (pvz. `1.0`):
testai → `Brezly_Setup.exe`, `Brezly_programa.zip`, `Brezly.lsp` → Release, įdiegtos programos pasiūlo atnaujinti.
Programėlė į https://vilkavaitkaitis-ui.github.io/Brezly/ pasiskelbia pati („Brėžly programėlė“), kai `main` šakoje pasikeičia `app/`, `pamokos.json`, `praktika/`, `mokymas.js`, `zinynas.json` ar `paveiksleliai/`.
Į surinkimą įtraukiami failai išvardyti vienoje vietoje – `irankiai/surinkti.py`.

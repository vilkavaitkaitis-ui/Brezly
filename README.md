# Brėžly 📐

**Tavo braižymo mokymosi draugas.** Tu braižai AutoCAD'e, o Brėžly veda žingsnis po žingsnio, tikrina brėžinį ir padeda.

## ⬇ Atsisiųsti

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

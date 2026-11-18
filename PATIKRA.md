# Patikra prieš išleidžiant naują versiją

Automatiniai testai (`python -m unittest discover -s testai`) tikrina viską, ką galima be AutoCAD.
Šį sąrašą reikia praeiti **rankomis, Windows kompiuteryje su pilnu AutoCAD** - apie 15 minučių.

## 1. Diegimas ir paleidimas
- [ ] `Brezly_Setup.exe` (iš Actions artefakto) įsidiegia be administratoriaus teisių, Brėžly pasileidžia atskirame lange.
- [ ] Senesnė versija pasiūlo atnaujinti, atnaujina ir persikrauna; progresas (XP, pamokos) išlieka.
- [ ] Pirmą kartą po atnaujinimo parodomas „Kas naujo“ langas (iš `naujienos.json`).

## 2. Ryšys su AutoCAD
- [ ] Atidarius AutoCAD būsena tampa žalia („AutoCAD · Drawing1.dwg“).
- [ ] AutoCAD tik su pradžios (Start) langu, be brėžinio → oranžinė „AutoCAD · nėra brėžinio“; „Naujas“ sukuria brėžinį iš acadiso.dwt.
- [ ] AutoCAD'e atidarytas langas (pvz. OPTIONS) → „AutoCAD užimtas (Esc)“, uždarius - vėl žalia, ryšys nenutrūksta.
- [ ] AutoCAD paleistas „Run as administrator“ → „Kitos teisės (admin)“, „Kodėl?“ paaiškina; `brezly.log` yra eilutė „AutoCAD ryšys: teises_acad“.
- [ ] Uždarius ir vėl atidarius AutoCAD - ryšys atsistato pats.
- [ ] Jei įdiegtos dvi AutoCAD versijos - prisijungia prie tos, kuri atidaryta (ne tik naujausios).

## 3. Pamokos (po vieną žingsnį iš kelių pamokų)
- [ ] 1 pamoka: naujas brėžinys iš acadiso.dwt → „Patikrinti“ priima.
- [ ] 3 pamoka: „Parodyk man“ nubraižo plokštę; automatinis tikrinimas pastebi atliktą žingsnį.
- [ ] 7 pamoka: BOX žingsnis - specialiai suklysk (z = 10) ir pažiūrėk, ar paaiškinimas aiškus.
- [ ] 8 pamoka: ketvirtinė išpjova (BOX + SUBTRACT) priimama; VIEWBASE ir VIEWSECTION žingsniai priimami
      (**pirmas kartas su tikru AutoCAD** - jei ne, `Pranešti apie klaidą` ir pažiūrėk `brezly.log`).
- [ ] 9 pamoka: 1, 3 ir 4 vaizdai A3 lape atpažįstami.
- [ ] 10 pamoka: visi 4 žingsniai su „Parodyk man“ ir tikrinimu.

## 4. Praktika
- [ ] U1: „Pradėti“ atidaro tuščią A4 lapą; nubraižius - priimama.
- [ ] U4, U6, U7: „Pavyzdys AutoCAD'e“ atsidaro; pavyzdžio failą išsaugojus kitu vardu ir patikrinus - priimamas.

## 5. Kalba
- [ ] Nustatymai › Kalba / Language → English: pamokos, mygtukai ir tikrinimo pastabos angliškai.
- [ ] Atgal į Lietuvių - viskas lietuviškai.

## 6. Progresas ir ataskaitos
- [ ] Eksportuoti → failas `Dokumentai\Brezly\perkelimas`; kitame kompiuteryje Importuoti → XP perkeltas.
- [ ] 🎓 Ataskaita dėstytojui atsidaro naršyklėje, Ctrl+P → PDF atrodo tvarkingai.
- [ ] Pranešti apie klaidą → ZIP su `brezly.log`.

## 7. AutoCAD priedas
- [ ] `Brezly.lsp` nutempus į AutoCAD: `BREZLY` rodo 8 užduotis, versija sutampa su programos.

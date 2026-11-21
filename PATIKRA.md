# Patikra prieš išleidžiant naują versiją

Automatiniai testai (`python -m unittest discover -s testai`) tikrina viską, ką galima be AutoCAD.
Šį sąrašą reikia praeiti **rankomis, Windows kompiuteryje su pilnu AutoCAD** - apie 15 minučių.

## 1. Diegimas ir paleidimas
- [ ] `Brezly_Setup.exe` (iš Actions artefakto) įsidiegia be administratoriaus teisių, Brėžly pasileidžia atskirame lange.
- [ ] Senesnė versija pasiūlo atnaujinti, atnaujina ir persikrauna; progresas (XP, pamokos) išlieka.
- [ ] Pirmą kartą po atnaujinimo parodomas „Kas naujo“ langas (iš `naujienos.json`).

## 2. Ryšys su AutoCAD
- [ ] **Greitis:** AutoCAD'e atidaryk OPTIONS langą ir Brėžly'je vaikščiok po pamokas, nustatymus - viskas atsidaro iškart (anksčiau stigo ~10 s).
- [ ] Nubraižius žingsnį, automatinis tikrinimas jį pastebi per ~2 s; UNITS pakeitimą - per ~6 s.
- [ ] Brėžly lange pamokoje: H - užuomina, Enter - patikrinti / kitas žingsnis.
- [ ] Atidarius AutoCAD būsena tampa žalia („AutoCAD · Drawing1.dwg“).
- [ ] AutoCAD tik su pradžios (Start) langu, be brėžinio → oranžinė „AutoCAD · nėra brėžinio“; „Naujas“ sukuria brėžinį iš acadiso.dwt.
- [ ] AutoCAD'e atidarytas langas (pvz. OPTIONS) → „AutoCAD užimtas (Esc)“, uždarius - vėl žalia, ryšys nenutrūksta.
- [ ] AutoCAD paleistas „Run as administrator“ → „Kitos teisės (admin)“, „Kodėl?“ paaiškina; `brezly.log` yra eilutė „AutoCAD ryšys: teises_acad“.
- [ ] Uždarius ir vėl atidarius AutoCAD - ryšys atsistato pats.
- [ ] Jei įdiegtos dvi AutoCAD versijos - prisijungia prie tos, kuri atidaryta (ne tik naujausios).

## 3. Pamokos (po vieną žingsnį iš kelių pamokų)
- [ ] Pamokų sąrašas: Failas ir formatai, Kampinis įrašas, 2D brėžinys, Šriftai ir tekstas, Matmenys,
      Pirmoji 3D detalė, Projekcijos, Aksonometrija, Pjūviai, Elektrinė schema, A3 lapas (paskutinė).
- [ ] 1 pamoka („Failas ir formatai“): naujas brėžinys iš acadiso.dwt → „Patikrinti“ priima.
- [ ] 2 pamoka („Kampinis įrašas“): visi 4 žingsniai priimami; be vertikalios linijos 295,5 → 295,45 - aiški pastaba;
      išsaugotas `Kampinis_irasas.dwg`.
- [ ] 3 pamoka („2D brėžinys“): „Parodyk man“ nubraižo plokštę; automatinis tikrinimas pastebi atliktą žingsnį.
- [ ] 6 pamoka („Pirmoji 3D detalė“): BOX žingsnis - specialiai suklysk (z = 10) ir pažiūrėk, ar paaiškinimas aiškus.
- [ ] 7 pamoka („Projekcijos“): 1, 3 ir 4 vaizdai A3 lape atpažįstami.
- [ ] 8 pamoka („Aksonometrija“): visi 4 žingsniai su „Parodyk man“ ir tikrinimu.
- [ ] 9 pamoka („Pjūviai“): ketvirtinė išpjova (BOX + SUBTRACT) priimama; VIEWBASE ir VIEWSECTION žingsniai priimami
      (**pirmas kartas su tikru AutoCAD** - jei ne, `Pranešti apie klaidą` ir pažiūrėk `brezly.log`).
- [ ] 11 pamoka („A3 lapas“): COPYBASE iš `Kampinis_irasas.dwg` (0,0) → lape PASTECLIP 0,0 → lentelė atsiduria
      rėmelio kampe ir „Patikrinti“ priima abu paskutinius žingsnius.
- [ ] Vedlyje „Moku pagrindus“ → atsidaro pamoka „2D brėžinys“.

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

## 8. Microsoft Store versija (MSIX) - prieš pateikiant Store'ui
- [ ] Iš Actions artefakto paleisk `IDIEGTI_BANDOMAJI_MSIX.ps1` (šalia `Brezly_bandomasis.msix` ir `.cer`) → Brėžly atsiranda meniu Pradžia.
- [ ] **Svarbiausia:** prisijungia prie AutoCAD (žalia būsena), „Patikrinti“ ir „Parodyk man“ veikia - ar ryšys su AutoCAD veikia iš paketo.
- [ ] Praktika: „Pavyzdys AutoCAD'e“ atsidaro.
- [ ] Nustatymai › Tikrinti atnaujinimus → „Brėžly atnaujina Microsoft Store“.
- [ ] Progresas tas pats kaip įprastoje versijoje (`Dokumentai\Brezly`).
- [ ] Šalinimas: Parametrai › Programos › Brėžly → Šalinti.

## 9. „Kur klaida?“, garsas, dienos kartojimas
- [ ] Pamokoje nubraižyk ką nors ne taip (pvz. RECTANG 230,5 → 400,45) → „Patikrinti“ → „🔍 Kur klaida?“ → AutoCAD priartina ir paryškina tik šiame žingsnyje nubraižytą stačiakampį.
- [ ] „Kur klaida?“, kai žingsnyje nieko nenubraižyta → aiškus pranešimas; kai braižyta lape, o žiūri į Model - pasako, kad kita erdvė.
- [ ] Dirbant AutoCAD'e (Brėžly už jo), automatiškai priimtas žingsnis → „dzin“ ir Brėžly mirksi užduočių juostoje; Nustatymuose garsą galima išjungti.
- [ ] Pradžios ekrane - „🧠 Dienos kartojimas“; 5 klausimai → +XP; tą pačią dieną juosta dingsta, rytoj grįžta.

## 10. 1.1: paveikslėliai, egzaminas, silpnos vietos, treniruoklis, žinynas
- [ ] 2D pamokos žingsnis (pvz. „2D brėžinys“ → „Plokštės kontūras“) - po tikslu matosi paveikslėlis (oranžinė - šis žingsnis, pilka - jau nubraižyta). Angliškai „Title block“ teksto žingsnyje paveikslėlyje - „Part“.
- [ ] Praktika → „⏱ Egzamino režimas“ → „Pradėti egzaminą“ → pasirink užduotį ir laiką → AutoCAD'e atsidaro tuščias lapas, laikmatis eina; pereik į kitą langą - dešinėje apačioje laikrodis.
- [ ] Nubraižyk ir „✔ Baigti ir patikrinti“ → „Įskaityta“ arba pastabos su laiku; rezultatas matosi juostoje „Egzamino režimas“. Uždaryk ir vėl atidaryk Brėžly egzamino metu - laikmatis tęsiasi.
- [ ] Pamokoje paimk užuominą, „Parodyk man“, nepavykęs „Patikrinti“ → Kartoti → „🎯 Silpnos vietos“ - tas žingsnis sąraše; „Kartoti žingsnį →“ atidaro jį.
- [ ] Kartoti → „⌨ Komandų eilutė“: įvesk LINE / L, koordinates, Enter (tuščias) - priima; klaida → „Ne visai“, antra klaida → parodo atsakymą. Žingsnis be klaidų → +2 XP (vieną kartą).
- [ ] Meniu „Žinynas“: paieška be lietuviškų raidžių („pjuvis“) randa „pjūvis“; „Standartų atmintinė“ → „🖨 Spausdinti“.
- [ ] Programėlė telefone: Komandos → „⌨ Treniruoklis“, meniu „Žinynas“; po atnaujinimo apačioje - v1.1.

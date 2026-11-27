# Brėžly saugumas

Brėžly veikia tik tavo kompiuteryje: mažas vietinis serveris rodo sąsają ir per COM valdo AutoCAD.
Šiame faile - kaip jis apsaugotas ir ką daryti kūrėjui.

## Vietinis serveris („užkarda“, nuo 1.5.1)

| Apsauga | Nuo ko saugo |
|---|---|
| Klausosi tik `127.0.0.1` | Kiti tinklo įrenginiai (bendrabučio, kolegijos Wi-Fi) negali prisijungti. Windows užkardos taisyklių nereikia. |
| `Host` turi būti `127.0.0.1:<prievadas>` arba `localhost:<prievadas>` | DNS rebinding - svetainė, apsimetanti vietiniu adresu, negali perskaityti puslapio ar duomenų. |
| Sesijos raktas (kiekvieną paleidimą naujas) | Įdedamas tik į Brėžly puslapį; be jo `/api/...` atsako 403. Kitos naršyklėje atidarytos svetainės jo nežino. |
| Svetimas `Origin` - 403 | Užklausos iš kitų svetainių (net `no-cors` ir `sendBeacon`). |
| `/api/...` tik POST | Negalima nieko paleisti per nuorodą ar `<img src>`. |
| Užklausa iki 20 MB | Atminties užpildymas. |
| `X-Frame-Options: DENY`, `frame-ancestors 'none'` | Brėžly negalima įdėti į svetimą puslapį ir apgaule priversti spausti mygtukų. |
| `Cross-Origin-Resource-Policy: same-origin`, `nosniff` | Kitos svetainės negali naudoti Brėžly failų. |

Kiek svetimų užklausų atmesta - matosi „Pranešti apie klaidą“ ataskaitoje (`sistema.json` → `atmestos_svetimos_uzklausos`).
Kodas: `serveris.py` (skyrius „apsauga“), testai: `testai/test_saugumas.py`.

## Atnaujinimai

- Tikrinama ir siunčiama tik per HTTPS iš `atnaujinimai_url.txt` (diegimo aplanke - keisti gali tik administratorius).
- Diegiamas tik failas iš tos pačios GitHub repozitorijos Releases (`.../releases/download/...`) ir tik su sutampančia SHA-256 kontroline suma. Kitaip - atsisakoma ir parašoma atsisiųsti iš oficialios svetainės.
- Naujesnė versija tik į priekį (senesnės neįdiegia).

## Kūrėjui: svarbiausia apsauga - GitHub paskyra

Jei kas nors perimtų GitHub paskyrą, galėtų paskelbti netikrą versiją, o ją gautų visi vartotojai.
Parašo raktas GitHub Secrets nuo to neapsaugotų - paskyros savininkas gali pakeisti surinkimą ir pasirašyti ką nori.
Todėl:

1. **Įjunk dviejų veiksnių patvirtinimą (2FA)**: GitHub → Settings → Password and authentication → Two-factor authentication (programėlė, pvz. Microsoft/Google Authenticator, arba passkey). Atsarginius kodus išsaugok.
2. Tą patį - el. paštui, prie kurio pririšta GitHub paskyra.
3. Neduok kitiems teisių rašyti į repozitoriją; trečiųjų šalių GitHub programėlėms - tik tiek teisių, kiek būtina.
4. Kodo pasirašymo sertifikatas (Authenticode) ar Microsoft Store pašalintų „Windows apsaugojo jūsų kompiuterį“ langą - žr. „Brėžly: beta testavimas ir Microsoft Store“.

## Ko Brėžly nedaro

- Nesiunčia progreso, brėžinių ar asmeninių duomenų į internetą (žr. `PRIVATUMAS.md`). Internetu jungiasi tik atnaujinimų patikrai.
- `api_raktas.txt` ir `testavimas.json` niekada neįtraukiami į diegimo programą, ZIP ar repozitoriją.

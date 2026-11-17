// Programėlės tikrinimo testas: pavyzdiniai brėžiniai (atsakymai) turi būti priimti, tušti ruošiniai - ne.
// Paleisti: node testai/tikrinimas.test.js
const fs = require("fs"), path = require("path"), assert = require("assert");
const SAKNIS = path.join(__dirname, "..");
const T = require(path.join(SAKNIS, "app", "tikrinimas.js"));
const D = JSON.parse(fs.readFileSync(path.join(SAKNIS, "praktika", "uzduotys.json"), "utf8"));
T.nustatytiUzduotis(D);

const dxf = v => T.analizuoti(T.skaityti(fs.readFileSync(path.join(SAKNIS, "praktika", v), "latin1")));
// Žinoma: šių pavyzdinių DXF brūkšniuotė, izoapskritimas ir schemos ženklai nubraižyti linijomis,
// todėl tikrinimas juose neranda HATCH / ELLIPSE / INSERT. Kai pavyzdžiai bus perdaryti - ištrinti iš sąrašo.
const SUPAPRASTINTI = { U4_Velenas: "HATCH", U6_Izometrija: "ELLIPSE", U7_Schema: "INSERT" };
let klaidos = 0;
for (const u of D.uzduotys) {
  const ruosinys = dxf(u.id + "_ruosinys.dxf");
  const atsakymas = dxf(u.id + ".dxf");
  const turis = u.tikrinimas.turis || null;
  const geras = T.tikrinti(u.id, atsakymas, ruosinys, turis);
  const tuscias = T.tikrinti(u.id, ruosinys, ruosinys, null);
  const leista = SUPAPRASTINTI[u.id];
  const atsakymasOk = geras.priimta || (leista && geras.klaidos.length === 1 && geras.klaidos[0].includes(leista));
  const ok = atsakymasOk && !tuscias.priimta;
  if (!ok) klaidos++;
  console.log(`${ok ? "✓" : "✗"} ${u.id}: atsakymas ${geras.priimta ? "priimtas" : (atsakymasOk ? `be ${leista} (žinoma)` : "ATMESTAS " + JSON.stringify(geras.klaidos))}, ` +
              `ruošinys ${tuscias.priimta ? "PRIIMTAS (blogai)" : "atmestas"}`);
}
// tipinė studento klaida: apskritimas su skersmeniu vietoj spindulio
const a = { sk: {}, r: [40, 10, 10, 10, 10], remelis: false, solidai: 0 };
const r = T.tikrinti("U1_Tarpine", a, null, null);
assert(r.klaidos.some(k => k.includes("tai skersmuo")), "turi pastebėti skersmenį vietoj spindulio");
console.log("✓ pastebi skersmenį vietoj spindulio");
process.exit(klaidos ? 1 : 0);

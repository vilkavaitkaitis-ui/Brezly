/* Brėžly personažų SVG svetainei - tas pats piešimo kodas kaip programoje (brezly.js, PERSONAŽAI dalis).
   node irankiai/personazai.js  ->  JSON į stdout: {personazai:[{id,vardas,pav,forma,txt,fonas,svg}], robis_dziaug}
   Kviečia irankiai/generuoti.py. */
const fs = require("fs"), path = require("path");
const src = fs.readFileSync(path.join(__dirname, "..", "brezly.js"), "utf8");
const pr = src.indexOf("const BH="), pab = src.indexOf("function suDaiktu(");
if (pr < 0 || pab < 0) throw new Error("brezly.js: nerasta personažų dalis (const BH= ... function suDaiktu)");
const m = new Function("S", src.slice(pr, pab) + "\nreturn {PERSONAZAI, robotoSVG, PRADINIS, BH};")({ eq: null });
const vienas = (id, n) => m.robotoSVG({ ...m.PRADINIS, personazas: id }, { eks: true, n });
process.stdout.write(JSON.stringify({
  personazai: m.PERSONAZAI.map(p => ({ id: p.id, vardas: p.vardas, pav: p.pav, forma: p.forma, txt: p.txt,
                                       fonas: m.BH[p.fonas] || m.BH.B, svg: vienas(p.id, "lauk") })),
  robis_dziaug: vienas(m.PERSONAZAI[0].id, "dziaug"),
}));

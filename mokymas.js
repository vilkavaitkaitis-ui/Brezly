/* Brėžly: žinynas (terminai LT–EN, standartų atmintinė) ir komandų eilutės treniruoklis.
   Vienas failas programai (brezly.html) ir programėlei telefone (app/). Be priklausomybių ir be interneto.
   Spalvos - iš --mk-* kintamųjų (kiekviena sąsaja juos nustato pagal savo temą), su tamsiomis atsarginėmis. */
(function(){
"use strict";
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const be = s => String(s ?? "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");     // be diakritikų: „brezinys“ randa „brėžinys“

const Z = {
  lt: {
    terminai:"Terminai LT–EN", atmintine:"Standartų atmintinė", ieskoti:"Ieškoti: pjūvis, section, HATCH…", rasta:"rasta",
    nerasta:"Nieko nerasta. Pabandyk kitą žodį arba anglišką terminą.", kraunama:"Kraunama…", klaida:"Nepavyko įkelti žinyno.",
    spausdinti:"🖨 Spausdinti atmintinę", kopijuoti:"Kopijuoti komandą",
    pastaba:"Skaičiai - pagal LST EN ISO standartus ir įprastą mokymo praktiką. Tikslius reikalavimus patikslink pas dėstytoją.",
    visos:"Visos pradėtos pamokos", visosVisos:"Visos pamokos", zingsnis:"Žingsnis", is:"iš", tikslas:"Tikslas",
    ivesk:"Įvesk atsakymą ir spausk Enter", bandyk:"Ne visai - pabandyk dar kartą.", teisingas:"Teisingas atsakymas:", ivesKji:"įvesk jį",
    parodyti:"💡 Parodyti atsakymą", praleisti:"Praleisti žingsnį", baigta:"✓ Žingsnis baigtas", beKlaidu:"be klaidų!",
    kitas:"Kitas žingsnis →", rezultatas:"Rezultatas", isPirmo:"Iš pirmo karto teisingai", darKarta:"↻ Dar kartą", painioji:"Kur suklydai:",
    pele:"pelė / langas", nera:"Šioje pamokoje nėra komandų, kurias galima įvesti klaviatūra.",
    puiku:"Puiku - visos komandos iš pirmo karto! 🎉", gerai:"Gerai! Suklydusias pakartok dar kartą.",
    pagalba:"Rašyk taip, kaip AutoCAD komandų eilutėje: komandą (pvz. LINE arba L), koordinates (0,0 · @100,0 · @50<30), parinkties raidę (R). Tuščias Enter - tiesiog spausk Enter.",
    pamoka:"Pamoka"
  },
  en: {
    terminai:"Terms LT–EN", atmintine:"Standards cheat sheet", ieskoti:"Search: section, pjūvis, HATCH…", rasta:"found",
    nerasta:"Nothing found. Try another word or the Lithuanian term.", kraunama:"Loading…", klaida:"Couldn't load the glossary.",
    spausdinti:"🖨 Print cheat sheet", kopijuoti:"Copy command",
    pastaba:"Values follow EN ISO standards and common teaching practice. Check exact requirements with your lecturer.",
    visos:"All started lessons", visosVisos:"All lessons", zingsnis:"Step", is:"of", tikslas:"Goal",
    ivesk:"Type the answer and press Enter", bandyk:"Not quite - try again.", teisingas:"Correct answer:", ivesKji:"type it",
    parodyti:"💡 Show answer", praleisti:"Skip step", baigta:"✓ Step done", beKlaidu:"no mistakes!",
    kitas:"Next step →", rezultatas:"Result", isPirmo:"Right on the first try", darKarta:"↻ Again", painioji:"Where you slipped:",
    pele:"mouse / dialog", nera:"This lesson has no commands to type on the keyboard.",
    puiku:"Great - every command right on the first try! 🎉", gerai:"Good! Practise the ones you missed once more.",
    pagalba:"Type as in the AutoCAD command line: a command (e.g. LINE or L), coordinates (0,0 · @100,0 · @50<30), an option letter (R). Empty Enter - just press Enter.",
    pamoka:"Lesson"
  }
};
let kalba = "lt";
const t = k => (Z[kalba] || Z.lt)[k] ?? Z.lt[k] ?? k;

/* ---------- stilius (įterpiamas vieną kartą) ---------- */
function stilius(){
  if (document.getElementById("mk-stilius")) return;
  const s = document.createElement("style"); s.id = "mk-stilius";
  s.textContent = `
.mk{--k:var(--mk-kortele,#151e35);--l:var(--mk-linija,#24304e);--b:var(--mk-blankus,#8d9cb9);--a:var(--mk-akcentas,#f59e0b);--tx:var(--mk-tekstas,#eaf0fa);
  --kod:var(--mk-kodas,#05080f);--ok:var(--mk-gerai,#22c55e);--er:var(--mk-klaida,#f87171);--mono:var(--mk-mono,ui-monospace,Consolas,monospace);color:var(--tx)}
.mk *{box-sizing:border-box}
.mk-sk{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 14px}
.mk-sk button{border:1px solid var(--l);background:var(--k);color:inherit;border-radius:10px;padding:8px 14px;font:inherit;font-weight:600;cursor:pointer}
.mk-sk button[aria-selected="true"]{border-color:var(--a);box-shadow:inset 0 -2px 0 var(--a)}
.mk-paieska{display:flex;gap:10px;align-items:center;margin-bottom:12px}
.mk-paieska input{flex:1;min-width:0;border:1px solid var(--l);background:var(--k);color:inherit;border-radius:10px;padding:10px 12px;font:inherit}
.mk-paieska small,.mk small{color:var(--b)}
.mk-terminai{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.mk-t{border:1px solid var(--l);background:var(--k);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:4px}
.mk-t b{font-size:15.5px}.mk-t .mk-en{color:var(--a);font-weight:600}
.mk-t p{margin:2px 0 0;color:var(--b);font-size:13.5px;line-height:1.45}
.mk-t button{align-self:flex-start;margin-top:4px;border:1px solid var(--l);background:var(--kod);color:var(--a);border-radius:7px;padding:2px 8px;font:12.5px var(--mono);cursor:pointer}
.mk-atm{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}
.mk-a{border:1px solid var(--l);background:var(--k);border-radius:12px;padding:14px 16px}
.mk-a h3{margin:0 0 8px;font-size:15.5px}
.mk-a table{width:100%;border-collapse:collapse;font-size:13.5px}
.mk-a td{padding:5px 0;border-top:1px solid var(--l);vertical-align:top}
.mk-a td:first-child{color:var(--b);padding-right:12px;width:44%}
.mk-a td:last-child{font-family:var(--mono);font-size:12.5px}
.mk-a p{margin:8px 0 0;font-size:12.5px;color:var(--b);line-height:1.45}
.mk-past{margin:14px 0 0;font-size:12.5px;color:var(--b)}
.mk-mygt{border:1px solid var(--l);background:var(--k);color:inherit;border-radius:10px;padding:8px 14px;font:inherit;font-weight:600;cursor:pointer}
.mk-mygt.pagr{background:var(--a);border-color:var(--a);color:#1a1300}
.mk-mygt:disabled{opacity:.5;cursor:default}
.mk-eil{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.mk-tren{display:flex;flex-direction:column;gap:12px;max-width:760px}
.mk-tren select{border:1px solid var(--l);background:var(--k);color:inherit;border-radius:10px;padding:8px 10px;font:inherit;max-width:100%}
.mk-uzd{border:1px solid var(--l);background:var(--k);border-radius:12px;padding:12px 14px}
.mk-uzd b{display:block;font-size:16px;margin:2px 0}
.mk-uzd p{margin:4px 0 0;color:var(--b);font-size:13.5px}
.mk-cli{background:var(--kod);border:1px solid var(--l);border-radius:12px;padding:12px 14px;font:14px/1.6 var(--mono);min-height:150px;max-height:340px;overflow:auto}
.mk-l{display:flex;gap:8px;flex-wrap:wrap;align-items:baseline}
.mk-pr{color:#9fb0cc}
.mk-iv{color:#fbbf24;font-weight:600}.mk-iv.ok{color:var(--ok)}.mk-iv.pz{color:#fb923c}
.mk-info .mk-iv{color:#7c8aa5;font-weight:400;font-style:italic}
.mk-dab{display:flex;gap:8px;align-items:baseline;margin:0}
.mk-dab input{flex:1;min-width:80px;background:transparent;border:0;border-bottom:1px dashed #3b4a6b;color:#fbbf24;font:600 14px var(--mono);padding:2px 0;outline:none;text-transform:uppercase}
.mk-dab input.txt{text-transform:none}
.mk-dab input:focus{border-bottom-color:var(--a)}
.mk-dab.kreta{animation:mk-kr .3s}
@keyframes mk-kr{25%{transform:translateX(-6px)}75%{transform:translateX(6px)}}
.mk-zin{min-height:22px;font-size:14px}.mk-zin.er{color:var(--er)}.mk-zin.ok{color:var(--ok);font-weight:600}
.mk-zin code{font-family:var(--mono);color:#fbbf24;background:var(--kod);padding:1px 6px;border-radius:5px}
.mk-juosta{height:6px;border-radius:3px;background:var(--l);overflow:hidden}.mk-juosta i{display:block;height:100%;background:var(--a)}
.mk-rez{border:1px solid var(--l);background:var(--k);border-radius:12px;padding:16px}
.mk-rez h3{margin:0 0 6px;font-size:20px}
.mk-rez ul{margin:8px 0 12px;padding-left:20px;color:var(--b)}
.mk-rez code{font-family:var(--mono);color:#fbbf24}
@media print{.mk-sk,.mk-paieska,.mk-mygt{display:none}}`;
  document.head.appendChild(s);
}

/* =================== ŽINYNAS =================== */
let ZD = null;
async function ikelti(url){
  if (!ZD) { const r = await fetch(url); if (!r.ok) throw new Error(r.status); ZD = await r.json(); }
  return ZD;
}
function terminoTekstas(x){ return be([x.lt, x.en, x.ka, x.ka_en, x.komanda].join(" ")); }
function terminaiHTML(d, q){
  const z = be(q.trim()), l = d.terminai.filter(x => !z || terminoTekstas(x).includes(z));
  if (!l.length) return `<p class="mk-past">${t("nerasta")}</p>`;
  return `<div class="mk-terminai">${l.map(x => {
    const [pirm, antr, ka] = kalba === "en" ? [x.en, x.lt, x.ka_en || x.ka] : [x.lt, x.en, x.ka];
    return `<div class="mk-t"><b>${esc(pirm)}</b><span class="mk-en">${esc(antr)}</span><p>${esc(ka)}</p>
      ${x.komanda ? `<button type="button" data-kom="${esc(x.komanda)}" title="${t("kopijuoti")}">${esc(x.komanda)}</button>` : ""}</div>`;
  }).join("")}</div>`;
}
function atmintineHTML(d){
  return `<div class="mk-atm">${d.atmintine.map(a => `<div class="mk-a"><h3>${esc(kalba === "en" ? a.pavadinimas_en || a.pavadinimas : a.pavadinimas)}</h3>
    <table>${a.eilutes.map(e => { const [x, y] = kalba === "en" ? (e.length > 2 ? [e[2], e[3]] : e) : e;
      return `<tr><td>${esc(x)}</td><td>${esc(y)}</td></tr>`; }).join("")}</table>
    ${a.pastaba ? `<p>${esc(kalba === "en" ? a.pastaba_en || a.pastaba : a.pastaba)}</p>` : ""}</div>`).join("")}</div>
    <p class="mk-past">${t("pastaba")}</p>`;
}
function spausdinti(d){
  const w = window.open("", "_blank"); if (!w) return;
  w.document.write(`<!doctype html><html lang="${kalba}"><head><meta charset="utf-8"><title>Brėžly - ${esc(t("atmintine"))}</title><style>
body{font:12px/1.4 system-ui,Segoe UI,sans-serif;margin:14mm;color:#111}h1{font-size:18px;margin:0 0 10px}
.mk-atm{columns:2;column-gap:10mm}.mk-a{break-inside:avoid;margin:0 0 6mm}.mk-a h3{font-size:13px;margin:0 0 4px}
table{width:100%;border-collapse:collapse}td{border-top:1px solid #ccc;padding:2px 4px 2px 0;vertical-align:top}td:first-child{width:44%;color:#444}
.mk-a p,.mk-past{color:#444;font-size:11px;margin:4px 0 0}</style></head><body><h1>Brėžly · ${esc(t("atmintine"))}</h1>${atmintineHTML(d)}</body></html>`);
  w.document.close(); w.focus(); setTimeout(() => w.print(), 250);
}
function zinynas(el, o = {}){
  stilius(); kalba = o.kalba === "en" ? "en" : "lt";
  const st = { sk: o.skirtukas || "terminai", q: "" };
  el.classList.add("mk"); el.innerHTML = `<p class="mk-past">${t("kraunama")}</p>`;
  ikelti(o.url || "zinynas.json").then(d => {
    const piesti = () => {
      el.innerHTML = `<div class="mk-sk" role="tablist">${[["terminai", t("terminai")], ["atmintine", t("atmintine")]].map(([k, v]) =>
        `<button type="button" role="tab" aria-selected="${st.sk === k}" data-sk="${k}">${v}</button>`).join("")}</div>` +
        (st.sk === "terminai"
          ? `<div class="mk-paieska"><input type="search" id="mkPaieska" placeholder="${esc(t("ieskoti"))}" aria-label="${esc(t("ieskoti"))}" value="${esc(st.q)}"><small id="mkKiek"></small></div><div id="mkTerm"></div>`
          : `<div class="mk-eil" style="margin-bottom:12px"><button type="button" class="mk-mygt" id="mkSpausd">${t("spausdinti")}</button></div>${atmintineHTML(d)}`);
      el.querySelectorAll("[data-sk]").forEach(b => b.onclick = () => { st.sk = b.dataset.sk; piesti(); });
      if (st.sk === "terminai") {
        const ivestis = el.querySelector("#mkPaieska"), sar = el.querySelector("#mkTerm");
        const atnaujinti = () => {
          st.q = ivestis.value; sar.innerHTML = terminaiHTML(d, st.q);
          const n = sar.querySelectorAll(".mk-t").length; el.querySelector("#mkKiek").textContent = `${n} ${t("rasta")}`;
          sar.querySelectorAll("[data-kom]").forEach(b => b.onclick = () => o.onKomanda && o.onKomanda(b.dataset.kom));
        };
        ivestis.oninput = atnaujinti; atnaujinti();
      } else el.querySelector("#mkSpausd").onclick = () => spausdinti(d);
    };
    piesti();
  }).catch(() => { el.innerHTML = `<p class="mk-past">${t("klaida")}</p>`; });
}

/* =================== KOMANDŲ EILUTĖS TRENIRUOKLIS =================== */
// Numatytieji AutoCAD trumpiniai (acad.pgp) - priimami kaip ir pilnas komandos vardas
const TRUMPINIAI = { LINE:["L"], CIRCLE:["C"], RECTANG:["REC","RECTANGLE"], TEXT:["DT","DTEXT"], DIMLINEAR:["DLI"], DIMDIAMETER:["DDI"],
  DIMALIGNED:["DAL"], DIMEDIT:["DED"], FILLET:["F"], LAYER:["LA"], STYLE:["ST"], EXTRUDE:["EXT"], UNION:["UNI"], SUBTRACT:["SU"],
  POLYGON:["POL"], CYLINDER:["CYL"], MIRROR3D:["3DMIRROR"], ELLIPSE:["EL"], INSERT:["I"], BLOCK:["B"], ATTDEF:["ATT"], UNITS:["UN"],
  PLOT:["PRINT"], WEDGE:["WE"], HATCH:["H"], OPEN:[], SAVEAS:[], NEW:[], BOX:[] };
const EILUTES_PRASYMAS = /^(Command|Specify|Select|Enter|Center|Radius|Rotation|Name|Base point|Delete source|Align)\b/i;

function rusis(pr, iv){
  const s = String(iv).trim();
  if (!EILUTES_PRASYMAS.test(pr)) return "info";                     // dialogo laukai, pelės veiksmai
  if (/^\(?enter\)?$/i.test(s)) return "enter";
  if (/[()→·]/.test(s) || !s) return "info";
  if (/^Command/i.test(pr) && /^-?[A-Z0-9]+$/.test(s)) return "komanda";
  if (/^[A-Z][A-Z0-9]*$/.test(s)) return "parinktis";
  if (/^[@+\-0-9.,<]+$/.test(s) && /\d/.test(s)) return "skaicius";
  return "tekstas";
}
function trumpiniai(korteles){
  const m = {}; for (const [k, v] of Object.entries(TRUMPINIAI)) m[k] = new Set(v);
  (korteles || []).forEach(x => { const s = m[x.k] || (m[x.k] = new Set());
    String(x.trump || "").split(/[\s,/·]+/).forEach(p => { if (/^[A-Z0-9]+$/.test(p)) s.add(p); }); });
  return m;
}
function skaiciai(s){ return String(s).replace(/\s+/g, "").split(/([@,<])/).filter(x => x !== ""); }
function tinka(ats, e, alias){
  const a = String(ats).trim(), A = a.toUpperCase().replace(/^[_']+/, "");
  if (e.rusis === "enter") return a === "" || A === "ENTER";
  if (e.rusis === "komanda") return A === e.iv || !!(alias[e.iv] && alias[e.iv].has(A));
  if (e.rusis === "parinktis") {
    if (A === e.iv) return true;
    const opc = (e.pr.match(/\[([^\]]+)\]/) || [])[1];      // [Radius/Polyline] - galima rašyti ir visą žodį
    return !!opc && opc.split("/").some(w => w.replace(/[^A-Z]/g, "") === e.iv && A === w.toUpperCase());
  }
  if (e.rusis === "skaicius") {
    const x = skaiciai(a), y = skaiciai(e.iv);
    return x.length === y.length && x.every((v, i) => /^[@,<]$/.test(y[i]) ? v === y[i] : v !== "" && !isNaN(v) && Math.abs(parseFloat(v) - parseFloat(y[i])) < 1e-9);
  }
  return be(a) === be(e.iv);
}
function rodomas(ats, e){
  if (e.rusis === "enter") return "↵";
  return e.rusis === "tekstas" ? String(ats).trim() : String(ats).trim().toUpperCase();
}
function baseinas(pamokos){
  const r = [];
  pamokos.forEach(p => p.zingsniai.forEach(z => {
    const ir = (z.komandos || []).map(([pr, iv]) => ({ pr, iv: String(iv).trim(), rusis: rusis(pr, iv) }));
    if (ir.some(e => e.rusis !== "info")) r.push({ p, z, ir, raktas: p.id + "/" + z.id });
  }));
  return r;
}
function maisyti(a){ a = [...a]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

function treniruoklis(el, o = {}){
  stilius(); kalba = o.kalba === "en" ? "en" : "lt";
  el.classList.add("mk");
  const alias = trumpiniai(o.korteles), visi = baseinas(o.pamokos || []), kiek = o.kiek || 5;
  const pradetos = new Set(o.pradetos || []);
  let pas = o.rinkinys && o.rinkinys.length ? "rinkinys" : (o.pamoka || "visos");
  let S;                                              // sesija

  function sudaryti(){
    let eile;
    if (pas === "rinkinys") eile = visi.filter(x => o.rinkinys.includes(x.raktas));
    else if (pas === "visos" || pas === "visosVisos") {
      let b = pas === "visos" ? visi.filter(x => pradetos.has(x.p.id)) : visi;
      if (b.length < kiek) b = visi;
      eile = maisyti(b).slice(0, kiek);
    } else eile = visi.filter(x => x.p.id === pas);
    S = { eile, i: 0, j: 0, kl: 0, parodyta: false, teis: 0, viso: 0, zKlaidos: 0, klaidos: [], baigta: false };
  }
  const zing = () => S.eile[S.i], irasas = () => zing() && zing().ir[S.j];

  function pasirinkimas(){
    const pam = o.pamokos || [], sk = id => visi.filter(x => x.p.id === id).length;
    return `<select id="mkPam" aria-label="${t("pamoka")}">
      ${o.rinkinys && o.rinkinys.length ? `<option value="rinkinys" ${pas === "rinkinys" ? "selected" : ""}>${esc(o.rinkinioVardas || "★")}</option>` : ""}
      <option value="visos" ${pas === "visos" ? "selected" : ""}>${t("visos")} · ${kiek}</option>
      <option value="visosVisos" ${pas === "visosVisos" ? "selected" : ""}>${t("visosVisos")} · ${kiek}</option>
      ${pam.map((p, i) => sk(p.id) ? `<option value="${esc(p.id)}" ${pas === p.id ? "selected" : ""}>${i + 1}. ${esc(p.pavadinimas)} · ${sk(p.id)}</option>` : "").join("")}
    </select>`;
  }
  function eilute(e, ats, kl){
    return `<div class="mk-l ${e.rusis === "info" ? "mk-info" : ""}"><span class="mk-pr">${esc(e.pr || "›")}</span><span class="mk-iv ${kl || ""}">${esc(ats)}</span></div>`;
  }
  function praleistiInfo(cli){
    const z = zing();
    while (S.j < z.ir.length && z.ir[S.j].rusis === "info") { cli.insertAdjacentHTML("beforeend", eilute(z.ir[S.j], `🖱 ${z.ir[S.j].iv}`)); S.j++; }
  }
  function piesti(){
    if (!S) sudaryti();
    const z = zing();
    if (!S.eile.length) { el.innerHTML = `<div class="mk-tren"><div class="mk-eil">${pasirinkimas()}</div><p class="mk-past">${t("nera")}</p></div>`; susieti(); return; }
    if (!z) return rezultatas();
    el.innerHTML = `<div class="mk-tren">
      <div class="mk-eil">${pasirinkimas()}<span style="flex:1"></span><small>${t("zingsnis")} ${S.i + 1} ${t("is")} ${S.eile.length} · ✓ ${S.teis}/${S.viso}</small></div>
      <div class="mk-juosta"><i style="width:${S.i / S.eile.length * 100}%"></i></div>
      <div class="mk-uzd"><small>${esc(z.p.pavadinimas)}</small><b>${esc(z.z.pavadinimas)}</b>${z.z.tikslas ? `<p>🎯 ${t("tikslas")}: ${esc(z.z.tikslas)}</p>` : ""}</div>
      <div class="mk-cli" id="mkCli" aria-live="polite"></div>
      <div class="mk-zin" id="mkZin"></div>
      <div class="mk-eil" id="mkMygt"><button type="button" class="mk-mygt" id="mkRodyti">${t("parodyti")}</button>
        <button type="button" class="mk-mygt" id="mkPral">${t("praleisti")}</button><span style="flex:1"></span><small>${esc(t("pagalba"))}</small></div>
    </div>`;
    const cli = el.querySelector("#mkCli");
    for (let j = 0; j < S.j; j++) cli.insertAdjacentHTML("beforeend", eilute(z.ir[j], z.ir[j].rusis === "info" ? "🖱 " + z.ir[j].iv : rodomas(z.ir[j].iv, z.ir[j]), "ok"));
    praleistiInfo(cli);
    susieti();
    if (S.j >= z.ir.length) return zingsnisBaigtas();
    naujaEilute();
  }
  function naujaEilute(){
    const cli = el.querySelector("#mkCli"), e = irasas();
    S.kl = 0; S.parodyta = false;
    const f = document.createElement("form"); f.className = "mk-dab"; f.autocomplete = "off";
    f.innerHTML = `<label class="mk-pr" for="mkIv">${esc(e.pr)}</label><input id="mkIv" class="${e.rusis === "tekstas" ? "txt" : ""}" autocomplete="off" autocapitalize="${e.rusis === "tekstas" ? "sentences" : "characters"}" autocorrect="off" spellcheck="false" enterkeyhint="send" aria-describedby="mkZin" placeholder="${esc(t("ivesk"))}">`;
    cli.appendChild(f);
    const iv = f.querySelector("input");
    iv.addEventListener("keydown", ev => { if (ev.key === " " && e.rusis !== "tekstas") { ev.preventDefault(); f.requestSubmit ? f.requestSubmit() : f.onsubmit(ev); } });   // tarpas = Enter, kaip AutoCAD'e
    f.onsubmit = ev => { ev.preventDefault(); pateikti(iv.value); };
    cli.scrollTop = cli.scrollHeight;
    setTimeout(() => iv.focus({ preventScroll: true }), 0);
  }
  function zinute(html, kl){ const z = el.querySelector("#mkZin"); if (z) { z.className = "mk-zin " + (kl || ""); z.innerHTML = html; } }
  function pateikti(ats){
    const e = irasas(), f = el.querySelector(".mk-dab"), z = zing();
    if (!e || !f) return;
    if (tinka(ats, e, alias)) {
      const pirmas = S.kl === 0 && !S.parodyta;
      S.viso++; if (pirmas) S.teis++;
      f.remove();
      const cli = el.querySelector("#mkCli");
      cli.insertAdjacentHTML("beforeend", eilute(e, rodomas(ats, e), pirmas ? "ok" : "pz"));
      zinute("");
      S.j++; praleistiInfo(cli);
      const sm = el.querySelector(".mk-eil small"); if (sm) sm.textContent = `${t("zingsnis")} ${S.i + 1} ${t("is")} ${S.eile.length} · ✓ ${S.teis}/${S.viso}`;
      if (S.j >= z.ir.length) zingsnisBaigtas(); else naujaEilute();
      return;
    }
    S.kl++;
    if (S.kl === 1) { S.zKlaidos++; S.klaidos.push({ raktas: z.raktas, pr: e.pr, iv: e.iv, p: z.p.pavadinimas }); o.onKlaida && o.onKlaida({ raktas: z.raktas, iv: e.iv }); }
    f.classList.remove("kreta"); void f.offsetWidth; f.classList.add("kreta");
    const iv = f.querySelector("input"); iv.select();
    if (S.kl >= 2) rodytiAts(); else zinute(t("bandyk"), "er");
  }
  function rodytiAts(){
    const e = irasas(); if (!e) return;
    S.parodyta = true;
    const z = zing();
    if (S.kl === 0) { S.zKlaidos++; S.klaidos.push({ raktas: z.raktas, pr: e.pr, iv: e.iv, p: z.p.pavadinimas }); o.onKlaida && o.onKlaida({ raktas: z.raktas, iv: e.iv }); S.kl = 1; }
    zinute(`${t("teisingas")} <code>${esc(e.rusis === "enter" ? "Enter" : e.iv)}</code> - ${t("ivesKji")}.`, "er");
    const iv = el.querySelector("#mkIv"); if (iv) iv.focus();
  }
  function zingsnisBaigtas(){
    const z = zing(), be0 = S.zKlaidos === 0;
    o.onZingsnis && o.onZingsnis({ raktas: z.raktas, beKlaidu: be0, el });
    const m = el.querySelector("#mkMygt");
    zinute(`${t("baigta")}${be0 ? " - " + t("beKlaidu") : ""}`, "ok");
    if (m) { m.innerHTML = `<button type="button" class="mk-mygt pagr" id="mkKitas">${S.i < S.eile.length - 1 ? t("kitas") : t("rezultatas") + " →"}</button>`;
      const b = m.querySelector("#mkKitas"); b.onclick = () => { S.i++; S.j = 0; S.zKlaidos = 0; piesti(); }; setTimeout(() => b.focus(), 0); }
  }
  function rezultatas(){
    if (!S.baigta) { S.baigta = true; o.onBaigta && o.onBaigta({ teis: S.teis, viso: S.viso, klaidos: S.klaidos, el }); }
    const vis = S.teis === S.viso;
    el.innerHTML = `<div class="mk-tren"><div class="mk-eil">${pasirinkimas()}</div><div class="mk-rez" id="mkRez">
      <small>${t("rezultatas")}</small><h3>${t("isPirmo")}: ${S.teis} ${t("is")} ${S.viso}</h3><p style="margin:0">${vis ? t("puiku") : t("gerai")}</p>
      ${S.klaidos.length ? `<p style="margin:12px 0 0"><b>${t("painioji")}</b></p><ul>${S.klaidos.map(k => `<li>${esc(k.pr)} <code>${esc(k.iv)}</code> <small>· ${esc(k.p)}</small></li>`).join("")}</ul>` : ""}
      <div class="mk-eil" style="margin-top:12px"><button type="button" class="mk-mygt pagr" id="mkDar">${t("darKarta")}</button></div></div></div>`;
    susieti();
    const b = el.querySelector("#mkDar"); b.onclick = () => { sudaryti(); piesti(); }; setTimeout(() => b.focus(), 0);
  }
  function susieti(){
    const s = el.querySelector("#mkPam"); if (s) s.onchange = () => { pas = s.value; sudaryti(); piesti(); };
    const r = el.querySelector("#mkRodyti"); if (r) r.onclick = rodytiAts;
    const p = el.querySelector("#mkPral"); if (p) p.onclick = () => { S.i++; S.j = 0; S.zKlaidos = 0; piesti(); };
  }
  sudaryti(); piesti();
  return { naujas(){ sudaryti(); piesti(); } };
}

window.Mokymas = { zinynas, treniruoklis, _vidus: { rusis, tinka, trumpiniai, baseinas, be } };
})();

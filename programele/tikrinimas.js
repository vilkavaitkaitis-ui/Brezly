/* Brėžly - DXF brėžinio skaitymas ir praktikos užduočių tikrinimas (naršyklėje, be AutoCAD COM). */
(function (global) {
  "use strict";

  const IGNORUOTI = /^(REMELIS|BR_.*|DEFPOINTS)$/i;

  // Taisyklės - iš praktika/uzduotys.json (programėlėje: uzduotys.js -> window.BREZLY_UZDUOTYS)
  let TAISYKLES = {}, TOL_R = 0.05, TOL_V = 0.02;
  function nustatytiUzduotis(d) {
    TOL_R = d.tolerancija.spindulys;
    TOL_V = d.tolerancija.turis;
    TAISYKLES = {};
    for (const u of d.uzduotys) {
      const t = u.tikrinimas || {};
      TAISYKLES[u.id] = { apsk: t.apskritimai, tipai: t.tipai, turis: t.turis };
    }
  }
  if (global && global.BREZLY_UZDUOTYS) nustatytiUzduotis(global.BREZLY_UZDUOTYS);

  const VARDAI = {
    LINE: "atkarpų (LINE ir polilinijų tiesių dalių)",
    ARC: "lankų (ARC, FILLET)",
    HATCH: "brūkšniavimų (HATCH)",
    ELLIPSE: "elipsių / izoapskritimų (ELLIPSE)",
    INSERT: "įterptų blokų (INSERT)"
  };

  function fmt(x) {
    return Math.abs(x - Math.round(x)) < 0.005 ? String(Math.round(x)) : x.toFixed(2).replace(".", ",");
  }

  /** DXF tekstas -> objektų sąrašas [{tipas, g:[[kodas, reikšmė]]}] iš ENTITIES sekcijos */
  function skaityti(tekstas) {
    if (/^AutoCAD Binary DXF/.test(tekstas.slice(0, 22))) {
      throw new Error("Tai dvejetainis DXF. AutoCAD'e išsaugok kaip paprastą (ASCII) DXF.");
    }
    const L = tekstas.split(/\r?\n/);
    const ob = [];
    let sekcija = "", cur = null;
    for (let i = 0; i + 1 < L.length; i += 2) {
      const kodas = parseInt(L[i], 10);
      const v = L[i + 1].trim();
      if (Number.isNaN(kodas)) continue;
      if (kodas === 0) {
        if (cur) { ob.push(cur); cur = null; }
        if (v === "SECTION") { sekcija = (L[i + 3] || "").trim(); i += 2; continue; }
        if (v === "ENDSEC") { sekcija = ""; continue; }
        if (sekcija === "ENTITIES" && v !== "EOF") cur = { tipas: v, g: [] };
      } else if (cur) {
        cur.g.push([kodas, v]);
      }
    }
    if (cur) ob.push(cur);
    if (!ob.length && !/ENTITIES/.test(tekstas)) throw new Error("Tai ne DXF failas.");
    return ob;
  }

  const gauti = (o, k) => { const p = o.g.find(x => x[0] === k); return p ? p[1] : undefined; };

  /** Suskaičiuoja ką mato tikrinimas */
  function analizuoti(ob) {
    const sk = {}, r = [];
    let remelis = false, solidai = 0;
    const prideti = (k, n) => { sk[k] = (sk[k] || 0) + n; };
    for (let i = 0; i < ob.length; i++) {
      const o = ob[i];
      if (o.tipas === "VERTEX" || o.tipas === "SEQEND") continue;
      if (gauti(o, 67) === "1") continue;                       // popieriaus erdvė
      const sl = gauti(o, 8) || "0";
      if (/^REMELIS$/i.test(sl)) remelis = true;
      if (IGNORUOTI.test(sl)) {
        if (o.tipas === "POLYLINE") while (i + 1 < ob.length && ob[i + 1].tipas !== "SEQEND" && ob[i + 1].tipas === "VERTEX") i++;
        continue;
      }
      if (o.tipas === "CIRCLE") {
        prideti("CIRCLE", 1);
        r.push(parseFloat(gauti(o, 40)));
      } else if (o.tipas === "LWPOLYLINE" || o.tipas === "POLYLINE") {
        let n = 0, b = 0, uzd = (parseInt(gauti(o, 70) || "0", 10) & 1) === 1;
        if (o.tipas === "LWPOLYLINE") {
          for (const [k, v] of o.g) {
            if (k === 10) n++;
            if (k === 42 && Math.abs(parseFloat(v)) > 1e-9) b++;
          }
        } else {
          while (i + 1 < ob.length && ob[i + 1].tipas === "VERTEX") {
            i++; n++;
            const bl = gauti(ob[i], 42);
            if (bl && Math.abs(parseFloat(bl)) > 1e-9) b++;
          }
        }
        let seg = Math.max(0, uzd ? n : n - 1);
        b = Math.min(b, seg);
        prideti("ARC", b);
        prideti("LINE", seg - b);
      } else if (o.tipas === "3DSOLID") {
        solidai++;
        prideti("3DSOLID", 1);
      } else {
        prideti(o.tipas, 1);
      }
    }
    return { sk, r, remelis, solidai };
  }

  function kiekR(a, r) { return a.r.filter(x => Math.abs(x - r) <= TOL_R).length; }

  /**
   * Tikrina užduotį.
   * a       - analizuoti() rezultatas
   * bazine  - ruošinio analizė (atimama, jei brėžinys pradėtas iš ruošinio), gali būti null
   * turis   - studento įvestas MASSPROP tūris (U8), gali būti null
   * Grąžina {priimta, geri:[], klaidos:[], pastabos:[]}
   */
  function tikrinti(id, a, bazine, turis) {
    const t = TAISYKLES[id];
    const geri = [], klaidos = [], pastabos = [];
    const sk = Object.assign({}, a.sk);
    if (bazine && a.remelis) {
      for (const k in bazine.sk) sk[k] = Math.max(0, (sk[k] || 0) - bazine.sk[k]);
    }
    for (const rs in t.apsk || {}) {
      const r = +rs, reikia = t.apsk[rs], rasta = kiekR(a, r);
      if (rasta >= reikia) {
        geri.push(`${reikia} × apskritimas ø${fmt(2 * r)} (R${fmt(r)})`);
      } else {
        let p = `Trūksta apskritimo ø${fmt(2 * r)}` + (reikia > 1 ? ` (radau ${rasta} iš ${reikia})` : "") + ".";
        if (kiekR(a, 2 * r) > 0) {
          p += ` Radau apskritimą su spinduliu ${fmt(2 * r)} - tai skersmuo! CIRCLE prašo spindulio: įvesk ${fmt(r)} (arba spausk D ir įvesk ${fmt(2 * r)}).`;
        } else {
          const artimi = [...new Set(a.r.filter(x => Math.abs(x - r) <= Math.max(2, r * 0.3) && Math.abs(x - r) > TOL_R).map(x => fmt(2 * x)))];
          if (artimi.length) p += ` Radau ø${artimi.join(", ø")} - patikrink: CIRCLE prašo spindulio (R = ø / 2).`;
        }
        klaidos.push(p);
      }
    }
    for (const tp in t.tipai || {}) {
      const reikia = t.tipai[tp], rasta = sk[tp] || 0;
      if (rasta >= reikia) geri.push(`${rasta} ${VARDAI[tp] || tp}`);
      else klaidos.push(`Per mažai ${VARDAI[tp] || tp}: radau ${rasta}, reikia bent ${reikia}.`);
    }
    if (t.turis) {
      const tikslas = t.turis;
      if (turis == null || Number.isNaN(turis)) {
        klaidos.push("Įvesk kūno tūrį iš AutoCAD: komanda MASSPROP → pažymėk kūną → eilutė Volume.");
      } else if (Math.abs(turis - tikslas) <= tikslas * TOL_V) {
        geri.push(`Tūris ${fmt(turis)} mm³ (turi būti ≈ ${fmt(tikslas)})`);
      } else {
        klaidos.push(`Tūris ${fmt(turis)} mm³, o turi būti ≈ ${fmt(tikslas)} mm³.` +
          (turis > tikslas ? " Tūris per didelis - gal dar neišėmei skylių (SUBTRACT)?" : " Tūris per mažas - ar sujungei cilindrą su plokšte (UNION)?"));
      }
      if (a.solidai > 1) pastabos.push(`Brėžinyje yra ${a.solidai} atskiri 3D kūnai - sujunk juos UNION, skyles išimk SUBTRACT.`);
    }
    return { priimta: klaidos.length === 0, geri, klaidos, pastabos };
  }

  /** Trumpas aprašas „Ką mato tikrinimas“ */
  function aprasas(a) {
    const d = [];
    const v = { LINE: "atkarpos", ARC: "lankai", CIRCLE: "apskritimai", HATCH: "brūkšniavimai", ELLIPSE: "elipsės", INSERT: "blokai", "3DSOLID": "3D kūnai" };
    for (const k of Object.keys(v)) if (a.sk[k]) d.push(`${v[k]}: ${a.sk[k]}`);
    if (a.r.length) {
      const g = {};
      a.r.forEach(x => { const k = fmt(x); g[k] = (g[k] || 0) + 1; });
      d.push("spinduliai: " + Object.entries(g).sort((x, y) => parseFloat(x[0]) - parseFloat(y[0])).map(([k, n]) => `R${k}${n > 1 ? " ×" + n : ""}`).join(", "));
    }
    return d.join(" · ") || "brėžinys tuščias";
  }

  const API = { skaityti, analizuoti, tikrinti, aprasas, nustatytiUzduotis, taisykles: () => TAISYKLES };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  else global.BrTikrinimas = API;
})(this);

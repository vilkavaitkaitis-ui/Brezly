/* Brėžly sąsajos logika (brezly.html). Duomenys ateina iš brezly.py per /api/... */
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
let NUST={}, saugojimoLaikmatis=null;     // nustatymai - saugomi kartu su progresu faile
function sg(k,v){
  if(v===undefined){ let x=null; try{x=localStorage.getItem(k);}catch(e){} return x!==null?x:(NUST[k]??null); }
  try{localStorage.setItem(k,v);}catch(e){}
  if(k!=="cadet"){ NUST[k]=String(v); planuotiSaugojima(); }
}
let NESAUGOTI=false;  /* importuojant progresą: neperrašyti jo senu, kol puslapis persikrauna */
function planuotiSaugojima(dabar){
  clearTimeout(saugojimoLaikmatis); if(NESAUGOTI) return;
  saugojimoLaikmatis=setTimeout(()=>api("/api/progresas",DEMO_S?{nustatymai:NUST}:{S,nustatymai:NUST}).catch(()=>{}),dabar?0:500);
}
let DEMO_S=null;     // demo režimas: tikras progresas laikomas čia, rodomas pavyzdinis
addEventListener("pagehide",()=>{if(NESAUGOTI)return;try{navigator.sendBeacon("/api/progresas?r="+encodeURIComponent(RAKTAS),JSON.stringify(DEMO_S?{nustatymai:NUST}:{S,nustatymai:NUST}));}catch(e){}});
/* sesijos raktas: serveris jį įdeda tik į Brėžly puslapį; be jo /api neatsako (kitos svetainės jo nežino) */
const RAKTAS=document.querySelector('meta[name="brezly-raktas"]')?.content||"";
async function api(kelias,duom){const r=await fetch(kelias,{method:"POST",headers:{"Content-Type":"application/json","X-Brezly-Raktas":RAKTAS},body:JSON.stringify(duom===undefined?{}:duom)});return r.json();}
/* ===== Kalba. Pamokos, užduotys ir tikrinimo pastabos ateina iš serverio jau išverstos;
   sąsajos tekstai verčiami žodynu sasaja_en.json (# - skaičius, {} - tekstas). Neišversti lieka lietuviški. ===== */
const I18N={zod:null,sk:new Map(),sab:[],NUM:/\d+(?:[.,]\d+)?/g,
  async ikelti(){
    if(sg("kalba")!=="en") return;
    try{ const d=await (await fetch("/sasaja_en.json")).json(); this.paruosti(d.tekstai); }catch(e){ return; }
    document.documentElement.lang="en"; this.versti(document.body);
    new MutationObserver(ms=>{ for(const m of ms){
      if(m.type==="characterData") this.mazgas(m.target);
      else if(m.type==="attributes") this.atributai(m.target);
      else m.addedNodes.forEach(n=>this.versti(n)); } })
      .observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:["placeholder","title","aria-label"]});
    const c=window.confirm.bind(window); window.confirm=t=>c(this.vertimas(String(t)));
  },
  paruosti(t){
    this.zod=new Map(); const er=x=>x.replace(/[.*+?^$()|[\]\\]/g,"\\$&");
    for(const [lt,en] of Object.entries(t)){
      if(lt.includes("{}")){ const rusys=[...lt.matchAll(/#|\{\}/g)].map(m=>m[0]);
        const re=new RegExp("^"+lt.split(/(#|\{\})/).map(x=>x==="#"?"(\\d+(?:[.,]\\d+)?)":x==="{}"?"(.+?)":er(x)).join("")+"$");
        this.sab.push({re,rusys,en}); }
      else if(lt.includes("#")) this.sk.set(lt,en);
      else this.zod.set(lt,en);
    }
  },
  vertimas(t){
    if(!this.zod) return t;
    const tr=t.trim(); if(!tr||!/[A-Za-zĄ-ž]/.test(tr)) return t;
    let en=this.zod.get(tr);
    if(en===undefined){ const sk=tr.match(this.NUM); if(sk){ const e=this.sk.get(tr.replace(this.NUM,"#")); if(e!==undefined){ let i=0; en=e.replace(/#/g,()=>sk[i++]); } } }
    if(en===undefined) for(const s of this.sab){ const m=tr.match(s.re); if(!m) continue;
      const sk=[],tx=[]; s.rusys.forEach((r,j)=>(r==="#"?sk:tx).push(m[j+1])); let a=0,b=0;
      en=s.en.replace(/#|\{\}/g,x=>x==="#"?sk[a++]:this.vertimas(tx[b++])); break; }
    if(en===undefined&&tr.includes(", ")){ const d=tr.split(", ").map(x=>this.vertimas(x)); if(d.join(", ")!==tr) en=d.join(", "); }   // sąrašai
    return en===undefined?t:t.replace(tr,en);
  },
  mazgas(n){ if(n.nodeType!==3||(n.parentNode&&(/^(SCRIPT|STYLE|TEXTAREA|CODE)$/.test(n.parentNode.nodeName)||n.parentNode.closest?.('[translate="no"]')))) return;
    const v=this.vertimas(n.nodeValue); if(v!==n.nodeValue) n.nodeValue=v; },
  atributai(e){ if(e.nodeType!==1||e.closest('[translate="no"]')) return; for(const a of ["placeholder","title","aria-label"]){ const v=e.getAttribute(a); if(v){ const w=this.vertimas(v); if(w!==v) e.setAttribute(a,w); } } },
  versti(sakn){ if(!this.zod||!sakn) return;
    if(sakn.nodeType===3){ this.mazgas(sakn); return; } if(sakn.nodeType!==1) return;
    this.atributai(sakn); sakn.querySelectorAll("[placeholder],[title],[aria-label]").forEach(e=>this.atributai(e));
    const w=document.createTreeWalker(sakn,NodeFilter.SHOW_TEXT); let n; while((n=w.nextNode())) this.mazgas(n); }
};

/* Sąsajos klaidos -> brezly.log (Dokumentai\Brezly), kad „Pranešti apie klaidą“ ataskaitoje jos būtų */
const JS_KLAIDOS={n:0,matytos:new Set()};
function uzrasytiKlaida(zinute,vieta,deklas){
  try{
    const raktas=String(zinute).slice(0,200)+"|"+vieta;
    if(JS_KLAIDOS.n>=20||JS_KLAIDOS.matytos.has(raktas)) return;
    JS_KLAIDOS.n++; JS_KLAIDOS.matytos.add(raktas);
    fetch("/api/js_klaida",{method:"POST",headers:{"Content-Type":"application/json","X-Brezly-Raktas":RAKTAS},
      body:JSON.stringify({zinute:String(zinute).slice(0,500),vieta:String(vieta||"").slice(0,200),
        deklas:String(deklas||"").slice(0,1500),rodinys:typeof rodinys!=="undefined"?rodinys:""})}).catch(()=>{});
  }catch(e){}
}
window.addEventListener("error",e=>uzrasytiKlaida(e.message,(e.filename||"").split("/").pop()+":"+e.lineno+":"+e.colno,e.error&&e.error.stack));
window.addEventListener("unhandledrejection",e=>uzrasytiKlaida("Promise: "+((e.reason&&e.reason.message)||e.reason),"",e.reason&&e.reason.stack));
function pranesti(t){const p=$("#pranesimas");p.textContent=t;p.classList.add("rodo");clearTimeout(p._t);p._t=setTimeout(()=>p.classList.remove("rodo"),2600);}

const LYGIAI=[[0,"Naujokas"],[100,"Kadetas"],[250,"Braižytojas"],[450,"Konstruktorius"],[700,"Inžinierius"]];
const ZENKLELIAI={pirmas:"🎯 Pirmas žingsnis",be_uzuominu:"🧠 Be užuominų",detale:"🏆 Pirmoji 3D detalė",testas:"📝 Testas 100%",praktikas:"📐 Praktikas"};
let INFO=null, PAM=null;
let S={xp:0,atlikta:{},praktika:{},zenkleliai:[],dabartinis:{},eq:null,matyti:null,nauji:[],dienos:[],vardas:"",savininkas:""};   // progresas
let uzuominuRodyta=0, demo=false, bandymai=0, tikrina=false, paskutinisAtsakas=null;

function saugoti(){ if(DEMO_S) return; sg("cadet",JSON.stringify(S)); planuotiSaugojima();}
function ikelti(){try{const t=sg("cadet");if(t)S=Object.assign(S,JSON.parse(t));}catch(e){}}

/* ---------- XP ir lygiai ---------- */
function lygis(xp){let i=0;LYGIAI.forEach((l,j)=>{if(xp>=l[0])i=j;});return i;}
function piestiZaideja(){
  const i=lygis(S.xp), [nuo,pav]=LYGIAI[i], kitas=LYGIAI[i+1];
  if(S.eq){ $("#avataras").innerHTML=robotoSVG(S.eq); $("#avataras").style.cssText=fonoStilius(S.eq,true); $("#gidoRobotas").innerHTML=robotoSVG(S.eq); }
  $("#robotoVardas").textContent=personazoVardas();
  $("#naujiTaskelis").classList.toggle("hidden",!(S.nauji&&S.nauji.length));
  $("#lygNr").textContent=`${i+1} lygis`; $("#lygPav").textContent=pav; $("#xpTekstas").textContent=`${S.xp} XP`;
  $("#xpJuosta").style.width = kitas ? `${Math.round((S.xp-nuo)/(kitas[0]-nuo)*100)}%` : "100%";
  $("#vXP").textContent=`${S.xp} XP · ${i+1} lygis`;
  $("#ikiKito").textContent = kitas ? `Iki „${kitas[1]}“: ${kitas[0]-S.xp} XP` : "Aukščiausias lygis!";
  const xd=document.querySelector(".xp-deze"); if(xd) xd.title=$("#ikiKito").textContent;
  $("#zenkleliai").innerHTML=Object.entries(ZENKLELIAI).map(([k,p])=>`<span class="zenklelis ${S.zenkleliai.includes(k)?"":"uzr"}" title="${S.zenkleliai.includes(k)?"Gautas":"Dar negautas"}">${p}</span>`).join("");
}
function pridetiXP(kiek,el){
  if(kiek<=0)return;
  const pries=lygis(S.xp); S.xp+=kiek; saugoti(); piestiZaideja();
  const r=(el||$("#vidus")).getBoundingClientRect();
  const s=document.createElement("div"); s.className="skrenda"; s.textContent=`+${kiek} XP`;
  const z=parseFloat(document.body.style.zoom)||1;
  s.style.left=((r.left+r.width/2)/z-40)+"px"; s.style.top=(r.top/z-10)+"px"; document.body.appendChild(s); setTimeout(()=>s.remove(),1400);
  if(lygis(S.xp)>pries){ setTimeout(()=>{pranesti(`🎉 Naujas lygis: ${LYGIAI[lygis(S.xp)][1]}!`);konfeti(60);Robotas.reaguoti("lygis",3200);},700); }
  pazymetiDiena(); tikrintiAtlygiusVeliau();
}
function duotiZenkleli(k){ if(!S.zenkleliai.includes(k)){S.zenkleliai.push(k);saugoti();piestiZaideja();setTimeout(()=>pranesti(`Naujas ženklelis: ${ZENKLELIAI[k]}`),900);tikrintiAtlygiusVeliau();} }


/* =================== GYVAS ROBOTUKAS =================== */
const Robotas={
  laik:null,
  jungtas(){ return sg("judesys")!=="0"; },
  taikyti(){ document.body.classList.toggle("nejuda",!this.jungtas()); },
  reaguoti(busena,ms){
    if(!this.jungtas()) return;
    document.querySelectorAll(".gyvas").forEach(el=>{
      el.classList.remove("rob-dziaug","rob-liud","rob-kalba","rob-moja","rob-lygis"); void el.offsetWidth; el.classList.add("rob-"+busena);
      clearTimeout(el._rt); el._rt=setTimeout(()=>el.classList.remove("rob-"+busena),ms||1500);
    });
  },
  kalbeti(html){
    const el=$("#gidoRobotas"); if(!el||!this.jungtas()) return;
    const zod=String(html||"").replace(/<[^>]+>/g," ").split(/\s+/).filter(Boolean).length;
    el.classList.remove("rob-liud"); el.classList.add("rob-kalba");
    clearTimeout(el._kt); el._kt=setTimeout(()=>el.classList.remove("rob-kalba"),Math.min(4500,600+zod*170));
  },
  // akys seka pelę
  _x:0,_y:0,_lauk:false,
  pele(e){ this._x=e.clientX; this._y=e.clientY; if(this._lauk) return; this._lauk=true; requestAnimationFrame(()=>{ this._lauk=false; this.akys(); }); },
  akys(){
    document.querySelectorAll(".gyvas svg").forEach(svg=>{
      const r=svg.getBoundingClientRect(); if(!r.width) return;
      const cx=r.left+r.width/2, cy=r.top+r.height*0.47, dx=this._x-cx, dy=this._y-cy, d=Math.hypot(dx,dy)||1;
      const k=Math.min(1,d/220)*4.2;             // iki ~4 SVG vienetų
      svg.style.setProperty("--px",(dx/d*k).toFixed(2)+"px"); svg.style.setProperty("--py",(dy/d*k).toFixed(2)+"px");
    });
  },
  pradeti(){
    this.taikyti();
    addEventListener("mousemove",e=>this.pele(e),{passive:true});
    setInterval(()=>{ if(document.hidden||Math.random()<0.5) return; this.reaguoti("moja",1900); },26000);   // kartais pamoja
  }
};

/* =================== PERSONAŽAS IR DAIKTAI (1.4: Bauhaus personažai) =================== */
const BH={R:"#e2362b",Y:"#ffc400",B:"#1f4fd1",K:"#111111",P:"#f7f5f0",A:"#d9a520"};
/* Spalvų rinkiniai sukeičia personažo Bauhaus spalvas: kuri spalva tampa kuria.
   id - iš senesnių versijų, kad išsaugoti pasirinkimai liktų. */
const SPALVOS={zydra:{R:"R",Y:"Y",B:"B"},gintaras:{R:"Y",Y:"B",B:"R"},violetine:{R:"B",Y:"R",B:"Y"},auksas:{R:"B",Y:"A",B:"R"}};
/* tamsus - personažo savo spalva (iš dizaino); c - fono spalva, t - tinklelis, s - saulė, z - žvaigždės */
const FONAI={tamsus:{},tinklelis:{c:"P",t:true},saulelydis:{c:"R",s:true},kosmosas:{c:"K",z:true}};
/* Vardai - pagal AutoCAD komandas (nuo 1.4; seni vardai - SENI_VARDAI) */
const PERSONAZAI=[
  {id:"robotas",pav:"Robotas",forma:"Robotas · kvadratas",vardas:"Kadis",txt:"Antena gaudo kiekvieną AutoCAD komandą",fonas:"B"},
  {id:"katinas",pav:"Katinas",forma:"Katinas · apskritimas",vardas:"Kursorius",txt:"Gaudo pelę - ir tikrą, ir kompiuterio",fonas:"Y"},
  {id:"peleda",pav:"Pelėda",forma:"Pelėda · kupolas",vardas:"Snapas",txt:"Kaip OSNAP - pataiko tiksliai į tašką",fonas:"P"},
  {id:"lape",pav:"Lapė",forma:"Lapė · trikampis",vardas:"Trimas",txt:"Gudrus - nukerpa viską, kas nereikalinga",fonas:"K"},
  {id:"drakonas",pav:"Drakoniukas",forma:"Drakoniukas · kvadratas",vardas:"Ekstrudas",txt:"Vienu kvėptelėjimu iškelia 2D į 3D",fonas:"R"},
  {id:"ateivis",pav:"Ateivis",forma:"Ateivis · kapsulė",vardas:"Orbitas",txt:"Atskrido per 3DORBIT išmokti AutoCAD",fonas:"P"},
  {id:"pingvinas",pav:"Pingvinas",forma:"Pingvinas · ovalas",vardas:"Elipsas",txt:"Ramus ir apvalus kaip ELLIPSE",fonas:"B"},
  {id:"meska",pav:"Meškiukas",forma:"Meškiukas · apskritimai",vardas:"Dimas",txt:"Stiprus ir kantrus - viską išmatuoja",fonas:"Y"},
];
const SENI_VARDAI={robotas:"Robis",katinas:"Murkis",peleda:"Pelėdžius",lape:"Lapis",drakonas:"Drakis",ateivis:"Zūmas",pingvinas:"Ledukas",meska:"Meškis"};
const personazas=id=>PERSONAZAI.find(p=>p.id===id)||PERSONAZAI[0];
const personazoVardas=()=>S.vardas||personazas(S.eq&&S.eq.personazas).vardas;
const KATEGORIJOS=[["personazas","Personažas"],["galva","Galva"],["akys","Akys"],["kaklas","Kaklas"],["ranka","Rankoje"],["spalva","Spalva"],["fonas","Fonas"]];
const PRADINIS={personazas:"robotas",galva:null,akys:null,kaklas:null,ranka:null,spalva:"zydra",fonas:"tamsus"};
/* ar(b) - b: {lyg, zen[], pamokos, serija} */
const DAIKTAI=[
  ...PERSONAZAI.map(p=>({id:p.id,kat:"personazas",pav:p.pav,txt:p.txt,ar:b=>true})),
  {id:"kepure",kat:"galva",pav:"Absolvento kepurė",txt:"Pradinis daiktas",ar:b=>true},
  {id:"ausines",kat:"galva",pav:"Ausinės",txt:"Baik 2 pamokas",ar:b=>b.pamokos>=2},
  {id:"salmas",kat:"galva",pav:"Statybininko šalmas",txt:"3 lygis „Braižytojas“",ar:b=>b.lyg>=3,retas:true},
  {id:"karuna",kat:"galva",pav:"Inžinieriaus karūna",txt:"5 lygis „Inžinierius“",ar:b=>b.lyg>=5,retas:true},
  {id:"akiniai",kat:"akys",pav:"Protingi akiniai",txt:"Ženklelis „Be užuominų“",ar:b=>b.zen.includes("be_uzuominu")},
  {id:"saules",kat:"akys",pav:"Saulės akiniai",txt:"Ženklelis „Testas 100%“",ar:b=>b.zen.includes("testas")},
  {id:"monoklis",kat:"akys",pav:"Monoklis",txt:"4 lygis „Konstruktorius“",ar:b=>b.lyg>=4,retas:true},
  {id:"varlyte",kat:"kaklas",pav:"Varlytė",txt:"Ženklelis „Pirmoji 3D detalė“",ar:b=>b.zen.includes("detale")},
  {id:"salikas",kat:"kaklas",pav:"Šalikas",txt:"Mokykis 3 dienas iš eilės",ar:b=>b.serija>=3},
  {id:"piestukas",kat:"ranka",pav:"Pieštukas",txt:"Pradinis daiktas",ar:b=>true},
  {id:"skriestuvas",kat:"ranka",pav:"Skriestuvas",txt:"Baik bet kurią pamoką",ar:b=>b.pamokos>=1},
  {id:"liniuote",kat:"ranka",pav:"Liniuotė",txt:"3 lygis „Braižytojas“",ar:b=>b.lyg>=3},
  {id:"slankmatis",kat:"ranka",pav:"Slankmatis",txt:"Baik 3 pamokas",ar:b=>b.pamokos>=3,retas:true},
  {id:"zydra",kat:"spalva",pav:"Klasika",txt:"Pradinė spalva",ar:b=>true},
  {id:"gintaras",kat:"spalva",pav:"Spalvų ratas",txt:"2 lygis „Kadetas“",ar:b=>b.lyg>=2},
  {id:"violetine",kat:"spalva",pav:"Atvirkštinis ratas",txt:"3 lygis „Braižytojas“",ar:b=>b.lyg>=3},
  {id:"auksas",kat:"spalva",pav:"Auksinė",txt:"5 lygis „Inžinierius“",ar:b=>b.lyg>=5,retas:true},
  {id:"tamsus",kat:"fonas",pav:"Savo spalva",txt:"Pradinis fonas",ar:b=>true},
  {id:"tinklelis",kat:"fonas",pav:"Brėžinio tinklelis",txt:"2 lygis „Kadetas“",ar:b=>b.lyg>=2},
  {id:"saulelydis",kat:"fonas",pav:"Saulėlydis",txt:"4 lygis „Konstruktorius“",ar:b=>b.lyg>=4},
  {id:"kosmosas",kat:"fonas",pav:"Kosmosas",txt:"Surink visus 4 ženklelius",ar:b=>Object.keys(ZENKLELIAI).every(z=>b.zen.includes(z)),retas:true},
];
const daiktas=id=>DAIKTAI.find(d=>d.id===id);

function pamokuBaigta(){ return INFO ? INFO.pamokos.filter(p=>(S.atlikta[p.id]||[]).length>=p.zingsniai.length).length : 0; }
function dienaStr(d){ return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0"); }
function serija(){
  const set=new Set(S.dienos||[]); let n=0; const d=new Date();
  if(!set.has(dienaStr(d))) d.setDate(d.getDate()-1);
  while(set.has(dienaStr(d))){ n++; d.setDate(d.getDate()-1); }
  return n;
}
function pazymetiDiena(){ const t=dienaStr(new Date()); S.dienos=S.dienos||[]; if(!S.dienos.includes(t)){S.dienos.push(t);saugoti();} }
function busenaAtrakinimui(){ return {lyg:lygis(S.xp)+1, zen:S.zenkleliai, pamokos:pamokuBaigta(), serija:serija()}; }
function atrakinti(){ const b=busenaAtrakinimui(); return DAIKTAI.filter(d=>d.ar(b)).map(d=>d.id); }

function spalvosRinkinys(eq){ const p=SPALVOS[eq&&eq.spalva]||SPALVOS.zydra; return v=>BH[p[v]||v]; }
function plytelesSpalva(eq){
  const f=FONAI[eq&&eq.fonas]||FONAI.tamsus;
  return f.c ? BH[f.c] : spalvosRinkinys(eq)(personazas(eq&&eq.personazas).fonas);
}
/* fono CSS: eq - personažo apranga (fonas priklauso nuo personažo ir jo spalvų) */
function fonoStilius(eq,mazas){
  const f=FONAI[eq&&eq.fonas]||FONAI.tamsus, d=mazas?10:24;
  let st=`background-color:${plytelesSpalva(eq)};`;
  if(f.t) st+=`background-image:linear-gradient(rgba(17,17,17,.13) 1px,transparent 1px),linear-gradient(90deg,rgba(17,17,17,.13) 1px,transparent 1px);background-size:${d}px ${d}px;`;
  if(f.s) st+=`background-image:radial-gradient(circle at 50% 100%,${BH.Y} 0 36%,transparent 36%);`;
  if(f.z) st+=`background-image:radial-gradient(circle at 18% 22%,${BH.P} 0 1.5px,transparent 2px),radial-gradient(circle at 78% 18%,${BH.Y} 0 2.5px,transparent 3px),radial-gradient(circle at 84% 74%,${BH.R} 0 2px,transparent 2.5px),radial-gradient(circle at 30% 82%,${BH.B} 0 2.5px,transparent 3px),radial-gradient(circle at 55% 48%,${BH.P} 0 1px,transparent 1.5px);background-size:${mazas?44:120}px ${mazas?44:120}px;`;
  return st;
}
/* =================== PERSONAŽAI (pagal dizainą „Personažai · Bauhaus“, viewBox 0 0 160 160) ===================
   c(v): "R","Y","B" - pagal spalvų rinkinį, BH.K ir BH.P nesikeičia.
   akys [{x,y,r}], akis(e) - viena akis (vyzdys .r-vyzd seka pelę), m {x,y,w} - kur piešiamos nuotaikų burnos,
   ak - nuotaikų akių spalva, bk/lk - burnos užpildas/linija, veidas0 - veido spalva po akimis,
   isore - kontūro spalvos (jei fonas tokios pat spalvos - personažas apvedamas),
   virsus/plotis - galvos daiktams, ausys [x kairė, x dešinė, y] - ausinėms, kaklas {y,w}, ranka {x,y,f - veidrodiškai} */
function personazoDalys(p,c){
  const K=BH.K, P=BH.P;
  if(p==="katinas") return {
    galva:`<path d="M34 66 L44 14 L76 46 Z" fill="${K}"/><path d="M126 66 L116 14 L84 46 Z" fill="${K}"/><circle cx="80" cy="88" r="52" fill="${c("B")}"/>`,
    akys:[{x:60,y:80,r:13},{x:100,y:80,r:13}],
    akis:e=>`<circle cx="${e.x}" cy="${e.y}" r="13" fill="${c("Y")}"/><g class="r-vyzd"><rect x="${e.x-3}" y="${e.y-11}" width="6" height="22" fill="${K}"/></g>`,
    veidas:`<path d="M72 100 H88 L80 110 Z" fill="${c("R")}"/><path d="M8 98 H54 M8 112 L54 106 M106 98 H152 M106 106 L152 112" stroke="${K}" stroke-width="3"/>`,
    m:{x:80,y:114,w:20}, ak:c("Y"), bk:c("R"), lk:K, veidas0:c("B"), isore:["K","B"],
    virsus:36, plotis:70, ausys:[30,130,88], kaklas:{y:140,w:40}, ranka:{x:146,y:132}};
  if(p==="peleda") return {
    galva:`<path d="M30 40 L48 10 L58 44 Z" fill="${K}"/><path d="M130 40 L112 10 L102 44 Z" fill="${K}"/><path d="M26 150 V80 A54 54 0 0 1 134 80 V150 Z" fill="${c("R")}"/><path d="M44 124 H116 M50 138 H110" stroke="${P}" stroke-width="4"/>`,
    akys:[{x:58,y:76,r:22},{x:102,y:76,r:22}],
    akis:e=>`<circle cx="${e.x}" cy="${e.y}" r="22" fill="${c("Y")}"/><g class="r-vyzd"><circle cx="${e.x}" cy="${e.y}" r="10" fill="${K}"/></g>`,
    veidas:`<path d="M72 96 H88 L80 112 Z" fill="${K}"/>`,
    m:{x:80,y:112,w:18}, ak:c("Y"), bk:c("Y"), lk:K, veidas0:c("R"), isore:["K","R"],
    virsus:26, plotis:80, ausys:[26,134,96], kaklas:{y:118,w:40}, ranka:{x:148,y:132}};
  if(p==="lape") return {
    galva:`<path d="M20 50 L36 8 L62 46 Z" fill="${c("R")}"/><path d="M140 50 L124 8 L98 46 Z" fill="${c("R")}"/><path d="M14 44 H146 L80 150 Z" fill="${c("R")}"/><path d="M50 92 L80 150 L110 92 Z" fill="${P}"/>`,
    akys:[{x:55,y:69,r:7},{x:105,y:69,r:7}],
    akis:e=>`<g class="r-vyzd"><rect x="${e.x-7}" y="${e.y-7}" width="14" height="14" fill="${K}"/></g>`,
    veidas:`<circle cx="80" cy="140" r="8" fill="${K}"/>`,
    m:{x:80,y:110,w:18}, ak:K, bk:c("R"), lk:K, veidas0:c("R"), isore:["R"],
    virsus:44, plotis:96, ausys:[24,136,62], kaklas:{y:152,w:30}, ranka:{x:146,y:132}};
  if(p==="drakonas") return {
    uz:`<path d="M44 44 A40 40 0 0 0 4 84 H44 Z" fill="${c("Y")}"/><path d="M116 44 A40 40 0 0 1 156 84 H116 Z" fill="${c("Y")}"/><path d="M120 124 L148 150 L120 150 Z" fill="${c("B")}"/>`,
    galva:`<path d="M44 40 L56 18 L68 40 Z M68 40 L80 14 L92 40 Z M92 40 L104 18 L116 40 Z" fill="${K}"/><rect x="40" y="40" width="80" height="84" fill="${c("B")}"/>`,
    akys:[{x:62,y:74,r:11},{x:98,y:74,r:11}],
    akis:e=>`<circle cx="${e.x}" cy="${e.y}" r="11" fill="${P}"/><g class="r-vyzd"><circle cx="${e.x+2}" cy="${e.y+2}" r="6" fill="${K}"/></g>`,
    burna:`<rect x="52" y="100" width="56" height="14" fill="${K}"/><path d="M58 100 L64 108 L70 100 Z M90 100 L96 108 L102 100 Z" fill="${P}"/>`,
    m:{x:80,y:100,w:36}, ak:P, bk:K, lk:K, veidas0:c("B"), isore:["K","B","Y"],
    virsus:40, plotis:80, ausys:[40,120,80], kaklas:{y:126,w:40}, ranka:{x:18,y:132,f:1}};
  if(p==="ateivis") return {
    antena:`<path d="M58 34 L44 6 M102 34 L116 6" stroke="${K}" stroke-width="4"/><circle cx="44" cy="8" r="8" fill="${c("Y")}"/><circle cx="116" cy="8" r="8" fill="${c("Y")}"/>`,
    galva:`<rect x="38" y="26" width="84" height="124" rx="42" fill="${c("B")}"/>`,
    akys:[{x:80,y:74,r:28}],
    akis:e=>`<circle cx="${e.x}" cy="${e.y}" r="28" fill="${P}"/><g class="r-vyzd"><circle cx="${e.x}" cy="${e.y}" r="16" fill="${c("R")}"/><circle cx="${e.x}" cy="${e.y}" r="7" fill="${K}"/></g>`,
    burna:`<rect x="64" y="116" width="32" height="6" fill="${K}"/>`,
    m:{x:80,y:114,w:30}, ak:P, bk:c("R"), lk:K, veidas0:c("B"), isore:["B","K"],
    virsus:26, plotis:72, ausys:[38,122,84], kaklas:{y:138,w:44}, ranka:{x:146,y:132}};
  if(p==="pingvinas") return {
    galva:`<ellipse cx="80" cy="88" rx="50" ry="66" fill="${K}"/><ellipse cx="80" cy="98" rx="34" ry="50" fill="${P}"/>`,
    akys:[{x:66,y:66,r:6},{x:94,y:66,r:6}],
    akis:e=>`<g class="r-vyzd"><circle cx="${e.x}" cy="${e.y}" r="6" fill="${K}"/></g>`,
    veidas:`<path d="M68 78 H92 L80 94 Z" fill="${c("Y")}"/>`,
    kaklasSav:`<rect x="34" y="112" width="92" height="12" fill="${c("R")}"/><rect x="96" y="112" width="12" height="30" fill="${c("R")}"/>`,
    m:{x:80,y:97,w:18}, ak:K, bk:c("R"), lk:K, veidas0:P, isore:["K"],
    virsus:22, plotis:62, ausys:[32,128,70], kaklas:{y:118,w:64}, ranka:{x:146,y:132}};
  if(p==="meska") return {
    galva:`<circle cx="40" cy="38" r="20" fill="${K}"/><circle cx="120" cy="38" r="20" fill="${K}"/><circle cx="40" cy="38" r="9" fill="${c("R")}"/><circle cx="120" cy="38" r="9" fill="${c("R")}"/><circle cx="80" cy="78" r="50" fill="${K}"/><circle cx="80" cy="92" r="22" fill="${P}"/>`,
    akys:[{x:60,y:66,r:6},{x:100,y:66,r:6}],
    akis:e=>`<g class="r-vyzd"><circle cx="${e.x}" cy="${e.y}" r="6" fill="${P}"/></g>`,
    veidas:`<path d="M72 84 H88 L80 94 Z" fill="${K}"/>`,
    kaklasSav:`<path d="M80 138 L56 126 V150 Z M80 138 L104 126 V150 Z" fill="${c("B")}"/><rect x="74" y="132" width="12" height="12" fill="${c("R")}"/>`,
    m:{x:80,y:99,w:16}, ak:P, bk:c("R"), lk:K, veidas0:K, isore:["K"],
    virsus:28, plotis:62, ausys:[30,130,74], kaklas:{y:138,w:48}, ranka:{x:146,y:132}};
  return {     // robotas
    antena:`<rect x="76" y="14" width="8" height="22" fill="${K}"/><circle cx="80" cy="14" r="9" fill="${c("R")}"/>`,
    galva:`<rect x="22" y="62" width="12" height="28" fill="${K}"/><rect x="126" y="62" width="12" height="28" fill="${K}"/><rect x="34" y="36" width="92" height="80" fill="${c("Y")}"/>`,
    akys:[{x:60,y:72,r:12},{x:100,y:72,r:12}],
    akis:e=>`<circle cx="${e.x}" cy="${e.y}" r="12" fill="${K}"/><g class="r-vyzd"><circle cx="${e.x+3}" cy="${e.y-3}" r="4" fill="${P}"/></g>`,
    burna:`<path d="M62 94 A18 18 0 0 0 98 94 Z" fill="${c("R")}"/>`,
    kunas:`<path d="M40 160 L52 124 H108 L120 160 Z" fill="${K}"/>`,
    m:{x:80,y:94,w:36}, ak:K, bk:c("R"), lk:K, veidas0:c("Y"), isore:["K","Y"],
    virsus:36, plotis:92, ausys:[28,132,76], kaklas:{y:120,w:44}, ranka:{x:146,y:132}};
}
const PAKAITAS={[BH.Y]:BH.R,[BH.R]:BH.Y,[BH.B]:BH.Y,[BH.P]:BH.K,[BH.K]:BH.P};
const ne=(spalva,fonas)=>spalva===fonas?PAKAITAS[spalva]:spalva;      // daikto spalva neturi susilieti su fonu
const zvaigzde=(x,y,R)=>{ const q=R*.32; return `M${x} ${y-R} L${x+q} ${y-q} L${x+R} ${y} L${x+q} ${y+q} L${x} ${y+R} L${x-q} ${y+q} L${x-R} ${y} L${x-q} ${y-q} Z`; };
const KARUNA=(I,F)=>{ const y=ne(BH.Y,F); return `<path d="M10 74 L16 28 L34 50 L50 20 L66 50 L84 28 L90 74 Z" fill="${y}"/><rect x="10" y="64" width="80" height="10" fill="${I}"/><circle cx="50" cy="52" r="7" fill="${y===BH.R?BH.B:BH.R}"/>`; };
/* galvos daiktas: grąžina {svg, virsus} - virsus reikalingas, kad viskas tilptų į lapą */
function galvosDaiktas(g,z,I,ausAntena,F){
  const top=z.virsus, w=z.plotis;
  const dek=(s,ax,ay,turinys)=>({svg:`<g transform="translate(${(80-ax*s).toFixed(2)} ${(ay).toFixed(2)}) scale(${s.toFixed(3)})">${turinys}</g>`});
  if(g==="kepure"){ const s=w/80, y=top+8-72*s;
    return {...dek(s,50,y,`<path d="M50 16 L96 36 L50 56 L4 36 Z" fill="${I}"/><rect x="26" y="46" width="48" height="26" fill="${I}"/><rect x="86" y="38" width="4" height="30" fill="${ne(BH.R,F)}"/><rect x="82" y="66" width="12" height="12" fill="${ne(BH.R,F)}"/>`), virsus:y+16*s}; }
  if(g==="salmas"){ const s=w/76, y=top+10-74*s;
    return {...dek(s,50,y,`<path d="M14 66 A36 36 0 0 1 86 66 Z" fill="${ne(BH.Y,F)}"/><rect x="6" y="64" width="88" height="10" fill="${I}"/><rect x="46" y="30" width="8" height="34" fill="${I}"/>`), virsus:y+30*s}; }
  if(g==="karuna"){ const s=w/86, y=top+6-74*s;
    return {...dek(s,50,y,KARUNA(I,F)), virsus:y+20*s}; }
  if(g==="ausines"){ const [L,R,cy]=z.ausys, r=(R-L)/2, a=Math.min(cy,top-8+r), ks=[BH.B,BH.R,BH.Y].find(x=>x!==F&&x!==z.veidas0);
    return {svg:`<path d="M${L} ${cy} V${a} A${r} ${r} 0 0 1 ${R} ${a} V${cy}" fill="none" stroke="${I}" stroke-width="8"/><rect x="${L-10}" y="${cy-16}" width="20" height="32" fill="${ks}"/><rect x="${R-10}" y="${cy-16}" width="20" height="32" fill="${ks}"/>`, virsus:Math.min(a-r-4,ausAntena)}; }
  return {svg:"",virsus:ausAntena};
}
function akiuDaiktas(a,z){
  const E=z.akys, fr=z.veidas0===BH.K?BH.P:BH.K, [L,R]=z.ausys;
  const rr=e=>e.r+(e.r>15?4:7);
  if(a==="akiniai"){
    let s=E.map(e=>`<circle cx="${e.x}" cy="${e.y}" r="${rr(e)}" fill="none" stroke="${fr}" stroke-width="5"/>`).join("");
    if(E.length===2){ const x1=E[0].x+rr(E[0]), x2=E[1].x-rr(E[1]); if(x2>x1) s+=`<rect x="${x1}" y="${E[0].y-2.5}" width="${x2-x1}" height="5" fill="${fr}"/>`; }
    else s+=`<path d="M${L+6} ${E[0].y} H${E[0].x-rr(E[0])} M${E[0].x+rr(E[0])} ${E[0].y} H${R-6}" stroke="${fr}" stroke-width="5"/>`;
    return s;
  }
  if(a==="saules"){
    const st=fr===BH.P?BH.B:BH.K;
    if(E.length===1){ const e=E[0], h=e.r*.9; return `<rect x="${L+4}" y="${e.y-h}" width="${R-L-8}" height="${h*1.6}" fill="${st}"/><rect x="${L+14}" y="${e.y-h+6}" width="${(R-L)*.3}" height="5" fill="${BH.P}"/>`; }
    let s=E.map(e=>{ const R2=rr(e), h=R2*.8; return `<rect x="${e.x-R2}" y="${e.y-h}" width="${R2*2}" height="${h*1.7}" fill="${st}"/><rect x="${e.x-R2+4}" y="${e.y-h+4}" width="${R2*.7}" height="4" fill="${BH.P}"/>`; }).join("");
    const x1=E[0].x+rr(E[0]), x2=E[1].x-rr(E[1]); if(x2>x1) s+=`<rect x="${x1}" y="${E[0].y-rr(E[0])*.8}" width="${x2-x1}" height="5" fill="${st}"/>`;
    return s;
  }
  if(a==="monoklis"){ const e=E[E.length-1], R2=rr(e)+1, y=ne(BH.Y,z.veidas0);
    return `<circle cx="${e.x}" cy="${e.y}" r="${R2}" fill="none" stroke="${y}" stroke-width="4"/><path d="M${e.x+R2*.7} ${e.y+R2*.7} Q${e.x+R2+10} ${e.y+R2+6} ${e.x+R2+4} ${e.y+R2+28}" fill="none" stroke="${y}" stroke-width="2.5"/>`; }
  return "";
}
function kakloDaiktas(k,z,I,F){
  const {y,w}=z.kaklas;
  if(k==="varlyte"){ const s=w/48;
    return `<path d="M80 ${y} L${80-24*s} ${y-12*s} V${y+12*s} Z M80 ${y} L${80+24*s} ${y-12*s} V${y+12*s} Z" fill="${ne(BH.B,F)}"/><rect x="${80-6*s}" y="${y-6*s}" width="${12*s}" height="${12*s}" fill="${ne(BH.R,F)}"/>`; }
  if(k==="salikas"){ const sl=ne(BH.Y,F); return `<rect x="${80-w/2}" y="${y-6}" width="${w}" height="12" fill="${sl}"/><rect x="${80+w/2-18}" y="${y-6}" width="12" height="32" fill="${sl}"/><rect x="${80+w/2-18}" y="${y+14}" width="12" height="4" fill="${I}"/><rect x="${80+w/2-18}" y="${y+21}" width="12" height="4" fill="${I}"/>`; }
  return z.kaklasSav||"";
}
function rankosDaiktas(r,z,I,F){
  const {x,y,f}=z.ranka, s=.6, Y=ne(BH.Y,F), R=ne(BH.R,F), B=ne(BH.B,F);
  const D={
    piestukas:`<rect x="40" y="10" width="20" height="62" fill="${Y}"/><rect x="40" y="10" width="20" height="10" fill="${R}"/><path d="M40 72 H60 L50 94 Z" fill="${BH.P}" stroke="${I}" stroke-width="3"/><path d="M46 85 H54 L50 94 Z" fill="${I}"/>`,
    skriestuvas:`<path d="M50 22 L24 90 M50 22 L76 90" stroke="${I}" stroke-width="7"/><circle cx="50" cy="20" r="9" fill="${R}"/><rect x="47" y="2" width="6" height="12" fill="${I}"/><path d="M72 80 L82 80 L77 94 Z" fill="${B}"/>`,
    liniuote:`<g transform="rotate(90 50 50)"><rect x="8" y="38" width="84" height="24" fill="${B}"/><path d="M18 38 V50 M28 38 V46 M38 38 V50 M48 38 V46 M58 38 V50 M68 38 V46 M78 38 V50" stroke="${BH.P}" stroke-width="3"/></g>`,
    slankmatis:`<rect x="44" y="4" width="12" height="90" fill="${B}"/><rect x="56" y="4" width="32" height="12" fill="${I}"/><rect x="56" y="42" width="26" height="12" fill="${I}"/><path d="M44 68 H52 M44 76 H50 M44 84 H52" stroke="${BH.P}" stroke-width="2.5"/>`,
  }[r];
  if(!D) return "";
  const t=`translate(${x-50*s} ${y-60*s}) scale(${s})`;
  return `<g${f?` transform="translate(${2*x} 0) scale(-1 1)"`:""}><g transform="${t}">${D}</g><circle cx="${x}" cy="${y}" r="7" fill="${I}"/></g>`;
}
/* nuotaikos: įprasta, „lauk“ (laukia), „dziaug“ (priimta), „liud“ (klaida), „kalba“, „lygis“ (naujas lygis).
   Visos nupiešiamos iš karto, rodoma CSS klasėmis: .n-<nuotaika> ant svg arba .rob-<nuotaika> ant .gyvas. */
function nuotaikos(z,arKaruna,I,F){
  const {x,y,w}=z.m, E=z.akys, sw=e=>Math.max(3.5,Math.min(8,e.r*.55));
  const r=w*.72, h=w/2, ak2=E.length>1?E[1]:null;
  return {
    lauk:`<rect class="r-lauk" x="${x-h}" y="${y+2}" width="${w}" height="6" fill="${z.lk}"/>`,
    dziaug:`<path class="r-dz" d="M${x-r} ${y-4} A${r} ${r} 0 0 0 ${x+r} ${y-4} Z" fill="${z.bk}"/>`+
      `<g class="r-dz">${E.map(e=>`<path d="M${e.x-e.r} ${e.y+e.r*.5} A${e.r} ${e.r} 0 0 1 ${e.x+e.r} ${e.y+e.r*.5}" fill="none" stroke="${z.ak}" stroke-width="${sw(e)}"/>`).join("")}</g>`,
    liud:`<path class="r-liud" d="M${x-h} ${y+8} L${x-h/2} ${y+2} L${x} ${y+8} L${x+h/2} ${y+2} L${x+h} ${y+8}" fill="none" stroke="${z.lk}" stroke-width="5"/>`+
      `<g class="r-li">`+(ak2?`<rect x="${ak2.x-ak2.r}" y="${ak2.y-3}" width="${ak2.r*2}" height="${Math.max(4,ak2.r*.55)}" fill="${z.ak===BH.P&&z.veidas0===BH.P?BH.K:z.ak}"/><rect x="${E[0].x-E[0].r-1}" y="${E[0].y-E[0].r-9}" width="${E[0].r*2+2}" height="5" fill="${z.lk===z.veidas0?BH.P:z.lk}" transform="rotate(-10 ${E[0].x} ${E[0].y-E[0].r-7})"/>`
        :`<path d="M${E[0].x-E[0].r} ${E[0].y} A${E[0].r} ${E[0].r} 0 0 1 ${E[0].x+E[0].r} ${E[0].y} Z" fill="${z.veidas0}"/><rect x="${E[0].x-E[0].r}" y="${E[0].y-3}" width="${E[0].r*2}" height="6" fill="${BH.K}"/>`)+`</g>`,
    kalba:`<ellipse class="r-kalba" cx="${x}" cy="${y+6}" rx="${Math.max(6,w*.3)}" ry="7" fill="${z.bk}"/>`,
    lygis:`<circle class="r-ly" cx="${x}" cy="${y+6}" r="${Math.max(6,w*.28)}" fill="${z.lk}"/>`+
      `<g class="r-ly">${E.map(e=>{ const ap=z.ak, zv=ap===BH.K?BH.Y:BH.K; return `<circle cx="${e.x}" cy="${e.y}" r="${e.r}" fill="${ap}"/><path d="${zvaigzde(e.x,e.y,e.r*.85)}" fill="${zv}"/>`; }).join("")}`+
      (arKaruna?(()=>{ const s2=Math.min(z.plotis/100,(z.virsus+8)/56); return `<g transform="translate(${80-50*s2} ${z.virsus+8-74*s2}) scale(${s2})">${KARUNA(I,F)}</g>`; })():"")+`</g>`,
  };
}
/* paveikslėliui (be CSS) - ką paslėpti, kai rodoma viena nuotaika */
const NUOT_SLEPIA={lauk:["r-burna"],dziaug:["r-akys","r-burna"],liud:["r-a1","r-burna"],kalba:["r-burna"],lygis:["r-akys","r-burna"]};
const KONFETI=`<g class="r-konf"><rect x="6" y="54" width="10" height="10" fill="${BH.Y}"/><path d="M138 18 L154 26 L140 38 Z" fill="${BH.R}"/><rect x="144" y="94" width="10" height="10" fill="${BH.B}"/><circle cx="16" cy="118" r="5" fill="${BH.R}"/></g>`;
/* eq - apranga {personazas, galva, akys, kaklas, ranka, spalva, fonas}; o.n - nuotaika (statiškai);
   o.eks - paveikslėliui be CSS: nupiešiama tik o.n nuotaika */
function robotoSVG(eq,o){
  eq=eq||{}; o=o||{};
  const eks=!!o.eks, sl=k=>eks&&(NUOT_SLEPIA[o.n]||[]).includes(k)?' style="display:none"':"";
  const pid=eq.personazas||"robotas", c=spalvosRinkinys(eq), z=personazoDalys(pid,c);
  const g=eq.galva, a=eq.akys, k=eq.kaklas, r=eq.ranka;
  const fonas=plytelesSpalva(eq), I=fonas===BH.K?BH.P:BH.K;
  const antena=z.antena&&(!g||g==="ausines")?z.antena:"";
  const ant0=antena?4:(pid==="peleda"?10:pid==="lape"?8:pid==="drakonas"?14:pid==="katinas"?14:z.virsus);
  const gd=galvosDaiktas(g,z,I,ant0,fonas);
  const k1=gd.virsus<3 ? 157/(160-gd.virsus) : 1;          // kepurė netelpa - visą personažą šiek tiek sumažinam
  const tf=k1<1?` transform="translate(80 160) scale(${k1.toFixed(3)}) translate(-80 -160)"`:"";
  const kontur=z.isore.map(v=>c(v)).includes(fonas) ? (fonas===BH.K||fonas===BH.B?BH.P:BH.K) : null;
  const fid=kontur?(kontur===BH.P?"bhKonturP":"bhKonturK"):"";
  const defs=kontur?`<defs><filter id="${fid}" x="-8%" y="-8%" width="116%" height="116%"><feMorphology in="SourceAlpha" operator="dilate" radius="2.6" result="d"/><feFlood flood-color="${kontur}"/><feComposite in2="d" operator="in"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>`:"";
  const akys=z.akys.map((e,i)=>`<g class="r-a${i}"${sl("r-a"+i)}>${z.akis(e)}</g>`).join("");
  const nt=nuotaikos(z,!g,I,fonas), nuot=eks?(nt[o.n]||""):Object.values(nt).join("");
  const konf=!eks||o.n==="dziaug"||o.n==="lygis"?KONFETI:"";
  return `<svg viewBox="0 0 160 160" class="bh-pers${o.n?" n-"+o.n:""}" aria-hidden="true">${defs}<g${kontur?` filter="url(#${fid})"`:""}><g${tf}>`+
    `<g class="r-kunas">${z.uz||""}${z.kunas||""}`+
    `<g class="r-galva">${antena?`<g class="r-antena">${antena}</g>`:""}${z.galva}<g class="r-akys"${sl("r-akys")}>${akys}</g>`+
    `${z.burna?`<g class="r-burna"${sl("r-burna")}>${z.burna}</g>`:""}${nuot}${z.veidas||""}${akiuDaiktas(a,z)}${gd.svg}</g>`+
    `${kakloDaiktas(k,z,I,fonas)}<g class="r-ranka">${rankosDaiktas(r,z,I,fonas)}</g>${konf}</g></g></g></svg>`;
}
function suDaiktu(id){ const d=daiktas(id); return {...S.eq, [d.kat]:id}; }
/* mažas personažas savo fone (žingsnio pastaboje, mini kortelėje); n - nuotaika */
function avataroMini(n,kl){ const eq=S.eq||PRADINIS; return `<span class="av-mini gyvas ${kl||""}" style="${fonoStilius(eq,true)}" aria-hidden="true">${robotoSVG(eq,{n})}</span>`; }

/* ---- atlygiai ---- */
let atlygioEile=[], atlygioLaikmatis=null;
function inicializuotiDaiktus(){
  if(!S.eq) S.eq={...PRADINIS};
  if(!S.vardas||S.vardas===SENI_VARDAI[S.eq.personazas]) S.vardas=personazas(S.eq.personazas).vardas;   // 1.4: nauji vardai
  if(!S.matyti){ S.matyti=atrakinti(); S.nauji=[]; }
  saugoti();
}
function tikrintiAtlygiusVeliau(){ clearTimeout(atlygioLaikmatis); atlygioLaikmatis=setTimeout(tikrintiAtlygius,1600); }
function tikrintiAtlygius(){
  if(!S.matyti) return;
  const nauji=atrakinti().filter(id=>!S.matyti.includes(id));
  if(!nauji.length) return;
  S.matyti.push(...nauji); S.nauji=[...new Set([...(S.nauji||[]),...nauji])]; saugoti(); piestiZaideja();
  atlygioEile.push(...nauji);
  if($("#atlygis").classList.contains("hidden")) rodytiAtlygi();
}
function rodytiAtlygi(){
  const id=atlygioEile.shift(); if(!id){ $("#atlygis").classList.add("hidden"); return; }
  const d=daiktas(id), liko=atlygioEile.length;
  Gidas.slepti();
  $("#atlygis").innerHTML=`<div class="lang" role="dialog" aria-labelledby="atlAnt">
    <div class="eil" style="justify-content:center"><span class="zyme">Naujas daiktas</span>${d.retas?'<span class="zyme t">Retas</span>':""}</div>
    <div class="apsk" style="${fonoStilius(suDaiktu(id))}">${robotoSVG(suDaiktu(id),{n:"dziaug"})}</div>
    <h2 id="atlAnt">${esc(d.pav)}</h2><p>Gavai už: <b style="color:var(--text)">${esc(d.txt)}</b></p>
    <div class="eil" style="width:100%;margin-top:8px">
      <button class="btn pagr didelis" style="flex:1" onclick="uzsideti('${id}');rodytiAtlygi()">Užsidėti dabar</button>
      <button class="btn didelis" style="flex:1" onclick="rodytiAtlygi()">${liko?`Kitas (${liko}) →`:"Vėliau"}</button></div>
    <button class="btn" style="border:0;background:none;color:var(--muted)" onclick="atlygioEile=[];$('#atlygis').classList.add('hidden');rodytiSpinta()">Atidaryti spintą</button></div>`;
  $("#atlygis").classList.remove("hidden"); konfeti(50);
}
function uzsideti(id){
  const d=daiktas(id); if(!d||!atrakinti().includes(id)) return;
  S.eq[d.kat]=id; S.nauji=(S.nauji||[]).filter(x=>x!==id); saugoti(); piestiZaideja();
  if(rodinys==="spinta") rodytiSpinta();
}

/* ---- testavimo įrankiai ---- */
function testXP(n){ if(!testasAtrakintas)return; pridetiXP(n,$("#testav")); setTimeout(atnaujintiRodini,50); }
function testZenkleliai(){ if(!testasAtrakintas)return; Object.keys(ZENKLELIAI).forEach(k=>{ if(!S.zenkleliai.includes(k)) S.zenkleliai.push(k); }); saugoti(); piestiZaideja(); tikrintiAtlygiusVeliau(); atnaujintiRodini(); }
function testSerija(){ if(!testasAtrakintas)return; S.dienos=S.dienos||[]; const s=serija(); const d=new Date(); d.setDate(d.getDate()-Math.max(s,1)); S.dienos.push(dienaStr(d)); pazymetiDiena(); saugoti(); pranesti(`Mokymosi serija: ${serija()} d.`); tikrintiAtlygiusVeliau(); atnaujintiRodini(); }

/* =================== RODINIAI: SPINTA, LYGIAI, PROFILIS =================== */
let rodinys="pradzia", spintosSkirtukas="personazas";
function nustatytiRodini(v){ rodinys=v; document.body.classList.remove("meniu"); if(v!=="pamoka") auto.reset(); document.querySelectorAll("#nav button").forEach(b=>b.classList.toggle("akt",b.dataset.v===v||((v==="pamoka"||v==="testas")&&b.dataset.v==="pradzia"))); Gidas.slepti(); clearTimeout(Gidas.nuobodu); $("main").scrollTop=0; if(miniIjungtas()) setTimeout(miniPiesti,0); setTimeout(piestiApacia,0); }
function atnaujintiRodini(){ const f={kurejas:rodytiKureja,praktika:()=>prDabar?rodytiUzduoti(prDabar):rodytiPraktika(),spinta:rodytiSpinta,lygiai:rodytiLygius,profilis:rodytiProfili,nustatymai:rodytiNustatymus,zinynas:rodytiZinyna}[rodinys]; if(f) f(); }
function kitasAtlygis(){
  const b=busenaAtrakinimui(), i=lygis(S.xp), kitas=LYGIAI[i+1];
  if(!kitas) return null;
  const db={...b,lyg:i+2}, daiktai=DAIKTAI.filter(d=>!d.ar(b)&&d.ar(db));
  return {lygis:i+2, pav:kitas[1], truksta:kitas[0]-S.xp, proc:Math.round((S.xp-LYGIAI[i][0])/(kitas[0]-LYGIAI[i][0])*100), daiktai};
}
function rodytiSpinta(){
  nustatytiRodini("spinta");
  const at=atrakinti(), eq=S.eq;
  const sk=KATEGORIJOS.map(([id,pav])=>{const g=DAIKTAI.filter(d=>d.kat===id);return `<button class="${spintosSkirtukas===id?"akt":""}" onclick="spintosSkirtukas='${id}';rodytiSpinta()">${pav}${id==="personazas"?"":`<small>${g.filter(d=>at.includes(d.id)).length}/${g.length}</small>`}</button>`;}).join("");
  const kortos=DAIKTAI.filter(d=>d.kat===spintosSkirtukas).map(d=>{
    const ok=at.includes(d.id), on=eq[d.kat]===d.id, naujas=(S.nauji||[]).includes(d.id);
    const be={personazas:eq.personazas,spalva:eq.spalva,fonas:eq.fonas};       // personažas be daiktų - matosi tik šis daiktas
    const pv = d.kat==="personazas" ? {...eq,personazas:d.id} : d.kat==="spalva"||d.kat==="fonas" ? {...be,[d.kat]:d.id} : {...be,[d.kat]:d.id};
    if(d.kat==="personazas"){
      const p=personazas(d.id), nr=PERSONAZAI.indexOf(p)+1, sv=plytelesSpalva(pv)===BH.K||plytelesSpalva(pv)===BH.B;
      return `<button class="daiktas pers-k ${on?"uzs":""}" aria-pressed="${on}" onclick="spaustiDaikta('${d.id}')">${naujas?'<span class="naujas">NAUJA</span>':""}
        <div class="mini" style="${fonoStilius(pv,true)}"><span class="nr" style="color:${sv?BH.P:BH.K}">${String(nr).padStart(2,"0")}</span>${robotoSVG(pv)}</div>
        <b translate="no">${esc(p.vardas)}</b><small class="forma">${esc(p.forma)}</small>
        <div class="bus">${on?`<span class="ok">✓ Pasirinkta</span>`:`<span>${esc(p.txt)}</span>`}</div></button>`;
    }
    const mini=`<div class="mini" style="${fonoStilius(pv,true)}">${robotoSVG(pv)}</div>`;
    const bus = !ok ? `<span style="color:var(--muted)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg> ${esc(d.txt)}</span>`
              : on ? `<span style="color:var(--accent)">✓ ${d.kat==="personazas"?"Pasirinkta":"Užsidėta"}</span>` : `<span style="color:var(--accent2)">${d.kat==="personazas"?`${esc(d.txt)}`:"Spausk - užsidėk"}</span>`;
    return `<button class="daiktas ${on?"uzs":""}" ${ok?"":"disabled"} aria-pressed="${on}" onclick="spaustiDaikta('${d.id}')">${naujas?'<span class="naujas">NAUJA</span>':""}${mini}<b>${esc(d.pav)}</b><div class="bus">${bus}</div></button>`;
  }).join("");
  const ka=kitasAtlygis();
  $("#vidus").innerHTML=`<h1 class="ant1">Spinta</h1><p class="po1">Pasirink personažą ir aprenk jį. Nauji daiktai atsirakina mokantis: už lygius, ženklelius, pamokas ir mokymosi seriją.</p>
  <div class="spinta">
    <div>
      <div class="perziura gyvas" id="spintosRobotas" style="${fonoStilius(eq)}">${robotoSVG(eq)}</div>
      <div class="korta" style="padding:18px;margin-top:14px">
        <label for="robVardas" style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em">Personažo vardas</label>
        <input id="robVardas" class="vardas-ivestis" value="${esc(personazoVardas())}" maxlength="18" oninput="S.vardas=this.value;saugoti();$('#robotoVardas').textContent=this.value">
        <div class="eil" style="margin-top:12px;gap:6px">${KATEGORIJOS.map(([k])=>eq[k]?`<span class="cip">${esc(daiktas(eq[k]).pav)}</span>`:"").join("")}</div>
        <div class="eil" style="margin-top:14px"><button class="btn pagr" style="flex:1" onclick="atsitiktinis()">Atsitiktinis derinys</button><button class="btn" style="flex:1" onclick="nusiimti()">Nusiimti viską</button></div>
      </div>
    </div>
    <div>
      <div class="skirt" role="tablist">${sk}</div>
      <div class="daiktai${spintosSkirtukas==="personazas"?" pers4":""}">${kortos}</div>
      <div class="kitas-atl">${ka?`<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent2)" stroke-width="2"><path d="M12 3 4 7v6c0 4.4 3.4 7.6 8 8.5 4.6-.9 8-4.1 8-8.5V7z"/><path d="m9 12 2 2 4-4"/></svg>
        <div style="flex:1"><b>Kitas lygis: ${ka.lygis} „${esc(ka.pav)}“ - dar ${ka.truksta} XP</b><div style="color:var(--muted);font-size:13.5px">Atrakins: ${ka.daiktai.map(d=>esc(d.pav)).join(", ")||"naujų daiktų"}</div></div>
        <div class="juosta" style="width:160px;margin:0"><i style="width:${ka.proc}%"></i></div>`:`<b>Visi lygiai pasiekti! Tu - tikras inžinierius.</b>`}</div>
    </div>
  </div>`;
  S.nauji=(S.nauji||[]).filter(id=>daiktas(id).kat!==spintosSkirtukas); saugoti(); $("#naujiTaskelis").classList.toggle("hidden",!S.nauji.length);
}
function keistiPersonaza(id){
  const senas=personazas(S.eq.personazas||"robotas");
  S.eq.personazas=id;
  if(!S.vardas||S.vardas===senas.vardas||S.vardas===SENI_VARDAI[senas.id]) S.vardas=personazas(id).vardas;     // savo sugalvoto vardo nekeičiam
}
function spaustiDaikta(id){
  const d=daiktas(id);
  if(d.kat==="personazas"){ keistiPersonaza(id); saugoti(); piestiZaideja(); rodytiSpinta(); Robotas.reaguoti("moja",1600); return; }
  const lieka=d.kat==="spalva"||d.kat==="fonas";
  if(S.eq[d.kat]===id && !lieka) S.eq[d.kat]=null; else S.eq[d.kat]=id;
  saugoti(); piestiZaideja(); rodytiSpinta();
}
function atsitiktinis(){
  const at=atrakinti();
  KATEGORIJOS.filter(([k])=>k!=="personazas").forEach(([k])=>{ const g=DAIKTAI.filter(d=>d.kat===k&&at.includes(d.id)).map(d=>d.id); const pas=(k==="spalva"||k==="fonas")?g:[null,...g]; S.eq[k]=pas[Math.floor(Math.random()*pas.length)]; });
  saugoti(); piestiZaideja(); rodytiSpinta();
}
function nusiimti(){ ["galva","akys","kaklas","ranka"].forEach(k=>S.eq[k]=null); saugoti(); piestiZaideja(); rodytiSpinta(); }

function rodytiLygius(){
  nustatytiRodini("lygiai");
  const i=lygis(S.xp);
  const IS=[{spalva:"zydra",fonas:"tamsus"},{galva:"kepure",ranka:"piestukas",spalva:"gintaras",fonas:"tinklelis"},
            {galva:"salmas",akys:"akiniai",ranka:"liniuote",spalva:"violetine",fonas:"tinklelis"},{galva:"salmas",akys:"monoklis",kaklas:"varlyte",ranka:"skriestuvas",spalva:"violetine",fonas:"saulelydis"},
            {galva:"karuna",akys:"monoklis",kaklas:"varlyte",ranka:"skriestuvas",spalva:"auksas",fonas:"kosmosas"}];
  $("#vidus").innerHTML=`<h1 class="ant1">Lygiai</h1><p class="po1">Kiekvienas lygis - nauja apranga. XP gauni už pamokų žingsnius ir testus.</p>
  <div class="lygiu">${LYGIAI.map(([xp,pav],j)=>{
    const db={lyg:j+1,zen:[],pamokos:0,serija:0}, ankst={lyg:j,zen:[],pamokos:0,serija:0};
    const daiktai=DAIKTAI.filter(d=>d.ar(db)&&!d.ar(ankst)&&!d.txt.startsWith("Pradin"));
    const prad=j===0?["8 personažai","Kepurė ir pieštukas"]:[];
    return `<div class="lyg-k ${j<=i?"pasiekta":"uzr"} ${j===i?"dabar":""}">${j===i?'<span class="cia">Tu esi čia</span>':""}
      <div class="eil" style="gap:10px;flex-wrap:nowrap"><div class="nr">${j+1}</div><div><b style="font-size:16px">${pav}</b><div style="color:var(--muted);font-size:12.5px">nuo ${xp} XP</div></div></div>
      <div class="lyg-fon" style="${fonoStilius({...IS[j],personazas:S.eq.personazas},true)}">${robotoSVG({...IS[j],personazas:S.eq.personazas})}</div>
      <div style="font-size:11.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)">Atrakina</div>
      <ul>${[...prad,...daiktai.map(d=>d.pav)].map(t=>`<li>${esc(t)}</li>`).join("")}</ul></div>`;}).join("")}</div>
  <div class="kitas-atl"><b style="flex:1">Tavo XP: ${S.xp}</b>${LYGIAI[i+1]?`<span style="color:var(--muted)">Iki „${LYGIAI[i+1][1]}“ liko ${LYGIAI[i+1][0]-S.xp} XP</span>`:"<span>Aukščiausias lygis!</span>"}</div>`;
}

function profilioDuomenys(){
  return {xp:S.xp, lyg:lygis(S.xp), pamokos:pamokuBaigta(), visoPamoku:INFO.pamokos.length+INFO.ateityje.length, serija:serija(), daiktai:atrakinti().length, visoDaiktu:DAIKTAI.length};
}
function rodytiProfili(){
  nustatytiRodini("profilis");
  const p=profilioDuomenys();
  $("#vidus").innerHTML=`<h1 class="ant1">Profilis</h1><p class="po1">Tavo pažanga vienoje kortelėje - atsisiųsk ir pasigirk draugams.</p>
  <div class="profilis">
    <div class="prof-fon" style="${fonoStilius(S.eq)}">
      <span class="zyme prof-lyg">${p.lyg+1} lygis · ${LYGIAI[p.lyg][1]}</span>
      <div class="gyvas prof-pers">${robotoSVG(S.eq)}</div><b class="prof-vardas" translate="no">${esc(personazoVardas())}</b>
      <input class="prof-savininkas" aria-label="Tavo vardas" placeholder="Tavo vardas (nebūtina)" value="${esc(S.savininkas||"")}" oninput="S.savininkas=this.value;saugoti()">
    </div>
    <div style="display:flex;flex-direction:column;gap:16px">
      <div class="statai4"><div><b>${p.xp}</b><small>XP iš viso</small></div><div><b>${p.pamokos}/${p.visoPamoku}</b><small>pamokos baigtos</small></div>
        <div><b>${p.serija} d.</b><small>mokymosi serija</small></div><div><b>${p.daiktai}/${p.visoDaiktu}</b><small>daiktų spintoje</small></div></div>
      <div class="korta" style="padding:18px"><div style="font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:10px">Ženkleliai</div>
        <div class="zen-tink">${Object.entries(ZENKLELIAI).map(([k,v])=>`<div class="${S.zenkleliai.includes(k)?"gautas":"negautas"}">${v}</div>`).join("")}</div></div>
      <div class="eil"><button class="btn pagr didelis" onclick="atsisiustiKortele()">Atsisiųsti kortelę (PNG)</button>
        <button class="btn didelis" onclick="kopijuotiTeksta()">Kopijuoti tekstą</button></div>
    </div>
  </div>`;
}
function kopijuotiTeksta(){
  const p=profilioDuomenys();
  const t=`Mokausi braižyti su Brėžly! ${p.lyg+1} lygis „${LYGIAI[p.lyg][1]}“, ${p.xp} XP, ${S.zenkleliai.length} ženkleliai. Mano personažas - ${personazoVardas()}.`;
  navigator.clipboard?.writeText(t).then(()=>pranesti("Nukopijuota - įklijuok žinutėje draugams"),()=>pranesti(t));
}
function atsisiustiKortele(){
  const p=profilioDuomenys(), W=1080, H=600, eq=S.eq, f=FONAI[eq.fonas]||FONAI.tamsus, fon=plytelesSpalva(eq);
  const K=BH.K, P=BH.P, e=t=>esc(t), sr="'Arial Black','Archivo',Arial,sans-serif", mono="'Courier New','Space Mono',monospace";
  const rob=robotoSVG(eq,{eks:true}).replace('<svg ','<svg x="72" y="96" width="336" height="336" ');
  const tinklas = f.t ? `<defs><pattern id="tk" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="rgba(17,17,17,.13)"/></pattern></defs><rect x="36" y="36" width="408" height="528" fill="url(#tk)"/>` : "";
  const saule = f.s ? `<clipPath id="sk"><rect x="36" y="36" width="408" height="528"/></clipPath><circle cx="240" cy="564" r="230" fill="${BH.Y}" clip-path="url(#sk)"/>` : "";
  const zvaigzdes = f.z ? Array.from({length:36},(_,i)=>`<circle cx="${56+((i*97)%370)}" cy="${56+((i*53)%490)}" r="${i%3?1.6:2.6}" fill="${[P,BH.Y,BH.R,BH.B][i%4]}"/>`).join("") : "";
  const stat=(x,v,l)=>`<rect x="${x}" y="232" width="128" height="96" fill="#fff" stroke="${K}" stroke-width="4"/><text x="${x+16}" y="280" font-family="${sr}" font-size="30" font-weight="900" fill="${K}">${e(v)}</text><text x="${x+16}" y="310" font-family="${mono}" font-size="13" fill="#55524b">${e(l.toUpperCase())}</text>`;
  const zen=Object.entries(ZENKLELIAI).map(([k,v],j)=>{const g=S.zenkleliai.includes(k);const x=484+(j%2)*276,y=352+Math.floor(j/2)*54;
    return `<rect x="${x}" y="${y}" width="264" height="42" fill="${g?BH.Y:"#fff"}" stroke="${K}" stroke-width="${g?4:2}" ${g?"":'stroke-dasharray="6 5"'}/><text x="${x+14}" y="${y+27}" font-family="${sr}" font-size="15" font-weight="700" fill="${g?K:"#8a867c"}">${e(v.replace(/^\S+\s/,""))}</text>`;}).join("");
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" font-family="${sr}">`+
    `<rect width="${W}" height="${H}" fill="${P}"/><rect x="6" y="6" width="${W-12}" height="${H-12}" fill="none" stroke="${K}" stroke-width="12"/>`+
    `<rect x="36" y="36" width="408" height="528" fill="${fon}"/>${tinklas}${saule}${zvaigzdes}<rect x="36" y="36" width="408" height="528" fill="none" stroke="${K}" stroke-width="6"/>`+
    `${rob}<rect x="36" y="452" width="408" height="112" fill="${K}"/><text x="240" y="504" text-anchor="middle" font-size="36" font-weight="900" fill="${P}">${e(personazoVardas().toUpperCase())}</text>`+
    `<text x="240" y="536" text-anchor="middle" font-family="${mono}" font-size="15" fill="${BH.Y}">${e((S.savininkas?S.savininkas+" · ":"")+"mano Brėžly")}</text>`+
    `<rect x="56" y="56" width="216" height="34" fill="${BH.Y}" stroke="${K}" stroke-width="3"/><text x="70" y="79" font-family="${mono}" font-size="15" font-weight="700" fill="${K}">${p.lyg+1} lygis · ${e(LYGIAI[p.lyg][1])}</text>`+
    `<text x="484" y="98" font-family="${mono}" font-size="15" font-weight="700" letter-spacing="1" fill="${K}">MANO PAŽANGA · ${e(new Date().toLocaleDateString("lt-LT"))}</text>`+
    `<text x="484" y="150" font-size="38" font-weight="900" fill="${K}">MOKAUSI BRAIŽYTI</text><text x="484" y="194" font-size="38" font-weight="900" fill="${K}">SU BRĖŽLY</text>`+
    `${stat(484,p.xp,"XP")}${stat(624,p.pamokos+"/"+p.visoPamoku,"pamokos")}${stat(764,p.serija+" d.","serija")}${stat(904,p.daiktai+"/"+p.visoDaiktu,"daiktai")}`+
    `${zen}<g transform="translate(484 522)"><circle cx="11" cy="11" r="9" fill="${BH.R}"/><rect x="14" y="14" width="14" height="14" fill="${BH.Y}"/><path d="M2 28 L14 28 L2 16 Z" fill="${BH.B}"/></g>`+
    `<text x="524" y="549" font-size="24" font-weight="900" fill="${K}">BRĖŽLY</text><text x="640" y="549" font-family="${mono}" font-size="14" fill="#55524b">braižymo mokymosi draugas</text></svg>`;
  const img=new Image();
  img.onload=()=>{ const cv=document.createElement("canvas"); cv.width=W*2; cv.height=H*2; const cx=cv.getContext("2d"); cx.scale(2,2); cx.drawImage(img,0,0);
    cv.toBlob(b=>{ const a=document.createElement("a"); a.href=URL.createObjectURL(b); a.download=`Brezly_${personazoVardas().replace(/[^\wąčęėįšųūž-]/gi,"_")}.png`; document.body.appendChild(a); a.click(); a.remove(); pranesti("Kortelė atsisiųsta"); },"image/png"); };
  img.onerror=()=>pranesti("Nepavyko sukurti paveikslėlio");
  img.src="data:image/svg+xml;charset=utf-8,"+encodeURIComponent(svg);
}


/* ---------- šoninė ---------- */
function piestiSonine(){
  const el=$("#pamokuSarasas");
  if(el) el.innerHTML=INFO.pamokos.map((p,i)=>{
    const atl=(S.atlikta[p.id]||[]).length, viso=p.zingsniai.length, baigta=atl>=viso;
    return `<button class="pam ${PAM&&PAM.id===p.id?"akt":""} ${baigta?"baigta":""}" onclick="rodytiPradzia('${p.id}')">
      <span class="nr">${baigta?BH_VARNELE:dvi(i+1)}</span><b>${esc(p.pavadinimas)}</b><small>${atl}/${viso} žingsnių</small></button>`;
  }).join("")+INFO.ateityje.map(p=>`<div class="pam uzr" title="Bus kitoje versijoje"><span class="nr">·</span><b>${esc(p.pavadinimas)}</b><small>Netrukus</small></div>`).join("");
  piestiZaideja();
}
function keistiTema(){sg("tema",(sg("tema")||"light")==="dark"?"light":"dark");taikytiTema();}
function taikytiTema(){const t=sg("tema")||"light";document.documentElement.dataset.theme=t;if(rodinys==="nustatymai")rodytiNustatymus();}
function zoomas(){return parseFloat(document.body.style.zoom)||1;}
function taikytiDydi(){
  const d=sg("dydis");
  if(d){ document.body.style.zoom=d; return; }
  const h=innerHeight, w=innerWidth;           // nenustatyta - prisitaikom prie ekrano
  document.body.style.zoom=(miniIjungtas()||(h>=720&&w>=400))?"1":(h<600||w<380)?"0.86":"0.93";
}
addEventListener("resize",()=>{clearTimeout(window._dydLaik);window._dydLaik=setTimeout(taikytiDydi,200);});

/* ---------- pradžios ekranas ---------- */
function pamokaPagalId(id){ return INFO.pamokos.find(p=>p.id===id); }
function pirmaNebaigta(){ return INFO.pamokos.find(p=>(S.atlikta[p.id]||[]).length<p.zingsniai.length)||INFO.pamokos[0]; }
function rodytiPradzia(pid){
  nustatytiRodini("pradzia");
  PAM=(pid&&pamokaPagalId(pid))||PAM||pamokaPagalId(S.pamoka)||pirmaNebaigta(); S.pamoka=PAM.id; saugoti(); $("#vPam").textContent=`${INFO.pamokos.indexOf(PAM)+1}. ${PAM.pavadinimas}`; if(!Gidas.turas) Gidas.slepti(); clearTimeout(Gidas.nuobodu);
  const atl=S.atlikta[PAM.id]||[], viso=PAM.zingsniai.length, prad=atl.length>0&&atl.length<viso, pnr=INFO.pamokos.indexOf(PAM)+1;
  const kitas=prad?(S.dabartinis[PAM.id]||0):Math.max(0,PAM.zingsniai.findIndex(z=>!atl.includes(z.id)));
  const kart=Object.values(S.atlikta).some(a=>a.length)?Kartojimas.likoSiandien():0;
  $("#vidus").innerHTML=`<div class="bh-du">
  <section class="bh-lapas" aria-label="Brėžinio lapas">
    <span class="bh-fonas-nr" aria-hidden="true">${dvi(pnr)}</span>
    <span class="bh-zyme">Pamoka ${dvi(pnr)} / ${dvi(INFO.pamokos.length)} · ${esc(PAM.trukme)} · iki ${PAM.zingsniai.reduce((a,z)=>a+z.xp,0)+PAM.testas.length*10} XP</span>
    <h1 class="bh-h1">${esc(PAM.pavadinimas)}</h1>
    ${lapoSVG(PAM,atl.length>=viso?-1:kitas,atl,"pradeti")}
  </section>
  <div class="bh-skydas" role="complementary">
    <div class="bh-geltona">
      <div class="bh-poz"><span class="bh-burb">${dvi(pnr)}</span><span>${viso} žingsn. · ${esc(PAM.trukme)}</span></div>
      <h2>${prad?"Tęsk pamoką":atl.length>=viso?"Pamoka baigta":"Pradėk pamoką"}</h2>
      <p>${esc(PAM.aprasas)}</p>
    </div>
    <div class="bh-veiksmai">
      <button class="bh-tikr" id="pradetiBtn" onclick="pradeti(${prad?"S.dabartinis[PAM.id]||0":0})">${prad?"Tęsti →":atl.length>=viso?"Kartoti →":"Pradėti →"}</button>
      <button class="bh-uz" id="naujasBtn" onclick="naujasBrezinys()" title="Naujas brėžinys iš acadiso.dwt">Naujas brėžinys</button>
    </div>
    <div class="bh-robis">${avataroMini()}<div><b>Ar žinojai?</b> <span id="patarimas"></span></div></div>
    ${kart?`<div class="kart-juosta"><div><b>Dienos kartojimas</b><small>${kart} kom. · ~2 min · iki +${kart*2+5} XP</small></div><button class="btn" onclick="kartTab='diena';kartSesija=null;rodytiKartojima()">Pradėti</button></div>`:""}
    ${zingsniuLangeliai(PAM,-1,atl,"pradeti")}
  </div></div>
  <section class="bh-visos" aria-label="Visos pamokos"><h2 class="bh-ant">Visos pamokos</h2><div id="pamokuSarasas" class="bh-pamokos"></div></section>`;
  piestiSonine(); rodytiPatarima();
}
async function naujasBrezinys(){const r=await api("/api/naujas",{});pranesti(r.ok?"Atidarytas naujas brėžinys iš acadiso.dwt":"Nepavyko: "+r.klaida);}

/* ---------- pamokos žingsnis ---------- */
function pradeti(nr){ if(nr>=PAM.zingsniai.length) nr=0; rodytiZingsni(nr); }
function rodytiZingsni(nr){
  nustatytiRodini("pamoka");
  S.dabartinis[PAM.id]=nr; saugoti();
  uzuominuRodyta=0; demo=false; bandymai=0; paskutinisAtsakas=null; auto.reset();
  $("#vPam").textContent=`${INFO.pamokos.indexOf(PAM)+1}. ${PAM.pavadinimas} · ${nr+1}/${PAM.zingsniai.length}`;
  Gidas.slepti(); piestiZingsni(); $("main").scrollTop=0;
  Gidas.zingsnioPradzia(nr);
  if(BUS.prisijungta) api("/api/zingsnio_pradzia",{pamoka:PAM.id,zingsnis:nr}).catch(()=>{});   // „Kur klaida?“ - nuo čia
}
function piestiZingsni(){
  const nr=S.dabartinis[PAM.id], z=PAM.zingsniai[nr], atl=S.atlikta[PAM.id]||[], jau=atl.includes(z.id);
  const xpDabar=uzdirbtiXP(z), pnr=INFO.pamokos.indexOf(PAM)+1, n=PAM.zingsniai.length;
  const kom=(z.komandos||[]).find(([pr,iv])=>/^Command/i.test(pr)), komT=kom?komandosTekstas(kom[0],kom[1]):"";
  $("#vidus").innerHTML=`<div class="bh-du">
  <section class="bh-lapas" aria-label="Brėžinio lapas">
    <span class="bh-fonas-nr" aria-hidden="true">${dvi(pnr)}</span>
    <button class="bh-zyme" onclick="rodytiPradzia()">← Pamoka ${dvi(pnr)} / ${dvi(INFO.pamokos.length)}</button>
    <h1 class="bh-h1">${esc(PAM.pavadinimas)}</h1>
    ${lapoSVG(PAM,nr,atl,"rodytiZingsni")}
    <div class="bh-darbas">
      <h3 class="bh-ant">Daryk</h3>
      <ol class="daryk">${z.zingsniai.map(t=>`<li>${esc(t)}</li>`).join("")}</ol>
      ${z.komandos.length?`<div class="komandos" id="komandos"><div class="ant"><span>AutoCAD komandų eilutė - įvesk geltonus atsakymus</span></div>
        ${z.komandos.map(([pr,iv0])=>{const iv=komandosTekstas(pr,iv0),pele=iv.startsWith("(")||iv==="Enter";return `<div class="kl"><span class="pr">${esc(pr)}</span><span class="iv ${pele?"pele":""}">${esc(iv)}</span>${pele?"":`<button onclick="kopijuoti('${esc(iv)}')">Kopijuoti</button>`}</div>`;}).join("")}</div>`:""}
      ${z.tikslas?`<div class="tikslas" id="tikslas"><span>Tikslas:</span> <b>${esc(z.tikslas)}</b></div>`:""}
    </div>
  </section>
  <div class="bh-skydas" id="korta" role="complementary">
    <div class="bh-geltona">
      <div class="bh-poz"><span class="bh-burb">${nr+1}</span><span>Pozicija ${nr+1} · ${jau?"✓ atlikta":`+${xpDabar} XP`}</span></div>
      <h2>${esc(z.pavadinimas)}</h2>
      <p class="kodel">${esc(z.kodel)}</p>
      ${kom?`<button class="bh-kom" onclick="kopijuoti('${esc(komT)}')" title="Kopijuoti">&gt; ${esc(komT)}</button>`:""}
    </div>
    <div class="bh-veiksmai" id="veiksmai">
      <button class="bh-tikr" id="tikrinti" onclick="tikrinti()">${z.tikrinama?"Tikrinti →":"Atlikau →"}</button>
      <button class="bh-uz" id="uzuominaBtn" onclick="uzuomina()" ${uzuominuRodyta>=z.uzuominos.length?"disabled":""}>Užuomina <small>${uzuominuRodyta}/${z.uzuominos.length}</small></button>
    </div>
    <div class="bh-antr">
      ${z.demonstruojama?`<button id="parodykBtn" onclick="parodyti()">Parodyk man</button>`:""}
      ${nr>0?`<button onclick="rodytiZingsni(${nr-1})">← Atgal</button>`:""}
      <button onclick="toliau()">${nr<n-1?"Praleisti →":"Į testą →"}</button>
    </div>
    <div class="bh-robis">${avataroMini(jau?"dziaug":"lauk")}<div><p><b translate="no">${esc(personazoVardas())}:</b> ${esc(robioTekstas(nr,atl))}</p>${z.tikrinama&&!jau?auto.html():""}</div></div>
    <div id="uzuominos">${z.uzuominos.slice(0,uzuominuRodyta).map((u,i)=>`<div class="uzuomina"><b>Užuomina ${i+1}:</b> ${esc(u)}</div>`).join("")}</div>
    <div id="atsakas">${paskutinisAtsakas||""}</div>
    ${zingsniuLangeliai(PAM,nr,atl,"rodytiZingsni")}
  </div></div>`;
  Gidas.atnaujinti(); piestiApacia();
  if(miniIjungtas()) miniPiesti();
}
const BH_VARNELE="✓";
function dvi(n){ return String(n).padStart(2,"0"); }
function trumpasPav(z){ const t=z.pavadinimas, i=t.lastIndexOf(":"); const s=(i>=0?t.slice(i+1):t).trim(); return s.length>16?s.slice(0,15)+"…":s; }
function robioTekstas(nr,atl){
  const z=PAM.zingsniai[nr], pries=PAM.zingsniai.slice(0,nr).filter(s=>atl.includes(s.id)).length;
  if(atl.includes(z.id)) return `${nr+1} pozicija jau pažymėta. Gali eiti toliau.`;
  if(nr===0) return `Pradedam! Daryk, kas parašyta kairėje, o aš stebėsiu tavo brėžinį.`;
  return pries===nr ? `Pozicijos 1–${nr} pažymėtos. Dabar - ${nr+1}: ${trumpasPav(z)}.` : `Dabar - ${nr+1} pozicija: ${trumpasPav(z)}.`;
}
function zingsniuLangeliai(pam,dab,atl,fn){
  const n=pam.zingsniai.length;
  return `<div class="progresas bh-tabs" style="grid-template-columns:repeat(${Math.min(n,5)},minmax(0,1fr))">${pam.zingsniai.map((s,i)=>{
    const a=atl.includes(s.id), d=i===dab;
    return `<button class="${a?"atl":""} ${d?"dab":""}" onclick="${fn}(${i})" title="${esc((i+1)+". "+s.pavadinimas)}"><b>${a&&!d?BH_VARNELE:i+1}</b><small>${esc(trumpasPav(s))}</small></button>`;}).join("")}</div>`;
}
/* lapas su pozicijų burbuliukais: kiekvienas pamokos žingsnis - pozicija, kaip surinkimo brėžinyje */
function lapoSVG(pam,dab,atl,fn){
  const n=pam.zingsniai.length, kair=Math.ceil(n/2), des=n-kair, z=pam.zingsniai[Math.max(dab,0)];
  const yy=(k,i)=>k<=1?230:62+i*(336/(k-1));
  const vietos=pam.zingsniai.map((s,i)=>i<kair?{x:74,y:yy(kair,i),k:-1}:{x:686,y:yy(des,des-1-(i-kair)),k:1});
  const balionas=(s,i)=>{
    const v=vietos[i], a=atl.includes(s.id), d=i===dab, r=d?30:24;
    const ex=v.k<0?178:552, ey=v.y+(232-v.y)*.18, dx=ex-v.x, dy=ey-v.y, L=Math.hypot(dx,dy)||1;
    const fonas=d?"#ffc400":a?"#111111":"#ffffff", spalva=a&&!d?"#f7f5f0":"#111111";
    const zenklas=a&&!d?`<path d="M${v.x-9} ${v.y+1}l6 6 12-13" fill="none" stroke="${spalva}" stroke-width="4" stroke-linecap="square"/>`
      :`<text x="${v.x}" y="${v.y+(d?9:8)}" text-anchor="middle" class="bh-bn" font-size="${d?26:22}" fill="${spalva}">${i+1}</text>`;
    return `<g class="bh-b${d?" dab":""}${a?" atl":""}" role="button" tabindex="0" aria-label="${esc((i+1)+". "+s.pavadinimas)}"
      onclick="${fn}(${i})" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();${fn}(${i})}"><title>${esc((i+1)+". "+s.pavadinimas)}</title>
      <path d="M${(v.x+dx/L*r).toFixed(1)} ${(v.y+dy/L*r).toFixed(1)}L${ex} ${ey.toFixed(1)}" stroke="#111" stroke-width="2"/><circle cx="${ex}" cy="${ey.toFixed(1)}" r="3.5" fill="#111"/>
      <circle cx="${v.x}" cy="${v.y}" r="${r}" fill="${fonas}" stroke="#111" stroke-width="3"/>${zenklas}
      <text x="${v.x}" y="${v.y+r+17}" text-anchor="middle" class="bh-bl">${esc(trumpasPav(s))}</text></g>`;
  };
  const eil=t=>{ const zod=String(t||"").split(/\s+/), r=[]; let e=""; for(const w of zod){ if((e+" "+w).trim().length>26){ if(e) r.push(e); e=w; } else e=(e+" "+w).trim(); } if(e) r.push(e); return r.slice(0,3); };
  const vidus=z&&z.pav&&dab>=0
    ? `<image href="/${esc(z.pav)}" x="182" y="48" width="366" height="292" preserveAspectRatio="xMidYMid meet"/>`
    : `<path d="M215 196h300M365 70v250" stroke="#e2362b" stroke-width="1.4" stroke-dasharray="16 5 3 5"/><circle cx="365" cy="196" r="46" fill="none" stroke="#111" stroke-width="2.5"/>
       ${eil(dab>=0&&z.tikslas?z.tikslas:pam.aprasas).map((t,i)=>`<text x="365" y="${282+i*20}" text-anchor="middle" class="bh-lt">${esc(t)}</text>`).join("")}`;
  const pav=pam.pavadinimas.toUpperCase();
  const legenda=z&&z.pav&&dab>=0?`<g class="bh-leg"><rect x="150" y="458" width="12" height="12" fill="#e2362b"/><text x="168" y="469">šis žingsnis</text><rect x="290" y="458" width="12" height="12" fill="#111"/><text x="308" y="469">jau nubraižyta</text></g>`:"";
  return `<svg class="bh-svg" viewBox="0 0 760 476" role="group" aria-label="Pamokos žingsniai">${legenda}
    <rect x="150" y="18" width="430" height="430" fill="#ffffff" stroke="#111" stroke-width="3"/>
    <rect x="166" y="34" width="398" height="398" fill="none" stroke="#111" stroke-width="1.2"/>
    ${vidus}
    <g class="bh-ki"><rect x="380" y="352" width="184" height="80" fill="#fff" stroke="#111" stroke-width="1.5"/><path d="M380 378h184M380 404h184M448 352v80" stroke="#111" stroke-width="1.5"/>
      <rect x="449" y="379" width="114" height="24" fill="#ffc400"/>
      <text x="386" y="369">PAV.</text><text x="455" y="369">${esc(pav.length>15?pav.slice(0,14)+"…":pav)}</text>
      <text x="386" y="395">ŽINGSN.</text><text x="455" y="395" font-weight="700">${dab>=0?dab+1:n} / ${n}</text>
      <text x="386" y="421">MAST.</text><text x="455" y="421">1:1</text></g>
    ${pam.zingsniai.map(balionas).join("")}
  </svg>`;
}
/* apatinė juosta: AutoCAD būsena, dabartinė komanda, KITA → */
function piestiApacia(){
  const k=$("#apKom"), kb=$("#apKita"), kb2=$("#kompBtn"); if(!k||!kb||!INFO) return;
  if(kb2) kb2.textContent=langoRez()==="kompaktiskas"?"Didelis langas":"Šalia AutoCAD";
  let kom="", kita=null, veiks=null;
  if(PAM){
    const pnr=INFO.pamokos.indexOf(PAM), kitaPam=INFO.pamokos[pnr+1];
    if(rodinys==="pamoka"){
      const nr=S.dabartinis[PAM.id]||0, z=PAM.zingsniai[nr], c=(z.komandos||[]).find(([pr])=>/^Command/i.test(pr));
      if(c) kom=komandosTekstas(c[0],c[1]);
      if(nr<PAM.zingsniai.length-1){ kita=`Kita: ${nr+2} · ${trumpasPav(PAM.zingsniai[nr+1])}`; veiks=()=>rodytiZingsni(nr+1); }
      else { kita="Kita: testas"; veiks=()=>rodytiTesta(); }
    } else if(rodinys==="pradzia"||rodinys==="testas"){
      if(kitaPam){ kita=`Kita: ${dvi(pnr+2)} ${kitaPam.pavadinimas}`; veiks=()=>rodytiPradzia(kitaPam.id); }
    } else { kita=`Tęsti: ${dvi(pnr+1)} ${PAM.pavadinimas}`; veiks=()=>rodytiPradzia(PAM.id); }
  }
  k.hidden=!kom; k.textContent=kom?`Komanda: ${kom}`:"";
  kb.hidden=!kita; kb.textContent=kita?kita+" →":""; kb.onclick=veiks;
}
function uzdirbtiXP(z){ if(demo) return 0; return Math.max(Math.round(z.xp*(1-0.25*uzuominuRodyta)), Math.round(z.xp*0.25)); }
function kopijuoti(t){ navigator.clipboard?.writeText(t).then(()=>pranesti(`Nukopijuota: ${t} - įklijuok AutoCAD'e (Ctrl+V)`),()=>pranesti(t)); }
function uzuomina(){ uzuominuRodyta++; Silpnos.pazymeti("u"); Gidas.slepti(); piestiZingsni(); }
async function parodyti(){
  if(!confirm("Brėžly pats atliks šį žingsnį AutoCAD'e. Už jį XP negausi, bet galėsi pažiūrėti ir tęsti. Rodyti?"))return;
  const z=PAM.zingsniai[S.dabartinis[PAM.id]];
  const r=await api("/api/parodyti",{pamoka:PAM.id,zingsnis:S.dabartinis[PAM.id]});
  if(!r.ok){pranesti(r.klaida);return;}
  demo=true; Silpnos.pazymeti("d"); pranesti("Pažiūrėk į AutoCAD - žingsnis atliktas. Dabar spausk „Patikrinti“.");
  piestiZingsni();
}
async function tikrinti(automatinis){
  if(tikrina)return; tikrina=true; Gidas.slepti(); Gidas.veiksmas(); auto.reset(); if(miniIjungtas()) miniPiesti();
  const nr=S.dabartinis[PAM.id], z=PAM.zingsniai[nr], btn=$("#tikrinti");
  btn.innerHTML='<span class="sukasi"></span>Tikrinu brėžinį...'; btn.disabled=true;
  let r; try{ r=await api("/api/tikrinti",{pamoka:PAM.id,zingsnis:nr}); }catch(e){ r={ok:false,klaida:"Brėžly neatsako"}; }
  tikrina=false; if(!automatinis) bandymai++; else bandymai=Math.max(bandymai,1);
  if(!r.ok){ paskutinisAtsakas=`<div class="atsakas blogai"><b>Nepavyko patikrinti</b>${esc(r.klaida)}</div>`; piestiZingsni(); rodytiAtsaka(); return; }
  if(r.teisingai){
    const atl=S.atlikta[PAM.id]||(S.atlikta[PAM.id]=[]); const naujai=!atl.includes(z.id);
    const xp=naujai?uzdirbtiXP(z):0;
    if(naujai){atl.push(z.id);saugoti();}
    const pagyrimai=["Puiku!","Šaunu!","Taip ir yra!","Tikras braižytojas!","Nė vienos klaidos!"];
    Robotas.reaguoti("dziaug",1300);
    paskutinisAtsakas=`<div class="atsakas gerai"><b>✓ ${automatinis?"Pastebėjau - padarei! ":""}${pagyrimai[Math.floor(Math.random()*pagyrimai.length)]} ${xp?`+${xp} XP`:""}</b>
      ${bandymai===1&&!uzuominuRodyta&&!demo?"Iš pirmo karto ir be užuominų. ":""}${demo?"Šį kartą parodžiau aš - kitą kartą pabandyk pats. ":""}
      <div class="eil" style="margin-top:12px"><button class="btn zalias" id="kitasBtn" onclick="toliau()">${nr<PAM.zingsniai.length-1?"Kitas žingsnis →":"Į testą →"}</button></div></div>`;
    piestiZingsni(); piestiSonine(); rodytiAtsaka();
    if(automatinis){ Garsas.dzin(); if(!document.hasFocus()) api("/api/mirkteleti",{}).catch(()=>{}); }
    if(xp) pridetiXP(xp,$("#atsakas"));
    Gidas.pavyko(); pazymetiDiena();
    if(naujai && atl.length>=PAM.zingsniai.length) tikrintiAtlygiusVeliau();
    if(naujai&&atl.length===1) duotiZenkleli("pirmas");
    if(naujai&&!uzuominuRodyta&&!demo) S._beUz=(S._beUz||0)+1;
    if(bandymai<=1&&!uzuominuRodyta&&!demo) Silpnos.pazymeti("g");      // pavyko švariai - silpna vieta taisosi
    if((S._beUz||0)>=5) duotiZenkleli("be_uzuominu");
  } else {
    Robotas.reaguoti("liud",2600); if(!automatinis) Silpnos.pazymeti("b");
    paskutinisAtsakas=`<div class="atsakas blogai"><b>Dar ne visai ${bandymai>2?"- nepasiduok! Gali paimti užuominą 💡":""}</b><ul>${r.pastabos.map(p=>`<li>${esc(p)}</li>`).join("")}</ul>
      ${z.tikrinama&&BUS.prisijungta?`<div class="eil" style="margin-top:10px"><button class="btn" id="kurKlaidaBtn" onclick="kurKlaida()">🔍 Kur klaida? Parodyk AutoCAD'e</button></div>`:""}</div>`;
    piestiZingsni();
    Gidas.nepavyko(z);
  }
}
function toliau(){ const nr=S.dabartinis[PAM.id]; if(nr<PAM.zingsniai.length-1) rodytiZingsni(nr+1); else rodytiTesta(); }
async function kurKlaida(){
  const btn=$("#kurKlaidaBtn"); if(btn) btn.disabled=true;
  let r; try{ r=await api("/api/kur_klaida",{pamoka:PAM.id,zingsnis:S.dabartinis[PAM.id]}); }catch(e){ r={ok:false,klaida:"Brėžly neatsako"}; }
  if(btn) btn.disabled=false;
  if(!r.ok){ pranesti("Nepavyko: "+r.klaida); return; }
  Silpnos.pazymeti("k");
  pranesti(r.kiek?`🔍 AutoCAD'e paryškinau, ką nubraižei šiame žingsnyje (${r.kiek}) - klaida greičiausiai ten.`:r.pranesimas);
}

/* ---------- garsas, kai žingsnis atliktas (be failų - WebAudio) ---------- */
const Garsas={
  ctx:null,
  ijungtas(){ return sg("garsas")!=="0"; },
  paruosti(){ // naršyklė leidžia garsą tik po naudotojo veiksmo - kontekstą kuriam per pirmą spragtelėjimą
    if(!this.ctx){ try{ this.ctx=new (window.AudioContext||window.webkitAudioContext)(); }catch(e){ return; } }
    if(this.ctx.state==="suspended") this.ctx.resume().catch(()=>{});
  },
  dzin(){
    if(!this.ijungtas()||!this.ctx) return;
    try{ const c=this.ctx, t=c.currentTime;
      [[880,0],[1318.5,0.11]].forEach(([f,d])=>{ const o=c.createOscillator(), g=c.createGain(); o.type="sine"; o.frequency.value=f;
        g.gain.setValueAtTime(0.0001,t+d); g.gain.exponentialRampToValueAtTime(0.12,t+d+0.02); g.gain.exponentialRampToValueAtTime(0.0001,t+d+0.35);
        o.connect(g); g.connect(c.destination); o.start(t+d); o.stop(t+d+0.4); });
    }catch(e){}
  },
  perjungti(){ sg("garsas",this.ijungtas()?"0":"1"); if(this.ijungtas()){ this.paruosti(); this.dzin(); } if(rodinys==="nustatymai") rodytiNustatymus(); }
};
["pointerdown","keydown"].forEach(ev=>addEventListener(ev,()=>Garsas.paruosti(),{passive:true}));

/* ---------- dienos kartojimas: 5 komandos, dažniau tos, kurias pamiršti (Leitnerio dėžutės) ---------- */
const Kartojimas={
  INTERVALAI:[1,2,4,8,16],        // dienos iki kito kartojimo pagal dėžutę 1-5
  diena(d=new Date()){ return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`; },
  po(diena,n){ const d=new Date(diena+"T12:00:00"); d.setDate(d.getDate()+n); return this.diena(d); },
  B(){ return S.kart||(S.kart={dez:{},diena:""}); },
  baseinas(){       // pradėtų pamokų komandos; kol jų mažai - pirmųjų pamokų
    const eile=INFO.pamokos.map(p=>p.id), prad=new Set(eile.filter(id=>(S.atlikta[id]||[]).length));
    let k=INFO.korteles.filter(x=>prad.has(x.pamoka));
    if(k.length<8) k=[...INFO.korteles].sort((a,b)=>eile.indexOf(a.pamoka)-eile.indexOf(b.pamoka)).slice(0,8);
    return k;
  },
  laukia(diena=this.diena()){ const D=this.B().dez;
    return this.baseinas().filter(k=>!(D[k.k]&&D[k.k].kada>diena))
      .sort((a,b)=>((D[a.k]||{}).d||0)-((D[b.k]||{}).d||0)||String((D[a.k]||{}).kada||"").localeCompare(String((D[b.k]||{}).kada||""))); },
  likoSiandien(){ return this.B().diena===this.diena()?0:Math.min(5,this.laukia().length); },
  sudaryti(){ return this.laukia().slice(0,5).map(k=>({k,v:mesk([k,...mesk(INFO.korteles.filter(x=>x.k!==k.k)).slice(0,3)]),ats:null})); },
  atsakyti(j){
    const ses=kartSesija, q=ses.kl[ses.i]; if(q.ats!==null) return; q.ats=j;
    const teis=q.v[j].k===q.k.k, D=this.B().dez, buvo=(D[q.k.k]||{}).d||1, d=teis?Math.min(5,buvo+1):1;   // nauja + teisingai - po 2 d.
    D[q.k.k]={d,kada:this.po(this.diena(),this.INTERVALAI[d-1])};
    if(teis&&this.B().diena!==this.diena()) ses.xp+=2;
    saugoti(); rodytiKartojima();
  },
  toliau(){
    const ses=kartSesija; ses.i++;
    if(ses.i>=ses.kl.length){ const pirmas=this.B().diena!==this.diena(); this.B().diena=this.diena();
      const xp=pirmas?ses.xp+5:0; saugoti(); rodytiKartojima(); if(xp) pridetiXP(xp,$("#kartRez")); return; }
    rodytiKartojima();
  },
  html(){
    const ses=kartSesija||(kartSesija={kl:this.sudaryti(),i:0,xp:0});
    if(!ses.kl.length) return `<div class="kart-diena"><h3>Šiandien kartoti nėra ko ✓</h3><p>Visos komandos dar atmintyje. Grįžk rytoj - parinksiu tas, kurias laikas pakartoti.</p></div>`;
    if(ses.i>=ses.kl.length){ const teis=ses.kl.filter(q=>q.v[q.ats].k===q.k.k).length, rytoj=Math.min(5,this.laukia(this.po(this.diena(),1)).length);
      return `<div class="kart-diena" id="kartRez"><h3>✓ Šiandien pakartota: ${teis} iš ${ses.kl.length}</h3><p>Rytoj laukia ${rytoj} kom. Ką suklydai - paklausiu dar kartą jau rytoj.</p>
        <div class="eil"><button class="btn" onclick="kartTab='korteles';rodytiKartojima()">Visos kortelės</button></div></div>`; }
    const q=ses.kl[ses.i], a=q.ats;
    return `<div class="kart-diena"><div class="eil"><small style="color:var(--muted)">Dienos kartojimas</small><span class="tarpas"></span><small style="color:var(--muted)">${ses.i+1} / ${ses.kl.length}</small></div>
      <p class="kart-kl">Kuri komanda tai daro?</p><h3>${esc(q.k.ka)}</h3>
      <div class="variantai kart-var">${q.v.map((v,j)=>{const kl=a===null?"":v.k===q.k.k?"teis":j===a?"neteis":"";return `<button class="${kl}" ${a!==null?"disabled":""} onclick="Kartojimas.atsakyti(${j})">${esc(v.k)}</button>`;}).join("")}</div>
      ${a!==null?`<div class="paaisk">${q.v[a].k===q.k.k?"✓ Teisingai!":`✗ Teisingas atsakymas - <b>${esc(q.k.k)}</b>`}${q.k.trump?` · trumpinys ${esc(q.k.trump)}`:""}<br><code>${esc(q.k.pvz)}</code></div>
        <div class="eil" style="margin-top:12px"><button class="btn pagr" onclick="Kartojimas.toliau()">${ses.i<ses.kl.length-1?"Toliau →":"Baigti"}</button></div>`:""}</div>`;
  }
};
let kartSesija=null;

/* ---------- testas ---------- */
let testoAts=[];
function rodytiTesta(){
  nustatytiRodini("testas");
  Gidas.slepti();
  testoAts=PAM.testas.map(()=>null);
  piestiTesta();
}
function piestiTesta(){
  const atsakyta=testoAts.filter(x=>x!==null).length;
  $("#vidus").innerHTML=`
  <div class="progresas"><button class="btn" onclick="rodytiZingsni(PAM.zingsniai.length-1)">← Atgal</button>
    <div class="taskai">${PAM.testas.map((_,i)=>`<i class="${testoAts[i]===null?"":testoAts[i]===PAM.testas[i].t?"atl":"dab"}"></i>`).join("")}</div><small>Testas · ${atsakyta}/${PAM.testas.length}</small></div>
  <div class="korta-ant" style="margin-bottom:16px"><h1>Greitas testas 📝</h1><span class="xp-zyme">+10 XP už teisingą</span></div>
  ${PAM.testas.map((q,i)=>`<div class="klausimas"><h3>${i+1}. ${esc(q.k)}</h3><div class="variantai">
    ${q.v.map((v,j)=>{const a=testoAts[i];const kl=a===null?"":j===q.t?"teis":j===a?"neteis":"";return `<button class="${kl}" ${a!==null?"disabled":""} onclick="atsakyti(${i},${j},this)">${esc(v)}</button>`;}).join("")}</div>
    ${testoAts[i]!==null?`<div class="paaisk">${testoAts[i]===q.t?"✓":"✗"} ${esc(q.p)}</div>`:""}</div>`).join("")}
  ${atsakyta===PAM.testas.length?`<div class="eil"><button class="btn pagr didelis" onclick="pabaiga()">Baigti pamoką 🏁</button></div>`:""}`;
}
function atsakyti(i,j,el){
  testoAts[i]=j; const teis=j===PAM.testas[i].t;
  const r=el.getBoundingClientRect(); piestiTesta();
  if(teis){ const d=document.createElement("div"); d.style.cssText=`position:fixed;left:${r.left/zoomas()}px;top:${r.top/zoomas()}px;width:${r.width/zoomas()}px;height:1px`; document.body.appendChild(d); pridetiXP(10,d); setTimeout(()=>d.remove(),50); }
}
function pabaiga(){
  const teis=testoAts.filter((a,i)=>a===PAM.testas[i].t).length, atl=(S.atlikta[PAM.id]||[]).length;
  if(atl>=PAM.zingsniai.length && PAM.id==="pirmoji-3d") duotiZenkleli("detale");
  const kita=INFO.pamokos[INFO.pamokos.indexOf(PAM)+1];
  if(teis===PAM.testas.length) duotiZenkleli("testas");
  { const siandien=dienaStr(new Date()); S.testai=S.testai||{}; S.baigta=S.baigta||{};          // ataskaitai dėstytojui
    const sen=S.testai[PAM.id]; if(!sen||teis>=sen.t) S.testai[PAM.id]={t:teis,n:PAM.testas.length,d:siandien};
    if(atl>=PAM.zingsniai.length&&!S.baigta[PAM.id]) S.baigta[PAM.id]=siandien; saugoti(); }
  konfeti(140);
  $("#vidus").innerHTML=`<div class="pabaiga"><div class="taure">🏆</div><h1>Pamoka baigta!</h1>
    <p>${esc(PAM.pabaiga||"Puikiai padirbėjai!")}</p>
    <div class="statai"><div><b>${atl}/${PAM.zingsniai.length}</b><small>žingsnių</small></div><div><b>${teis}/${PAM.testas.length}</b><small>teste</small></div><div><b>${S.xp}</b><small>XP iš viso</small></div></div>
    <p>${kita?`Kita pamoka: <b>${esc(kita.pavadinimas)}</b>`:"Baigei visas pamokas!"+(INFO.ateityje.length?" Netrukus: "+esc(INFO.ateityje.map(a=>a.pavadinimas).join(", "))+".":"")}</p>
    <div class="eil" style="justify-content:center;margin-top:18px">${kita?`<button class="btn pagr didelis" onclick="rodytiPradzia('${kita.id}')">Kita pamoka →</button><button class="btn" onclick="rodytiPradzia()">Į pradžią</button>`:`<button class="btn pagr didelis" onclick="rodytiPradzia()">Į pradžią</button>`}
    <button class="btn" onclick="if(confirm('Ištrinti visą progresą ir XP?')){S={xp:0,atlikta:{},zenkleliai:[],dabartinis:{},eq:S.eq,dienos:[],nauji:[],vardas:S.vardas};PAM=null;saugoti();rodytiPradzia(INFO.pamokos[0].id);}">Pradėti iš naujo</button></div></div>`;
}
function konfeti(n){
  const sp=["#e2362b","#ffc400","#1f4fd1","#111111"];
  for(let i=0;i<n;i++){const c=document.createElement("div");c.className="konfeti";c.style.left=Math.random()*100+"vw";c.style.background=sp[i%sp.length];
    c.style.animationDuration=(1.8+Math.random()*1.8)+"s";c.style.animationDelay=(Math.random()*.6)+"s";c.style.borderRadius=Math.random()<.5?"50%":"2px";
    document.body.appendChild(c);setTimeout(()=>c.remove(),4500);}
}

/* ---------- robotas gidas ---------- */
const Gidas = {
  taikinys:null, turas:null, turoNr:0, laikmatis:null, nuobodu:null, sekmes:0, nesekmes:{},
  ijungtas(){ return sg("cadet_gidas")!=="ne"; },
  perjungti(){ sg("cadet_gidas", this.ijungtas()?"ne":"taip"); this.piestiJungikli(); if(!this.ijungtas()) this.slepti(true); else this.rodyti({tekstas:"Sveikas sugrįžęs! Vėl būsiu šalia ir parodysiu, kur spausti. 🤖", auto:3500}); },
  piestiJungikli(){ const b=$("#gidoJungiklis"); b.textContent=this.ijungtas()?"🤖 Gidas: įj.":"🤖 Gidas: išj."; b.classList.toggle("ij",this.ijungtas()); },

  /* tekstas, taikinys (CSS selektorius), mygtukai [[tekstas, funkcija, klasė]], tamsinti, auto (ms) */
  rodyti(o){
    if(!this.ijungtas() && !o.privaloma) return;
    clearTimeout(this.laikmatis);
    this.o=o; this.taikinys=o.taikinys||null;
    const g=$("#gidas");
    g.querySelector(".g-tekstas").innerHTML=o.tekstas;
    const m=g.querySelector(".g-mygt");
    m.innerHTML=(o.mygtukai||[]).map((x,i)=>`<button class="${x[2]||"g-toliau"}" data-i="${i}">${x[0]}</button>`).join("")+(o.zingsnis?`<small>${o.zingsnis}</small>`:"");
    m.querySelectorAll("button").forEach(b=>b.onclick=()=>o.mygtukai[b.dataset.i][1]());
    m.classList.toggle("hidden",!m.innerHTML);
    g.classList.remove("hidden","slepiasi"); void g.offsetWidth; g.classList.add("rodo");
    Robotas.kalbeti(o.tekstas);
    const el=this.el();
    if(el) el.scrollIntoView({block:"center",behavior:"smooth"});
    setTimeout(()=>this.pozicija(),el?320:0); this.pozicija();
    if(o.auto) this.laikmatis=setTimeout(()=>this.slepti(),o.auto);
  },
  el(){ const e=this.taikinys ? document.querySelector(this.taikinys) : null; return e&&e.getClientRects().length?e:null; },
  slepti(rankiniu){
    clearTimeout(this.laikmatis);
    const g=$("#gidas"); if(g.classList.contains("hidden")) return;
    if(rankiniu && this.turas){ this.turas=null; }
    g.classList.remove("rodo"); g.classList.add("slepiasi");
    $("#gidoZiedas").classList.add("hidden"); $("#gidoRodykle").classList.add("hidden");
    setTimeout(()=>{ if(g.classList.contains("slepiasi")) g.classList.add("hidden"); },250);
    this.taikinys=null; this.o=null;
  },
  atnaujinti(){ if(this.o) setTimeout(()=>this.pozicija(),0); },
  pozicija(){
    const g=$("#gidas"); if(g.classList.contains("hidden")||!this.o) return;
    const zied=$("#gidoZiedas"), rod=$("#gidoRodykle"), el=this.el();
    const z=parseFloat(document.body.style.zoom)||1;      // padidintas šriftas: koordinatės dalinamos iš mastelio
    const W=innerWidth/z, H=innerHeight/z, gw=g.offsetWidth, gh=g.offsetHeight, tarp=58;
    if(!el){                                     // be taikinio - apačioje dešinėje
      zied.classList.add("hidden"); rod.classList.add("hidden");
      g.style.left=(W-gw-28)+"px"; g.style.top=(H-gh-28)+"px"; return;
    }
    const R=el.getBoundingClientRect(), p=6;
    const r={left:R.left/z,top:R.top/z,right:R.right/z,bottom:R.bottom/z,width:R.width/z,height:R.height/z};
    zied.classList.remove("hidden"); zied.classList.toggle("tamsu",!!this.o.tamsinti);
    Object.assign(zied.style,{left:(r.left-p)+"px",top:(r.top-p)+"px",width:(r.width+2*p)+"px",height:(r.height+2*p)+"px"});
    const telpa=(x,y)=>x>=8&&y>=8&&x+gw<=W-8&&y+gh<=H-8;
    const cx=Math.min(Math.max(r.left+r.width/2-gw/2,8),W-gw-8), cy=Math.min(Math.max(r.top+r.height/2-gh/2,8),H-gh-8);
    const var_=[["apacia",cx,r.bottom+tarp],["virsus",cx,r.top-gh-tarp],["desine",r.right+tarp,cy],["kaire",r.left-gw-tarp,cy]];
    let [kur,x,y]=var_.find(v=>telpa(v[1],v[2]))||["apacia",cx,Math.min(r.bottom+tarp,H-gh-8)];
    g.style.left=x+"px"; g.style.top=y+"px";
    // rodyklė tarp gido ir taikinio, nukreipta į taikinį
    const kampas={apacia:-90,virsus:90,desine:180,kaire:0}[kur];
    let ax,ay;
    if(kur==="apacia"){ax=Math.min(Math.max(r.left+r.width/2,x+20),x+gw-20)-22;ay=r.bottom+8;}
    if(kur==="virsus"){ax=Math.min(Math.max(r.left+r.width/2,x+20),x+gw-20)-22;ay=r.top-52;}
    if(kur==="desine"){ax=r.right+8;ay=r.top+r.height/2-22;}
    if(kur==="kaire"){ax=r.left-52;ay=r.top+r.height/2-22;}
    rod.classList.remove("hidden"); Object.assign(rod.style,{left:ax+"px",top:ay+"px",transform:`rotate(${kampas}deg)`});
  },

  /* ---- turai ---- */
  pradetiTura(zingsniai, raktas){
    if(!this.ijungtas()) return;
    zingsniai=zingsniai.filter(z=>!z.taikinys||matomas(z.taikinys));
    this.turas={zingsniai,raktas}; this.turoNr=0; this.turoZingsnis();
  },
  turoZingsnis(){
    const t=this.turas; if(!t) return;
    const z=t.zingsniai[this.turoNr]; if(!z){ this.baigtiTura(); return; }
    if(z.taikinys && !matomas(z.taikinys)){ this.turoNr++; return this.turoZingsnis(); }
    const pask=this.turoNr===t.zingsniai.length-1;
    this.rodyti({tekstas:z.tekstas, taikinys:z.taikinys, tamsinti:true, zingsnis:`${this.turoNr+1}/${t.zingsniai.length}`,
      mygtukai:[[pask?(z.paskutinis||"Supratau! 👍"):"Toliau →",()=>{this.turoNr++;this.turoZingsnis();if(pask&&z.veiksmas)z.veiksmas();}],
                ...(pask?[]:[["Praleisti",()=>this.baigtiTura(),"g-praleisti"]])]});
  },
  baigtiTura(){ if(this.turas) sg(this.turas.raktas,"taip"); this.turas=null; this.slepti(); },
  turasIsNaujo(){
    sg("cadet_gidas","taip"); this.piestiJungikli();
    if(document.querySelector("#korta")) this.pradetiTura(this.ZINGSNIO_TURAS,"cadet_turas_zingsnis");
    else this.pradetiTura(this.PRADZIOS_TURAS,"cadet_turas");
  },
  PRADZIOS_TURAS:[
    {tekstas:"<b>Labas! Aš Brėžly</b> - tavo braižymo mokymosi draugas. 🤖<br>Braižysi tu pats, o aš parodysiu, kur ką spausti, ir patikrinsiu tavo darbą."},
    {taikinys:".zaidejas", tekstas:"Čia tavo <b>lygis ir XP</b>. Už kiekvieną teisingą žingsnį gausi taškų, o už ypatingus pasiekimus - ženklelių 🏆"},
    {taikinys:"#busena", tekstas:"Čia matai, ar esu prisijungęs prie <b>AutoCAD</b>. Žalias taškas - viskas gerai. Jei raudonas - spausk mygtuką šalia, padėsiu."},
    {taikinys:"#kompBtn", tekstas:"Patarimas: spausk <b>📌 Šalia AutoCAD</b> - tapsiu siauru langu dešinėje ir visada būsiu matomas, kol braižai."},
    {taikinys:"#naujasBtn", tekstas:"Prieš pamoką spausk čia - atidarysiu <b>naują švarų brėžinį</b> iš acadiso.dwt, kad niekas netrukdytų."},
    {taikinys:"#pradetiBtn", tekstas:"O kai būsi pasiruošęs - <b>spausk čia</b> ir pradedam! 🚀", paskutinis:"Pradedam! 🚀",
     veiksmas:()=>pradeti(S.dabartinis[PAM.id]||0)},
  ],
  ZINGSNIO_TURAS:[
    {taikinys:".progresas", tekstas:"Šie langeliai - pamokos žingsniai. <b>✓</b> - atlikta, <b>juodas</b> - dabar. Spustelėk bet kurį - nueisi į tą žingsnį."},
    {taikinys:".kodel", tekstas:"Visada perskaityk <b>„Kodėl?“</b> - taip suprasi, ne tik atkartosi."},
    {taikinys:"#komandos", tekstas:"Čia - lyg AutoCAD komandų eilutė. <b>Geltoni</b> žodžiai - ką tau įvesti AutoCAD'e. <i>Mėlyni kursyvu</i> - ką padaryti pele. Užvedęs pelę gali <b>Kopijuoti</b>."},
    {taikinys:"#tikrinti", tekstas:"Aš <b>stebiu tavo brėžinį</b> - kai padarysi, pastebėsiu pats. Jei nori sužinoti, kas dar ne taip - spausk <b>Patikrinti</b>."},
    {taikinys:"#uzuominaBtn", tekstas:"Įstrigai? Čia <b>užuomina</b> 💡 Kiekviena atima šiek tiek XP, bet tai visai normalu."},
    {taikinys:"#parodykBtn", tekstas:"O jei visai nesiseka - <b>Parodyk man</b>: padarysiu šį žingsnį pats, o tu žiūrėk į AutoCAD.", paskutinis:"Aišku, braižau! ✏️"},
  ],

  /* ---- reakcijos ---- */
  pradzia(){ this.piestiJungikli(); if(!sg("cadet_turas") && sg("vedlys")) setTimeout(()=>this.pradetiTura(this.PRADZIOS_TURAS,"cadet_turas"),2900); },
  zingsnioPradzia(nr){
    clearTimeout(this.nuobodu);
    if(!sg("cadet_turas_zingsnis")){ setTimeout(()=>this.pradetiTura(this.ZINGSNIO_TURAS,"cadet_turas_zingsnis"),450); return; }
    const z=PAM.zingsniai[nr];
    if($("#busena").classList.contains("blogai"))
      return setTimeout(()=>this.rodyti({taikinys:"#busena button", tekstas:"Oi, aš nematau AutoCAD! Spausk čia - padėsiu prisijungti, kitaip negalėsiu patikrinti."}),500);
    if(z.komandos.length && nr<=2) setTimeout(()=>this.rodyti({taikinys:"#komandos", tekstas:"Įvesk šiuos atsakymus AutoCAD komandų eilutėje <b>vieną po kito</b>, po kiekvieno - Enter.", auto:6000}),500);
    this.laukti();
  },
  laukti(){
    clearTimeout(this.nuobodu);
    this.nuobodu=setTimeout(()=>{ if(document.querySelector("#tikrinti")&&!this.o)
      this.rodyti({taikinys:"#tikrinti", tekstas:"Jau nubraižei? 👀 Spausk <b>Patikrinti</b> - pažiūrėsiu!<br>O jei įstrigai - gali paimti užuominą.", auto:9000}); }, 90000);
  },
  veiksmas(){ this.laukti(); },
  nepavyko(z){
    const k=(this.nesekmes[z.id]=(this.nesekmes[z.id]||0)+1);
    if(k===1) return setTimeout(()=>this.rodyti({taikinys:"#atsakas", tekstas:"Ne bėda! Perskaityk, <b>ką radau tavo brėžinyje</b> - ten parašiau, kas ne taip. Pataisyk ir tikrink dar kartą.", auto:7000}),300);
    const likoUz = uzuominuRodyta < z.uzuominos.length;
    if(likoUz) setTimeout(()=>this.rodyti({taikinys:"#uzuominaBtn", tekstas:"Nepasiduok! 💪 Gal paimk <b>užuominą</b>?", mygtukai:[["Rodyk užuominą 💡",()=>{this.slepti();uzuomina();}],["Bandysiu pats",()=>this.slepti(),"g-praleisti"]]}),300);
    else if(z.demonstruojama) setTimeout(()=>this.rodyti({taikinys:"#parodykBtn", tekstas:"Užuominos baigėsi. Spausk <b>Parodyk man</b> - padarysiu pats, o tu stebėk AutoCAD. Kitą kartą tikrai pavyks!"}),300);
  },
  pavyko(){
    clearTimeout(this.nuobodu); this.sekmes++;
    if(this.sekmes<=2) setTimeout(()=>this.rodyti({taikinys:"#kitasBtn", tekstas:["Šaunu! 🎉 Spausk čia ir eime toliau.","Puikiai sekasi! Kitas žingsnis - čia."][this.sekmes-1], auto:5000}),700);
  },
};
addEventListener("resize",()=>Gidas.atnaujinti());
document.addEventListener("scroll",()=>Gidas.atnaujinti(),true);

/* ---------- ryšys ---------- */
let BUS={};
async function tikrintiBusena(){
  const b=$("#busena"), info=$("#busenaInfo");
  try{ BUS=await api("/api/busena"); }catch(e){ b.className="busena blogai"; b.querySelector(".txt").textContent="Brėžly neatsako"; $("#vTsk").className="v-tsk blogai"; return; }
  const r=BUS, mygt=b.querySelector("button");
  const klase=r.prisijungta?(r.be_brezinio||r.uzimtas?"ispejimas":"gerai"):"blogai";
  b.className="busena "+klase; $("#vTsk").className="v-tsk "+klase;
  info.classList.add("hidden"); info.title="";
  poBusenos();
  if(r.prisijungta){
    if(r.be_brezinio){ b.querySelector(".txt").textContent="AutoCAD · nėra brėžinio"; mygt.textContent="Naujas"; mygt.title="Sukurti naują brėžinį AutoCAD'e"; return; }
    b.querySelector(".txt").textContent=r.uzimtas?"AutoCAD užimtas (Esc)":`AutoCAD · ${r.brezinys}`; mygt.textContent="↻"; mygt.title="Prisijungti iš naujo";
    if(r.kalba && sg("pabr")===null){ sg("pabr", r.kalba.toUpperCase()==="ENU"?"0":"1"); if(document.querySelector("#komandos")) piestiZingsni(); }
    return;
  }
  let txt="AutoCAD neprijungtas", m="Jungtis", pag="";
  const pr=r.priezastis||"";
  if(r.paleidziamas){ txt="Paleidžiamas AutoCAD..."; m="⏳"; pag="Tai gali užtrukti iki minutės."; }
  else if(pr==="pywin32"){ txt="Trūksta pywin32"; m="Kodėl?"; pag=r.paaiskinimas; }
  else if(r.lt_veikia || (r.lt_idiegtas && !r.pilnas_idiegtas)){ txt="Rastas AutoCAD LT"; m="Kodėl?"; pag="AutoCAD LT neleidžia programoms valdyti brėžinio, todėl Brėžly negali jo patikrinti. Reikia pilno AutoCAD (studentams nemokamas)."; }
  else if(pr==="teises_acad"||pr==="teises_brezly"){ txt="Kitos teisės (admin)"; m="Kodėl?"; pag=r.paaiskinimas; }
  else if(pr==="kraunasi"){ txt="AutoCAD dar neatsiliepia"; m="Jungtis"; pag=r.paaiskinimas; }
  else if(pr==="uzimtas"){ txt="AutoCAD užimtas"; m="Jungtis"; pag=r.paaiskinimas; }
  else if(pr==="neregistruotas"){ txt="AutoCAD nepasiekiamas"; m="Kodėl?"; pag=r.paaiskinimas; }
  else if(r.windows && !r.pilnas_idiegtas && !r.pilnas_veikia){ txt="AutoCAD nerastas"; m="Kaip gauti?"; }
  else if(r.pilnas_idiegtas && !r.pilnas_veikia){ txt="AutoCAD neatidarytas"; m="Atidaryti"; }
  else if(pr==="kita"){ pag=r.paaiskinimas; }
  b.querySelector(".txt").textContent=txt; mygt.textContent=m; mygt.title="";
  if(pag){ info.textContent=pag; if(r.klaida) info.title=r.klaida; info.classList.remove("hidden"); }
}
async function busenosVeiksmas(){
  const r=BUS||{}, pr=r.priezastis||"";
  if(r.prisijungta && r.be_brezinio){ await naujasBrezinys(); return tikrintiBusena(); }
  if(r.prisijungta || !r.windows) return prisijungti();
  if(r.paleidziamas) return;
  if(pr==="pywin32"||pr==="teises_acad"||pr==="teises_brezly"||pr==="neregistruotas") return rodytiLangeli(`<h2>Kodėl neprisijungia?</h2>
    <p>${esc(r.paaiskinimas)}</p>${r.klaida?`<p class="klaidos-kodas">Klaidos kodas: <code>${esc(r.klaida)}</code></p>`:""}
    <div class="eil"><button class="btn pagr" onclick="uzdarytiLangeli();prisijungti()">Bandyti dar kartą</button><button class="btn" onclick="uzdarytiLangeli()">Uždaryti</button></div>`);
  if(r.lt_veikia || (r.lt_idiegtas && !r.pilnas_idiegtas)) return rodytiLangeli(`<h2>AutoCAD LT nepalaikomas</h2>
    <p>Brėžly tikrina tavo brėžinį per AutoCAD programavimo sąsają (COM). <b>AutoCAD LT</b> jos neturi, todėl su juo Brėžly gali tik rodyti pamokas, bet ne tikrinti.</p>
    <p>Studentams <b>pilnas AutoCAD nemokamas</b> - jį gausi per „Autodesk Education“ svetainę su universiteto el. paštu.</p>
    <div class="eil"><button class="btn pagr" onclick="uzdarytiLangeli()">Supratau</button></div>`);
  if(!r.pilnas_idiegtas && !r.pilnas_veikia && !pr.match(/kraunasi|uzimtas|kita/)) return rodytiLangeli(`<h2>AutoCAD nerastas</h2>
    <p>Šiame kompiuteryje neradau įdiegto AutoCAD. Studentams jis <b>nemokamas</b> - ieškok „Autodesk Education AutoCAD“ ir prisiregistruok su universiteto el. paštu.</p>
    <p>Jei AutoCAD įdiegtas, bet aš jo nerandu - atsidaryk jį pats ir spausk „Bandyti dar kartą“.</p>
    <div class="eil"><button class="btn pagr" onclick="uzdarytiLangeli();prisijungti()">Bandyti dar kartą</button><button class="btn" onclick="uzdarytiLangeli()">Uždaryti</button></div>`);
  if(r.pilnas_idiegtas && !r.pilnas_veikia && pr==="neatidarytas"){
    const a=await api("/api/paleisti_autocad",{}); if(!a.ok){pranesti(a.klaida);return;}
    pranesti("Paleidžiu AutoCAD - tai gali užtrukti iki minutės ⏳"); tikrintiBusena(); return;
  }
  prisijungti();
}
async function prisijungti(){$("#busena .txt").textContent="Jungiamasi...";let r;try{r=await api("/api/prisijungti",{});}catch(e){r={ok:false,klaida:"Brėžly neatsako"};}if(!r.ok)pranesti("Nepavyko: "+r.klaida);tikrintiBusena();}
function rodytiPatarima(){ const el=$("#patarimas"); if(el) el.textContent=INFO.patarimai[Math.floor(Math.random()*INFO.patarimai.length)]; }

/* =================== PROGRESAS FAILE =================== */
async function ikeltiProgresa(){
  let r=null; try{ r=await api("/api/progresas"); }catch(e){}
  if(r&&r.yra){
    if(r.S) S=Object.assign(S,r.S);
    NUST=r.nustatymai||{};
    for(const [k,v] of Object.entries(NUST)){ try{localStorage.setItem(k,v);}catch(e){} }
  } else {                                    // pirmas kartas su failu - perkeliam iš naršyklės atminties
    ikelti();
    ["tema","cadet_turas","cadet_turas_zingsnis","cadet_gidas"].forEach(k=>{let v=null;try{v=localStorage.getItem(k);}catch(e){} if(v!==null)NUST[k]=v;});
    if(S.xp||Object.keys(S.atlikta||{}).length) NUST.vedlys="1";
    planuotiSaugojima(true);
  }
}
function matomas(sel){ const e=document.querySelector(sel); return !!(e&&e.getClientRects().length); }
function mesk(a){ a=[...a]; for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];} return a; }
/* Ne anglų kalbos AutoCAD: komandos su „_“ priekyje veikia bet kurioje kalboje */
function komandosTekstas(pr,iv){ return sg("pabr")==="1" && /^Command/i.test(pr) && /^[A-Z][A-Z0-9]+$/.test(iv) ? "_"+iv : iv; }

/* =================== LANGELIS (modalinis) =================== */
function rodytiLangeli(html,uzdaromas=true){
  const l=$("#langelis"); l.innerHTML=`<div class="lang" role="dialog" aria-modal="true">${html}</div>`;
  l.classList.remove("hidden"); l.onclick=e=>{ if(uzdaromas&&e.target===l) uzdarytiLangeli(); };
  Gidas.slepti(); setTimeout(()=>l.querySelector("input,textarea,button")?.focus(),60);
}
function uzdarytiLangeli(){ const l=$("#langelis"); l.classList.add("hidden"); l.innerHTML=""; }
addEventListener("keydown",e=>{ if(e.key==="Escape" && !$("#langelis").classList.contains("hidden") && $("#langelis").onclick) uzdarytiLangeli(); });
// Pamokoje Brėžly lange: Enter - patikrinti arba eiti toliau, H - užuomina (ne rašant į laukelį ir ne ant mygtuko)
addEventListener("keydown",e=>{
  if(e.ctrlKey||e.altKey||e.metaKey||e.repeat||rodinys!=="pamoka"||!document.querySelector("#korta")) return;
  const t=e.target; if(t&&(["INPUT","TEXTAREA","SELECT","BUTTON","A"].includes(t.tagName)||t.isContentEditable)) return;
  if(!$("#langelis").classList.contains("hidden")||!$("#atlygis").classList.contains("hidden")) return;
  const spausti=id=>{ const b=$(id); if(b&&!b.disabled){ e.preventDefault(); b.click(); return true; } return false; };
  if(e.key==="Enter") spausti("#kitasBtn")||spausti("#tikrinti");
  else if(e.key==="h"||e.key==="H") spausti("#uzuominaBtn");
});

/* =================== AUTOMATINIS TIKRINIMAS =================== */
/* Įskaito tik tada, kai pirma matė „dar ne“, o paskui „taip“ - kad žingsnis nebūtų įskaitytas vien todėl, kad brėžinyje jau kažkas yra. */
const auto={
  matytaNe:false, raktas:null, vyksta:false,
  ijungtas(){ return sg("auto")!=="0"; },
  reset(){ this.matytaNe=false; this.raktas=null; },
  html(){
    return this.ijungtas()
      ? `<div class="stebiu" id="stebiu"><span class="akis"></span><span>Stebiu tavo brėžinį - kai padarysi, pastebėsiu pats.</span><button onclick="auto.perjungti()">Išjungti</button></div>`
      : `<div class="stebiu"><span>Automatinis tikrinimas išjungtas - spausk „Patikrinti“.</span><button onclick="auto.perjungti()">Įjungti</button></div>`;
  },
  perjungti(){ sg("auto",this.ijungtas()?"0":"1"); if(document.querySelector("#korta")) piestiZingsni(); if(rodinys==="nustatymai") rodytiNustatymus(); },
  async tikrinti(){
    if(this.vyksta||!this.ijungtas()||tikrina||rodinys!=="pamoka"||!PAM||!document.querySelector("#korta")||!BUS.prisijungta||BUS.be_brezinio||BUS.uzimtas) return;
    if(!$("#langelis").classList.contains("hidden")||!$("#atlygis").classList.contains("hidden")) return;
    const nr=S.dabartinis[PAM.id], z=PAM.zingsniai[nr];
    if(!z||!z.tikrinama||(S.atlikta[PAM.id]||[]).includes(z.id)) return;
    const raktas=PAM.id+"/"+nr; if(this.raktas!==raktas){ this.raktas=raktas; this.matytaNe=false; }
    this.vyksta=true; let r;
    try{ r=await api("/api/tikrinti",{pamoka:PAM.id,zingsnis:nr,tyliai:true}); }catch(e){ return; } finally{ this.vyksta=false; }
    if(this.raktas!==raktas||tikrina||!r.ok||r.laukia) return;
    if(!r.teisingai){ this.matytaNe=true; return; }
    if(this.matytaNe||demo) tikrinti(true);
  }
};

/* =================== LANGO REŽIMAI: didelis / šalia AutoCAD / mini =================== */
function langoRez(){ return sg("langas_rez")||(sg("kompakt")==="1"?"kompaktiskas":"iprastas"); }
function miniIjungtas(){ return document.body.classList.contains("mini-rez"); }
async function langoRezimas(rez,tyliai){
  sg("langas_rez",rez); sg("kompakt",rez==="kompaktiskas"?"1":"0");
  document.body.classList.toggle("mini-rez",rez==="mini");
  if(rez==="mini") miniPiesti(); else taikytiDydi();
  let r; try{ r=await api("/api/langas",{rezimas:rez,acad:sg("acad_isd")!=="0"}); }catch(e){ r={ok:false}; }
  if(!r.ok){ if(!tyliai&&INFO.windows) pranesti(r.klaida||"Nepavyko pakeisti lango"); }
  else if(!tyliai){
    if(rez==="kompaktiskas") pranesti(r.acad?"📌 Brėžly dešinėje, AutoCAD - kairėje. Niekas neuždengta.":"📌 Būsiu šalia AutoCAD. Kai atidarysi AutoCAD, sutvarkysiu ir jo langą.");
    if(rez==="mini") pranesti("▫ Mini kortelė. Tikrinti galima ir iš AutoCAD: Ctrl+Alt+T");
  }
  if(rodinys==="nustatymai") rodytiNustatymus();
  piestiApacia();
}
async function kompaktiskas(on,tyliai){ return langoRezimas(on?"kompaktiskas":"iprastas",tyliai); }
/* AutoCAD atsidarė vėliau - sutvarkom ir jo langą */
let buvoPrisijungta=false;
function poBusenos(){
  if(BUS.prisijungta&&!buvoPrisijungta&&langoRez()==="kompaktiskas"&&sg("acad_isd")!=="0") api("/api/langas",{rezimas:"kompaktiskas",acad:true}).catch(()=>{});
  buvoPrisijungta=!!BUS.prisijungta;
}

/* ---- mini kortelė: tik tai, ko reikia braižant ---- */
let miniTikrina=false;
function tekstasIsHtml(h){ const d=document.createElement("div"); d.innerHTML=h||""; return d.textContent.replace(/\s+/g," ").trim(); }
function miniPiesti(){
  const el=$("#mini"); if(!el) return;
  const virsus=(t,sub)=>`<div class="mi-v">${avataroMini("","m")}<div class="t"><b>${esc(t)}</b><small>${esc(sub)}</small></div>
    <button onclick="langoRezimas('kompaktiskas')" title="Šalia AutoCAD" aria-label="Šalia AutoCAD">📌</button><button onclick="langoRezimas('iprastas')" title="Didelis langas" aria-label="Didelis langas">⇱</button></div>`;
  const pastaba=`<div class="mi-pastaba">Ctrl+Alt+T - patikrinti net neišeinant iš AutoCAD · Ctrl+Alt+B - parodyti Brėžly</div>`;
  if(rodinys==="pamoka"&&PAM){
    const nr=S.dabartinis[PAM.id]||0, z=PAM.zingsniai[nr], atl=(S.atlikta[PAM.id]||[]).includes(z.id);
    const kom=(z.komandos||[]).slice(0,4).map(([pr,iv0])=>{const iv=komandosTekstas(pr,iv0);return `<code>${esc(iv)}</code>`;}).join("");
    const ats=paskutinisAtsakas?tekstasIsHtml(paskutinisAtsakas).replace(/Kitas žingsnis →|Į testą →/,"").slice(0,170):"";
    const gerai=paskutinisAtsakas&&paskutinisAtsakas.includes("atsakas gerai");
    el.innerHTML=virsus(`${nr+1}/${PAM.zingsniai.length} · ${z.pavadinimas}`,`${PAM.pavadinimas}${atl?" · ✓ atlikta":""}`)+
      `<div class="mi-tikslas">${z.tikslas?`🎯 <b>${esc(z.tikslas)}</b>`:esc(z.zingsniai[0]||"")}</div>
      ${kom?`<div class="mi-kom">${kom}</div>`:""}
      <div class="mi-veiks">
        ${gerai?`<button class="btn zalias pagr" onclick="toliau()">${nr<PAM.zingsniai.length-1?"Kitas žingsnis →":"Į testą →"}</button>`
          :`<button class="btn pagr" onclick="tikrinti()" ${tikrina?"disabled":""}>${tikrina?'<span class="sukasi"></span>Tikrinu...':(z.tikrinama?"✓ Patikrinti":"✓ Atlikau")}</button>`}
        <button class="btn" onclick="uzuomina()" title="Užuomina" aria-label="Užuomina" ${uzuominuRodyta>=z.uzuominos.length?"disabled":""}>💡</button>
        ${gerai?"":`<button class="btn" onclick="toliau()" title="Praleisti" aria-label="Praleisti">→</button>`}
      </div>
      ${ats?`<div class="mi-ats ${gerai?"gerai":"blogai"}">${esc(ats)}</div>`:""}
      ${uzuominuRodyta?`<div class="mi-ats">💡 ${esc(z.uzuominos[uzuominuRodyta-1])}</div>`:""}`+pastaba;
    return;
  }
  if(rodinys==="praktika"&&prDabar){
    const u=PRAKTIKA.find(x=>x.id===prDabar), r=prPaskutinis[prDabar];
    el.innerHTML=virsus(`Praktika ${u.nr}. ${u.pav}`,`${u.d} · ${u.fmt}${prAtlikta(u.id)?" · ✓ atlikta":""}`)+
      `<div class="mi-tikslas">${esc(u.uzd)}</div>
      <div class="mi-kom">${u.kom.map(k=>`<code class="pr">${esc(k)}</code>`).join("")}</div>
      <div class="mi-veiks"><button class="btn pagr" onclick="prTikrinti('${u.id}')">✓ Patikrinti</button><button class="btn" onclick="prAtidaryti('${u.id}','ruosinys')" title="Tuščias lapas AutoCAD'e" aria-label="Tuščias lapas">▶</button></div>
      ${r?`<div class="mi-ats ${r.teisingai?"gerai":"blogai"}">${r.teisingai?"✓ Puiku! Brėžinys atitinka užduotį.":esc(r.pastabos.join(" "))}</div>`:""}`+pastaba;
    return;
  }
  el.innerHTML=virsus("Brėžly","Mini kortelė")+`<div class="mi-tikslas">Atidaryk pamoką ar praktikos užduotį - čia matysi dabartinį žingsnį ir mygtuką „Patikrinti“.</div>
    <div class="mi-veiks"><button class="btn pagr" onclick="langoRezimas('kompaktiskas')">📌 Atidaryti pamokas</button></div>`+pastaba;
}
function rodytiAtsaka(){ const a=$("#atsakas"); if(a&&a.firstElementChild) a.scrollIntoView({block:"nearest",behavior:"smooth"}); }

/* ---- spartieji klavišai iš AutoCAD (serveris juos pagauna ir praneša čia) ---- */
let ivykN=-1;
async function tikrintiIvykius(){
  let r; try{ r=await api("/api/ivykiai",{nuo:Math.max(0,ivykN)}); }catch(e){ return; }
  if(!r.ok) return;
  if(ivykN<0){ ivykN=r.n; return; }          // seni įvykiai - ignoruojam
  ivykN=r.n;
  for(const e of r.ivykiai){
    if(e.veiksmas==="tikrinti"){
      if(rodinys==="pamoka"&&PAM){ if(!tikrina) tikrinti(); }
      else if(rodinys==="praktika"&&prDabar) prTikrinti(prDabar);
      else pranesti("Ctrl+Alt+T: atidaryk pamokos žingsnį ar praktikos užduotį");
    }
    if(e.veiksmas==="mini") langoRezimas(miniIjungtas()?"kompaktiskas":"mini",true);
  }
}

/* =================== PRAKTIKA (0.8): 2D A4, 3D A3 =================== */
let PRAKTIKA=[];      /* praktikos užduotys - iš praktika/uzduotys.json (ateina per /api/info) */
let prFiltras="visos", prDabar=null, prPaskutinis={};
function prAtlikta(id){ return !!(S.praktika||{})[id]; }
function prZvaigzd(n){ return "★".repeat(n)+"☆".repeat(3-n); }
function rodytiPraktika(){
  if(Egzaminas.dabar()) return Egzaminas.rodyti();
  nustatytiRodini("praktika"); prDabar=null; $("#vPam").textContent="Praktika";
  if(!sg("praktika_matyta")){ sg("praktika_matyta","1"); $("#praktikosTaskelis").classList.add("hidden"); }
  const sar=PRAKTIKA.filter(u=>prFiltras==="visos"||u.fmt===prFiltras), atl=PRAKTIKA.filter(u=>prAtlikta(u.id)).length;
  $("#vidus").innerHTML=`<h1 class="ant1">Praktika</h1><p class="po1">Tikri brėžiniai su rėmeliu: 2D - A4 lapas, 3D - A3 lapas. Atidaryk tuščią lapą AutoCAD'e, nubraižyk ir aš patikrinsiu.</p>
  <div class="pr-filtr">${[["visos","Visos"],["A4","2D · A4"],["A3","3D · A3"]].map(([v,t])=>`<button aria-pressed="${prFiltras===v}" onclick="prFiltras='${v}';rodytiPraktika()">${t}</button>`).join("")}
    <div class="pr-eiga"><span>Atlikta ${atl} iš ${PRAKTIKA.length}</span><div class="juosta"><i style="width:${atl/PRAKTIKA.length*100}%"></i></div></div></div>
  ${Egzaminas.juostaHTML()}
  ${issukiuSekcija()}
  <div class="pr-tink">${sar.map(u=>`<button class="pr-k" onclick="rodytiUzduoti('${u.id}')" aria-label="${u.nr}. ${esc(u.pav)}, ${u.fmt}${prAtlikta(u.id)?", atlikta":""}">
    <div class="pr-lap"><img src="/praktika/${u.id}.svg" alt="" loading="lazy"></div>
    <span class="pr-fmt ${u.fmt==="A3"?"a3":""}">${u.d} · ${u.fmt}</span>${prAtlikta(u.id)?'<span class="pr-ok">✓</span>':""}
    <b>${u.nr}. ${esc(u.pav)}</b><small>${prZvaigzd(u.lyg)} · ~${u.min} min · +${u.xp} XP</small></button>`).join("")}</div>`;
}
function rodytiUzduoti(id){
  if(Egzaminas.dabar()) return Egzaminas.rodyti();
  const u=PRAKTIKA.find(x=>x.id===id); if(!u) return rodytiPraktika();
  nustatytiRodini("praktika"); prDabar=id; $("#vPam").textContent=`Praktika ${u.nr}. ${u.pav}`;
  const i=PRAKTIKA.indexOf(u), kitas=PRAKTIKA[i+1], ats=prPaskutinis[id];
  $("#vidus").innerHTML=`<div class="eil" style="margin-bottom:14px"><button class="btn" onclick="rodytiPraktika()">← Visos užduotys</button><span class="tarpas"></span>
    ${prAtlikta(id)?'<span class="zyme t">✓ Atlikta</span>':""}<span class="zyme">${u.d} · ${u.fmt}</span><span class="zyme t">~${u.min} min</span><span class="zyme">+${u.xp} XP</span></div>
  <div class="pr-det">
    <div class="pr-lap" onclick="prDidinti('${id}')" title="Spausk - padidinsiu"><img src="/praktika/${id}.svg" alt="Užduoties ${u.nr} brėžinys ${u.fmt} formatu"></div>
    <div class="pr-info">
      <div><h1 class="ant1" style="font-size:26px">${u.nr}. ${esc(u.pav)}</h1><p style="margin:6px 0 0;color:var(--muted)">${prZvaigzd(u.lyg)} · ${esc(u.uzd)}</p></div>
      <div class="pr-kom">${u.kom.map(k=>`<code>${esc(k)}</code>`).join("")}</div>
      <div><b style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)">Kaip daryti</b><ol class="pr-zingsn">${u.z.map(t=>`<li>${esc(t)}</li>`).join("")}</ol></div>
      <div class="pr-mygt">
        <button class="btn pagr didelis" id="prPradeti" onclick="prAtidaryti('${id}','ruosinys')">▶ Pradėti: tuščias ${u.fmt} lapas AutoCAD'e</button>
        <button class="btn" id="prTikr" onclick="prTikrinti('${id}')">✔ Patikrinti mano brėžinį</button>
        <div class="eil"><button class="btn" onclick="prAtidaryti('${id}','pavyzdys')" title="Atidaro atsakymą atskirame faile">👁 Pavyzdys AutoCAD'e</button>
          <button class="btn" onclick="prPDF('${id}')">🖨 Spausdinti (PDF)</button></div>
        <button class="btn" onclick="Egzaminas.pasirinkti('${id}')" title="Su laikmačiu, be užuominų ir pavyzdžio">⏱ Daryti kaip egzaminą</button>
      </div>
      <div id="prAts">${ats?prAtsHTML(ats):""}</div>
      ${kitas?`<button class="btn" style="align-self:flex-start" onclick="rodytiUzduoti('${kitas.id}')">Kita: ${kitas.nr}. ${esc(kitas.pav)} →</button>`:""}
    </div></div>`;
  if(miniIjungtas()) miniPiesti();
}
function prDidinti(id){ rodytiLangeli(`<div class="pr-didelis"><img src="/praktika/${id}.svg" alt="Brėžinys"></div><div class="eil" style="margin-top:12px"><span class="tarpas"></span><button class="btn" onclick="uzdarytiLangeli()">Uždaryti</button></div>`); document.querySelector("#langelis .lang").style.maxWidth="min(1100px,94vw)"; }
function prAtsHTML(r){
  return r.teisingai?`<div class="pr-ats gerai"><b>Puiku! Brėžinys atitinka užduotį. 🎉</b></div>`
    :`<div class="pr-ats blogai"><b>Dar ne viskas:</b><ul>${r.pastabos.map(p=>`<li>${esc(p)}</li>`).join("")}</ul></div>`;
}
async function prAtidaryti(id,kas){
  if(!BUS.prisijungta){ pranesti("Pirmiausia prisijunk prie AutoCAD (mygtukas apačioje kairėje)."); return; }
  pranesti(kas==="pavyzdys"?"Atidarau pavyzdį...":"Atidarau tuščią lapą...");
  let r; try{ r=await api("/api/praktika_atidaryti",{id,kas}); }catch(e){ r={ok:false}; }
  if(!r.ok){ pranesti(r.klaida||"Nepavyko atidaryti AutoCAD'e"); return; }
  pranesti(kas==="pavyzdys"?"Pavyzdys atidarytas. Braižyk tuščiame lape - „Pradėti“.":`Atidaryta: ${r.failas}. Braižyk rėmelio viduje, pabaigoje - „Patikrinti“.`);
  if(kas!=="pavyzdys") Robotas.reaguoti("moja",1500);
}
async function prPDF(id){ let r; try{ r=await api("/api/praktika_pdf",{id}); }catch(e){ r={ok:false}; } if(!r.ok) window.open(`/praktika/${id}.pdf`); }
async function prTikrinti(id){
  if(!BUS.prisijungta){ pranesti("Pirmiausia prisijunk prie AutoCAD."); return; }
  const u=PRAKTIKA.find(x=>x.id===id), btn=$("#prTikr"); btn.disabled=true; btn.textContent="Tikrinu...";
  let r; try{ r=await api("/api/praktika_tikrinti",{id}); }catch(e){ r={ok:false,klaida:"Ryšio klaida"}; }
  if(prDabar!==id) return;
  btn.disabled=false; btn.textContent="✔ Patikrinti mano brėžinį";
  if(!r.ok){ pranesti(r.klaida||"Nepavyko patikrinti"); return; }
  prPaskutinis[id]=r; $("#prAts").innerHTML=prAtsHTML(r); $("#prAts").scrollIntoView({block:"nearest",behavior:"smooth"}); if(miniIjungtas()) miniPiesti();
  if(!r.teisingai){ Robotas.reaguoti("liud",1400); return; }
  Robotas.reaguoti("dziaug",1500);
  if(!prAtlikta(id)){
    S.praktika={...(S.praktika||{}),[id]:new Date().toISOString().slice(0,10)}; pridetiXP(u.xp,btn); konfeti(70);
    const n=PRAKTIKA.filter(x=>prAtlikta(x.id)).length;
    if(n>=4) duotiZenkleli("praktikas");
    saugoti(); setTimeout(()=>{ if(prDabar===id&&rodinys==="praktika") rodytiUzduoti(id); },1600);
  }
}

/* =================== EGZAMINO REŽIMAS =================== */
/* Praktikos užduotis su laikmačiu: be „Kaip daryti“, komandų, pavyzdžio. Pabaigoje - tas pats tikrinimas. Būsena S.egz išlieka perkrovus. */
const Egzaminas={
  t:null,
  B(){ return S.egz||(S.egz={ist:[]}); },
  dabar(){ return (S.egz&&S.egz.dab)||null; },
  liko(){ const d=this.dabar(); return d?d.pradzia+d.min*60000-Date.now():0; },
  laikas(ms){ const s=Math.max(0,Math.round(ms/1000)); return `${Math.floor(s/60)}:${String(s%60).padStart(2,"0")}`; },
  rekom(u){ return Math.max(10,Math.ceil(u.min*1.5/5)*5); },
  juostaHTML(){
    const ist=this.B().ist.slice(0,5);
    return `<div class="egz-juosta"><div><b>⏱ Egzamino režimas</b><p>Užduotis su laikmačiu - be užuominų, komandų ir pavyzdžio. Kaip per tikrą atsiskaitymą.</p>
      ${ist.length?`<div class="egz-ist">${ist.map(r=>{const u=PRAKTIKA.find(x=>x.id===r.id);return `<span class="${r.iskaityta?"ok":"ne"}" title="${esc(u?u.pav:r.id)} · ${r.data}">${r.iskaityta?"✓":"✗"} ${u?u.nr:"?"}. ${this.laikas(r.sek*1000)} / ${r.min} min</span>`;}).join("")}</div>`:""}</div>
      <button class="btn pagr" onclick="Egzaminas.pasirinkti()">Pradėti egzaminą</button></div>`;
  },
  pasirinkti(id){
    if(this.dabar()){ pranesti("Egzaminas jau vyksta - pirmiausia jį baik arba nutrauk."); return this.rodyti(); }
    const u0=PRAKTIKA.find(x=>x.id===id);
    rodytiLangeli(`<h2 style="margin-top:0">⏱ Egzaminas</h2><p style="color:var(--muted);margin-top:0">Laikmatis prasidės, kai atidarysiu tuščią lapą AutoCAD'e. Užuominų, komandų ir pavyzdžio nebus - tik užduoties brėžinys. Baigęs spausk „Baigti ir patikrinti“.</p>
      <label class="egz-lauk">Užduotis<select id="egzUzd" onchange="Egzaminas.atnLaika()"><option value="">🎲 Atsitiktinė</option>${PRAKTIKA.map(u=>`<option value="${u.id}" ${u0&&u0.id===u.id?"selected":""}>${u.nr}. ${esc(u.pav)} · ${u.fmt}</option>`).join("")}</select></label>
      <label class="egz-lauk">Laikas<select id="egzMin"></select></label>
      <div class="eil" style="margin-top:16px"><span class="tarpas"></span><button class="btn" onclick="uzdarytiLangeli()">Atšaukti</button><button class="btn pagr" onclick="Egzaminas.pradeti()">▶ Pradėti</button></div>`);
    this.atnLaika();
  },
  atnLaika(){
    const u=PRAKTIKA.find(x=>x.id===$("#egzUzd").value), r=u?this.rekom(u):null;
    $("#egzMin").innerHTML=(r?`<option value="${r}">Rekomenduojama: ${r} min</option>`:`<option value="0">Pagal užduotį (~1,5 × numatyto)</option>`)+[15,30,45,60,90].map(m=>`<option value="${m}">${m} min</option>`).join("");
  },
  async pradeti(){
    if(!BUS.prisijungta){ pranesti("Pirmiausia prisijunk prie AutoCAD (mygtukas apačioje kairėje)."); return; }
    let id=$("#egzUzd").value; if(!id){ const ne=PRAKTIKA.filter(u=>!prAtlikta(u.id)); id=mesk(ne.length?ne:PRAKTIKA)[0].id; }
    const u=PRAKTIKA.find(x=>x.id===id), min=parseInt($("#egzMin").value)||this.rekom(u);
    uzdarytiLangeli(); pranesti("Atidarau tuščią lapą...");
    let r; try{ r=await api("/api/praktika_atidaryti",{id,kas:"ruosinys"}); }catch(e){ r={ok:false}; }
    if(!r.ok){ pranesti(r.klaida||"Nepavyko atidaryti AutoCAD'e"); return; }
    this.B().dab={id,pradzia:Date.now(),min}; saugoti();
    pranesti(`Egzaminas prasidėjo: ${min} min. Sėkmės!`); Robotas.reaguoti("moja",1500);
    this.rodyti(); this.ciklas();
  },
  rodyti(){
    const d=this.dabar(); if(!d) return rodytiPraktika();
    const u=PRAKTIKA.find(x=>x.id===d.id); if(!u){ delete this.B().dab; saugoti(); return rodytiPraktika(); }
    nustatytiRodini("praktika"); prDabar=null; $("#vPam").textContent="Egzaminas";
    $("#vidus").innerHTML=`<div class="egz-virsus"><div><small style="color:var(--muted)">Egzaminas · ${u.d} · ${u.fmt}</small><h1 class="ant1" style="font-size:26px;margin:2px 0 0">${u.nr}. ${esc(u.pav)}</h1></div>
      <span class="tarpas"></span><div class="egz-laikas" id="egzLaikas" role="timer" aria-label="Liko laiko">${this.laikas(this.liko())}</div></div>
      <div class="pr-det egz-det"><div class="pr-lap" onclick="prDidinti('${u.id}')" title="Spausk - padidinsiu"><img src="/praktika/${u.id}.svg" alt="Užduoties ${u.nr} brėžinys ${u.fmt} formatu"></div>
      <div class="pr-info"><p style="margin:0">${esc(u.uzd)}</p>
        <div class="pr-mygt"><button class="btn pagr didelis" id="egzBaigti" onclick="Egzaminas.baigti()">✔ Baigti ir patikrinti</button>
          <div class="eil"><button class="btn" onclick="prAtidaryti('${u.id}','ruosinys')">↻ Atidaryti lapą dar kartą</button><button class="btn" onclick="Egzaminas.nutraukti()">✕ Nutraukti</button></div></div>
        <p style="color:var(--muted);font-size:13px;margin:0">Laikas: ${d.min} min. Galima pereiti į kitus langus - laikmatis eis toliau.</p></div></div>`;
    this.ciklas();
  },
  ciklas(){
    clearInterval(this.t);
    const zenkl=()=>{ let z=$("#egzZyme"); const d=this.dabar();
      if(!d){ if(z) z.remove(); return; }
      if(!z){ z=document.createElement("button"); z.id="egzZyme"; z.className="egz-zyme"; z.onclick=()=>Egzaminas.rodyti(); document.body.appendChild(z); }
      const ms=this.liko(); z.textContent=`⏱ ${this.laikas(ms)}`; z.classList.toggle("mazai",ms<5*60000);
      const l=$("#egzLaikas"); if(l){ l.textContent=this.laikas(ms); l.classList.toggle("mazai",ms<5*60000); }
      z.classList.toggle("hidden",!!l);
      if(ms<=0){ if(!BUS.prisijungta&&(this.lauke=(this.lauke||0)+1)<15) return;    // ką tik paleista - palaukiam ryšio su AutoCAD
        clearInterval(this.t); this.lauke=0; this.baigti(true); } };
    zenkl(); if(this.dabar()) this.t=setInterval(zenkl,1000);
  },
  async baigti(laikasBaigesi){
    const d=this.dabar(); if(!d||this.tikrina) return;
    if(!laikasBaigesi&&!confirm("Baigti egzaminą ir patikrinti brėžinį?")) return;
    const btn=$("#egzBaigti"); if(btn){ btn.disabled=true; btn.innerHTML='<span class="sukasi"></span>Tikrinu...'; }
    this.tikrina=true;
    let r; if(BUS.prisijungta){ try{ r=await api("/api/praktika_tikrinti",{id:d.id}); }catch(e){ r={ok:false,klaida:"Ryšio klaida"}; } }
    else r={ok:false,klaida:"AutoCAD neprijungtas."};
    this.tikrina=false;
    if(!r.ok&&!laikasBaigesi){ pranesti((r.klaida||"Nepavyko patikrinti")+" Laikmatis eina - pabandyk dar kartą."); if(btn){ btn.disabled=false; btn.textContent="✔ Baigti ir patikrinti"; } return; }
    const sek=Math.min(Math.round((Date.now()-d.pradzia)/1000),d.min*60), u=PRAKTIKA.find(x=>x.id===d.id);
    const ir={id:d.id,data:Kartojimas.diena(),sek,min:d.min,iskaityta:!!(r.ok&&r.teisingai),
      pastabos:r.ok?r.pastabos:[r.klaida,"Laikas baigėsi, o brėžinio patikrinti nepavyko."],baigesi:!!laikasBaigesi};
    const B=this.B(); B.ist.unshift(ir); B.ist=B.ist.slice(0,30); delete B.dab; clearInterval(this.t); this.ciklas();
    pazymetiDiena();
    let xp=0; if(ir.iskaityta&&u&&!prAtlikta(u.id)){ S.praktika={...(S.praktika||{}),[u.id]:ir.data}; xp=u.xp; if(PRAKTIKA.filter(x=>prAtlikta(x.id)).length>=4) duotiZenkleli("praktikas"); }
    saugoti(); this.rezultatas(ir);
    if(ir.iskaityta){ Robotas.reaguoti("dziaug",1500); konfeti(70); if(xp) pridetiXP(xp,$("#egzRez")); } else Robotas.reaguoti("liud",1400);
  },
  nutraukti(){ if(!confirm("Nutraukti egzaminą? Rezultatas nebus įrašytas.")) return; delete this.B().dab; saugoti(); clearInterval(this.t); this.ciklas(); rodytiPraktika(); },
  rezultatas(ir){
    const u=PRAKTIKA.find(x=>x.id===ir.id)||{nr:"?",pav:ir.id};
    nustatytiRodini("praktika"); prDabar=null; $("#vPam").textContent="Egzaminas";
    $("#vidus").innerHTML=`<div class="egz-rez ${ir.iskaityta?"gerai":"blogai"}" id="egzRez"><small>Egzaminas · ${u.nr}. ${esc(u.pav)}</small>
      <h1>${ir.iskaityta?"✓ Įskaityta":"✗ Neįskaityta"}</h1>
      <p>Užtrukai <b>${this.laikas(ir.sek*1000)}</b> iš ${ir.min} min${ir.baigesi?" - laikas baigėsi":""}.</p>
      ${ir.pastabos.length?`<b>Pastabos (${ir.pastabos.length}):</b><ul>${ir.pastabos.map(p=>`<li>${esc(p)}</li>`).join("")}</ul>`:"<p>Brėžinys atitinka užduotį - nė vienos pastabos. 🎉</p>"}
      <div class="eil" style="margin-top:14px"><button class="btn pagr" onclick="Egzaminas.pasirinkti('${ir.id}')">↻ Dar kartą</button><button class="btn" onclick="rodytiUzduoti('${ir.id}')">Užduotis su užuominomis</button><button class="btn" onclick="rodytiPraktika()">Visos užduotys</button></div></div>`;
  }
};

/* =================== MANO SILPNOS VIETOS =================== */
/* Pagal tai, kur reikėjo pagalbos: nepavykę tikrinimai, užuominos, „Parodyk man“, „Kur klaida?“, klaidos komandų eilutėje, dienos kartojimas, testai. */
const Silpnos={
  st(raktas){ S.stat=S.stat||{}; return S.stat[raktas]||(S.stat[raktas]={b:0,u:0,d:0,k:0,g:0}); },
  pazymeti(lauk){ if(!PAM) return; const z=PAM.zingsniai[S.dabartinis[PAM.id]]; if(!z) return; this.st(PAM.id+"/"+z.id)[lauk]++; saugoti(); },
  balas(s,tr){ return (s.b||0)+1.5*(s.u||0)+3*(s.d||0)+(s.k||0)+0.75*(tr||0)-3*(s.g||0); },
  zingsniai(){
    const r=[], st=S.stat||{}, tk=S.trenKl||{}, tusc={b:0,u:0,d:0,k:0,g:0};
    INFO.pamokos.forEach((p,pi)=>p.zingsniai.forEach((z,zi)=>{ const k=p.id+"/"+z.id, s=st[k]||tusc, bal=this.balas(s,tk[k]);
      if(bal>=2) r.push({p,pi,z,zi,k,s,tr:tk[k]||0,bal}); }));
    return r.sort((a,b)=>b.bal-a.bal).slice(0,8);
  },
  komandos(){ const D=(S.kart&&S.kart.dez)||{}; return INFO.korteles.filter(k=>D[k.k]&&D[k.k].d===1); },
  testai(){ const ts=S.testai||{}; return INFO.pamokos.map((p,pi)=>({p,pi,t:ts[p.id]})).filter(x=>x.t&&x.t.n&&x.t.t/x.t.n<0.8); },
  html(){
    const zs=this.zingsniai(), ks=this.komandos(), ts=this.testai();
    if(!zs.length&&!ks.length&&!ts.length) return `<div class="kart-diena"><h3>Silpnų vietų kol kas nerasta ✓</h3><p>Braižyk pamokas, kartok komandas - pastebėsiu, kur reikėjo daugiau pagalbos, ir surinksiu tai čia.</p></div>`;
    const priez=x=>[x.s.b?`<span class="zyme">✗ Nepavykę tikrinimai: ${x.s.b}</span>`:"",x.s.u?`<span class="zyme">💡 Užuominos: ${x.s.u}</span>`:"",
      x.s.d?`<span class="zyme">👀 „Parodyk man“: ${x.s.d}</span>`:"",x.s.k?`<span class="zyme">🔍 „Kur klaida?“: ${x.s.k}</span>`:"",x.tr?`<span class="zyme">⌨ Klaidos komandų eilutėje: ${x.tr}</span>`:""].join("");
    const turiKom=x=>(x.z.komandos||[]).length>0;
    return `<p class="po1" style="margin-top:0">Čia - kur tau reikėjo daugiausia pagalbos. Pakartok šiuos žingsnius ir komandas: kai pavyks iš pirmo karto, jie dings iš sąrašo.</p>
    ${zs.length?`<h3 class="silp-ant">Žingsniai AutoCAD'e</h3><div class="silp-sar">${zs.map(x=>`<div class="silp-k"><div><small style="color:var(--muted)">${x.pi+1}. ${esc(x.p.pavadinimas)}</small><b>${esc(x.z.pavadinimas)}</b><div class="silp-pr">${priez(x)}</div></div>
      <div class="silp-m"><button class="btn pagr" onclick="Silpnos.atidaryti('${x.p.id}',${x.zi})">Kartoti žingsnį →</button>${turiKom(x)?`<button class="btn" onclick="Silpnos.treniruoti(['${x.k}'])">⌨ Komandos</button>`:""}</div></div>`).join("")}</div>
      ${zs.some(turiKom)?`<div class="eil" style="margin:10px 0 0"><button class="btn" onclick="Silpnos.treniruoti(${esc(JSON.stringify(zs.filter(turiKom).map(x=>x.k)))})">⌨ Treniruoti visų šių žingsnių komandas</button></div>`:""}`:""}
    ${ks.length?`<h3 class="silp-ant">Komandos, kurias dar painioji</h3><div class="silp-kom">${ks.map(k=>`<span class="zyme" title="${esc(k.ka)}">${esc(k.k)}</span>`).join("")}</div>
      <div class="eil" style="margin-top:10px"><button class="btn" onclick="kartTab='diena';rodytiKartojima()">🧠 Dienos kartojimas</button></div>`:""}
    ${ts.length?`<h3 class="silp-ant">Testai, kuriuos verta perlaikyti</h3><div class="silp-sar">${ts.map(x=>`<div class="silp-k"><div><small style="color:var(--muted)">${x.pi+1} pamoka</small><b>${esc(x.p.pavadinimas)}</b><div class="silp-pr"><span class="zyme">Geriausias: ${x.t.t}/${x.t.n}</span></div></div>
      <div class="silp-m"><button class="btn" onclick="rodytiPradzia('${x.p.id}');rodytiTesta()">Perlaikyti testą →</button></div></div>`).join("")}</div>`:""}`;
  },
  atidaryti(pid,zi){ rodytiPradzia(pid); rodytiZingsni(zi); },
  treniruoti(raktai){ trenRinkinys=raktai; kartTab="treniruoklis"; rodytiKartojima(); }
};

/* =================== KOMANDŲ EILUTĖS TRENIRUOKLIS (mokymas.js) =================== */
let trenRinkinys=null;
function trenPaleisti(){
  const el=$("#trenVieta"); if(!el||!window.Mokymas) return;
  el.setAttribute("translate","no");
  Mokymas.treniruoklis(el,{pamokos:INFO.pamokos,korteles:INFO.korteles,kalba:INFO.kalba,
    pradetos:INFO.pamokos.filter(p=>(S.atlikta[p.id]||[]).length).map(p=>p.id),
    rinkinys:trenRinkinys, rinkinioVardas:INFO.kalba==="en"?"🎯 My weak spots":"🎯 Mano silpnos vietos",
    onKlaida:({raktas})=>{ S.trenKl=S.trenKl||{}; S.trenKl[raktas]=(S.trenKl[raktas]||0)+1; saugoti(); },
    onZingsnis:({raktas,beKlaidu,el})=>{
      if(!beKlaidu) return;
      if(S.trenKl&&S.trenKl[raktas]) S.trenKl[raktas]=Math.max(0,S.trenKl[raktas]-2);     // pavyko be klaidų - silpna vieta taisosi
      S.trenAtl=S.trenAtl||[]; const xp=!S.trenAtl.includes(raktas); if(xp) S.trenAtl.push(raktas);
      saugoti(); if(xp) pridetiXP(2,el.querySelector("#mkZin")||el);
    },
    onBaigta:()=>pazymetiDiena()});
  trenRinkinys=null;
}

/* =================== ŽINYNAS (terminai LT-EN, standartų atmintinė - mokymas.js) =================== */
function rodytiZinyna(){
  nustatytiRodini("zinynas"); $("#vPam").textContent="Žinynas";
  $("#vidus").innerHTML=`<h1 class="ant1">Žinynas</h1><p class="po1">Inžinerinės grafikos terminai lietuviškai ir angliškai bei standartų atmintinė: formatai, linijos, masteliai, šriftai, matmenys.</p><div id="zinVieta" translate="no"></div>`;
  if(window.Mokymas) Mokymas.zinynas($("#zinVieta"),{url:"/zinynas.json",kalba:INFO.kalba,onKomanda:k=>kopijuoti(k)});
}

/* =================== KAS NAUJO (naujienos.json) =================== */
function verSk(v){ return String(v||"0").split(/[^0-9.]/)[0].split(".").map(x=>parseInt(x)||0); }
function verMaz(a,b){ const x=verSk(a),y=verSk(b); for(let i=0;i<Math.max(x.length,y.length);i++){ if((x[i]||0)!==(y[i]||0)) return (x[i]||0)<(y[i]||0); } return false; }
/* Šios versijos naujiena: tiksliai ši versija, o jei jos nėra - naujausia ne naujesnė už ją */
function dabartineNaujiena(){
  const N=(INFO.naujienos||[]).filter(n=>n.punktai&&n.punktai.length);
  const n=N.find(n=>!verMaz(INFO.versija,n.versija)) || null;
  return n&&INFO.kalba==="en"&&n.en ? {...n,...n.en} : n;
}
function kasNaujo(){
  const n=dabartineNaujiena(); if(!n) return;
  sg("matyta_versija",n.versija);
  rodytiLangeli(`<div class="v-naujiena"><span class="v-zyme" style="top:0;margin:0">NAUJA ${esc(n.versija)}</span></div>
    <h2 style="font:600 24px var(--font);letter-spacing:-.01em;text-transform:none;color:var(--text);margin:8px 0 4px">${esc(n.pavadinimas)}</h2>
    <p>${esc(n.aprasas||"")}</p>
    <ul class="kas-sar">${n.punktai.map(x=>`<li>${x}</li>`).join("")}</ul>
    <div class="eil" style="margin-top:16px"><span class="tarpas"></span><button class="btn pagr" onclick="uzdarytiLangeli()">Gerai</button></div>`);
}

/* =================== PIRMO PALEIDIMO VEDLYS =================== */
const Vedlys={
  nr:0, d:{},
  pradeti(){
    if(sg("vedlys")) return;
    if(S.xp>0){ sg("vedlys","1"); return; }          // jau mokėsi anksčiau
    this.d={vardas:S.savininkas||"", personazas:(S.eq&&S.eq.personazas)||"robotas", pvardas:"", patirtis:"naujas", tema:sg("tema")||"dark", dydis:sg("dydis")||"1"};
    this.nr=0; this.piesti();
  },
  taskai(){ return `<div class="vedlio-taskai">${[0,1,2,3].map(i=>`<i class="${i<=this.nr?"on":""}"></i>`).join("")}</div>`; },
  piesti(){
    const d=this.d, p=(k,v)=>d[k]===v;
    let h="";
    if(this.nr===0) h=`${this.taskai()}<h2>Labas! Aš Brėžly 🤖</h2><p>Padėsiu išmokti AutoCAD. Keli trumpi klausimai - ir pradedam.</p>
      <label for="vVardas">Kaip tave vadinti?</label>
      <input type="text" id="vVardas" maxlength="24" placeholder="Tavo vardas" value="${esc(d.vardas)}" oninput="Vedlys.d.vardas=this.value" onkeydown="if(event.key==='Enter')Vedlys.toliau()">`;
    if(this.nr===1){
      const eq={...(S.eq||PRADINIS)};
      h=`${this.taskai()}<h2>Pasirink savo personažą</h2><p>Jis mokysis kartu su tavimi, rodys kur spausti ir džiaugsis tavo sėkme. Vėliau jį aprengsi spintoje.</p>
      <div class="pers-tinklas">${PERSONAZAI.map(x=>`<button class="pers ${p("personazas",x.id)?"pas":""} ${p("personazas",x.id)?"gyvas":""}" aria-pressed="${p("personazas",x.id)}" onclick="Vedlys.rinktis('${x.id}')">
        <span class="pers-pav" style="${fonoStilius({...eq,personazas:x.id},true)}">${robotoSVG({...eq,personazas:x.id})}</span><b translate="no">${esc(x.vardas)}</b><small>${esc(x.pav)}</small></button>`).join("")}</div>
      <label for="vPVardas">Kaip jį pavadinsi?</label>
      <input type="text" id="vPVardas" maxlength="18" value="${esc(d.pvardas||personazas(d.personazas).vardas)}" oninput="Vedlys.d.pvardas=this.value" onkeydown="if(event.key==='Enter')Vedlys.toliau()">`;
    }
    if(this.nr===2) h=`${this.taskai()}<h2>Ar jau naudojai AutoCAD?</h2><p>Pagal tai parinksiu, nuo kurios pamokos pradėti.</p>
      <div class="rinktis">
        <button aria-pressed="${p("patirtis","naujas")}" onclick="Vedlys.d.patirtis='naujas';Vedlys.piesti()"><b>Pirmą kartą</b><small>Pradėsim nuo pradžių: failas, kampinis įrašas, 2D brėžinys...</small></button>
        <button aria-pressed="${p("patirtis","pagrindai")}" onclick="Vedlys.d.patirtis='pagrindai';Vedlys.piesti()"><b>Moku pagrindus</b><small>Pradėsim nuo pamokos „2D brėžinys“. Prie pirmųjų dviejų galėsi grįžti bet kada.</small></button>
      </div>`;
    if(this.nr===3) h=`${this.taskai()}<h2>Kaip tau patogiau?</h2><p>Visa tai galėsi pakeisti „Nustatymuose“.</p>
      <div class="nust-eil"><div><b>Tema</b></div><div class="pasir">${[["dark","☾ Tamsi"],["light","☀ Šviesi"]].map(([v,t])=>`<button aria-pressed="${p("tema",v)}" onclick="Vedlys.d.tema='${v}';sg('tema','${v}');taikytiTema();Vedlys.piesti()">${t}</button>`).join("")}</div></div>
      <div class="nust-eil"><div><b>Teksto dydis</b></div><div class="pasir">${[["1","Įprastas"],["1.15","Didesnis"]].map(([v,t])=>`<button aria-pressed="${p("dydis",v)}" onclick="Vedlys.d.dydis='${v}';sg('dydis','${v}');taikytiDydi();Vedlys.piesti()">${t}</button>`).join("")}</div></div>
      <div class="nust-eil"><div><b>📌 Šalia AutoCAD</b><small>Siauras Brėžly langas dešinėje, visada virš AutoCAD - nereikės perjunginėti langų.</small></div></div>`;
    h+=`<div class="eil" style="margin-top:20px">${this.nr>0?`<button class="btn" onclick="Vedlys.nr--;Vedlys.piesti()">← Atgal</button>`:""}<span class="tarpas"></span>
      <button class="btn pagr didelis" onclick="Vedlys.toliau()">${this.nr<3?"Toliau →":"Pradedam! 🚀"}</button></div>`;
    rodytiLangeli(h,false);
  },
  rinktis(id){
    const senas=personazas(this.d.personazas).vardas;
    if(!this.d.pvardas||this.d.pvardas===senas) this.d.pvardas=personazas(id).vardas;
    this.d.personazas=id; this.piesti();
    const el=document.querySelector(".pers.pas"); if(el) setTimeout(()=>{ el.classList.add("rob-moja"); setTimeout(()=>el.classList.remove("rob-moja"),1400); },30);
  },
  toliau(){
    if(this.nr<3){ this.nr++; return this.piesti(); }
    const d=this.d;
    if(!S.eq) S.eq={...PRADINIS};
    S.eq.personazas=d.personazas||"robotas"; S.vardas=(d.pvardas||personazas(S.eq.personazas).vardas).trim()||personazas(S.eq.personazas).vardas;
    piestiZaideja();
    S.savininkas=(d.vardas||"").trim(); sg("vedlys","1"); saugoti(); uzdarytiLangeli();
    if(d.patirtis==="pagrindai"){ PAM=null; rodytiPradzia((INFO.pamokos.find(p=>p.id==="2d")||INFO.pamokos[0]).id); } else rodytiPradzia();
    pranesti(S.savininkas?`Malonu susipažinti, ${S.savininkas}! 👋`:"Pradedam! 👋");
    if(!sg("cadet_turas")) setTimeout(()=>Gidas.pradetiTura(Gidas.PRADZIOS_TURAS,"cadet_turas"),900);
  }
};

/* =================== NUSTATYMAI =================== */
let testasAtrakintas=false;
function jung(on,veiksmas,pav){ return `<button class="jung" aria-pressed="${!!on}" aria-label="${esc(pav)}" onclick="${veiksmas}"></button>`; }
/* =================== BRĖŽINIO IŠŠŪKIAI IR PERŽIŪRA (1.5, bandomoji funkcija: Nustatymai → Bandomosios funkcijos) =================== */
const betaIjungta=()=>sg("beta")==="1";
const ISS={id:null,t0:0,aktyvus:false,laikm:null,naujas:true,paskutinis:{}};
const issLaikas=s=>{ s=Math.max(0,Math.round(s)); return `${Math.floor(s/60)}:${String(s%60).padStart(2,"0")}`; };
const issZv=n=>`<span class="iss-zv" aria-label="${n} iš 3">${"★".repeat(n)}<i>${"★".repeat(3-n)}</i></span>`;
const issRez=id=>(S.issukiai||{})[id];
function issSarasas(){ return INFO.issukiai||[]; }

/* brėžinys su matmenimis (SVG; CAD koordinatės, y aukštyn) */
function issukioSVG(i,mazas){
  const P=i.geom.map(g=>g.l?{t:"l",v:g.l}:g.a?{t:"a",v:g.a}:{t:"c",v:g.c});
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9; const ext=(x,y)=>{x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);};
  P.forEach(p=>{ if(p.t==="l"){ext(p.v[0],p.v[1]);ext(p.v[2],p.v[3]);} else {ext(p.v[0]-p.v[2],p.v[1]-p.v[2]);ext(p.v[0]+p.v[2],p.v[1]+p.v[2]);} });
  const K="#111111", M="#1f4fd1", A="#e2362b", f=n=>+n.toFixed(3), Y=y=>f(-y), rad=a=>a*Math.PI/180;
  const tw=t=>t.length*2.55+1;
  let dims="";
  const rodykle=(x,y,dx,dy)=>{ const L=Math.hypot(dx,dy)||1, ux=dx/L, uy=dy/L, bx=x-ux*2.6, by=y-uy*2.6, px=-uy*.85, py=ux*.85;
    return `<path d="M${f(x)} ${Y(y)} L${f(bx+px)} ${Y(by+py)} L${f(bx-px)} ${Y(by-py)} Z" fill="${M}"/>`; };
  const tekst=(x,y,t,kamp)=>`<text x="${f(x)}" y="${Y(y)}" ${kamp?`transform="rotate(-90 ${f(x)} ${Y(y)})"`:""} text-anchor="middle" font-size="4.2" font-family="'Space Mono',monospace" fill="${M}">${esc(t)}</text>`;
  if(!mazas) for(const d of i.matmenys){
    if(d.t==="h"){ const [ax,ay]=d.a,[bx,by]=d.b, s=Math.sign(d.y-ay)||1, sb=Math.sign(d.y-by)||1;
      dims+=`<path d="M${f(ax)} ${Y(ay+s*1.5)} V${Y(d.y+s*2)} M${f(bx)} ${Y(by+sb*1.5)} V${Y(d.y+sb*2)} M${f(ax)} ${Y(d.y)} H${f(bx)}" stroke="${M}" stroke-width=".3" fill="none"/>`
        +rodykle(ax,d.y,ax-bx,0)+rodykle(bx,d.y,bx-ax,0)+tekst((ax+bx)/2,d.y+1.3,d.txt);
      ext(ax,d.y-2);ext(bx,d.y+6); }
    else if(d.t==="v"){ const [ax,ay]=d.a,[bx,by]=d.b, s=Math.sign(d.x-ax)||1, sb=Math.sign(d.x-bx)||1;
      dims+=`<path d="M${f(ax+s*1.5)} ${Y(ay)} H${f(d.x+s*2)} M${f(bx+sb*1.5)} ${Y(by)} H${f(d.x+sb*2)} M${f(d.x)} ${Y(ay)} V${Y(by)}" stroke="${M}" stroke-width=".3" fill="none"/>`
        +rodykle(d.x,ay,0,ay-by)+rodykle(d.x,by,0,by-ay)+tekst(d.x-1.3,(ay+by)/2,d.txt,true);
      ext(d.x-6,ay);ext(d.x+2,by); }
    else { const [cx,cy]=d.c, k=rad(d.kampas), px=cx+d.r*Math.cos(k), py=cy+d.r*Math.sin(k), qx=cx+(d.r+(d.ilgis||11))*Math.cos(k), qy=cy+(d.r+(d.ilgis||11))*Math.sin(k), kr=Math.cos(k)>=0?1:-1, w=tw(d.txt), ex=qx+kr*w;
      dims+=`<path d="M${f(px)} ${Y(py)} L${f(qx)} ${Y(qy)} H${f(ex)}" stroke="${M}" stroke-width=".3" fill="none"/>`+rodykle(px,py,px-qx,py-qy)+tekst((qx+ex)/2,qy+1.2,d.txt);
      ext(qx,qy-2);ext(ex,qy+6); }
  }
  const sw=mazas?1.4:.7;
  const geo=P.map(p=>{ const v=p.v;
    if(p.t==="l") return `<line x1="${f(v[0])}" y1="${Y(v[1])}" x2="${f(v[2])}" y2="${Y(v[3])}"/>`;
    if(p.t==="c") return `<circle cx="${f(v[0])}" cy="${Y(v[1])}" r="${f(v[2])}"/>`;
    const [cx,cy,r,a0,a1]=v, ap=((a1-a0)%360+360)%360||360, sx=cx+r*Math.cos(rad(a0)), sy=cy+r*Math.sin(rad(a0)), exx=cx+r*Math.cos(rad(a1)), ey=cy+r*Math.sin(rad(a1));
    return `<path d="M${f(sx)} ${Y(sy)} A${f(r)} ${f(r)} 0 ${ap>180?1:0} 0 ${f(exx)} ${Y(ey)}"/>`; }).join("");
  const asys=mazas?"":`<g stroke="${A}" stroke-width=".3" stroke-dasharray="6 1.5 1 1.5" fill="none">${(i.asys||[]).map(a=>`<line x1="${f(a[0])}" y1="${Y(a[1])}" x2="${f(a[2])}" y2="${Y(a[3])}"/>`).join("")}${(i.asys_apsk||[]).map(c=>`<circle cx="${f(c[0])}" cy="${Y(c[1])}" r="${f(c[2])}"/>`).join("")}</g>`;
  const m=mazas?4:6;
  return `<svg class="iss-svg" viewBox="${f(x0-m)} ${f(-y1-m)} ${f(x1-x0+2*m)} ${f(y1-y0+2*m)}" role="img" aria-label="${esc(i.pav)} - brėžinys su matmenimis">${asys}<g stroke="${K}" stroke-width="${sw}" fill="none" stroke-linecap="square">${geo}</g>${dims}</svg>`;
}

function issukiuSekcija(){
  if(!betaIjungta()) return "";
  const sar=issSarasas(); if(!sar.length) return "";
  return `<section class="iss-sek" aria-label="Brėžinio iššūkiai">
    <div class="iss-ant"><h2>Brėžinio iššūkiai <span class="beta">BETA</span></h2><p>Tik brėžinys su matmenimis - be žingsnių. Nubraižyk kuo greičiau ir pagerink savo rekordą. Pabaigoje - tavo komandų peržiūra.</p></div>
    <div class="iss-tink">${sar.map(i=>{ const r=issRez(i.id);
      return `<button class="iss-k" onclick="rodytiIssuki('${i.id}')" aria-label="Iššūkis ${i.nr}: ${esc(i.pav)}${r?", rekordas "+issLaikas(r.geriausias):""}">
        <div class="iss-mini">${issukioSVG(i,true)}</div>
        <span class="iss-nr">${String(i.nr).padStart(2,"0")}</span>${r?`<span class="iss-rek">${issZv(r.zv||1)}</span>`:""}
        <b>${esc(i.pav)}</b><small>${prZvaigzd(i.lyg)} · tikslas ${issLaikas(i.tikslas)}${r?` · rekordas ${issLaikas(r.geriausias)}`:` · +${i.xp} XP`}</small></button>`; }).join("")}</div></section>`;
}

function rodytiIssuki(id){
  const i=issSarasas().find(x=>x.id===id); if(!i) return rodytiPraktika();
  nustatytiRodini("praktika"); prDabar=null; $("#vPam").textContent=`Iššūkis ${i.nr}. ${i.pav}`;
  const r=issRez(id), akt=ISS.aktyvus&&ISS.id===id, ats=ISS.paskutinis[id];
  $("#vidus").innerHTML=`<div class="bh-du iss-du">
    <section class="bh-lapas iss-lapas" aria-label="Brėžinys">
      <span class="bh-zyme">Iššūkis ${String(i.nr).padStart(2,"0")} / ${String(issSarasas().length).padStart(2,"0")} · ${prZvaigzd(i.lyg)} · tikslas ${issLaikas(i.tikslas)}</span>
      <h1 class="bh-h1">${esc(i.pav)}</h1>
      <div class="iss-brez" onclick="issDidinti('${id}')" title="Spausk - padidinsiu">${issukioSVG(i)}</div>
      <p class="iss-pastaba">Matmenys milimetrais. Ašys (raudonos) ir matmenys netikrinami - braižyk tik detalę.</p>
    </section>
    <div class="bh-skydas" role="complementary">
      <div class="bh-geltona">
        <span class="bh-poz">BETA · ${prZvaigzd(i.lyg)} · +${i.xp} XP</span>
        <h2>Nubraižyk pagal brėžinį</h2>
        <p>${esc(i.aprasas)} Žingsnių nėra - tik matmenys. Braižyk bet kurioje vietoje, aš rasiu.</p>
        <div class="iss-laikr"><div><small>Laikas</small><b id="issLaikas">${akt?issLaikas((Date.now()-ISS.t0)/1000):"0:00"}</b></div>
          <div><small>Tikslas</small><b>${issLaikas(i.tikslas)}</b></div><div><small>Rekordas</small><b>${r?issLaikas(r.geriausias):"-"}</b></div></div>
        <div class="bh-veiksmai">${akt
          ?`<button class="bh-tikr" id="issTikr" onclick="issTikrinti('${id}')">Tikrinti →</button><button class="bh-uz" onclick="issBaigti()">Baigti</button>`
          :`<button class="bh-tikr" id="issPrad" onclick="issPradeti('${id}')">${r?"Bandyti dar kartą →":"Pradėti →"}</button>`}</div>
        ${akt?"":`<label class="iss-naujas"><input type="checkbox" ${ISS.naujas?"checked":""} onchange="ISS.naujas=this.checked"> Atidaryti naują tuščią brėžinį</label>`}
      </div>
      <details class="iss-uz"><summary>Užuomina: kokios komandos tinka</summary><div class="pr-kom">${i.kom.map(k=>`<code>${esc(k)}</code>`).join("")}</div></details>
      <div id="issAts">${ats?issAtsHTML(id,ats):""}</div>
      <button class="btn iss-atgal" onclick="rodytiPraktika()">← Visi iššūkiai</button>
    </div></div>`;
  issLaikmatis();
}
function issDidinti(id){ const i=issSarasas().find(x=>x.id===id); rodytiLangeli(`<div class="iss-didelis">${issukioSVG(i)}</div><div class="eil" style="margin-top:12px"><span class="tarpas"></span><button class="btn" onclick="uzdarytiLangeli()">Uždaryti</button></div>`); document.querySelector("#langelis .lang").style.maxWidth="min(1100px,94vw)"; }
function issLaikmatis(){
  clearInterval(ISS.laikm);
  if(!ISS.aktyvus) return;
  ISS.laikm=setInterval(()=>{ const el=$("#issLaikas"); if(el&&ISS.aktyvus) el.textContent=issLaikas((Date.now()-ISS.t0)/1000); },250);
}
async function issPradeti(id){
  if(!BUS.prisijungta&&!BUS.imitacija){ pranesti("Pirmiausia prisijunk prie AutoCAD (mygtukas apačioje kairėje)."); return; }
  const b=$("#issPrad"); if(b){ b.disabled=true; b.textContent="Ruošiu..."; }
  let r; try{ r=await api("/api/issukis_pradeti",{id,naujas:ISS.naujas}); }catch(e){ r={ok:false}; }
  if(!r.ok){ pranesti(r.klaida||"Nepavyko pradėti"); rodytiIssuki(id); return; }
  Object.assign(ISS,{id,t0:Date.now(),aktyvus:true}); delete ISS.paskutinis[id];
  pranesti(ISS.naujas?"Atidariau tuščią brėžinį. Laikas eina - braižyk!":"Laikas eina - braižyk!");
  Robotas.reaguoti("moja",1200); rodytiIssuki(id);
}
async function issTikrinti(id){
  const b=$("#issTikr"); if(b){ b.disabled=true; b.textContent="Tikrinu..."; }
  const sek=(Date.now()-ISS.t0)/1000;
  let r; try{ r=await api("/api/issukis_tikrinti",{id,sekundes:sek}); }catch(e){ r={ok:false,klaida:"Ryšio klaida"}; }
  if(b){ b.disabled=false; b.textContent="Tikrinti →"; }
  if(!r.ok){ pranesti(r.klaida||"Nepavyko patikrinti"); return; }
  ISS.paskutinis[id]=r;
  if(!r.teisingai){ Robotas.reaguoti("liud",1400); const el=$("#issAts"); if(el){ el.innerHTML=issAtsHTML(id,r); el.scrollIntoView({block:"nearest",behavior:"smooth"}); } return; }
  ISS.aktyvus=false; clearInterval(ISS.laikm);
  const i=issSarasas().find(x=>x.id===id), sen=issRez(id), zv=r.perziura?.zvaigzdes||1;
  const rekordas=!sen||sek<sen.geriausias;
  S.issukiai={...(S.issukiai||{}),[id]:{geriausias:rekordas?Math.round(sek):sen.geriausias,kartai:(sen?.kartai||0)+1,data:new Date().toISOString().slice(0,10),zv:Math.max(zv,sen?.zv||0)}};
  r.rekordas=rekordas&&!!sen; r.pirmas=!sen;
  if(!sen) pridetiXP(i.xp,$("#issAts")); else if(rekordas) pridetiXP(10,$("#issAts")); else saugoti();
  Robotas.reaguoti("dziaug",1800); konfeti(rekordas?80:40);
  rodytiIssuki(id); issPerziura(id);
}
function issBaigti(){ ISS.aktyvus=false; clearInterval(ISS.laikm); api("/api/issukis_baigti",{}).catch(()=>{}); if(ISS.id) rodytiIssuki(ISS.id); }
function issAtsHTML(id,r){
  if(!r.teisingai) return `<div class="pr-ats blogai"><b>Dar ne viskas:</b><ul>${r.pastabos.map(p=>`<li>${esc(p)}</li>`).join("")}</ul></div>`;
  const p=r.perziura||{};
  return `<div class="pr-ats gerai"><b>${r.pirmas?"Iššūkis įveiktas!":r.rekordas?"Naujas rekordas!":"Įveikta!"} ${issZv(p.zvaigzdes||1)}</b>
    <p style="margin:6px 0 0">Laikas ${issLaikas(p.laikas||0)} · tikslas ${issLaikas(p.tikslas||0)}</p>
    <button class="btn" style="margin-top:10px" onclick="issPerziura('${id}')">Peržiūra: tavo komandos →</button></div>`;
}
const ISS_GRUPES={piesti:["LINE","CIRCLE","ARC","PLINE","RECTANG","POLYGON","XLINE","ELLIPSE"],keisti:["TRIM","EXTEND","FILLET","CHAMFER","OFFSET","COPY","MOVE","MIRROR","ROTATE","ARRAYPOLAR","ARRAYRECT","ARRAY","STRETCH","SCALE","JOIN"],
  taisyti:["U","UNDO","ERASE","REDO","OOPS"],vaizdas:["ZOOM","PAN","3DORBIT"]};
const issGrupe=k=>Object.keys(ISS_GRUPES).find(g=>ISS_GRUPES[g].includes(k))||"kita";
function issPerziura(id){
  const r=ISS.paskutinis[id], p=r&&r.perziura; if(!p) return;
  const i=issSarasas().find(x=>x.id===id), viso=Math.max(p.laikas||1,...(p.seka||[]).map(s=>s.t+s.tr),1);
  const juosta=(p.seka||[]).length?`<div class="iss-juosta" role="img" aria-label="Komandų laiko juosta">${p.seka.map(s=>{ const l=s.t/viso*100, w=Math.max(.6,s.tr/viso*100);
      return `<span class="g-${issGrupe(s.k)}" style="left:${l.toFixed(2)}%;width:${w.toFixed(2)}%" title="${esc(s.k)} · ${s.tr.toFixed(1)} s">${w>7?esc(s.k):""}</span>`; }).join("")}</div>
    <div class="iss-leg"><span class="g-piesti">Braižymas</span><span class="g-keisti">Keitimas</span><span class="g-taisyti">Taisymas</span><span class="g-vaizdas">ZOOM / PAN</span><span class="g-kita">Kita</span></div>`:"";
  const lent=(p.komandos||[]).length?`<table class="iss-lent"><thead><tr><th>Komanda</th><th>Kartų</th><th>Laikas</th></tr></thead><tbody>${p.komandos.map(k=>`<tr><td><code>${esc(k.k)}</code></td><td>${k.kiek}</td><td>${issLaikas(k.laikas)}</td></tr>`).join("")}</tbody></table>`:"";
  rodytiLangeli(`<div class="iss-perz">
    <span class="bh-poz">Brėžinio peržiūra · ${esc(i.pav)} · BETA</span>
    <h2>${issZv(p.zvaigzdes||1)} ${issLaikas(p.laikas)} <small>tikslas ${issLaikas(p.tikslas)}${r.rekordas?" · naujas rekordas!":""}</small></h2>
    ${juosta}
    <div class="iss-perz-du">${lent?`<div>${lent}</div>`:""}
      <div><h3>Patarimai</h3><ol class="iss-pat">${(p.patarimai||[]).map(t=>`<li class="p-${esc(t.tipas)}">${esc(t.tekstas)}</li>`).join("")}</ol>
      ${p.pastaba?`<p class="iss-pastaba">${esc(p.pastaba)}</p>`:""}${p.budas==="imitacija"?`<p class="iss-pastaba">Imitacija (kūrėjo režimas): pavyzdinis pradedančiojo įrašas.</p>`:""}</div></div>
    <div class="eil" style="margin-top:14px"><span class="tarpas"></span><button class="btn" onclick="uzdarytiLangeli()">Uždaryti</button><button class="btn pagr" onclick="uzdarytiLangeli();issPradeti('${id}')">Bandyti dar kartą</button></div></div>`);
  document.querySelector("#langelis .lang").style.maxWidth="min(880px,94vw)";
}

function rodytiNustatymus(){
  nustatytiRodini("nustatymai");
  const t=sg("tema")||"dark", dyd=sg("dydis")||"auto", komp=langoRez()==="kompaktiskas", lrez=langoRez(), sep=INFO.windows?"\\":"/";
  const pas=(rinkinys,dab,f)=>`<div class="pasir">${rinkinys.map(([v,p])=>`<button aria-pressed="${dab===v}" onclick="${f(v)}">${p}</button>`).join("")}</div>`;
  $("#vidus").innerHTML=`<h1 class="ant1">Nustatymai</h1><p class="po1">Kaip tau patogiau mokytis.</p>
  <div class="nust-gr"><h3>Vaizdas</h3>
    <div class="nust-eil"><div><b>Tema</b><small>Tamsi mažiau vargina akis vakare.</small></div>${pas([["dark","☾ Tamsi"],["light","☀ Šviesi"]],t,v=>`sg('tema','${v}');taikytiTema()`)}</div>
    <div class="nust-eil"><div><b>Kalba / Language</b><small>Brėžly sąsajos ir pamokų kalba. Language of the interface and lessons.</small></div>${pas([["lt","Lietuvių"],["en","English"]],sg("kalba")||"lt",v=>`sg('kalba','${v}');planuotiSaugojima(true);setTimeout(()=>location.reload(),300)`)}</div>
    <div class="nust-eil"><div><b>Teksto dydis</b><small>Padidina visą Brėžly langą.</small></div>${pas([["auto","Pagal ekraną"],["1","Įprastas"],["1.15","Didesnis"],["1.3","Didelis"]],dyd,v=>v==="auto"?`sg('dydis','');taikytiDydi();rodytiNustatymus()`:`sg('dydis','${v}');taikytiDydi();rodytiNustatymus()`)}</div>
  </div>
  <div class="nust-gr"><h3>Darbas su AutoCAD</h3>
    <div class="nust-eil"><div><b>Brėžly langas</b><small>Nešiojamam kompiuteriui: „Šalia AutoCAD“ padalina ekraną, „Mini“ - maža kortelė virš AutoCAD.</small></div>${pas([["iprastas","⇱ Didelis"],["kompaktiskas","📌 Šalia AutoCAD"],["mini","▫ Mini"]],lrez,v=>`langoRezimas('${v}')`)}</div>
    <div class="nust-eil"><div><b>Sutvarkyti AutoCAD langą</b><small>„Šalia AutoCAD“ režime AutoCAD sumažinamas iki likusios vietos, kad Brėžly neuždengtų brėžinio.</small></div>${jung(sg("acad_isd")!=="0",`sg('acad_isd',sg('acad_isd')==='0'?'1':'0');rodytiNustatymus()`,"Sutvarkyti AutoCAD langą")}</div>
    <div class="nust-eil"><div><b>Spartieji klavišai</b><small>Veikia ir kai dirbi AutoCAD'e: <b style="display:inline">Ctrl+Alt+T</b> - patikrinti, <b style="display:inline">Ctrl+Alt+M</b> - mini / šalia, <b style="display:inline">Ctrl+Alt+B</b> - parodyti Brėžly. <span>Brėžly lange:</span> <b style="display:inline">Enter</b> - patikrinti arba toliau, <b style="display:inline">H</b> - užuomina.${(INFO.klavisai&&INFO.klavisai.nepavyko.length)?` Užimti kitos programos: ${esc(INFO.klavisai.nepavyko.join(", "))}.`:""}</small></div></div>
    <div class="nust-eil"><div><b>Gyvas robotukas</b><small>Mirksi, seka pelę akimis, džiaugiasi ir nuliūsta kartu su tavimi.</small></div>${jung(Robotas.jungtas(),`sg('judesys',Robotas.jungtas()?'0':'1');Robotas.taikyti();rodytiNustatymus()`,"Gyvas robotukas")}</div>
    <div class="nust-eil"><div><b>Automatinis tikrinimas</b><small>Kas kelias sekundes pažiūriu į brėžinį ir pats pastebiu atliktą žingsnį.</small></div>${jung(auto.ijungtas(),"auto.perjungti()","Automatinis tikrinimas")}</div>
    <div class="nust-eil"><div><b>Garsas, kai žingsnis atliktas</b><small>Trumpas „dzin“ ir Brėžly mirktelėjimas užduočių juostoje, kai dirbi AutoCAD'e.</small></div>${jung(Garsas.ijungtas(),"Garsas.perjungti()","Garsas")}</div>
    <div class="nust-eil"><div><b>Komandos su „_“</b><small>Jei tavo AutoCAD ne anglų kalba: _LINE, _CIRCLE veikia bet kurioje kalboje.${BUS.kalba?` Tavo AutoCAD kalba: <b style="display:inline">${esc(BUS.kalba)}</b>.`:""}</small></div>${jung(sg("pabr")==="1",`sg('pabr',sg('pabr')==='1'?'0':'1');rodytiNustatymus()`,"Komandos su pabraukimu")}</div>
    <div class="nust-eil"><div><b>🤖 Robotas gidas</b><small>Parodo, kur spausti, ir padrąsina.</small></div><button class="btn" onclick="Gidas.turasIsNaujo()">❔ Turas</button>${jung(Gidas.ijungtas(),"Gidas.perjungti();rodytiNustatymus()","Robotas gidas")}</div>
  </div>
  <div class="nust-gr"><h3>Bandomosios funkcijos <span class="beta">BETA</span></h3><p>Naujos funkcijos, kurios dar testuojamos - gali keistis ar dingti. Įprastai išjungtos.</p>
    <div class="nust-eil"><div><b>Brėžinio iššūkiai ir peržiūra</b><small>Praktikoje atsiras iššūkiai: tik brėžinys su matmenimis, laikmatis ir asmeninis rekordas. Pabaigoje - tavo komandų peržiūra su patarimais, kaip braižyti greičiau.</small></div>${jung(betaIjungta(),`sg('beta',betaIjungta()?'0':'1');rodytiNustatymus()`,"Brėžinio iššūkiai ir peržiūra")}</div>
  </div>
  <div class="nust-gr"><h3>Progresas</h3><p>XP, pamokos ir daiktai saugomi faile - išliks ir perdiegus Brėžly.</p>
    <code class="kelias">${esc(INFO.duomenys+sep+"progresas.json")}</code>
    <div class="nust-eil" style="margin-top:12px"><div><b>Perkelti į kitą kompiuterį</b><small>Eksportuok čia, nusikopijuok failą (USB, el. paštas, OneDrive) ir kitame kompiuteryje spausk „Importuoti“.</small></div>
      <button class="btn" onclick="eksportuotiProgresa()">⇪ Eksportuoti</button><button class="btn" onclick="$('#importoFailas').click()">⇩ Importuoti</button>
      <input type="file" id="importoFailas" accept=".json,application/json" hidden onchange="importuotiProgresa(this)"></div>
    <div class="nust-eil"><div><b>Ataskaita dėstytojui</b><small>Atliktos pamokos, testai, praktikos užduotys ir XP - atsispausdink arba išsaugok PDF.</small></div><button class="btn" onclick="destytojoAtaskaita()">🎓 Ataskaita</button></div>
    <div class="eil" style="margin-top:12px"><button class="btn" onclick="api('/api/duomenys',{})">📂 Atidaryti aplanką</button></div>
  </div>
  <div class="nust-gr"><h3>Pagalba</h3>
    <div class="nust-eil"><div><b>Pranešti apie klaidą</b><small>Sukursiu failą su informacija - atsiųsk jį kūrėjui.</small></div><button class="btn" onclick="ataskaitosLangas()">🐞 Pranešti</button></div>
    ${INFO.atnaujinimai?`<div class="nust-eil"><div><b>Atnaujinimai</b><small>Patikrinsiu, ar yra nauja Brėžly versija.</small></div><button class="btn" onclick="tikrintiAtnaujinimus(true)">↻ Tikrinti</button></div>`:""}
    <div class="nust-eil"><div><b>Versija</b><small>Brėžly ${esc(INFO.versija)}</small></div></div>
  </div>
  ${INFO.testavimas?`<div class="nust-gr"><h3>Kūrėjo režimas</h3>${testasAtrakintas?`
    <p>Atrakinta. Užsirakins pati po 30 min. neveiklumo.</p>
    <div class="eil"><button class="btn pagr" onclick="rodytiKureja()">🛠 Kūrėjo pultas</button><button class="btn" onclick="uzrakintiTesta()">🔒 Užrakinti</button></div>`
    :`<p>Kūrėjo įrankiai apsaugoti slaptažodžiu.</p><button class="btn" onclick="testoLangas()">🔒 Atrakinti</button>`}</div>`:""}`;
}

/* ---- ataskaita dėstytojui: spausdinamas HTML (Dokumentai\\Brezly\\ataskaitos) ---- */
function destytojoAtaskaita(){
  rodytiLangeli(`<h2>🎓 Ataskaita dėstytojui</h2>
    <p>Bus sukurta ataskaita su tavo pamokomis, testais ir praktikos užduotimis. Ją atsidarysi naršyklėje ir galėsi atsispausdinti arba išsaugoti PDF (Ctrl+P).</p>
    <label for="ataVardas">Vardas ir pavardė</label><input type="text" id="ataVardas" value="${esc(sg("studentas")||S.savininkas||"")}" maxlength="80" autocomplete="name">
    <label for="ataGrupe" style="margin-top:10px;display:block">Grupė / kursas</label><input type="text" id="ataGrupe" value="${esc(sg("grupe")||"")}" maxlength="40" placeholder="pvz. AI26">
    <label for="ataDalykas" style="margin-top:10px;display:block">Dalykas, dėstytojas (nebūtina)</label><input type="text" id="ataDalykas" value="${esc(sg("dalykas")||"")}" maxlength="120" placeholder="pvz. Inžinerinė grafika">
    <div class="eil" style="margin-top:14px"><span class="tarpas"></span><button class="btn" onclick="uzdarytiLangeli()">Atšaukti</button><button class="btn pagr" onclick="kurtiDestytojoAtaskaita()">Sukurti</button></div>`);
}
function ataskaitosHTML(st){
  const pam=INFO.pamokos, ts=S.testai||{}, bg=S.baigta||{}, pr=S.praktika||{};
  const baigtos=pam.filter(p=>(S.atlikta[p.id]||[]).length>=p.zingsniai.length).length, prN=PRAKTIKA.filter(u=>pr[u.id]).length;
  const e=esc, d=new Date();
  const eilP=pam.map((p,i)=>{ const a=(S.atlikta[p.id]||[]).length, n=p.zingsniai.length, t=ts[p.id];
    return `<tr class="${a>=n?"ok":""}"><td>${i+1}</td><td>${e(p.pavadinimas)}</td><td>${a}/${n}</td><td>${t?`${t.t}/${t.n}`:"-"}</td><td>${e(bg[p.id]||(a>=n?"✓":""))}</td></tr>`; }).join("");
  const eilU=PRAKTIKA.slice().sort((a,b)=>a.nr-b.nr).map(u=>`<tr class="${pr[u.id]?"ok":""}"><td>U${u.nr}</td><td>${e(u.pav)}</td><td>${e(u.fmt)} · ${e(u.d)}</td><td>${pr[u.id]?"✓ "+e(typeof pr[u.id]==="string"?pr[u.id]:""):"-"}</td></tr>`).join("");
  return `<!doctype html><html lang="lt"><head><meta charset="utf-8"><title>Brėžly ataskaita - ${e(st.vardas)}</title><style>
  @page{size:A4;margin:16mm 14mm}
  body{font:13px/1.5 "Segoe UI",system-ui,sans-serif;color:#111;max-width:780px;margin:24px auto;padding:0 16px}
  h1{font-size:22px;margin:0}.sub{color:#555;margin:2px 0 18px}
  .kort{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:14px 0 20px}.kort div{border:1px solid #ccc;border-radius:4px;padding:8px 10px}
  .kort b{display:block;font-size:20px}.kort small{color:#555}
  table{width:100%;border-collapse:collapse;margin:6px 0 18px}th,td{border-bottom:1px solid #ddd;padding:5px 8px;text-align:left}
  th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#555;border-bottom:1.5px solid #333}tr.ok td:first-child{border-left:3px solid #1a7f37}
  h2{font-size:15px;margin:18px 0 2px}.duom{width:auto}.duom td{border:0;padding:2px 24px 2px 0}.duom td:first-child{color:#555}.pastaba{color:#555;font-size:11.5px;margin-top:22px;border-top:1px solid #ddd;padding-top:8px}
  .spausd{margin:0 0 16px}@media print{.spausd{display:none}body{margin:0}}
  </style></head><body>
  <button class="spausd" onclick="print()">🖨 Spausdinti / išsaugoti PDF</button>
  <h1>Brėžly - AutoCAD mokymosi ataskaita</h1><p class="sub">Sugeneruota ${e(dienaStr(d))} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")} · Brėžly ${e(INFO.versija)}</p>
  <table class="duom"><tr><td>Studentas</td><td><b>${e(st.vardas||"-")}</b></td></tr><tr><td>Grupė</td><td>${e(st.grupe||"-")}</td></tr>${st.dalykas?`<tr><td>Dalykas</td><td>${e(st.dalykas)}</td></tr>`:""}</table>
  <div class="kort"><div><b>${baigtos}/${pam.length}</b><small>pamokos baigtos</small></div><div><b>${prN}/${PRAKTIKA.length}</b><small>praktikos užduotys</small></div>
    <div><b>${S.xp}</b><small>XP · ${e(LYGIAI[lygis(S.xp)][1])}</small></div><div><b>${(S.zenkleliai||[]).length}</b><small>ženkleliai</small></div></div>
  <h2>Pamokos</h2><table><tr><th>Nr.</th><th>Pamoka</th><th>Žingsniai</th><th>Testas</th><th>Baigta</th></tr>${eilP}</table>
  <h2>Praktikos užduotys</h2><table><tr><th>Nr.</th><th>Užduotis</th><th>Lapas</th><th>Priimta</th></tr>${eilU}</table>
  <p class="pastaba">Žingsnius ir praktikos užduotis Brėžly patikrino tiesiai AutoCAD brėžinyje. Ataskaita sukurta studento kompiuteryje -
  dėstytojas gali paprašyti parodyti brėžinius (DWG) ar atlikti užduotį auditorijoje.</p>
  </body></html>`;
}
async function kurtiDestytojoAtaskaita(){
  const st={vardas:$("#ataVardas").value.trim(), grupe:$("#ataGrupe").value.trim(), dalykas:$("#ataDalykas").value.trim()};
  if(!st.vardas){ $("#ataVardas").focus(); pranesti("Įrašyk vardą ir pavardę."); return; }
  sg("studentas",st.vardas); sg("grupe",st.grupe); sg("dalykas",st.dalykas);
  const r=await api("/api/destytojo_ataskaita",{vardas:st.vardas,html:ataskaitosHTML(st)});
  if(!r.ok){ pranesti(r.klaida); return; }
  rodytiLangeli(`<h2>Ataskaita sukurta</h2><p>${INFO.windows?"Atidariau ją naršyklėje - spausk „Spausdinti / išsaugoti PDF“.":"Atsidaryk ją naršyklėje ir spausdink (Ctrl+P)."}</p>
    <code class="kelias">${esc(r.kelias)}</code>
    <div class="eil" style="margin-top:14px"><span class="tarpas"></span><button class="btn pagr" onclick="uzdarytiLangeli()">Gerai</button></div>`);
}

/* ---- progreso perkėlimas tarp kompiuterių ---- */
async function eksportuotiProgresa(){
  if(DEMO_S){ pranesti("Išjunk demo režimą prieš eksportuodamas."); return; }
  try{ await api("/api/progresas",{S,nustatymai:NUST}); }catch(e){}
  const r=await api("/api/progresas_eksportuoti",{});
  if(!r.ok){ pranesti(r.klaida); return; }
  rodytiLangeli(`<h2>Progresas eksportuotas</h2>
    <p>${r.santrauka.xp} XP · ${r.santrauka.zingsniai} žingsn. · ${r.santrauka.praktika} užduot. · ${r.santrauka.zenkleliai} ženkl.</p>
    <code class="kelias">${esc(r.kelias)}</code>
    <p style="margin-top:10px">Nusikopijuok šį failą į kitą kompiuterį ir ten: Nustatymai › Progresas › <b>Importuoti</b>.</p>
    <div class="eil" style="margin-top:14px"><span class="tarpas"></span><button class="btn pagr" onclick="uzdarytiLangeli()">Gerai</button></div>`);
}
async function importuotiProgresa(inp){
  const f=inp.files&&inp.files[0]; inp.value=""; if(!f) return;
  if(f.size>5e6){ pranesti("Per didelis failas - tai ne Brėžly progresas."); return; }
  const turinys=await f.text();
  const r=await api("/api/progresas_importuoti",{turinys});
  if(!r.ok){ pranesti(r.klaida); return; }
  const eil=(p,a)=>`<tr><td>${p}</td><td>${a(r.dabar)}</td><td><b>${a(r.failas)}</b></td></tr>`;
  window._importoTurinys=turinys;
  rodytiLangeli(`<h2>Importuoti progresą?</h2>
    <p>Dabartinis progresas bus <b>pakeistas</b> failo progresu. Jo kopija išliks aplanke „perkelimas“.</p>
    <table class="lent-palyg"><tr><th></th><th>Dabar</th><th>Faile</th></tr>
      ${eil("Vardas",x=>esc(x.vardas||"-"))}${eil("XP",x=>x.xp)}${eil("Žingsniai",x=>x.zingsniai)}${eil("Užduotys",x=>x.praktika)}${eil("Ženkleliai",x=>x.zenkleliai)}</table>
    ${r.eksportuota?`<p style="margin-top:8px;opacity:.75">Failas sukurtas ${esc(r.eksportuota.replace("T"," "))}</p>`:""}
    ${r.failas.xp<r.dabar.xp?`<p style="color:var(--err)">Faile XP mažiau nei dabar - ar tikrai tas failas?</p>`:""}
    <div class="eil" style="margin-top:14px"><span class="tarpas"></span><button class="btn" onclick="uzdarytiLangeli()">Atšaukti</button><button class="btn pagr" onclick="patvirtintiImporta()">Importuoti</button></div>`);
}
async function patvirtintiImporta(){
  NESAUGOTI=true; clearTimeout(saugojimoLaikmatis);
  const r=await api("/api/progresas_importuoti",{turinys:window._importoTurinys,patvirtinta:true});
  if(!r.ok){ NESAUGOTI=false; pranesti(r.klaida); return; }
  try{ localStorage.removeItem("cadet"); }catch(e){}
  location.reload();
}

/* ---- testavimo įrankiai: atrakinami slaptažodžiu (tikrina serveris) ---- */
function testoLangas(){
  rodytiLangeli(`<h2>🔒 Kūrėjo režimas</h2><p>Įvesk testavimo slaptažodį.</p>
    <form onsubmit="event.preventDefault();atrakintiTesta()"><label for="testSl">Slaptažodis</label>
    <input type="password" id="testSl" autocomplete="current-password"><p id="testKl" style="color:var(--err);margin:8px 0 0" role="alert"></p>
    <div class="eil" style="margin-top:14px"><button class="btn pagr" type="submit" id="testBtn">Atrakinti</button><button class="btn" type="button" onclick="uzdarytiLangeli()">Atšaukti</button></div></form>`);
}
async function atrakintiTesta(){
  const b=$("#testBtn"); b.disabled=true;
  let r; try{ r=await api("/api/testas",{slaptazodis:$("#testSl").value}); }catch(e){ r={ok:false,klaida:"Brėžly neatsako"}; }
  b.disabled=false;
  if(!r.ok){ $("#testKl").textContent=r.klaida; $("#testSl").select(); return; }
  testasAtrakintas=true; try{sessionStorage.setItem("testZ",r.zetonas);}catch(e){}
  Kurejas.veikla(); uzdarytiLangeli(); pranesti("🛠 Kūrėjo režimas atrakintas"); Kurejas.juosta(); rodytiKureja();
}
function uzrakintiTesta(tyliai){
  const z=(()=>{try{return sessionStorage.getItem("testZ");}catch(e){return null;}})();
  if(z) api("/api/testas_uzrakinti",{zetonas:z}).catch(()=>{});
  testasAtrakintas=false; try{sessionStorage.removeItem("testZ");}catch(e){}
  if(DEMO_S) Kurejas.demo(false);
  Kurejas.juosta(); if(!tyliai) pranesti("🔒 Kūrėjo režimas užrakintas");
  if(rodinys==="kurejas"||rodinys==="nustatymai") rodytiNustatymus();
}
function atstatytiViska(){
  if(!testasAtrakintas||!confirm("Ištrinti visą progresą, XP ir daiktus?")) return;
  S={xp:0,atlikta:{},zenkleliai:[],dabartinis:{},eq:null,matyti:null,nauji:[],dienos:[],vardas:"",savininkas:""};
  try{localStorage.removeItem("cadet");}catch(e){}
  api("/api/progresas",{S,nustatymai:NUST}).then(()=>location.reload());
}



/* ---- atsidarė įprastoje naršyklėje (nerasta Edge/Chrome) ---- */
function narsyklesJuosta(){
  const d=document.createElement("div"); d.id="narsJuosta"; d.setAttribute("role","status");
  d.style.cssText="position:fixed;left:50%;top:12px;transform:translateX(-50%);z-index:90;max-width:min(680px,94vw);display:flex;gap:12px;align-items:center;padding:12px 14px;border-radius:14px;background:var(--panel);border:1px solid var(--accent);box-shadow:0 10px 30px #0007;font-size:14px;color:var(--text)";
  d.innerHTML=`<span style="font-size:22px" aria-hidden="true">🪟</span><div style="flex:1"><b>Brėžly atsidarė naršyklėje.</b> Patogiau - atskirame lange: įdiek <b>Microsoft Edge</b> arba <b>Google Chrome</b> ir paleisk Brėžly iš naujo. Veikia ir taip.</div>
    <button class="btn" onclick="sg('narsykle_ok','1');this.parentNode.remove()">Supratau</button>`;
  document.body.appendChild(d);
}
/* =================== KŪRĖJO PULTAS (tik atrakinus slaptažodžiu) =================== */
const Kurejas={
  paskVeikla:Date.now(), info:null, isvestis:{},
  zetonas(){ try{return sessionStorage.getItem("testZ");}catch(e){return null;} },
  async api(kelias,d={}){
    let r; try{ r=await api(kelias,{...d,zetonas:this.zetonas()}); }catch(e){ r={ok:false,klaida:"Brėžly neatsako"}; }
    if(r.uzrakinta){ uzrakintiTesta(true); pranesti("🔒 Kūrėjo režimas užsirakino - atrakink iš naujo."); }
    return r;
  },
  veikla(){ this.paskVeikla=Date.now(); },
  tikrintiLaika(){ if(testasAtrakintas && Date.now()-this.paskVeikla>30*60*1000){ uzrakintiTesta(true); pranesti("🔒 30 min. be veiklos - kūrėjo režimas užrakintas."); } },
  juosta(){
    let b=$("#kurBar");
    if(!testasAtrakintas){ if(b) b.remove(); return; }
    if(!b){ b=document.createElement("div"); b.id="kurBar"; document.body.appendChild(b); }
    const im=BUS.imitacija||(this.info&&this.info.imitacija);
    if(DEMO_S){ b.style.opacity=".25"; b.innerHTML=`<button onclick="rodytiKureja()" title="Kūrėjo pultas (demo režimas)">🛠</button>`; return; }
    b.style.opacity="";
    b.innerHTML=`${im?`<span class="im" title="AutoCAD imituojamas">IMIT: ${im==="gerai"?"✓":"✗"}</span>`:""}${DEMO_S?'<span class="im dm">DEMO</span>':""}
      <button onclick="Kurejas.iskaityti()" title="Įskaityti dabartinį žingsnį ar užduotį be tikrinimo">⚡ Įskaityti</button>
      <button onclick="rodytiKureja()" title="Kūrėjo pultas">🛠</button>`;
  },
  /* --- šuoliai ir įskaitymas --- */
  iskaityti(){
    if(rodinys==="pamoka"&&PAM){
      const nr=S.dabartinis[PAM.id], z=PAM.zingsniai[nr]; if(!z) return;
      const atl=S.atlikta[PAM.id]||(S.atlikta[PAM.id]=[]); if(!atl.includes(z.id)) atl.push(z.id);
      saugoti(); piestiSonine(); pranesti(`⚡ Įskaityta: ${z.pavadinimas||z.id}`); toliau(); return;
    }
    if(rodinys==="praktika"&&prDabar){ this.praktika(prDabar,true); rodytiUzduoti(prDabar); return; }
    pranesti("Atidaryk pamokos žingsnį arba praktikos užduotį.");
  },
  eiti(){
    const pid=$("#kPam").value, nr=+$("#kZing").value;
    rodytiPradzia(pid); rodytiZingsni(nr);
  },
  iskaitytiIki(){
    const p=pamokaPagalId($("#kPam").value), nr=+$("#kZing").value;
    S.atlikta[p.id]=p.zingsniai.slice(0,nr).map(z=>z.id); S.dabartinis[p.id]=nr; saugoti(); piestiSonine();
    pranesti(`⚡ ${p.pavadinimas}: įskaityti ${nr} žingsniai`); rodytiKureja();
  },
  pamokaVisa(atlikta){
    const p=pamokaPagalId($("#kPam").value);
    S.atlikta[p.id]=atlikta?p.zingsniai.map(z=>z.id):[]; S.dabartinis[p.id]=0; saugoti(); piestiSonine(); tikrintiAtlygiusVeliau();
    pranesti(atlikta?`🏆 ${p.pavadinimas} - baigta`:`↺ ${p.pavadinimas} - nuo pradžių`); rodytiKureja();
  },
  zingsniai(){ const p=pamokaPagalId($("#kPam").value); $("#kZing").innerHTML=p.zingsniai.map((z,i)=>`<option value="${i}">${i+1}. ${esc(z.pavadinimas||z.id)}</option>`).join(""); },
  praktika(id,atlikta){
    S.praktika=S.praktika||{};
    if(atlikta) S.praktika[id]=new Date().toISOString().slice(0,10); else delete S.praktika[id];
    if(PRAKTIKA.filter(u=>S.praktika[u.id]).length>=4) duotiZenkleli("praktikas");
    saugoti(); pranesti(atlikta?"✓ Užduotis pažymėta atlikta":"↺ Užduotis nebeatlikta");
  },
  /* --- progresas --- */
  lygis(n){ S.xp=LYGIAI[n-1][0]; saugoti(); piestiZaideja(); tikrintiAtlygiusVeliau(); pranesti(`Lygis ${n}: ${LYGIAI[n-1][1]}`); rodytiKureja(); },
  eksportuoti(){
    const t=JSON.stringify({brezly:INFO.versija,data:new Date().toISOString(),S:DEMO_S||S,nustatymai:NUST},null,1);
    const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob([t],{type:"application/json"}));
    a.download=`Brezly_profilis_${new Date().toISOString().slice(0,10)}.json`; document.body.appendChild(a); a.click();
    setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},1000); pranesti("Profilis išsaugotas aplanke Atsisiuntimai.");
  },
  importuoti(inp){
    const f=inp.files[0]; if(!f) return;
    f.text().then(t=>{
      let d; try{ d=JSON.parse(t); }catch(e){ pranesti("Netinkamas failas"); return; }
      if(!d.S||typeof d.S.xp!=="number"){ pranesti("Faile nėra Brėžly profilio"); return; }
      if(!confirm(`Pakeisti dabartinį progresą šiuo (${d.S.xp} XP)? Dabartinis bus perrašytas.`)) return;
      if(DEMO_S) this.demo(false);
      S=Object.assign({xp:0,atlikta:{},praktika:{},zenkleliai:[],dabartinis:{},nauji:[],dienos:[]},d.S);
      if(d.nustatymai) Object.assign(NUST,d.nustatymai);
      saugoti(); planuotiSaugojima(true); setTimeout(()=>location.reload(),600);
    });
  },
  /* --- AutoCAD --- */
  async imitacija(v){ const r=await this.api("/api/k_imitacija",{rezimas:v}); if(r.ok){ BUS.imitacija=r.imitacija; await tikrintiBusena(); this.info=null; pranesti(v?`Imitacija: tikrinimas visada „${v}“`:"Imitacija išjungta - vėl tikras AutoCAD"); rodytiKureja(); } },
  async kaMato(){
    const d={}; const sel=$("#kKas").value;
    if(sel==="pamoka"&&PAM){ d.pamoka=PAM.id; d.zingsnis=S.dabartinis[PAM.id]||0; }
    if(sel.startsWith("U")) d.praktika=sel;
    this.isvestis.acad="Skaitau brėžinį..."; $("#kAcad").textContent=this.isvestis.acad;
    const r=await this.api("/api/k_acad",d);
    let t;
    if(!r.ok) t="KLAIDA: "+(r.klaida||"?");
    else{
      t=`AutoCAD ${r.versija}  ·  kalba ${r.kalba}  ·  INSUNITS ${r.vienetai}\nFailas: ${r.failas}\nAktyvus sluoksnis: ${r.sluoksnis}\nSluoksniai: ${(r.sluoksniai||[]).join(", ")||"-"}\n\nObjektai:\n`+
        (Object.entries(r.tipai||{}).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`  ${String(v).padStart(4)} × ${k}`).join("\n")||"  (tuščia)")+
        `\n\nApskritimų skersmenys: ${(r.skersmenys||[]).map(x=>"ø"+x).join(", ")||"-"}\n3D kūnų tūriai: ${(r.turiai||[]).map(x=>x+" mm³").join(", ")||"-"}`;
      if((r.kunai||[]).length) t+="\n\n3D kūnų ribos:\n"+r.kunai.map((k,i)=>`  ${i+1}. [${k.min.join(", ")}] → [${k.max.join(", ")}]  ${k.turis} mm³  (${k.sluoksnis})`).join("\n");
      if(r.pamokos_pastabos) t+=`\n\nPamokos žingsnio tikrinimas (${PAM.pavadinimas}, ${(S.dabartinis[PAM.id]||0)+1} žingsnis):\n`+(r.pamokos_pastabos.length?r.pamokos_pastabos.map(p=>"  ✗ "+p).join("\n"):"  ✓ teisingai");
      if(r.praktikos_pastabos) t+=`\n\nPraktikos tikrinimas (${d.praktika}):\n`+(r.praktikos_pastabos.length?r.praktikos_pastabos.map(p=>"  ✗ "+p).join("\n"):"  ✓ teisingai");
    }
    this.isvestis.acad=t; const el=$("#kAcad"); if(el) el.textContent=t;
  },
  /* --- langai iš naujo --- */
  vedlys(){
    this.d=null; Vedlys.d={vardas:S.savininkas||"",personazas:(S.eq&&S.eq.personazas)||"robotas",pvardas:S.vardas||"",patirtis:"naujas",tema:sg("tema")||"dark",dydis:sg("dydis")||"1"};
    Vedlys.nr=0; Vedlys.piesti();
  },
  turas(){ rodytiPradzia(); setTimeout(()=>Gidas.pradetiTura(Gidas.PRADZIOS_TURAS,"cadet_turas"),300); },
  atlygis(){ const ids=atrakinti(); const id=ids[Math.floor(Math.random()*ids.length)]||DAIKTAI[0].id; atlygioEile.push(id); rodytiAtlygi(); },
  /* --- personažas, animacijos, demo --- */
  greitis(v){ sg("anim_greitis",String(v)); taikytiAnimGreiti(); rodytiKureja(); },
  demo(on){
    if(on&&!DEMO_S){
      DEMO_S=JSON.parse(JSON.stringify(S));
      const d=JSON.parse(JSON.stringify(S)), dienos=[];
      for(let i=0;i<6;i++){ const x=new Date(); x.setDate(x.getDate()-i); dienos.push(dienaStr(x)); }
      d.xp=320; d.savininkas=""; d.dienos=dienos; d.zenkleliai=["pirmas","be_uzuominu","praktikas"];
      d.atlikta={}; INFO.pamokos.slice(0,3).forEach(p=>d.atlikta[p.id]=p.zingsniai.map(z=>z.id));
      d.praktika={U1_Tarpine:"2026-11-01",U2_Flansas:"2026-11-03",U3_Laikiklis:"2026-11-05",U5_Projekcijos:"2026-11-08"};
      S=d; S.matyti=atrakinti(); S.nauji=[];
      pranesti("🎬 Demo režimas: rodomas pavyzdinis progresas, niekas neįrašoma.");
    } else if(!on&&DEMO_S){ S=DEMO_S; DEMO_S=null; pranesti("Demo išjungtas - grąžintas tikras progresas."); }
    piestiZaideja(); piestiSonine(); this.juosta(); rodytiKureja();
  },
  /* --- žurnalas, nuotrauka --- */
  async zurnalas(){
    const r=await this.api("/api/k_zurnalas"); if(!r.ok) return;
    this.isvestis.zurn=(r.klaida?`=== klaida.txt ===\n${r.klaida}\n\n`:"")+`=== ${r.kelias} (paskutinės ${r.eilutes.length}) ===\n`+(r.eilutes.slice().reverse().join("\n")||"(tuščias - klaidų nebuvo)");
    $("#kZurn").textContent=this.isvestis.zurn;
  },
  kopijuoti(id){ const t=$("#"+id).textContent; navigator.clipboard.writeText(t).then(()=>pranesti("Nukopijuota"),()=>pranesti("Nepavyko nukopijuoti")); },
  async nuotrauka(){
    const bar=$("#kurBar"); if(bar) bar.style.visibility="hidden";
    await new Promise(r=>setTimeout(r,250));
    const r=await this.api("/api/k_nuotrauka"); if(bar) bar.style.visibility="";
    pranesti(r.ok?"📸 Išsaugota: "+r.kelias.split(/[\\/]/).pop():(r.klaida||"Nepavyko"));
  },
  /* --- funkcijos ir saugumas --- */
  async funkcija(k,v){ const r=await this.api("/api/k_funkcijos",{funkcijos:{[k]:v}}); if(r.ok){ INFO.funkcijos=r.funkcijos; taikytiFunkcijas(); this.info=null; rodytiKureja(); } },
  async slaptazodis(){
    const n1=$("#kSl1").value, n2=$("#kSl2").value, kl=$("#kSlKl");
    if(n1!==n2){ kl.textContent="Nauji slaptažodžiai nesutampa."; return; }
    const r=await this.api("/api/k_slaptazodis",{senas:$("#kSl0").value,naujas:n1,tik_siame:$("#kSlKomp").checked});
    if(!r.ok){ kl.textContent=r.klaida; return; }
    pranesti(r.kompiuteris?`🔑 Slaptažodis pakeistas. Kūrėjo režimas veiks tik kompiuteryje ${r.kompiuteris}.`:"🔑 Slaptažodis pakeistas"); this.info=null; rodytiKureja();
  }
};
function taikytiFunkcijas(){
  const f=INFO.funkcijos||{};
  document.querySelectorAll("#nav button[data-v]").forEach(b=>{ const k=b.dataset.v; if(k in f) b.classList.toggle("hidden",!f[k]); });
}
let animLaikmatis=null;
function taikytiAnimGreiti(){
  const g=parseFloat(sg("anim_greitis"))||1; clearInterval(animLaikmatis);
  const taikyti=()=>{ try{ document.getAnimations().forEach(a=>{ if(a.playbackRate!==g) a.playbackRate=g; }); }catch(e){} };
  taikyti(); if(g!==1) animLaikmatis=setInterval(taikyti,250);
}
async function rodytiKureja(){
  if(!testasAtrakintas){ rodytiNustatymus(); return; }
  nustatytiRodini("kurejas"); $("#vPam").textContent="Kūrėjo pultas";
  document.querySelectorAll("#nav button").forEach(b=>b.classList.toggle("akt",b.dataset.v==="nustatymai"));
  if(!Kurejas.info){ const r=await Kurejas.api("/api/k_busena"); if(!r.ok) return; Kurejas.info=r; }
  const K=Kurejas.info, im=BUS.imitacija||K.imitacija||null, g=parseFloat(sg("anim_greitis"))||1, f=INFO.funkcijos||{};
  const pamId=(PAM||INFO.pamokos[0]).id, pmyg=(arr,dab,fn)=>arr.map(([v,t])=>`<button aria-pressed="${dab===v}" onclick="${fn(v)}">${t}</button>`).join("");
  $("#vidus").innerHTML=`<div class="eil" style="margin-bottom:6px"><h1 class="ant1" style="flex:1">🛠 Kūrėjo pultas</h1><button class="btn" onclick="uzrakintiTesta()">🔒 Užrakinti</button></div>
  <p class="po1">Matai tik tu - po slaptažodžiu. Kompiuteris: <b>${esc(K.kompiuteris)}</b> · Python ${esc(K.python)} · užsirakins po ${K.galiojimas_min} min. be veiklos.</p>
  <div class="kur-tink">
   <div class="nust-gr"><h3>🎯 Šuolis į pamoką</h3><p>Nueik į bet kurį žingsnį arba įskaityk be tikrinimo.</p>
    <div class="kur-m"><select id="kPam" onchange="Kurejas.zingsniai()" aria-label="Pamoka">${INFO.pamokos.map((p,i)=>`<option value="${p.id}" ${p.id===pamId?"selected":""}>${i+1}. ${esc(p.pavadinimas)}</option>`).join("")}</select></div>
    <div class="kur-m"><select id="kZing" aria-label="Žingsnis"></select><button onclick="Kurejas.eiti()">Eiti →</button></div>
    <div class="kur-m"><button onclick="Kurejas.iskaitytiIki()" title="Visi ankstesni žingsniai - atlikti">⚡ Įskaityti iki šio</button><button onclick="Kurejas.pamokaVisa(true)">🏆 Visa pamoka</button><button class="pavoj" onclick="Kurejas.pamokaVisa(false)">↺ Iš naujo</button></div>
    <p class="kur-sm">Mygtukas „⚡ Įskaityti“ apačioje dešinėje įskaito dabartinį žingsnį ar užduotį.</p></div>

   <div class="nust-gr"><h3>📐 Praktika</h3><p>Pažymėk užduotis atliktomis ar ne.</p>
    ${PRAKTIKA.map(u=>`<div class="kur-m" style="align-items:center"><span style="flex:1;font-size:13.5px">${u.nr}. ${esc(u.pav)} <small style="color:var(--muted)">${u.fmt}</small></span>${prAtlikta(u.id)?`<button onclick="Kurejas.praktika('${u.id}',false);rodytiKureja()">✓ atlikta</button>`:`<button onclick="Kurejas.praktika('${u.id}',true);rodytiKureja()">pažymėti</button>`}<button onclick="rodytiUzduoti('${u.id}')">→</button></div>`).join("")}</div>

   <div class="nust-gr"><h3>⭐ Progresas</h3><p>XP ${S.xp} · lygis ${lygis(S.xp)+1}${DEMO_S?" · (DEMO)":""}</p>
    <div class="kur-m"><button onclick="testXP(50)">+50 XP</button><button onclick="testXP(250)">+250 XP</button><button onclick="testZenkleliai()">Visi ženkleliai</button><button onclick="testSerija()">+1 d. serija</button></div>
    <div class="kur-m"><span style="font-size:13px;align-self:center;color:var(--muted)">Lygis:</span>${LYGIAI.map((l,i)=>`<button aria-pressed="${lygis(S.xp)===i}" title="${l[1]} (${l[0]} XP)" onclick="Kurejas.lygis(${i+1})">${i+1}</button>`).join("")}</div>
    <div class="kur-m"><button onclick="Kurejas.eksportuoti()">⬇ Eksportuoti profilį</button><label class="btn" style="font-size:13px;padding:6px 11px;border-radius:9px;cursor:pointer">⬆ Importuoti<input type="file" accept=".json" hidden onchange="Kurejas.importuoti(this)"></label><button class="pavoj" onclick="atstatytiViska()">Atstatyti viską</button></div>
    <p class="kur-sm">Failas: ${esc(K.duomenys)}</p></div>

   <div class="nust-gr"><h3>🖥 AutoCAD</h3><p>Imitacija - testuok be AutoCAD: tikrinimas visada grąžins pasirinktą atsakymą.</p>
    <div class="kur-m">${pmyg([[null,"Išjungta"],["gerai","✓ Visada gerai"],["blogai","✗ Visada blogai"]],im,v=>`Kurejas.imitacija(${v?`'${v}'`:"null"})`)}</div>
    <p style="margin:14px 0 0;font-weight:700;font-size:13.5px">Ką mato tikrinimas</p>
    <div class="kur-m"><select id="kKas" aria-label="Ką tikrinti"><option value="">Tik brėžinio turinys</option>${PAM?`<option value="pamoka">+ pamokos žingsnis (${esc(PAM.pavadinimas)})</option>`:""}${PRAKTIKA.map(u=>`<option value="${u.id}" ${prDabar===u.id?"selected":""}>+ praktika ${u.nr}. ${esc(u.pav)}</option>`).join("")}</select><button onclick="Kurejas.kaMato()">🔍 Skaityti</button><button onclick="Kurejas.kopijuoti('kAcad')">📋</button></div>
    <div class="kur-isv" id="kAcad">${esc(Kurejas.isvestis.acad||"")}</div></div>

   <div class="nust-gr"><h3>🔁 Langai iš naujo</h3><p>Pažiūrėk, ką mato naujas vartotojas.</p>
    <div class="kur-m"><button onclick="Kurejas.vedlys()">👋 Vedlys</button><button onclick="kasNaujo()">✨ Kas naujo</button><button onclick="Kurejas.turas()">❔ Gido turas</button><button onclick="Kurejas.atlygis()">🎁 Atlygio langas</button><button onclick="konfeti(80)">🎉 Konfeti</button></div></div>

   <div class="nust-gr"><h3>🤖 Personažas ir animacijos</h3>
    <div class="kur-m"><button onclick="Robotas.reaguoti('dziaug',1600)">😄 Džiaugtis</button><button onclick="Robotas.reaguoti('liud',1600)">😢 Liūdėti</button><button onclick="Robotas.reaguoti('moja',1900)">👋 Mojuoti</button><button onclick="Robotas.kalbeti('Labas! Aš tavo braižymo draugas.')">💬 Kalbėti</button></div>
    <div class="kur-m"><span style="font-size:13px;align-self:center;color:var(--muted)">Animacijų greitis:</span>${pmyg([[0.5,"×0.5"],[1,"×1"],[2,"×2"]],g,v=>`Kurejas.greitis(${v})`)}</div>
    <div class="nust-eil" style="margin-top:6px"><div><b>🎬 Demo režimas</b><small>TikTok įrašams: pavyzdinis progresas (320 XP, 3 pamokos, 4 užduotys), vardas paslėptas. Niekas neįrašoma; išjungus - grįžta tikras.</small></div>${jung(!!DEMO_S,`Kurejas.demo(${!DEMO_S})`,"Demo režimas")}</div>
    <div class="kur-m"><button onclick="Kurejas.nuotrauka()">📸 Lango nuotrauka (PNG)</button></div>
    <p class="kur-sm">Nuotraukos: Dokumentai\\Brezly\\Nuotraukos</p></div>

   <div class="nust-gr"><h3>📜 Žurnalas</h3><p>Paskutinės klaidos ir įvykiai (naujausi viršuje).</p>
    <div class="kur-m"><button onclick="Kurejas.zurnalas()">↻ Rodyti</button><button onclick="Kurejas.kopijuoti('kZurn')">📋 Kopijuoti</button><button onclick="ataskaitosLangas()">🐞 Ataskaita ZIP</button></div>
    <div class="kur-isv" id="kZurn">${esc(Kurejas.isvestis.zurn||"")}</div></div>

   <div class="nust-gr"><h3>🧩 Funkcijų jungikliai</h3><p>Išjungta funkcija dingsta iš meniu. Įrašoma į <code>funkcijos.json</code> programos aplanke - nukopijavus aplanką draugams, jie irgi jos nematys.</p>
    ${[["praktika","📐 Praktika"],["spinta","👕 Spinta"],["lygiai","📊 Lygiai"],["profilis","🪪 Profilis"],["kartoti","🃏 Kartoti"]].map(([k,t])=>`<div class="nust-eil"><div><b>${t}</b></div>${jung(f[k]!==false,`Kurejas.funkcija('${k}',${f[k]===false})`,t)}</div>`).join("")}</div>

   <div class="nust-gr"><h3>🔑 Saugumas</h3><p>${K.susietas?`Kūrėjo režimas susietas su kompiuteriu <b>${esc(K.susietas)}</b> - kituose jo nebus.`:"Kūrėjo režimas veikia bet kuriame kompiuteryje, kur yra testavimas.json."} Diegimo failuose draugams (Brezly_Setup) testavimas.json nėra.</p>
    <form onsubmit="event.preventDefault();Kurejas.slaptazodis()">
    <div class="kur-m"><input type="password" id="kSl0" placeholder="Senas slaptažodis" autocomplete="current-password" style="flex:1"></div>
    <div class="kur-m"><input type="password" id="kSl1" placeholder="Naujas (≥ 8)" autocomplete="new-password" style="flex:1"><input type="password" id="kSl2" placeholder="Pakartok" autocomplete="new-password" style="flex:1"></div>
    <label class="kur-m" style="align-items:center;font-size:13.5px;gap:8px"><input type="checkbox" id="kSlKomp" ${K.susietas?"checked":""}> Leisti tik šiame kompiuteryje (${esc(K.kompiuteris)})</label>
    <p id="kSlKl" style="color:var(--err);margin:6px 0 0;font-size:13px" role="alert"></p>
    <div class="kur-m"><button type="submit">Pakeisti slaptažodį</button></div></form></div>
  </div>`;
  Kurejas.zingsniai();
  const z=PAM&&PAM.id===$("#kPam").value?S.dabartinis[PAM.id]||0:0; $("#kZing").value=z;
  Kurejas.juosta();
}

/* ---- pranešimas apie klaidą ---- */
function ataskaitosLangas(){
  rodytiLangeli(`<h2>🐞 Pranešti apie klaidą</h2><p>Aprašyk, kas nutiko. Sukursiu failą su informacija apie Brėžly ir AutoCAD - jį galėsi atsiųsti kūrėjui.</p>
    <label for="atsAp">Kas nutiko?</label><textarea id="atsAp" placeholder="Pvz.: 3 pamokos 4 žingsnis sako „ne taip“, nors nubraižiau teisingai."></textarea>
    <div class="eil" style="margin-top:14px"><button class="btn pagr" id="atsBtn" onclick="kurtiAtaskaita()">Sukurti failą</button><button class="btn" onclick="uzdarytiLangeli()">Atšaukti</button></div>`);
}
async function kurtiAtaskaita(){
  $("#atsBtn").disabled=true;
  let r; try{ r=await api("/api/ataskaita",{aprasymas:$("#atsAp").value,busena:{rodinys,pamoka:PAM&&PAM.id,zingsnis:PAM&&S.dabartinis[PAM.id],xp:S.xp,autocad:BUS,ekranas:[innerWidth,innerHeight]}}); }
  catch(e){ r={ok:false,klaida:"Brėžly neatsako"}; }
  if(!r.ok){ pranesti(r.klaida); $("#atsBtn").disabled=false; return; }
  rodytiLangeli(`<h2>Failas paruoštas ✓</h2><p>Atidariau aplanką su failu. Atsiųsk jį kūrėjui el. paštu ar žinute.</p><code class="kelias">${esc(r.kelias)}</code>
    <div class="eil" style="margin-top:14px"><button class="btn pagr" onclick="uzdarytiLangeli()">Gerai</button></div>`);
}

/* ---- atnaujinimai ---- */
async function tikrintiAtnaujinimus(rankinis){
  let r; try{ r=await api("/api/atnaujinimai"); }catch(e){ r={ok:false}; }
  if(!r.ok){ if(rankinis) pranesti("Nepavyko patikrinti - ar yra internetas?"); return; }
  if(!r.yra){ if(rankinis) pranesti(r.parduotuve?"Brėžly atnaujina Microsoft Store ✓":"Turi naujausią versiją ✓"); return; }
  rodytiLangeli(`<h2>Nauja versija ${esc(r.versija)} 🎉</h2><p>${esc(r.pastabos||"Pataisymai ir patobulinimai.")}</p><p>Tavo progresas išliks.</p>
    <div class="eil"><button class="btn pagr" id="atnBtn" onclick="atnaujinti()">Atnaujinti dabar</button><button class="btn" onclick="uzdarytiLangeli()">Vėliau</button></div>`);
}
async function atnaujinti(){
  const b=$("#atnBtn"); b.disabled=true; b.innerHTML='<span class="sukasi"></span>Atsisiunčiama...';
  await api("/api/progresas",{S,nustatymai:NUST}).catch(()=>{});
  let r; try{ r=await api("/api/atnaujinti",{}); }catch(e){ r={ok:false,klaida:"Ryšio klaida"}; }
  if(!r.ok){ b.disabled=false; b.textContent="Bandyti dar kartą"; pranesti(r.klaida); return; }
  if(r.budas==="setup"){ rodytiLangeli(`<h2>Diegiama nauja versija...</h2><p>Brėžly užsidarys ir netrukus atsidarys iš naujo.</p>`,false); return; }
  rodytiLangeli(`<h2>Perkraunama...</h2><p>Palauk kelias sekundes.</p>`,false);
  api("/api/perkrauti",{}).catch(()=>{});
  setTimeout(()=>location.reload(),5000);
}

/* =================== KARTOJIMAS BE AUTOCAD =================== */
let kartTab="diena", kortNr=0, kortTvarka=null, kartTestas=null;
function naujasKartTestas(){
  const vis=[]; INFO.pamokos.forEach(p=>p.testas.forEach((q,i)=>vis.push({...q,id:p.id+"/"+i,pam:p.pavadinimas})));
  kartTestas={kl:mesk(vis).slice(0,8),ats:[]};
}
function rodytiKartojima(){
  nustatytiRodini("kartoti");
  if(!kortTvarka) kortTvarka=mesk(INFO.korteles.map((_,i)=>i));
  if(!kartTestas) naujasKartTestas();
  const sk=`<div class="skirt" role="tablist">${[["diena","🧠 Dienos kartojimas"],["treniruoklis","⌨ Komandų eilutė"],["silpnos","🎯 Silpnos vietos"],["korteles","Komandų kortelės"],["testas","Testas iš visų pamokų"]]
    .map(([k,v])=>`<button class="${kartTab===k?"akt":""}" onclick="kartTab='${k}';rodytiKartojima()">${v}</button>`).join("")}</div>`;
  let t="";
  if(kartTab==="diena") t=Kartojimas.html();
  else if(kartTab==="treniruoklis") t=`<p class="po1" style="margin-top:0">Įvesk komandas ir atsakymus taip, kaip AutoCAD komandų eilutėje - be AutoCAD. Taip greičiau įsimeni, ką rašyti.</p><div id="trenVieta"></div>`;
  else if(kartTab==="silpnos") t=Silpnos.html();
  else if(kartTab==="korteles"){
    const n=kortTvarka.length, k=INFO.korteles[kortTvarka[((kortNr%n)+n)%n]], pam=pamokaPagalId(k.pamoka);
    t=`<div class="kort-viet"><button class="kortele" id="kortele" onclick="this.classList.toggle('apversta')" aria-label="Apversti kortelę">
      <div class="pr"><small style="color:var(--muted)">Ką daro ši komanda?</small><b>${esc(k.k)}</b>${k.trump?`<small style="color:var(--muted)">trumpinys: ${esc(k.trump)}</small>`:""}<small style="color:var(--muted);margin-top:8px">Spausk - apversk</small></div>
      <div class="ga"><p>${esc(k.ka)}</p><code>${esc(k.pvz)}</code>${pam?`<small style="color:var(--muted)">${INFO.pamokos.indexOf(pam)+1} pamoka: ${esc(pam.pavadinimas)}</small>`:""}</div></button></div>
      <div class="eil"><button class="btn" onclick="kortNr--;rodytiKartojima()">← Ankstesnė</button><span class="tarpas" style="text-align:center;color:var(--muted)">${((kortNr%n)+n)%n+1} / ${n}</span><button class="btn pagr" onclick="kortNr++;rodytiKartojima()">Kita →</button></div>`;
  } else {
    const T=kartTestas, ats=T.ats.filter(x=>x!==undefined).length, teis=T.kl.filter((q,i)=>T.ats[i]===q.t).length;
    t=T.kl.map((q,i)=>{const a=T.ats[i];return `<div class="klausimas"><small style="color:var(--muted)">${esc(q.pam)}</small><h3>${i+1}. ${esc(q.k)}</h3><div class="variantai">
      ${q.v.map((v,j)=>{const kl=a===undefined?"":j===q.t?"teis":j===a?"neteis":"";return `<button class="${kl}" ${a!==undefined?"disabled":""} onclick="kartAtsakyti(${i},${j},this)">${esc(v)}</button>`;}).join("")}</div>
      ${a!==undefined?`<div class="paaisk">${a===q.t?"✓":"✗"} ${esc(q.p)}</div>`:""}</div>`;}).join("")
      +`<div class="eil">${ats===T.kl.length?`<b style="font-size:17px">Rezultatas: ${teis}/${T.kl.length}</b>`:`<span style="color:var(--muted)">Už pirmą kartą teisingą atsakymą - +3 XP</span>`}<span class="tarpas"></span><button class="btn pagr" onclick="naujasKartTestas();rodytiKartojima()">↻ Nauji klausimai</button></div>`;
  }
  $("#vidus").innerHTML=`<h1 class="ant1">Kartok be AutoCAD</h1><p class="po1">Pasikartok komandas ir teoriją, kai AutoCAD po ranka nėra.</p>${sk}${t}
    <div class="nust-gr" style="margin-top:22px"><h3>📱 Kortelės telefone</h3><p>Atsisiųsk vieną failą su visomis kortelėmis ir testu. Nusiųsk jį sau į telefoną - atsidaro naršyklėje net be interneto.</p>
    <button class="btn" onclick="atsisiustiTelefonui()">Atsisiųsti failą telefonui</button></div>`;
  if(kartTab==="treniruoklis") trenPaleisti();
}
function kartAtsakyti(i,j,el){
  const q=kartTestas.kl[i]; kartTestas.ats[i]=j; S.kartTeis=S.kartTeis||[];
  const r=el.getBoundingClientRect(), xp=j===q.t&&!S.kartTeis.includes(q.id);
  if(xp){ S.kartTeis.push(q.id); saugoti(); }
  rodytiKartojima();
  if(xp){ const d=document.createElement("div"); d.style.cssText=`position:fixed;left:${r.left/zoomas()}px;top:${r.top/zoomas()}px;width:${r.width/zoomas()}px;height:1px`; document.body.appendChild(d); pridetiXP(3,d); setTimeout(()=>d.remove(),50); }
}
function atsisiustiTelefonui(){
  const kl=[]; INFO.pamokos.forEach(p=>p.testas.forEach(q=>kl.push({k:q.k,v:q.v,t:q.t,p:q.p,pam:p.pavadinimas})));
  const duom=JSON.stringify({korteles:INFO.korteles,klausimai:kl}).replace(/</g,"\\u003c");
  const html=`<!doctype html><html lang="lt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Brėžly kortelės</title>
<style>*{box-sizing:border-box}body{margin:0;background:#0a0f1d;color:#eaf0fa;font:16px/1.5 system-ui,sans-serif;padding:16px;max-width:560px;margin:auto}
h1{font-size:24px;margin:6px 0 2px}h1 span{color:#f59e0b}.m{color:#8d9cb9;font-size:14px}.sk{display:flex;gap:6px;margin:16px 0}
.sk button,.b{flex:1;border:1px solid #24304e;background:#151e35;color:inherit;border-radius:12px;padding:12px;font:inherit;font-weight:600}
.sk button.a,.b.p{background:#f59e0b;color:#1a1300;border-color:#f59e0b}
.k{min-height:260px;border:1px solid #24304e;border-radius:20px;background:#151e35;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:22px;text-align:center}
.k b{font:700 34px monospace;color:#f59e0b}.k code{font:14px monospace;background:#05080f;color:#fbbf24;padding:6px 10px;border-radius:8px}
.e{display:flex;gap:8px;margin-top:12px}.q{border:1px solid #24304e;border-radius:16px;background:#151e35;padding:16px;margin-bottom:12px}
.q button{display:block;width:100%;text-align:left;margin-top:8px;border:1.5px solid #24304e;background:#1b2643;color:inherit;border-radius:11px;padding:11px;font:inherit}
.q .t{border-color:#22c55e;background:#123524}.q .n{border-color:#f87171;background:#3a1a1f}</style></head><body>
<h1>Brėž<span>ly</span> kortelės</h1><div class="m">Komandos ir testas iš visų pamokų</div>
<div class="sk"><button id="t1" class="a" onclick="r('k')">Kortelės</button><button id="t2" onclick="r('q')">Testas</button></div><div id="v"></div>
<script>const D=${duom};let n=0,ap=false,ats={},tv=D.korteles.map((_,i)=>i).sort(()=>Math.random()-.5),mode='k';
const e=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function r(m){if(m)mode=m;t1.className=mode=='k'?'a':'';t2.className=mode=='q'?'a':'';
if(mode=='k'){const k=D.korteles[tv[n%tv.length]];v.innerHTML='<div class="k" onclick="ap=!ap;r()">'+(ap?'<p>'+e(k.ka)+'</p><code>'+e(k.pvz)+'</code>':'<span class="m">Ką daro?</span><b>'+e(k.k)+'</b><span class="m">Bakstelk - apversk</span>')+'</div><div class="e"><button class="b" onclick="n=(n+tv.length-1)%tv.length;ap=false;r()">←</button><button class="b p" onclick="n++;ap=false;r()">Kita →</button></div><p class="m" style="text-align:center">'+(n%tv.length+1)+' / '+tv.length+'</p>';}
else{v.innerHTML=D.klausimai.map((q,i)=>'<div class="q"><div class="m">'+e(q.pam)+'</div><b>'+(i+1)+'. '+e(q.k)+'</b>'+q.v.map((x,j)=>'<button class="'+(ats[i]===undefined?'':j===q.t?'t':j===ats[i]?'n':'')+'" onclick="if(ats['+i+']===undefined){ats['+i+']='+j+';r()}">'+e(x)+'</button>').join('')+(ats[i]!==undefined?'<p class="m">'+e(q.p)+'</p>':'')+'</div>').join('');}}
r();<\/script></body></html>`;
  const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob([html],{type:"text/html"})); a.download="Brezly_korteles.html";
  document.body.appendChild(a); a.click(); setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},1000);
  pranesti("Failas „Brezly_korteles.html“ - aplanke Atsisiuntimai. Nusiųsk jį sau į telefoną.");
}

/* ---------- pradžia ---------- */
(async function(){
  await ikeltiProgresa(); await I18N.ikelti(); taikytiTema(); taikytiDydi(); S.eq=S.eq||{...PRADINIS};
  const u=$("#uzsklanda"), baigti=()=>{u.classList.add("dingsta");setTimeout(()=>u.remove(),700);};
  const tvarka=["lape","katinas","peleda","robotas","drakonas","ateivis","pingvinas","meska"];
  $("#uPers").innerHTML=tvarka.map((id,i)=>`<span style="animation-delay:${[.36,.24,.12,0,0,.12,.24,.36][i]}s">${robotoSVG({...PRADINIS,personazas:id,galva:null,ranka:null})}</span>`).join("");
  // užsklanda: pirmą kartą per dieną - visa animacija, vėliau - trumpai; spragtelėjimas ar klavišas praleidžia
  const siandien=new Date().toISOString().slice(0,10), pirmasKartas=sg("uzsklanda_diena")!==siandien; sg("uzsklanda_diena",siandien);
  u.onclick=baigti; addEventListener("keydown",baigti,{once:true}); setTimeout(baigti,pirmasKartas?2200:700);
  INFO=await api("/api/info?kalba="+encodeURIComponent(sg("kalba")||"lt")); PRAKTIKA=INFO.praktika||[]; $("#ver").textContent=INFO.versija;
  $("#verZyme").textContent=String(INFO.versija).split(" ")[0];
  inicializuotiDaiktus(); piestiZaideja(); setTimeout(tikrintiAtlygius,3200); Egzaminas.ciklas();
  rodytiPatarima(); setInterval(rodytiPatarima,20000); Robotas.pradeti();
  rodytiPradzia(); tikrintiBusena(); Gidas.pradzia();
  setInterval(()=>{if(!tikrina)api("/api/ping",{}).catch(()=>{});},3000);
  // būsena ir automatinis tikrinimas: dažnai, kai langas matomas; sumažintas langas AutoCAD netrukdo
  (function busenosCiklas(){ setTimeout(async()=>{ if(!tikrina&&!document.hidden) await tikrintiBusena().catch(()=>{}); busenosCiklas(); },
    document.hidden?20000:(BUS.prisijungta?6000:4000)); })();
  setInterval(()=>{ if(!document.hidden) auto.tikrinti(); },2000);
  document.addEventListener("visibilitychange",()=>{ if(!document.hidden){ tikrintiBusena(); auto.tikrinti(); } });
  { const n=dabartineNaujiena();
    if(!sg("vedlys")){ if(n) sg("matyta_versija",n.versija); setTimeout(()=>Vedlys.pradeti(),3000); }
    else if(n && sg("matyta_versija")!==n.versija) setTimeout(kasNaujo,3300);
    if(n){ const u=$("#uNauja"); if(u){ u.textContent="Nauja "+n.versija+" · "+n.pavadinimas; u.hidden=false; } } }
  if(!sg("praktika_matyta")) $("#praktikosTaskelis").classList.remove("hidden");
  { const lr=langoRez(), ekr=INFO.ekranas||[0,0,1920,1040];
    if(sg("langas_rez")===null&&sg("kompakt")===null&&INFO.windows&&ekr[2]<1700){     // mažas ekranas - pirmą kartą pats
      setTimeout(()=>{ langoRezimas("kompaktiskas",true); pranesti("💻 Mažas ekranas: Brėžly dešinėje, AutoCAD kairėje. Pakeisti - Nustatymai › Brėžly langas."); },1500);
    } else if(lr!=="iprastas") setTimeout(()=>langoRezimas(lr,true),1200);
  }
  setInterval(tikrintiIvykius,700);
  if(sessionStorage.getItem("testZ")) api("/api/testas_galioja",{zetonas:sessionStorage.getItem("testZ")}).then(r=>{testasAtrakintas=!!r.galioja; if(!r.galioja) sessionStorage.removeItem("testZ"); Kurejas.juosta();});
  taikytiFunkcijas(); taikytiAnimGreiti();
  if(INFO.langas&&INFO.langas.budas==="narsykle"&&!sg("narsykle_ok")) narsyklesJuosta();
  ["pointerdown","keydown"].forEach(ev=>addEventListener(ev,()=>Kurejas.veikla(),{passive:true}));
  setInterval(()=>Kurejas.tikrintiLaika(),60000);
  if(INFO.atnaujinimai) setTimeout(tikrintiAtnaujinimus,5000);
})();

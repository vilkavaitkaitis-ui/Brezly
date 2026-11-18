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
addEventListener("pagehide",()=>{if(NESAUGOTI)return;try{navigator.sendBeacon("/api/progresas",JSON.stringify(DEMO_S?{nustatymai:NUST}:{S,nustatymai:NUST}));}catch(e){}});
async function api(kelias,duom){const r=await fetch(kelias,duom===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(duom)});return r.json();}
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
  mazgas(n){ if(n.nodeType!==3||(n.parentNode&&/^(SCRIPT|STYLE|TEXTAREA|CODE)$/.test(n.parentNode.nodeName))) return;
    const v=this.vertimas(n.nodeValue); if(v!==n.nodeValue) n.nodeValue=v; },
  atributai(e){ if(e.nodeType!==1) return; for(const a of ["placeholder","title","aria-label"]){ const v=e.getAttribute(a); if(v){ const w=this.vertimas(v); if(w!==v) e.setAttribute(a,w); } } },
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
    fetch("/api/js_klaida",{method:"POST",headers:{"Content-Type":"application/json"},
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
let S={xp:0,atlikta:{},praktika:{},zenkleliai:[],dabartinis:{},eq:null,matyti:null,nauji:[],dienos:[],vardas:"Robis",savininkas:""};   // progresas
let uzuominuRodyta=0, demo=false, bandymai=0, tikrina=false, paskutinisAtsakas=null;

function saugoti(){ if(DEMO_S) return; sg("cadet",JSON.stringify(S)); planuotiSaugojima();}
function ikelti(){try{const t=sg("cadet");if(t)S=Object.assign(S,JSON.parse(t));}catch(e){}}

/* ---------- XP ir lygiai ---------- */
function lygis(xp){let i=0;LYGIAI.forEach((l,j)=>{if(xp>=l[0])i=j;});return i;}
function piestiZaideja(){
  const i=lygis(S.xp), [nuo,pav]=LYGIAI[i], kitas=LYGIAI[i+1];
  if(S.eq){ $("#avataras").innerHTML=robotoSVG(S.eq); $("#avataras").style.cssText=fonoStilius(S.eq.fonas,true); $("#gidoRobotas").innerHTML=robotoSVG(S.eq); }
  $("#robotoVardas").textContent=S.vardas||"Robis";
  $("#naujiTaskelis").classList.toggle("hidden",!(S.nauji&&S.nauji.length));
  $("#lygNr").textContent=i+1; $("#lygPav").textContent=pav; $("#xpTekstas").textContent=`${S.xp} XP`;
  $("#xpJuosta").style.width = kitas ? `${Math.round((S.xp-nuo)/(kitas[0]-nuo)*100)}%` : "100%";
  $("#vXP").textContent=`${S.xp} XP · ${i+1} lygis`;
  $("#ikiKito").textContent = kitas ? `Iki „${kitas[1]}“: ${kitas[0]-S.xp} XP` : "Aukščiausias lygis!";
  $("#zenkleliai").innerHTML=Object.entries(ZENKLELIAI).map(([k,p])=>`<span class="zenklelis ${S.zenkleliai.includes(k)?"":"uzr"}" title="${S.zenkleliai.includes(k)?"Gautas":"Dar negautas"}">${p}</span>`).join("");
}
function pridetiXP(kiek,el){
  if(kiek<=0)return;
  const pries=lygis(S.xp); S.xp+=kiek; saugoti(); piestiZaideja();
  const r=(el||$("#vidus")).getBoundingClientRect();
  const s=document.createElement("div"); s.className="skrenda"; s.textContent=`+${kiek} XP`;
  const z=parseFloat(document.body.style.zoom)||1;
  s.style.left=((r.left+r.width/2)/z-40)+"px"; s.style.top=(r.top/z-10)+"px"; document.body.appendChild(s); setTimeout(()=>s.remove(),1400);
  if(lygis(S.xp)>pries){ setTimeout(()=>{pranesti(`🎉 Naujas lygis: ${LYGIAI[lygis(S.xp)][1]}!`);konfeti(60);},700); }
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
      el.classList.remove("rob-dziaug","rob-liud","rob-kalba","rob-moja"); void el.offsetWidth; el.classList.add("rob-"+busena);
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

/* =================== PERSONAŽAS IR DAIKTAI =================== */
const SPALVOS={zydra:"#14b8a6",gintaras:"#f59e0b",violetine:"#a78bfa",auksas:"#fbbf24"};
const FONAI={tamsus:{c:"#151e35"},tinklelis:{c:"#0c2f55",t:true},saulelydis:{c:"#7c2d4a",g:"linear-gradient(180deg,#fb7185 0%,#f59e0b 55%,#7c2d4a 100%)"},kosmosas:{c:"#1e1b4b",z:true}};
const PERSONAZAI=[
  {id:"robotas",pav:"Robotas",vardas:"Robis",txt:"Klasika: antena ir šypsena"},
  {id:"katinas",pav:"Katinas",vardas:"Murkis",txt:"Smalsus, ūsuotas, mėgsta tikslumą"},
  {id:"peleda",pav:"Pelėda",vardas:"Pelėdžius",txt:"Išmintinga - žino visas komandas"},
  {id:"lape",pav:"Lapė",vardas:"Lapis",txt:"Gudri - randa trumpiausią kelią"},
  {id:"drakonas",pav:"Drakoniukas",vardas:"Drakis",txt:"Mažas, bet su sparnais"},
  {id:"ateivis",pav:"Ateivis",vardas:"Zūmas",txt:"Atskrido išmokti AutoCAD"},
  {id:"pingvinas",pav:"Pingvinas",vardas:"Ledukas",txt:"Ramus kaip ledkalnis"},
  {id:"meska",pav:"Meškiukas",vardas:"Meškis",txt:"Stiprus ir kantrus"},
];
const personazas=id=>PERSONAZAI.find(p=>p.id===id)||PERSONAZAI[0];
const KATEGORIJOS=[["personazas","Personažas"],["galva","Galva"],["akys","Akys"],["kaklas","Kaklas"],["ranka","Rankoje"],["spalva","Spalva"],["fonas","Fonas"]];
const PRADINIS={personazas:"robotas",galva:"kepure",akys:null,kaklas:null,ranka:"piestukas",spalva:"zydra",fonas:"tamsus"};
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
  {id:"zydra",kat:"spalva",pav:"Žydra",txt:"Pradinė spalva",ar:b=>true},
  {id:"gintaras",kat:"spalva",pav:"Gintarinė",txt:"2 lygis „Kadetas“",ar:b=>b.lyg>=2},
  {id:"violetine",kat:"spalva",pav:"Violetinė",txt:"3 lygis „Braižytojas“",ar:b=>b.lyg>=3},
  {id:"auksas",kat:"spalva",pav:"Auksinė",txt:"5 lygis „Inžinierius“",ar:b=>b.lyg>=5,retas:true},
  {id:"tamsus",kat:"fonas",pav:"Naktis",txt:"Pradinis fonas",ar:b=>true},
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

function fonoStilius(id,mazas){
  const f=FONAI[id]||FONAI.tamsus, dyd=mazas?10:24;
  let st=`background-color:${f.c};`;
  if(f.g) st+=`background-image:${f.g};`;
  if(f.t) st+=`background-image:linear-gradient(rgba(125,211,252,.14) 1px,transparent 1px),linear-gradient(90deg,rgba(125,211,252,.14) 1px,transparent 1px);background-size:${dyd}px ${dyd}px;`;
  if(f.z) st+=`background-image:radial-gradient(circle at 20% 30%,#fff 1px,transparent 1.5px),radial-gradient(circle at 70% 20%,#fde68a 1px,transparent 1.5px),radial-gradient(circle at 80% 70%,#fff 1px,transparent 1.5px),radial-gradient(circle at 35% 80%,#c4b5fd 1.2px,transparent 1.7px),radial-gradient(circle at 55% 50%,#fff .8px,transparent 1.3px);background-size:${mazas?40:120}px ${mazas?40:120}px;`;
  return st;
}
/* =================== PERSONAŽAI =================== */
/* Kiekvieno personažo dalys. Akys (78/122, 94), burna (100, 120), rankos ir kūnas lieka tose pačiose vietose,
   todėl tinka visi daiktai ir judesiai. uz - už kūno, kunas - ant kūno, ausys - už galvos, galva - galvos forma,
   veidasUz - po akimis/burna, veidas - virš jų. */
function personazoDalys(p,c,beKepures){
  const D="#0f172a", W="#e2e8f0", O="#f59e0b", R="#fb7185";
  const galvaRect=rx=>`<rect x="45" y="54" width="110" height="86" rx="${rx}" fill="${D}" stroke="${c}" stroke-width="6"/>`;
  const z={uz:"",kunas:"",ausys:"",galva:galvaRect(20),veidasUz:"",veidas:"",kaklas:true};
  if(p==="katinas") Object.assign(z,{kaklas:false,
    ausys:`<polygon points="50,76 56,26 92,58" fill="${D}" stroke="${c}" stroke-width="6" stroke-linejoin="round"/><polygon points="150,76 144,26 108,58" fill="${D}" stroke="${c}" stroke-width="6" stroke-linejoin="round"/><polygon points="58,62 60,40 76,56" fill="${R}" opacity=".75"/><polygon points="142,62 140,40 124,56" fill="${R}" opacity=".75"/>`,
    galva:galvaRect(40),
    veidas:`<polygon points="93,106 107,106 100,114" fill="${R}"/><path d="M58 112 L26 106 M58 120 L26 124 M142 112 L174 106 M142 120 L174 124" stroke="${c}" stroke-width="3" stroke-linecap="round" opacity=".85"/>`});
  if(p==="peleda") Object.assign(z,{kaklas:false,
    ausys:`<polygon points="52,66 44,28 80,56" fill="${c}"/><polygon points="148,66 156,28 120,56" fill="${c}"/>`,
    galva:galvaRect(38),
    veidasUz:`<circle cx="78" cy="94" r="21" fill="${c}" opacity=".22"/><circle cx="122" cy="94" r="21" fill="${c}" opacity=".22"/>`,
    veidas:`<polygon points="94,104 106,104 100,115" fill="${O}" stroke="${D}" stroke-width="1.5" stroke-linejoin="round"/>`,
    kunas:`<path d="M80 162 l6 6 l6 -6 M94 172 l6 6 l6 -6 M108 162 l6 6 l6 -6" fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity=".7"/>`});
  if(p==="lape") Object.assign(z,{kaklas:false,
    ausys:`<polygon points="46,80 52,18 90,58" fill="${D}" stroke="${c}" stroke-width="6" stroke-linejoin="round"/><polygon points="154,80 148,18 110,58" fill="${D}" stroke="${c}" stroke-width="6" stroke-linejoin="round"/><polygon points="56,64 57,36 76,56" fill="${O}"/><polygon points="144,64 143,36 124,56" fill="${O}"/>`,
    galva:galvaRect(30)+`<polygon points="46,112 32,128 50,128" fill="${c}"/><polygon points="154,112 168,128 150,128" fill="${c}"/>`,
    veidasUz:`<ellipse cx="100" cy="121" rx="27" ry="15" fill="${W}" opacity=".92"/>`,
    veidas:`<ellipse cx="100" cy="109" rx="6" ry="4.5" fill="${D}"/>`,
    kunas:`<ellipse cx="100" cy="171" rx="20" ry="15" fill="${W}" opacity=".85"/>`});
  if(p==="drakonas") Object.assign(z,{kaklas:false,
    uz:`<path d="M66 160 L22 136 L34 160 L18 172 L64 178 Z" fill="${D}" stroke="${c}" stroke-width="4" stroke-linejoin="round"/><path d="M134 160 L178 136 L166 160 L182 172 L136 178 Z" fill="${D}" stroke="${c}" stroke-width="4" stroke-linejoin="round"/>`,
    ausys:`<path d="M64 60 Q52 44 58 26" fill="none" stroke="${O}" stroke-width="7" stroke-linecap="round"/><path d="M136 60 Q148 44 142 26" fill="none" stroke="${O}" stroke-width="7" stroke-linecap="round"/><polygon points="82,57 91,38 100,57" fill="${c}"/><polygon points="100,57 109,38 118,57" fill="${c}"/>`,
    galva:galvaRect(24),
    veidas:`<ellipse cx="92" cy="109" rx="3" ry="2.2" fill="${c}"/><ellipse cx="108" cy="109" rx="3" ry="2.2" fill="${c}"/>`,
    kunas:`<path d="M78 158 h44 M80 168 h40 M84 178 h32" stroke="${c}" stroke-width="2.5" opacity=".45"/>`});
  if(p==="ateivis") Object.assign(z,{kaklas:true,
    ausys:beKepures?`<g class="r-antena"><path d="M78 56 L62 24" stroke="${c}" stroke-width="4.5" stroke-linecap="round"/><circle cx="61" cy="21" r="7" fill="#a3e635"/><path d="M122 56 L138 24" stroke="${c}" stroke-width="4.5" stroke-linecap="round"/><circle cx="139" cy="21" r="7" fill="#a3e635"/></g>`:"",
    galva:`<path d="M100 48 C150 48 162 80 156 106 C150 134 128 142 100 142 C72 142 50 134 44 106 C38 80 50 48 100 48 Z" fill="${D}" stroke="${c}" stroke-width="6"/>`,
    veidasUz:`<circle cx="58" cy="72" r="4" fill="${c}" opacity=".35"/><circle cx="146" cy="80" r="5" fill="${c}" opacity=".35"/><circle cx="138" cy="66" r="3" fill="${c}" opacity=".35"/>`});
  if(p==="pingvinas") Object.assign(z,{kaklas:false,
    uz:`<ellipse cx="82" cy="194" rx="13" ry="6" fill="${O}"/><ellipse cx="118" cy="194" rx="13" ry="6" fill="${O}"/>`,
    galva:galvaRect(42),
    veidasUz:`<path d="M100 76 C112 64 142 70 142 100 C142 124 124 134 100 134 C76 134 58 124 58 100 C58 70 88 64 100 76 Z" fill="${W}" opacity=".92"/>`,
    veidas:`<polygon points="92,105 108,105 100,115" fill="${O}" stroke="${D}" stroke-width="1.5" stroke-linejoin="round"/>`,
    kunas:`<ellipse cx="100" cy="171" rx="24" ry="17" fill="${W}" opacity=".9"/>`});
  if(p==="meska") Object.assign(z,{kaklas:false,
    ausys:`<circle cx="58" cy="60" r="17" fill="${D}" stroke="${c}" stroke-width="6"/><circle cx="142" cy="60" r="17" fill="${D}" stroke="${c}" stroke-width="6"/><circle cx="58" cy="60" r="7" fill="${R}" opacity=".7"/><circle cx="142" cy="60" r="7" fill="${R}" opacity=".7"/>`,
    galva:galvaRect(38),
    veidasUz:`<ellipse cx="100" cy="118" rx="25" ry="16" fill="${c}" opacity=".22"/>`,
    veidas:`<ellipse cx="100" cy="108" rx="7" ry="5" fill="${c}"/>`});
  return z;
}
function robotoSVG(eq){
  const c=SPALVOS[eq.spalva]||"#14b8a6", g=eq.galva, a=eq.akys, k=eq.kaklas, r=eq.ranka;
  // dalys sugrupuotos, kad jas būtų galima judinti (žr. .gyvas CSS ir Robotas)
  const pid=eq.personazas||"robotas", z=personazoDalys(pid,c,!g||g==="ausines");
  let s=`<svg viewBox="0 0 200 200" aria-hidden="true"><g class="r-kunas">`+z.uz;
  s+=`<g class="r-kaire"><path d="M62 160 Q44 168 40 184" fill="none" stroke="${c}" stroke-width="7" stroke-linecap="round"/><circle cx="40" cy="186" r="6" fill="${c}"/></g>`+
    `<g class="r-ranka"><path d="M138 160 Q156 164 162 152" fill="none" stroke="${c}" stroke-width="7" stroke-linecap="round"/></g>`+
    (z.kaklas?`<rect x="92" y="139" width="16" height="12" fill="${c}"/><rect x="62" y="150" width="76" height="42" rx="14" fill="#0f172a" stroke="${c}" stroke-width="6"/>`
              :`<rect x="62" y="143" width="76" height="49" rx="18" fill="#0f172a" stroke="${c}" stroke-width="6"/>`)+z.kunas+
    `<circle class="r-sirdis" cx="100" cy="171" r="6" fill="#fb7185"/><g class="r-galva">`+z.ausys;
  if(pid==="robotas"&&(!g||g==="ausines")) s+=`<g class="r-antena"><line x1="100" y1="54" x2="100" y2="36" stroke="${c}" stroke-width="5"/><circle cx="100" cy="31" r="7" fill="#f59e0b"/></g>`;
  s+=z.galva+z.veidasUz+
    `<g class="r-akys"><circle cx="78" cy="94" r="13" fill="#0f172a" stroke="${c}" stroke-width="5"/><circle cx="122" cy="94" r="13" fill="#0f172a" stroke="${c}" stroke-width="5"/>`+
    `<g class="r-vyzd"><circle cx="79" cy="96" r="5" fill="${c}"/><circle cx="123" cy="96" r="5" fill="${c}"/></g></g>`+
    `<path class="r-burna" d="M80 117 Q100 131 120 117" fill="none" stroke="${c}" stroke-width="5" stroke-linecap="round"/>`+
    `<path class="r-liud" display="none" d="M82 126 Q100 114 118 126" fill="none" stroke="${c}" stroke-width="5" stroke-linecap="round"/>`+
    `<ellipse class="r-kalba" display="none" cx="100" cy="121" rx="11" ry="7" fill="${c}"/>`+z.veidas;
  if(k==="varlyte") s+=`<polygon points="100,146 80,135 80,158" fill="#fb7185"/><polygon points="100,146 120,135 120,158" fill="#fb7185"/><circle cx="100" cy="146.5" r="5.5" fill="#be123c"/>`;
  if(k==="salikas") s+=`<path d="M62 140 Q100 156 138 140 L138 151 Q100 167 62 151 Z" fill="#f59e0b"/><rect x="110" y="150" width="13" height="32" rx="4" fill="#f59e0b" transform="rotate(-12 116 150)"/><path d="M70 146 L76 150 M84 150 L90 154 M98 152 L104 155" stroke="#b45309" stroke-width="2.5"/>`;
  if(a==="akiniai") s+=`<rect x="60" y="80" width="36" height="28" rx="9" fill="none" stroke="#e2e8f0" stroke-width="4"/><rect x="104" y="80" width="36" height="28" rx="9" fill="none" stroke="#e2e8f0" stroke-width="4"/><line x1="96" y1="92" x2="104" y2="92" stroke="#e2e8f0" stroke-width="4"/>`;
  if(a==="saules") s+=`<rect x="58" y="81" width="38" height="26" rx="8" fill="#020617" stroke="#f59e0b" stroke-width="3.5"/><rect x="104" y="81" width="38" height="26" rx="8" fill="#020617" stroke="#f59e0b" stroke-width="3.5"/><line x1="96" y1="90" x2="104" y2="90" stroke="#f59e0b" stroke-width="3.5"/><line x1="66" y1="88" x2="76" y2="88" stroke="#64748b" stroke-width="3" stroke-linecap="round"/><line x1="112" y1="88" x2="122" y2="88" stroke="#64748b" stroke-width="3" stroke-linecap="round"/>`;
  if(a==="monoklis") s+=`<circle cx="122" cy="94" r="18" fill="none" stroke="#fbbf24" stroke-width="4"/><path d="M139 101 Q152 122 141 142" fill="none" stroke="#fbbf24" stroke-width="2.5"/>`;
  if(g==="kepure") s+=`<path d="M70 42 V58 Q100 70 130 58 V42" fill="#1e293b" stroke="#f59e0b" stroke-width="4"/><polygon points="100,12 160,33 100,54 40,33" fill="#1e293b" stroke="#f59e0b" stroke-width="4" stroke-linejoin="round"/><line x1="153" y1="35" x2="153" y2="58" stroke="#f59e0b" stroke-width="3"/><circle cx="153" cy="62" r="5" fill="#fb7185"/>`;
  if(g==="salmas") s+=`<path d="M44 64 Q44 16 100 16 Q156 16 156 64 Z" fill="#facc15" stroke="#ca8a04" stroke-width="3"/><rect x="93" y="16" width="14" height="46" rx="5" fill="#fde047"/><rect x="32" y="58" width="136" height="11" rx="5.5" fill="#eab308" stroke="#ca8a04" stroke-width="2"/>`;
  if(g==="karuna") s+=`<polygon points="56,58 62,18 81,42 100,10 119,42 138,18 144,58" fill="#fbbf24" stroke="#b45309" stroke-width="3" stroke-linejoin="round"/><circle cx="100" cy="42" r="6" fill="#fb7185"/><circle cx="72" cy="48" r="4" fill="#22d3ee"/><circle cx="128" cy="48" r="4" fill="#22d3ee"/>`;
  if(g==="ausines") s+=`<path d="M40 92 Q40 26 100 26 Q160 26 160 92" fill="none" stroke="#a78bfa" stroke-width="9" stroke-linecap="round"/><rect x="28" y="80" width="22" height="34" rx="8" fill="#a78bfa"/><rect x="150" y="80" width="22" height="34" rx="8" fill="#a78bfa"/>`;
  s+=`</g>`;                                   // galvos pabaiga (su kepure/akiniais)
  const ranka=`<circle cx="163" cy="152" r="7" fill="${c}"/>`;
  let rk="";
  if(r==="piestukas") rk=`<polygon points="157,156 169,156 169,114 157,114" fill="#f59e0b" stroke="#0f172a" stroke-width="2"/><polygon points="157,114 169,114 163,100" fill="#fde68a" stroke="#0f172a" stroke-width="2" stroke-linejoin="round"/><rect x="157" y="156" width="12" height="7" fill="#fb7185"/>`+ranka;
  if(r==="skriestuvas") rk=`<line x1="170" y1="104" x2="156" y2="156" stroke="#cbd5e1" stroke-width="4.5" stroke-linecap="round"/><line x1="170" y1="104" x2="188" y2="152" stroke="#cbd5e1" stroke-width="4.5" stroke-linecap="round"/><circle cx="170" cy="102" r="6" fill="#94a3b8" stroke="#0f172a" stroke-width="2"/><polygon points="185,146 191,146 189,160" fill="#f59e0b"/>`+ranka;
  if(r==="liniuote") rk=`<rect x="157" y="88" width="14" height="72" rx="2" fill="#fde68a" stroke="#b45309" stroke-width="2"/><path d="M157 98 h6 M157 108 h4 M157 118 h6 M157 128 h4 M157 138 h6 M157 148 h4" stroke="#b45309" stroke-width="1.8"/>`+ranka;
  if(r==="slankmatis") rk=`<rect x="158" y="86" width="9" height="74" rx="2" fill="#cbd5e1" stroke="#475569" stroke-width="1.5"/><path d="M158 86 h30 v8 h-22 z" fill="#cbd5e1" stroke="#475569" stroke-width="1.5"/><path d="M158 106 h26 v8 h-26 z" fill="#94a3b8" stroke="#475569" stroke-width="1.5"/><path d="M160 124 v30 M163 124 v30" stroke="#475569" stroke-width="1"/>`+ranka;
  return s+`<g class="r-ranka">${rk}</g></g></svg>`;
}
function suDaiktu(id){ const d=daiktas(id); return {...S.eq, [d.kat]:id}; }

/* ---- atlygiai ---- */
let atlygioEile=[], atlygioLaikmatis=null;
function inicializuotiDaiktus(){
  if(!S.eq) S.eq={...PRADINIS};
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
    <div class="apsk" style="${fonoStilius(d.kat==="fonas"?id:S.eq.fonas)}">${robotoSVG(suDaiktu(id))}</div>
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
let rodinys="pradzia", spintosSkirtukas="galva";
function nustatytiRodini(v){ rodinys=v; document.body.classList.remove("meniu"); if(v!=="pamoka") auto.reset(); document.querySelectorAll("#nav button").forEach(b=>b.classList.toggle("akt",b.dataset.v===v)); Gidas.slepti(); clearTimeout(Gidas.nuobodu); $("main").scrollTop=0; if(miniIjungtas()) setTimeout(miniPiesti,0); }
function atnaujintiRodini(){ const f={kurejas:rodytiKureja,praktika:()=>prDabar?rodytiUzduoti(prDabar):rodytiPraktika(),spinta:rodytiSpinta,lygiai:rodytiLygius,profilis:rodytiProfili,nustatymai:rodytiNustatymus}[rodinys]; if(f) f(); }
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
    const mini = d.kat==="personazas" ? `<div class="mini" style="${fonoStilius(eq.fonas,true)}">${robotoSVG({...eq,personazas:d.id})}</div>`
               : d.kat==="fonas" ? `<div class="mini" style="${fonoStilius(d.id,true)}">${robotoSVG({spalva:eq.spalva})}</div>`
               : d.kat==="spalva" ? `<div class="mini" style="background:#0f172a">${robotoSVG({spalva:d.id})}</div>`
               : `<div class="mini" style="${fonoStilius(eq.fonas,true)}">${robotoSVG({spalva:eq.spalva,[d.kat]:d.id})}</div>`;
    const bus = !ok ? `<span style="color:var(--muted)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg> ${esc(d.txt)}</span>`
              : on ? `<span style="color:var(--accent)">✓ ${d.kat==="personazas"?"Pasirinkta":"Užsidėta"}</span>` : `<span style="color:var(--accent2)">${d.kat==="personazas"?`${esc(d.txt)}`:"Spausk - užsidėk"}</span>`;
    return `<button class="daiktas ${on?"uzs":""}" ${ok?"":"disabled"} aria-pressed="${on}" onclick="spaustiDaikta('${d.id}')">${naujas?'<span class="naujas">NAUJA</span>':""}${mini}<b>${esc(d.pav)}</b><div class="bus">${bus}</div></button>`;
  }).join("");
  const ka=kitasAtlygis();
  $("#vidus").innerHTML=`<h1 class="ant1">Spinta</h1><p class="po1">Pasirink personažą ir aprenk jį. Nauji daiktai atsirakina mokantis: už lygius, ženklelius, pamokas ir mokymosi seriją.</p>
  <div class="spinta">
    <div>
      <div class="perziura gyvas" id="spintosRobotas" style="${fonoStilius(eq.fonas)}">${robotoSVG(eq)}</div>
      <div class="korta" style="padding:18px;margin-top:14px">
        <label for="robVardas" style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em">Personažo vardas</label>
        <input id="robVardas" class="vardas-ivestis" value="${esc(S.vardas||"Robis")}" maxlength="18" oninput="S.vardas=this.value;saugoti();$('#robotoVardas').textContent=this.value">
        <div class="eil" style="margin-top:12px;gap:6px">${KATEGORIJOS.map(([k])=>eq[k]?`<span class="cip">${esc(daiktas(eq[k]).pav)}</span>`:"").join("")}</div>
        <div class="eil" style="margin-top:14px"><button class="btn pagr" style="flex:1" onclick="atsitiktinis()">Atsitiktinis derinys</button><button class="btn" style="flex:1" onclick="nusiimti()">Nusiimti viską</button></div>
      </div>
    </div>
    <div>
      <div class="skirt" role="tablist">${sk}</div>
      <div class="daiktai">${kortos}</div>
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
  if(!S.vardas||S.vardas===senas.vardas) S.vardas=personazas(id).vardas;     // savo sugalvoto vardo nekeičiam
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
    const prad=j===0?["Robotas Brėžly","Kepurė ir pieštukas"]:[];
    return `<div class="lyg-k ${j<=i?"pasiekta":"uzr"} ${j===i?"dabar":""}">${j===i?'<span class="cia">Tu esi čia</span>':""}
      <div class="eil" style="gap:10px;flex-wrap:nowrap"><div class="nr">${j+1}</div><div><b style="font-size:16px">${pav}</b><div style="color:var(--muted);font-size:12.5px">nuo ${xp} XP</div></div></div>
      <div class="lyg-fon" style="${fonoStilius(IS[j].fonas,true)}">${robotoSVG(IS[j])}</div>
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
    <div class="prof-fon" style="${fonoStilius(S.eq.fonas)}">
      <span class="zyme" style="position:absolute;top:16px;left:16px;background:rgba(5,8,15,.6);color:#fde68a">${p.lyg+1} lygis · ${LYGIAI[p.lyg][1]}</span>
      ${robotoSVG(S.eq)}<b style="font-size:24px;color:#fff">${esc(S.vardas||"Robis")}</b>
      <input aria-label="Tavo vardas" placeholder="Tavo vardas (nebūtina)" value="${esc(S.savininkas||"")}" oninput="S.savininkas=this.value;saugoti()" style="background:rgba(5,8,15,.45);border:1px solid rgba(255,255,255,.18);border-radius:10px;padding:8px 12px;color:#fff;text-align:center;width:220px">
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
  const t=`Mokausi braižyti su Brėžly! ${p.lyg+1} lygis „${LYGIAI[p.lyg][1]}“, ${p.xp} XP, ${S.zenkleliai.length} ženkleliai. Mano personažas - ${S.vardas||"Robis"}.`;
  navigator.clipboard?.writeText(t).then(()=>pranesti("Nukopijuota - įklijuok žinutėje draugams"),()=>pranesti(t));
}
function atsisiustiKortele(){
  const p=profilioDuomenys(), W=1080, H=600, f=FONAI[S.eq.fonas]||FONAI.tamsus;
  const rob=robotoSVG(S.eq).replace('<svg ','<svg x="70" y="90" width="340" height="340" ');
  const e=t=>esc(t);
  const perejimas = f.g ? `<defs><linearGradient id="sl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fb7185"/><stop offset=".55" stop-color="#f59e0b"/><stop offset="1" stop-color="#7c2d4a"/></linearGradient></defs><rect x="36" y="36" width="408" height="528" rx="26" fill="url(#sl)"/>` : "";
  const zvaigzdes = f.z ? Array.from({length:40},(_,i)=>`<circle cx="${60+((i*97)%360)}" cy="${60+((i*53)%480)}" r="${i%3?1.2:1.8}" fill="${i%4?"#fff":"#fde68a"}"/>`).join("") : "";
  const tinklas = f.t ? `<defs><pattern id="tk" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="rgba(125,211,252,.16)"/></pattern></defs><rect x="36" y="36" width="408" height="528" rx="26" fill="url(#tk)"/>` : "";
  const stat=(x,v,l)=>`<rect x="${x}" y="230" width="128" height="96" rx="16" fill="#151e35" stroke="#24304e"/><text x="${x+16}" y="276" font-size="30" font-weight="800" fill="#f59e0b">${e(v)}</text><text x="${x+16}" y="304" font-size="14" fill="#9aa8c3">${e(l)}</text>`;
  const zen=Object.entries(ZENKLELIAI).map(([k,v],j)=>{const g=S.zenkleliai.includes(k);const x=484+(j%2)*276,y=352+Math.floor(j/2)*54;
    return `<rect x="${x}" y="${y}" width="264" height="42" rx="12" fill="${g?"#2a2210":"#10172a"}" stroke="${g?"#6b4c10":"#2c3a5c"}" ${g?"":'stroke-dasharray="5 4"'}/><text x="${x+14}" y="${y+27}" font-size="15" font-weight="600" fill="${g?"#fcd34d":"#8794ad"}">${e(v.replace(/^\S+\s/,""))}</text>`;}).join("");
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" font-family="Segoe UI, Inter, Arial, sans-serif">`+
    `<rect width="${W}" height="${H}" fill="#0a0f1d"/><rect x="36" y="36" width="408" height="528" rx="26" fill="${f.c}" stroke="#2c3a5c"/>${perejimas}${zvaigzdes}${tinklas}`+
    `${rob}<text x="240" y="470" text-anchor="middle" font-size="30" font-weight="800" fill="#fff">${e(S.vardas||"Robis")}</text>`+
    `<text x="240" y="500" text-anchor="middle" font-size="16" fill="#bfdbfe">${e(S.savininkas?S.savininkas+" · mano Brėžly":"mano Brėžly")}</text>`+
    `<rect x="56" y="56" width="200" height="34" rx="17" fill="rgba(5,8,15,.6)"/><text x="74" y="79" font-size="15" font-weight="700" fill="#fde68a">${p.lyg+1} lygis · ${e(LYGIAI[p.lyg][1])}</text>`+
    `<text x="484" y="100" font-size="14" font-weight="800" letter-spacing="2" fill="#f59e0b">MANO PAŽANGA</text>`+
    `<text x="484" y="150" font-size="34" font-weight="800" fill="#eaf0fa">Mokausi braižyti su Brėžly</text>`+
    `<text x="484" y="190" font-size="16" fill="#9aa8c3">${e(new Date().toLocaleDateString("lt-LT"))}</text>`+
    `${stat(484,p.xp,"XP")}${stat(624,p.pamokos+"/"+p.visoPamoku,"pamokos")}${stat(764,p.serija+" d.","serija")}${stat(904,p.daiktai+"/"+p.visoDaiktu,"daiktai")}`+
    `${zen}<text x="484" y="560" font-size="22" font-weight="800" fill="#eaf0fa">Brėž<tspan fill="#f59e0b">ly</tspan><tspan font-size="14" font-weight="500" fill="#9aa8c3" dx="10">Braižymo mokymosi draugas</tspan></text></svg>`;
  const img=new Image();
  img.onload=()=>{ const cv=document.createElement("canvas"); cv.width=W*2; cv.height=H*2; const cx=cv.getContext("2d"); cx.scale(2,2); cx.drawImage(img,0,0);
    cv.toBlob(b=>{ const a=document.createElement("a"); a.href=URL.createObjectURL(b); a.download=`Brezly_${(S.vardas||"Robis").replace(/[^\wąčęėįšųūž-]/gi,"_")}.png`; document.body.appendChild(a); a.click(); a.remove(); pranesti("Kortelė atsisiųsta"); },"image/png"); };
  img.onerror=()=>pranesti("Nepavyko sukurti paveikslėlio");
  img.src="data:image/svg+xml;charset=utf-8,"+encodeURIComponent(svg);
}


/* ---------- šoninė ---------- */
function piestiSonine(){
  $("#pamokuSarasas").innerHTML=INFO.pamokos.map(p=>{
    const atl=(S.atlikta[p.id]||[]).length, viso=p.zingsniai.length;
    const nr=INFO.pamokos.indexOf(p)+1;
    return `<div class="pam ${PAM&&PAM.id===p.id?"akt":""}" onclick="rodytiPradzia('${p.id}')"><div class="nr">${atl>=viso?"🏆":nr}</div>
      <div><b>${esc(p.pavadinimas)}</b><small>${atl}/${viso} žingsnių</small></div></div>`;
  }).join("")+INFO.ateityje.map(p=>`<div class="pam uzr" title="Bus kitoje versijoje"><div class="nr">🔒</div><div><b>${esc(p.pavadinimas)}</b><small>Netrukus · ${esc(p.aprasas)}</small></div></div>`).join("");
  piestiZaideja();
}
function keistiTema(){sg("tema",(sg("tema")||"dark")==="dark"?"light":"dark");taikytiTema();}
function taikytiTema(){const t=sg("tema")||"dark";document.documentElement.dataset.theme=t;if(rodinys==="nustatymai")rodytiNustatymus();}
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
  PAM=(pid&&pamokaPagalId(pid))||PAM||pamokaPagalId(S.pamoka)||pirmaNebaigta(); S.pamoka=PAM.id; saugoti(); piestiSonine(); $("#vPam").textContent=`${INFO.pamokos.indexOf(PAM)+1}. ${PAM.pavadinimas}`; if(!Gidas.turas) Gidas.slepti(); clearTimeout(Gidas.nuobodu);
  const atl=S.atlikta[PAM.id]||[], viso=PAM.zingsniai.length, prad=atl.length>0&&atl.length<viso;
  $("#vidus").innerHTML=`
  <div class="herojus"><div>
    <div class="zymes"><span class="zyme">Pamoka ${INFO.pamokos.indexOf(PAM)+1} iš ${INFO.pamokos.length}</span><span class="zyme t">${esc(PAM.trukme)}</span><span class="zyme">iki ${PAM.zingsniai.reduce((a,z)=>a+z.xp,0)+PAM.testas.length*10} XP</span></div>
    <h1>${esc(PAM.pavadinimas)}</h1><p>${esc(PAM.aprasas)}</p>
    <div class="eil">
      <button class="btn pagr didelis" id="pradetiBtn" onclick="pradeti(${prad?"S.dabartinis[PAM.id]||0":0})">${prad?"▶ Tęsti pamoką":atl.length>=viso?"↻ Kartoti pamoką":"▶ Pradėti pamoką"}</button>
      <button class="btn" id="naujasBtn" onclick="naujasBrezinys()">Naujas brėžinys (acadiso.dwt)</button>
    </div></div>
    <svg viewBox="0 0 120 120"><use href="#maskotas"/></svg></div>
  <h2>Ką išmoksi</h2>
  <div class="planas">${PAM.zingsniai.map((z,i)=>`<div class="${atl.includes(z.id)?"atl":""}"><span>${atl.includes(z.id)?"✓":i+1}</span>${esc(z.pavadinimas)}</div>`).join("")}<div><span>?</span>Trumpas testas</div></div>
  <h2>Kaip tai veikia</h2>
  <div class="kaip">
    <div><i>⌨️</i><b>Braižai pats</b><p>Brėžly parodo, ką įvesti AutoCAD komandų eilutėje, ir paaiškina kodėl.</p></div>
    <div><i>🔍</i><b>Aš patikrinu</b><p>Stebiu tavo brėžinį ir pats pastebiu, kai žingsnis atliktas. Gali spausti ir „Patikrinti“ - pasakysiu, kas ne taip.</p></div>
    <div><i>⭐</i><b>Renki XP</b><p>Be užuominų - pilni taškai. Įstrigus - užuomina arba „Parodyk man“.</p></div>
  </div>`;
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
}
function piestiZingsni(){
  const nr=S.dabartinis[PAM.id], z=PAM.zingsniai[nr], atl=S.atlikta[PAM.id]||[], jau=atl.includes(z.id);
  const xpDabar=uzdirbtiXP(z);
  $("#vidus").innerHTML=`
  <div class="progresas"><button class="btn" onclick="rodytiPradzia()">← Pamoka</button>
    <div class="taskai">${PAM.zingsniai.map((s,i)=>`<i class="${atl.includes(s.id)?"atl":""} ${i===nr?"dab":""}" title="${esc(s.pavadinimas)}"></i>`).join("")}</div>
    <small>${nr+1} / ${PAM.zingsniai.length}</small></div>
  <div class="korta" id="korta">
    <div class="korta-ant"><h1>${esc(z.pavadinimas)}</h1><span class="xp-zyme">${jau?"✓ atlikta":`+${xpDabar} XP`}</span></div>
    <div class="kodel"><b>Kodėl?</b>${esc(z.kodel)}</div>
    <ol class="daryk">${z.zingsniai.map(t=>`<li>${esc(t)}</li>`).join("")}</ol>
    ${z.komandos.length?`<div class="komandos" id="komandos"><div class="ant"><i></i><i></i><i></i><span>AutoCAD komandų eilutė - įvesk geltonus atsakymus</span></div>
      ${z.komandos.map(([pr,iv0])=>{const iv=komandosTekstas(pr,iv0),pele=iv.startsWith("(")||iv==="Enter";return `<div class="kl"><span class="pr">${esc(pr)}</span><span class="iv ${pele?"pele":""}">${esc(iv)}</span>${pele?"":`<button onclick="kopijuoti('${esc(iv)}')">Kopijuoti</button>`}</div>`;}).join("")}</div>`:""}
    ${z.tikslas?`<div class="tikslas" id="tikslas">🎯 Tikslas: <b>${esc(z.tikslas)}</b></div>`:""}
    <div class="eil" id="veiksmai">
      <button class="btn pagr didelis" id="tikrinti" onclick="tikrinti()">${z.tikrinama?"✓ Patikrinti":"✓ Atlikau"}</button>
      <button class="btn" id="uzuominaBtn" onclick="uzuomina()" ${uzuominuRodyta>=z.uzuominos.length?"disabled":""}>💡 Užuomina (${uzuominuRodyta}/${z.uzuominos.length})</button>
      ${z.demonstruojama?`<button class="btn" id="parodykBtn" onclick="parodyti()">👀 Parodyk man</button>`:""}
      <span class="tarpas"></span>
      ${nr>0?`<button class="btn" onclick="rodytiZingsni(${nr-1})">← Atgal</button>`:""}
      <button class="btn" onclick="toliau()">${nr<PAM.zingsniai.length-1?"Praleisti →":"Į testą →"}</button>
    </div>
    ${z.tikrinama&&!jau?auto.html():""}
    <div id="uzuominos">${z.uzuominos.slice(0,uzuominuRodyta).map((u,i)=>`<div class="uzuomina"><b>Užuomina ${i+1}:</b> ${esc(u)}</div>`).join("")}</div>
    <div id="atsakas">${paskutinisAtsakas||""}</div>
  </div>`;
  Gidas.atnaujinti();
  if(miniIjungtas()) miniPiesti();
}
function uzdirbtiXP(z){ if(demo) return 0; return Math.max(Math.round(z.xp*(1-0.25*uzuominuRodyta)), Math.round(z.xp*0.25)); }
function kopijuoti(t){ navigator.clipboard?.writeText(t).then(()=>pranesti(`Nukopijuota: ${t} - įklijuok AutoCAD'e (Ctrl+V)`),()=>pranesti(t)); }
function uzuomina(){ uzuominuRodyta++; Gidas.slepti(); piestiZingsni(); }
async function parodyti(){
  if(!confirm("Brėžly pats atliks šį žingsnį AutoCAD'e. Už jį XP negausi, bet galėsi pažiūrėti ir tęsti. Rodyti?"))return;
  const z=PAM.zingsniai[S.dabartinis[PAM.id]];
  const r=await api("/api/parodyti",{pamoka:PAM.id,zingsnis:S.dabartinis[PAM.id]});
  if(!r.ok){pranesti(r.klaida);return;}
  demo=true; pranesti("Pažiūrėk į AutoCAD - žingsnis atliktas. Dabar spausk „Patikrinti“.");
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
    if(xp) pridetiXP(xp,$("#atsakas"));
    Gidas.pavyko(); pazymetiDiena();
    if(naujai && atl.length>=PAM.zingsniai.length) tikrintiAtlygiusVeliau();
    if(naujai&&atl.length===1) duotiZenkleli("pirmas");
    if(naujai&&!uzuominuRodyta&&!demo) S._beUz=(S._beUz||0)+1;
    if((S._beUz||0)>=5) duotiZenkleli("be_uzuominu");
  } else {
    Robotas.reaguoti("liud",2600);
    paskutinisAtsakas=`<div class="atsakas blogai"><b>Dar ne visai ${bandymai>2?"- nepasiduok! Gali paimti užuominą 💡":""}</b><ul>${r.pastabos.map(p=>`<li>${esc(p)}</li>`).join("")}</ul></div>`;
    piestiZingsni();
    Gidas.nepavyko(z);
  }
}
function toliau(){ const nr=S.dabartinis[PAM.id]; if(nr<PAM.zingsniai.length-1) rodytiZingsni(nr+1); else rodytiTesta(); }

/* ---------- testas ---------- */
let testoAts=[];
function rodytiTesta(){
  nustatytiRodini("pamoka");
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
  const sp=["#f59e0b","#fb7185","#14b8a6","#60a5fa","#a78bfa","#22c55e"];
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
    {taikinys:".progresas", tekstas:"Ši juosta rodo, kiek žingsnių jau padarei. <b>Žalia</b> - atlikta, <b>oranžinė</b> - dabar."},
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
  b.className="busena "+(r.prisijungta?"gerai":"blogai"); $("#vTsk").className="v-tsk "+(r.prisijungta?"gerai":"blogai");
  info.classList.add("hidden");
  poBusenos();
  if(r.prisijungta){
    b.querySelector(".txt").textContent=`AutoCAD · ${r.brezinys}`; mygt.textContent="↻"; mygt.title="Prisijungti iš naujo";
    if(r.kalba && sg("pabr")===null){ sg("pabr", r.kalba.toUpperCase()==="ENU"?"0":"1"); if(document.querySelector("#komandos")) piestiZingsni(); }
    return;
  }
  let txt="AutoCAD neprijungtas", m="Jungtis", pag="";
  if(r.paleidziamas){ txt="Paleidžiamas AutoCAD..."; m="⏳"; pag="Tai gali užtrukti iki minutės."; }
  else if(r.lt_veikia || (r.lt_idiegtas && !r.pilnas_idiegtas)){ txt="Rastas AutoCAD LT"; m="Kodėl?"; pag="AutoCAD LT neleidžia programoms valdyti brėžinio, todėl Brėžly negali jo patikrinti. Reikia pilno AutoCAD (studentams nemokamas)."; }
  else if(r.windows && !r.pilnas_idiegtas && !r.pilnas_veikia){ txt="AutoCAD nerastas"; m="Kaip gauti?"; }
  else if(r.pilnas_idiegtas && !r.pilnas_veikia){ txt="AutoCAD neatidarytas"; m="Atidaryti"; }
  b.querySelector(".txt").textContent=txt; mygt.textContent=m; mygt.title="";
  if(pag){ info.textContent=pag; info.classList.remove("hidden"); }
}
async function busenosVeiksmas(){
  const r=BUS||{};
  if(r.prisijungta || !r.windows) return prisijungti();
  if(r.paleidziamas) return;
  if(r.lt_veikia || (r.lt_idiegtas && !r.pilnas_idiegtas)) return rodytiLangeli(`<h2>AutoCAD LT nepalaikomas</h2>
    <p>Brėžly tikrina tavo brėžinį per AutoCAD programavimo sąsają (COM). <b>AutoCAD LT</b> jos neturi, todėl su juo Brėžly gali tik rodyti pamokas, bet ne tikrinti.</p>
    <p>Studentams <b>pilnas AutoCAD nemokamas</b> - jį gausi per „Autodesk Education“ svetainę su universiteto el. paštu.</p>
    <div class="eil"><button class="btn pagr" onclick="uzdarytiLangeli()">Supratau</button></div>`);
  if(!r.pilnas_idiegtas && !r.pilnas_veikia) return rodytiLangeli(`<h2>AutoCAD nerastas</h2>
    <p>Šiame kompiuteryje neradau įdiegto AutoCAD. Studentams jis <b>nemokamas</b> - ieškok „Autodesk Education AutoCAD“ ir prisiregistruok su universiteto el. paštu.</p>
    <p>Jei AutoCAD įdiegtas, bet aš jo nerandu - atsidaryk jį pats ir spausk „Bandyti dar kartą“.</p>
    <div class="eil"><button class="btn pagr" onclick="uzdarytiLangeli();prisijungti()">Bandyti dar kartą</button><button class="btn" onclick="uzdarytiLangeli()">Uždaryti</button></div>`);
  if(r.pilnas_idiegtas && !r.pilnas_veikia){
    const a=await api("/api/paleisti_autocad",{}); if(!a.ok){pranesti(a.klaida);return;}
    pranesti("Paleidžiu AutoCAD - tai gali užtrukti iki minutės ⏳"); tikrintiBusena(); return;
  }
  prisijungti();
}
async function prisijungti(){$("#busena .txt").textContent="Jungiamasi...";const r=await api("/api/prisijungti",{});if(!r.ok)pranesti("Nepavyko: "+r.klaida);tikrintiBusena();}
function rodytiPatarima(){ $("#patarimas").textContent=INFO.patarimai[Math.floor(Math.random()*INFO.patarimai.length)]; }

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
    if(this.vyksta||!this.ijungtas()||tikrina||rodinys!=="pamoka"||!PAM||!document.querySelector("#korta")||!BUS.prisijungta) return;
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
  const virsus=(t,sub)=>`<div class="mi-v"><svg class="m" aria-hidden="true"><use href="#maskotas"/></svg><div class="t"><b>${esc(t)}</b><small>${esc(sub)}</small></div>
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
  nustatytiRodini("praktika"); prDabar=null; $("#vPam").textContent="Praktika";
  if(!sg("praktika_matyta")){ sg("praktika_matyta","1"); $("#praktikosTaskelis").classList.add("hidden"); }
  const sar=PRAKTIKA.filter(u=>prFiltras==="visos"||u.fmt===prFiltras), atl=PRAKTIKA.filter(u=>prAtlikta(u.id)).length;
  $("#vidus").innerHTML=`<h1 class="ant1">Praktika</h1><p class="po1">Tikri brėžiniai su rėmeliu: 2D - A4 lapas, 3D - A3 lapas. Atidaryk tuščią lapą AutoCAD'e, nubraižyk ir aš patikrinsiu.</p>
  <div class="pr-filtr">${[["visos","Visos"],["A4","2D · A4"],["A3","3D · A3"]].map(([v,t])=>`<button aria-pressed="${prFiltras===v}" onclick="prFiltras='${v}';rodytiPraktika()">${t}</button>`).join("")}
    <div class="pr-eiga"><span>Atlikta ${atl} iš ${PRAKTIKA.length}</span><div class="juosta"><i style="width:${atl/PRAKTIKA.length*100}%"></i></div></div></div>
  <div class="pr-tink">${sar.map(u=>`<button class="pr-k" onclick="rodytiUzduoti('${u.id}')" aria-label="${u.nr}. ${esc(u.pav)}, ${u.fmt}${prAtlikta(u.id)?", atlikta":""}">
    <div class="pr-lap"><img src="/praktika/${u.id}.svg" alt="" loading="lazy"></div>
    <span class="pr-fmt ${u.fmt==="A3"?"a3":""}">${u.d} · ${u.fmt}</span>${prAtlikta(u.id)?'<span class="pr-ok">✓</span>':""}
    <b>${u.nr}. ${esc(u.pav)}</b><small>${prZvaigzd(u.lyg)} · ~${u.min} min · +${u.xp} XP</small></button>`).join("")}</div>`;
}
function rodytiUzduoti(id){
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
        <span class="pers-pav" style="${fonoStilius(eq.fonas,true)}">${robotoSVG({...eq,personazas:x.id})}</span><b>${esc(x.pav)}</b></button>`).join("")}</div>
      <label for="vPVardas">Kaip jį pavadinsi?</label>
      <input type="text" id="vPVardas" maxlength="18" value="${esc(d.pvardas||personazas(d.personazas).vardas)}" oninput="Vedlys.d.pvardas=this.value" onkeydown="if(event.key==='Enter')Vedlys.toliau()">`;
    }
    if(this.nr===2) h=`${this.taskai()}<h2>Ar jau naudojai AutoCAD?</h2><p>Pagal tai parinksiu, nuo kurios pamokos pradėti.</p>
      <div class="rinktis">
        <button aria-pressed="${p("patirtis","naujas")}" onclick="Vedlys.d.patirtis='naujas';Vedlys.piesti()"><b>Pirmą kartą</b><small>Pradėsim nuo pradžių: failas, lapas, 2D...</small></button>
        <button aria-pressed="${p("patirtis","pagrindai")}" onclick="Vedlys.d.patirtis='pagrindai';Vedlys.piesti()"><b>Moku pagrindus</b><small>Pradėsim nuo 3 pamokos „2D brėžinys“. Prie 1-2 galėsi grįžti bet kada.</small></button>
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
    if(d.patirtis==="pagrindai"){ PAM=null; rodytiPradzia(INFO.pamokos[2].id); } else rodytiPradzia();
    pranesti(S.savininkas?`Malonu susipažinti, ${S.savininkas}! 👋`:"Pradedam! 👋");
    if(!sg("cadet_turas")) setTimeout(()=>Gidas.pradetiTura(Gidas.PRADZIOS_TURAS,"cadet_turas"),900);
  }
};

/* =================== NUSTATYMAI =================== */
let testasAtrakintas=false;
function jung(on,veiksmas,pav){ return `<button class="jung" aria-pressed="${!!on}" aria-label="${esc(pav)}" onclick="${veiksmas}"></button>`; }
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
    <div class="nust-eil"><div><b>Spartieji klavišai</b><small>Veikia ir kai dirbi AutoCAD'e: <b style="display:inline">Ctrl+Alt+T</b> - patikrinti, <b style="display:inline">Ctrl+Alt+M</b> - mini / šalia, <b style="display:inline">Ctrl+Alt+B</b> - parodyti Brėžly.${(INFO.klavisai&&INFO.klavisai.nepavyko.length)?` Užimti kitos programos: ${esc(INFO.klavisai.nepavyko.join(", "))}.`:""}</small></div></div>
    <div class="nust-eil"><div><b>Gyvas robotukas</b><small>Mirksi, seka pelę akimis, džiaugiasi ir nuliūsta kartu su tavimi.</small></div>${jung(Robotas.jungtas(),`sg('judesys',Robotas.jungtas()?'0':'1');Robotas.taikyti();rodytiNustatymus()`,"Gyvas robotukas")}</div>
    <div class="nust-eil"><div><b>Automatinis tikrinimas</b><small>Kas kelias sekundes pažiūriu į brėžinį ir pats pastebiu atliktą žingsnį.</small></div>${jung(auto.ijungtas(),"auto.perjungti()","Automatinis tikrinimas")}</div>
    <div class="nust-eil"><div><b>Komandos su „_“</b><small>Jei tavo AutoCAD ne anglų kalba: _LINE, _CIRCLE veikia bet kurioje kalboje.${BUS.kalba?` Tavo AutoCAD kalba: <b style="display:inline">${esc(BUS.kalba)}</b>.`:""}</small></div>${jung(sg("pabr")==="1",`sg('pabr',sg('pabr')==='1'?'0':'1');rodytiNustatymus()`,"Komandos su pabraukimu")}</div>
    <div class="nust-eil"><div><b>🤖 Robotas gidas</b><small>Parodo, kur spausti, ir padrąsina.</small></div><button class="btn" onclick="Gidas.turasIsNaujo()">❔ Turas</button>${jung(Gidas.ijungtas(),"Gidas.perjungti();rodytiNustatymus()","Robotas gidas")}</div>
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
  S={xp:0,atlikta:{},zenkleliai:[],dabartinis:{},eq:null,matyti:null,nauji:[],dienos:[],vardas:"Robis",savininkas:""};
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
  if(!r.yra){ if(rankinis) pranesti("Turi naujausią versiją ✓"); return; }
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
let kartTab="korteles", kortNr=0, kortTvarka=null, kartTestas=null;
function naujasKartTestas(){
  const vis=[]; INFO.pamokos.forEach(p=>p.testas.forEach((q,i)=>vis.push({...q,id:p.id+"/"+i,pam:p.pavadinimas})));
  kartTestas={kl:mesk(vis).slice(0,8),ats:[]};
}
function rodytiKartojima(){
  nustatytiRodini("kartoti");
  if(!kortTvarka) kortTvarka=mesk(INFO.korteles.map((_,i)=>i));
  if(!kartTestas) naujasKartTestas();
  const sk=`<div class="skirt" role="tablist"><button class="${kartTab==="korteles"?"akt":""}" onclick="kartTab='korteles';rodytiKartojima()">Komandų kortelės</button><button class="${kartTab==="testas"?"akt":""}" onclick="kartTab='testas';rodytiKartojima()">Testas iš visų pamokų</button></div>`;
  let t="";
  if(kartTab==="korteles"){
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
  $("#uPers").innerHTML=tvarka.map((id,i)=>`<span style="animation-delay:${[.36,.24,.12,0,0,.12,.24,.36][i]}s">${robotoSVG({...PRADINIS,personazas:id,galva:["robotas","drakonas"].includes(id)?"kepure":null,ranka:null})}</span>`).join("");
  u.onclick=baigti; setTimeout(baigti,2900);
  INFO=await api("/api/info?kalba="+encodeURIComponent(sg("kalba")||"lt")); PRAKTIKA=INFO.praktika||[]; $("#ver").textContent=INFO.versija;
  $("#verZyme").textContent=String(INFO.versija).split(" ")[0];
  inicializuotiDaiktus(); piestiZaideja(); setTimeout(tikrintiAtlygius,3200);
  rodytiPatarima(); setInterval(rodytiPatarima,20000); Robotas.pradeti();
  rodytiPradzia(); tikrintiBusena(); Gidas.pradzia();
  setInterval(()=>{if(!tikrina)api("/api/ping",{}).catch(()=>{});},3000);
  setInterval(()=>{if(!tikrina)tikrintiBusena();},BUS.prisijungta?8000:5000);
  setInterval(()=>auto.tikrinti(),4000);
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

/* Brėžly programėlės talpykla - veikia be interneto */
const VERSIJA = "brezly-app-1";
const FAILAI = [
 "./",
 "index.html",
 "tikrinimas.js",
 "manifest.webmanifest",
 "icon-192.png",
 "icon-512.png",
 "praktika/U1_Tarpine.pdf",
 "praktika/U1_Tarpine.svg",
 "praktika/U1_Tarpine_ruosinys.dxf",
 "praktika/U2_Flansas.pdf",
 "praktika/U2_Flansas.svg",
 "praktika/U2_Flansas_ruosinys.dxf",
 "praktika/U3_Laikiklis.pdf",
 "praktika/U3_Laikiklis.svg",
 "praktika/U3_Laikiklis_ruosinys.dxf",
 "praktika/U4_Velenas.pdf",
 "praktika/U4_Velenas.svg",
 "praktika/U4_Velenas_ruosinys.dxf",
 "praktika/U5_Projekcijos.pdf",
 "praktika/U5_Projekcijos.svg",
 "praktika/U5_Projekcijos_ruosinys.dxf",
 "praktika/U6_Izometrija.pdf",
 "praktika/U6_Izometrija.svg",
 "praktika/U6_Izometrija_ruosinys.dxf",
 "praktika/U7_Schema.pdf",
 "praktika/U7_Schema.svg",
 "praktika/U7_Schema_ruosinys.dxf",
 "praktika/U8_3D_detale.pdf",
 "praktika/U8_3D_detale.svg",
 "praktika/U8_3D_detale_ruosinys.dxf"
];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSIJA).then(c => c.addAll(FAILAI)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSIJA).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).then(res => {
      const k = res.clone(); caches.open(VERSIJA).then(c => c.put(e.request, k)); return res;
    }).catch(() => r)));
    return;
  }
  // savi failai: tinklas pirma (kad atnaujinimai ateitų), talpykla - kai nėra interneto
  e.respondWith(fetch(e.request).then(res => {
    if (res.ok) { const k = res.clone(); caches.open(VERSIJA).then(c => c.put(e.request, k)); }
    return res;
  }).catch(() => caches.match(e.request, { ignoreSearch: true }).then(r => r || caches.match("./"))));
});

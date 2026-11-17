/* Brėžly programėlės talpykla - veikia be interneto */
const VERSIJA = "brezly-app-kuriama";      // tikrą versiją įrašo irankiai/generuoti.py
const FAILAI = ["./"];                     // pilną sąrašą įrašo irankiai/generuoti.py
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

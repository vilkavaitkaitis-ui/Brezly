/* Anksčiau programėlė buvo šiame adrese. Šis failas išvalo seną talpyklą,
   kad pagrindiniame puslapyje būtų rodomas atsisiuntimo puslapis.
   Programėlė dabar: programele/ (su savo sw.js). */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (!k.startsWith("brezly-programele")) await caches.delete(k);
    await self.registration.unregister();
    for (const c of await self.clients.matchAll({ type: "window" })) c.navigate(c.url);
  })());
});

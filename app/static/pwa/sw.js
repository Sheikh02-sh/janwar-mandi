// Janwar Mandi service worker.
// HTML pages are never cached (they contain logged-in user data and CSRF tokens).
// Only static files (CSS/JS/icons) are cached. When offline, a simple offline page is shown.
// Naya CSS/JS deploy karne par VERSION badal dein taake purana cache saaf ho jaye.
const VERSION = "v1";
const STATIC_CACHE = "jm-static-" + VERSION;
const OFFLINE_URL = "/static/pwa/offline.html";
const PRECACHE = [
  OFFLINE_URL,
  "/static/css/style.css",
  "/static/js/main.js",
  "/static/icons/icon-192.png"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(function (cache) { return cache.addAll(PRECACHE); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys
          .filter(function (k) { return k.indexOf("jm-static-") === 0 && k !== STATIC_CACHE; })
          .map(function (k) { return caches.delete(k); }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  var req = event.request;
  if (req.method !== "GET") return;               // forms / POST hamesha network se

  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Page navigation: network first, offline page if the network fails.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).catch(function () { return caches.match(OFFLINE_URL); })
    );
    return;
  }

  // Static files (not user uploads): serve cached copy fast, refresh in background.
  if (url.pathname.indexOf("/static/") === 0 && url.pathname.indexOf("/static/uploads/") !== 0) {
    event.respondWith(
      caches.open(STATIC_CACHE).then(function (cache) {
        return cache.match(req).then(function (cached) {
          var network = fetch(req).then(function (res) {
            if (res && res.ok) cache.put(req, res.clone());
            return res;
          }).catch(function () { return cached; });
          return cached || network;
        });
      })
    );
  }
});

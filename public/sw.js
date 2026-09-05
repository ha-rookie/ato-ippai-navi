"use strict";

const CACHE_NAME = "ato-ippai-navi-v1";
const APP_SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./manifest.webmanifest",
  "./favicon.svg",
  "./favicon.ico",
  "./apple-touch-icon.png",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-maskable-512.png",
  "./js/analytics.js",
  "./js/information-architecture.js",
  "./js/last-train-link.js",
  "./js/last-train-page.js",
  "./js/main-page.js",
  "./js/pwa.js",
  "./js/service-day.js",
  "./js/settings.js",
  "./js/sleep.js"
];

const NETWORK_ONLY_PREFIXES = ["/api/", "/ops/"];
const NETWORK_ONLY_PATHS = new Set(["/health", "/build.json"]);

function isNetworkOnly(url) {
  return (
    NETWORK_ONLY_PATHS.has(url.pathname) ||
    NETWORK_ONLY_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))
  );
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

async function networkFirst(request, navigationFallback = false) {
  const cache = await caches.open(CACHE_NAME);

  try {
    const response = await fetch(request);
    if (response && response.ok) {
      await cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) return cached;

    if (navigationFallback) {
      const fallback = await cache.match("./index.html");
      if (fallback) return fallback;
    }

    throw error;
  }
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (isNetworkOnly(url)) {
    event.respondWith(fetch(request));
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request, true));
    return;
  }

  event.respondWith(networkFirst(request, false));
});

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";

import { normalizeEvent } from "../public/js/analytics.js";
import { normalizePayload } from "../functions/api/event.js";

const manifest = JSON.parse(
  fs.readFileSync(new URL("../public/manifest.webmanifest", import.meta.url), "utf8")
);
const serviceWorker = fs.readFileSync(
  new URL("../public/sw.js", import.meta.url),
  "utf8"
);
const headers = fs.readFileSync(
  new URL("../public/_headers", import.meta.url),
  "utf8"
);

function pngDimensions(buffer) {
  assert.deepEqual(
    [...buffer.subarray(0, 8)],
    [137, 80, 78, 71, 13, 10, 26, 10]
  );
  return {
    width: buffer.readUInt32BE(16),
    height: buffer.readUInt32BE(20)
  };
}

test("manifest defines installable standalone app", () => {
  assert.equal(manifest.name, "あと一杯ナビ");
  assert.equal(manifest.short_name, "あと一杯ナビ");
  assert.equal(manifest.lang, "ja-JP");
  assert.equal(manifest.start_url, "./");
  assert.equal(manifest.scope, "./");
  assert.equal(manifest.display, "standalone");

  const icon192 = manifest.icons.find((icon) => icon.sizes === "192x192");
  const icon512 = manifest.icons.find((icon) => icon.sizes === "512x512" && icon.purpose === "any");
  const maskable = manifest.icons.find((icon) => icon.purpose === "maskable");
  assert.ok(icon192);
  assert.ok(icon512);
  assert.equal(maskable?.sizes, "512x512");
});

test("service worker never caches API or operations responses", () => {
  assert.match(serviceWorker, /NETWORK_ONLY_PREFIXES = \["\/api\/", "\/ops\/"\]/);
  assert.match(serviceWorker, /NETWORK_ONLY_PATHS = new Set\(\["\/health", "\/build\.json"\]\)/);
  assert.match(serviceWorker, /if \(isNetworkOnly\(url\)\) \{/);
  assert.doesNotMatch(serviceWorker, /"\.\/api\//);
  assert.doesNotMatch(serviceWorker, /"\.\/ops\//);
});

test("PWA control files are not served with stale-cache policy", () => {
  assert.match(headers, /\/sw\.js[\s\S]*no-cache, no-store, must-revalidate/);
  assert.match(headers, /\/manifest\.webmanifest[\s\S]*no-cache/);
});

test("temporary icon generator creates required PNG dimensions", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "ato-ippai-pwa-"));
  try {
    execFileSync(process.execPath, [
      path.resolve("scripts/generate_pwa_icons.cjs"),
      "--root",
      root
    ]);

    for (const [file, size] of [
      ["apple-touch-icon.png", 180],
      ["icons/icon-192.png", 192],
      ["icons/icon-512.png", 512],
      ["icons/icon-maskable-512.png", 512]
    ]) {
      const dimensions = pngDimensions(fs.readFileSync(path.join(root, file)));
      assert.deepEqual(dimensions, { width: size, height: size });
    }
    assert.ok(fs.statSync(path.join(root, "favicon.ico")).size > 20);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("PWA analytics events are allowed on client and server", () => {
  const events = [
    "install_prompt_shown",
    "install_prompt_clicked",
    "app_installed",
    "standalone_open",
    "offline_fallback"
  ];

  for (const event of events) {
    assert.equal(normalizeEvent(event)?.event, event);
    assert.equal(normalizePayload({ event })?.event, event);
  }
});

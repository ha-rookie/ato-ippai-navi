import test from "node:test";
import assert from "node:assert/strict";

import {
  isInternalTestMode,
  normalizeEvent,
  shouldSendForHost,
  withInternalTest
} from "../public/js/analytics.js";
import {
  normalizePayload,
  sameOrigin
} from "../functions/api/event.js";

test("analytics only sends for production host", () => {
  assert.equal(shouldSendForHost("ato-ippai.pages.dev"), true);
  assert.equal(shouldSendForHost("localhost"), false);
  assert.equal(shouldSendForHost("ato-ippai-api-poc.edward-se-pg.workers.dev"), false);
});

test("internal_test=1 disables analytics and is preserved on internal navigation", () => {
  assert.equal(isInternalTestMode("?internal_test=1"), true);
  assert.equal(isInternalTestMode("?foo=1&internal_test=1"), true);
  assert.equal(isInternalTestMode("?internal_test=0"), false);
  assert.equal(withInternalTest("/last-train", "?internal_test=1"), "/last-train?internal_test=1");
  assert.equal(withInternalTest("/last-train", ""), "/last-train");
});

test("client payload contains only aggregate operational fields", () => {
  const payload = normalizeEvent("last_train_check");
  assert.deepEqual(Object.keys(payload).sort(), [
    "display_mode",
    "event",
    "network_state"
  ]);
  assert.equal(payload.event, "last_train_check");
  assert.equal(normalizeEvent("unknown_event"), null);
});

test("server allowlist accepts expected events without station or location fields", () => {
  const payload = normalizePayload({
    event: "last_train_view",
    display_mode: "browser",
    network_state: "online",
    destinationCode: "H22",
    latitude: 35.1,
    longitude: 136.9
  });

  assert.deepEqual(payload, {
    event: "last_train_view",
    displayMode: "browser",
    networkState: "online"
  });
  assert.equal(normalizePayload({ event: "unknown_event" }), null);
});

test("analytics endpoint requires same-origin production requests", () => {
  const allowed = new Request("https://ato-ippai.pages.dev/api/event", {
    headers: { Origin: "https://ato-ippai.pages.dev" }
  });
  const foreignOrigin = new Request("https://ato-ippai.pages.dev/api/event", {
    headers: { Origin: "https://example.com" }
  });
  const workerHost = new Request("https://ato-ippai-api-poc.edward-se-pg.workers.dev/api/event", {
    headers: { Origin: "https://ato-ippai-api-poc.edward-se-pg.workers.dev" }
  });

  assert.equal(sameOrigin(allowed), true);
  assert.equal(sameOrigin(foreignOrigin), false);
  assert.equal(sameOrigin(workerHost), false);
});

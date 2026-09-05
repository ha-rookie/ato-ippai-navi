import test from "node:test";
import assert from "node:assert/strict";
import { mountLastTrainQuickLink } from "../public/js/last-train-link.js";

test("quick-link module exports a mount function", () => {
  assert.equal(typeof mountLastTrainQuickLink, "function");
});

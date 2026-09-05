import test from "node:test";
import assert from "node:assert/strict";

import { mountLastTrainPage } from "../public/js/last-train-page.js";

test("last-train page exports mount function without browser side effects", () => {
  assert.equal(typeof mountLastTrainPage, "function");
});

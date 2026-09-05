import test from "node:test";
import assert from "node:assert/strict";
import {
  clarifyLastTrainInformation,
  clarifyMainPageInformation
} from "../public/js/information-architecture.js";

test("information architecture module exports main-page clarifier", () => {
  assert.equal(typeof clarifyMainPageInformation, "function");
});

test("information architecture module exports last-train clarifier", () => {
  assert.equal(typeof clarifyLastTrainInformation, "function");
});

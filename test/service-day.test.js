import test from "node:test";
import assert from "node:assert/strict";

import {
  autoDayType,
  isJapaneseHoliday,
  serviceDate
} from "../public/js/service-day.js";

function jst(isoLocal) {
  return new Date(`${isoLocal}+09:00`);
}

test("04:00 is the service-day boundary", () => {
  assert.equal(serviceDate(jst("2026-09-05T03:59:00")).key, "2026-09-04");
  assert.equal(serviceDate(jst("2026-09-05T04:00:00")).key, "2026-09-05");
});

test("Saturday 00:30 uses Friday weekday service", () => {
  assert.equal(autoDayType(jst("2026-09-05T00:30:00")), "weekday");
});

test("Monday 01:00 after Sunday uses Sunday holiday service", () => {
  assert.equal(autoDayType(jst("2026-09-07T01:00:00")), "saturday_holiday");
});

test("regular Saturday is saturday_holiday", () => {
  assert.equal(autoDayType(jst("2026-09-05T12:00:00")), "saturday_holiday");
});

test("regular Monday is weekday", () => {
  assert.equal(autoDayType(jst("2026-09-14T12:00:00")), "weekday");
});

test("weekday national holiday is saturday_holiday", () => {
  assert.equal(isJapaneseHoliday("2026-09-21"), true);
  assert.equal(autoDayType(jst("2026-09-21T12:00:00")), "saturday_holiday");
});

test("citizens holiday is included", () => {
  assert.equal(isJapaneseHoliday("2026-09-22"), true);
  assert.equal(autoDayType(jst("2026-09-22T12:00:00")), "saturday_holiday");
});

test("unknown holiday calendar fails closed", () => {
  assert.throws(
    () => autoDayType(jst("2028-01-04T12:00:00")),
    /holiday calendar unavailable/
  );
});

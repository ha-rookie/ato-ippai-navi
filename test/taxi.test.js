import test from "node:test";
import assert from "node:assert/strict";
import {
  estimateNagoyaTaxiFare,
  isNagoyaTaxiNight
} from "../src/taxi.js";

test("daytime initial fare is 500 yen up to 910m", () => {
  const result = estimateNagoyaTaxiFare({
    distanceMeters: 910,
    departureTime: "2026-09-02T12:00:00+09:00",
    includeDispatchFee: false
  });

  assert.equal(result.nightSurcharge, false);
  assert.equal(result.distanceOnlyMeterFareYen, 500);
  assert.equal(result.estimatedTotalYen, 500);
});

test("daytime 911m adds one 100 yen increment", () => {
  const result = estimateNagoyaTaxiFare({
    distanceMeters: 911,
    departureTime: "2026-09-02T12:00:00+09:00",
    includeDispatchFee: false
  });

  assert.equal(result.distanceOnlyMeterFareYen, 600);
});

test("23:20 JST is deep-night fare period", () => {
  assert.equal(
    isNagoyaTaxiNight("2026-09-04T23:20:00+09:00"),
    true
  );
});

test("15.463km deep-night distance-only estimate is 8080 yen with dispatch", () => {
  const result = estimateNagoyaTaxiFare({
    distanceMeters: 15463,
    departureTime: "2026-09-04T23:20:00+09:00",
    includeDispatchFee: true
  });

  assert.equal(result.nightSurcharge, true);
  assert.equal(result.fareBeforeLongDistanceDiscountYen, 8200);
  assert.equal(result.longDistanceDiscountYen, 320);
  assert.equal(result.distanceOnlyMeterFareYen, 7880);
  assert.equal(result.dispatchFeeYen, 200);
  assert.equal(result.estimatedTotalYen, 8080);
});

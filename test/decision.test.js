import test from "node:test";
import assert from "node:assert/strict";
import { evaluateSakaeToFujigaoka } from "../src/decision.js";

test("weekday 23:20 gives now/+15/+30 reachable and +60 missed", () => {
  const result = evaluateSakaeToFujigaoka({
    departureTime: "2026-09-04T23:20:00+09:00",
    dayType: "weekday",
    offsetMinutes: [0, 15, 30, 60]
  });

  assert.deepEqual(
    result.scenarios.map((item) => ({
      offsetMinutes: item.offsetMinutes,
      localTime: item.localTime,
      canReachDestination: item.canReachDestination,
      nextTrain: item.nextTrain,
      lastTrain: item.lastTrain,
      minutesUntilLastTrain: item.minutesUntilLastTrain
    })),
    [
      {
        offsetMinutes: 0,
        localTime: "23:20",
        canReachDestination: true,
        nextTrain: "23:22",
        lastTrain: "00:02",
        minutesUntilLastTrain: 42
      },
      {
        offsetMinutes: 15,
        localTime: "23:35",
        canReachDestination: true,
        nextTrain: "23:42",
        lastTrain: "00:02",
        minutesUntilLastTrain: 27
      },
      {
        offsetMinutes: 30,
        localTime: "23:50",
        canReachDestination: true,
        nextTrain: "23:52",
        lastTrain: "00:02",
        minutesUntilLastTrain: 12
      },
      {
        offsetMinutes: 60,
        localTime: "00:20",
        canReachDestination: false,
        nextTrain: null,
        lastTrain: "00:02",
        minutesUntilLastTrain: -18
      }
    ]
  );
});

test("00:16 Hoshigaoka train is not treated as reaching Fujigaoka", () => {
  const result = evaluateSakaeToFujigaoka({
    departureTime: "2026-09-05T00:03:00+09:00",
    dayType: "weekday",
    offsetMinutes: [0]
  });

  assert.equal(result.scenarios[0].canReachDestination, false);
  assert.equal(result.scenarios[0].lastTrain, "00:02");
});

test("Saturday/holiday schedule has last Fujigaoka train at 00:02", () => {
  const result = evaluateSakaeToFujigaoka({
    departureTime: "2026-09-05T23:50:00+09:00",
    dayType: "saturday_holiday",
    offsetMinutes: [0]
  });

  assert.equal(result.scenarios[0].nextTrain, "23:52");
  assert.equal(result.scenarios[0].lastTrain, "00:02");
});

import test from "node:test";
import assert from "node:assert/strict";
import {
  calculateSleepEstimate,
  enrichTonightDecisionWithSleep,
  normalizeSleepSettings
} from "../public/js/sleep.js";
import {
  clearSleepSettings,
  loadSleepSettings,
  saveSleepSettings
} from "../public/js/settings.js";

test("23:53 station arrival calculates home, bedtime and next wake", () => {
  const result = calculateSleepEstimate(
    "2026-09-04T14:53:00.000Z",
    {
      stationToHomeMinutes: 12,
      bedtimePrepMinutes: 25,
      wakeTime: "07:00"
    }
  );

  assert.equal(result.localDestinationStationArrivalTime, "23:53");
  assert.equal(result.localEstimatedHomeArrivalTime, "00:05");
  assert.equal(result.localEstimatedBedtime, "00:30");
  assert.equal(result.localEstimatedWakeTime, "07:00");
  assert.equal(result.sleepMinutes, 390);
  assert.equal(result.sleepHours, 6.5);
  assert.equal(result.sleepLabel, "6時間30分");
});

test("00:23 arrival uses the same next-morning wake occurrence", () => {
  const result = calculateSleepEstimate(
    "2026-09-04T15:23:00.000Z",
    {
      stationToHomeMinutes: 12,
      bedtimePrepMinutes: 25,
      wakeTime: "07:00"
    }
  );

  assert.equal(result.localEstimatedBedtime, "01:00");
  assert.equal(result.sleepMinutes, 360);
  assert.equal(result.sleepLabel, "6時間0分");
});

test("decision scenarios are enriched without changing the API payload source", () => {
  const input = {
    destinationScope: "station_only",
    scenarios: [
      {
        offsetMinutes: 0,
        estimatedDestinationStationArrivalTime:
          "2026-09-04T14:53:00.000Z"
      },
      {
        offsetMinutes: 60,
        estimatedDestinationStationArrivalTime:
          "2026-09-04T15:41:00.000Z"
      }
    ]
  };

  const result = enrichTonightDecisionWithSleep(input, {
    stationToHomeMinutes: 12,
    bedtimePrepMinutes: 25,
    wakeTime: "07:00"
  });

  assert.equal(result.sleepPrivacy.calculation, "client_only");
  assert.equal(result.sleepPrivacy.sendsHomeAddressToServer, false);
  assert.equal(result.sleepPrivacy.sendsWakeTimeToServer, false);
  assert.equal(result.scenarios[0].sleep.sleepMinutes, 390);
  assert.equal(result.scenarios[1].sleep.sleepMinutes, 342);
  assert.equal(input.scenarios[0].sleep, undefined);
});

test("settings are validated", () => {
  assert.deepEqual(
    normalizeSleepSettings({
      stationToHomeMinutes: "10",
      bedtimePrepMinutes: 20,
      wakeTime: "06:30"
    }),
    {
      stationToHomeMinutes: 10,
      bedtimePrepMinutes: 20,
      wakeTime: "06:30"
    }
  );

  assert.throws(
    () =>
      normalizeSleepSettings({
        stationToHomeMinutes: 10,
        bedtimePrepMinutes: 20,
        wakeTime: "25:00"
      }),
    /wakeTime/
  );
});

test("sleep settings round-trip through device-local storage adapter", () => {
  const map = new Map();
  const storage = {
    getItem: (key) => map.get(key) ?? null,
    setItem: (key, value) => map.set(key, value),
    removeItem: (key) => map.delete(key)
  };

  assert.equal(loadSleepSettings(storage), null);

  saveSleepSettings(
    {
      stationToHomeMinutes: 8,
      bedtimePrepMinutes: 30,
      wakeTime: "06:45"
    },
    storage
  );

  assert.deepEqual(loadSleepSettings(storage), {
    stationToHomeMinutes: 8,
    bedtimePrepMinutes: 30,
    wakeTime: "06:45"
  });

  clearSleepSettings(storage);
  assert.equal(loadSleepSettings(storage), null);
});

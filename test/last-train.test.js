import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  clockToServiceMinutes,
  evaluateLastTrainBoundary
} from "../src/last-train.js";

const dataset = JSON.parse(
  fs.readFileSync(
    new URL("../src/data/last-trains-nagoya.json", import.meta.url),
    "utf8"
  )
);

test("clock values after midnight remain in the same service day", () => {
  assert.equal(clockToServiceMinutes("23:59"), 1439);
  assert.equal(clockToServiceMinutes("00:00"), 1440);
  assert.equal(clockToServiceMinutes("00:23"), 1463);
});

test("Sakae and Fushimi last-train JSON is verified for Fujigaoka", () => {
  const destination = dataset.destinations.H22;

  assert.equal(
    destination.routes.sakae.weekday.lastDeparture,
    "00:02"
  );
  assert.equal(
    destination.routes.fushimi.weekday.lastDeparture,
    "00:00"
  );
  assert.equal(
    destination.routes.sakae.saturday_holiday.lastArrival,
    "00:23"
  );
});

test("boundary chooses the safer reachable hub for each scenario", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:20:00+09:00",
    dayType: "weekday",
    destinationCode: "H22",
    offsetMinutes: [0, 15, 30, 60],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      sakae: { walkMinutes: 4 },
      fushimi: { walkMinutes: 12 }
    }
  });

  assert.equal(result.scenarios[0].recommendedOriginId, "sakae");
  assert.equal(result.scenarios[0].lastDeparture, "00:02");

  assert.equal(result.scenarios[2].localLeaveTime, "23:50");
  assert.equal(result.scenarios[2].canReachDestination, true);
  assert.equal(result.scenarios[2].recommendedOriginId, "sakae");
  assert.equal(result.scenarios[2].localStationReadyTime, "23:57");
  assert.equal(result.scenarios[2].lastDeparture, "00:02");
  assert.equal(result.scenarios[2].minutesUntilLastDeparture, 5);
  assert.equal(result.scenarios[2].usableMarginMinutes, 4);
  assert.equal(result.scenarios[2].localLastTrainArrivalTime, "00:23");
  assert.equal(
    result.scenarios[2].estimatedDestinationStationArrivalTime,
    null
  );
  assert.equal(
    result.scenarios[2].arrivalEstimateQuality,
    "last_train_boundary_only"
  );

  assert.equal(result.scenarios[3].localLeaveTime, "00:20");
  assert.equal(result.scenarios[3].canReachDestination, false);
});

test("same-minute arrival at the platform cannot board the last train", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-05T00:00:00+09:00",
    dayType: "weekday",
    destinationCode: "H22",
    offsetMinutes: [0],
    stationBufferMinutes: 0,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      fushimi: { walkMinutes: 0 }
    }
  });

  assert.equal(result.scenarios[0].options[0].localStationReadyTime, "00:00");
  assert.equal(result.scenarios[0].options[0].lastDeparture, "00:00");
  assert.equal(result.scenarios[0].options[0].canReachDestination, false);
});

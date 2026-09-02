import test from "node:test";
import assert from "node:assert/strict";
import { composeWalkHomeDecision } from "../src/walk-home.js";

test("hub destination recommends walking for all offsets", () => {
  const result = composeWalkHomeDecision({
    departureTime: "2026-09-04T23:20:00+09:00",
    offsetMinutes: [0, 15],
    destinationCode: "H10",
    destinationName: "栄",
    hubId: "sakae",
    hubName: "栄",
    walkResult: {
      routeFound: true,
      distanceMeters: 250,
      durationSeconds: 200
    },
    taxiEstimate: {
      routeFound: true,
      durationSeconds: 180,
      estimatedTotalYen: 800
    }
  });

  assert.equal(result.journeyType, "walk_to_home_station");
  assert.equal(result.walk.walkMinutes, 4);
  assert.equal(result.scenarios[0].recommendedMode, "walk");
  assert.equal(result.scenarios[0].localDestinationStationArrivalTime, "23:24");
  assert.equal(result.scenarios[1].localDestinationStationArrivalTime, "23:39");
  assert.equal(result.scenarios[0].taxiEstimatedTotalYen, 800);
});

test("taxi is fallback only when walk route is unavailable", () => {
  const result = composeWalkHomeDecision({
    departureTime: "2026-09-04T23:20:00+09:00",
    offsetMinutes: [0],
    destinationCode: "H09",
    destinationName: "伏見",
    hubId: "fushimi",
    hubName: "伏見",
    walkResult: { routeFound: false },
    taxiEstimate: {
      routeFound: true,
      durationSeconds: 300,
      estimatedTotalYen: 1000
    }
  });

  assert.equal(result.scenarios[0].recommendedMode, "taxi");
  assert.equal(result.scenarios[0].localDestinationStationArrivalTime, "23:25");
});

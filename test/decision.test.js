import test from "node:test";
import assert from "node:assert/strict";
import {
  evaluateSakaeToFujigaoka,
  evaluateSakaeToFujigaokaWithAccess
} from "../src/decision.js";

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


test("walk + station buffer shifts the effective boarding time", () => {
  const result = evaluateSakaeToFujigaokaWithAccess({
    departureTime: "2026-09-04T23:20:00+09:00",
    dayType: "weekday",
    offsetMinutes: [0, 15, 30, 60],
    walkMinutes: 5,
    stationBufferMinutes: 3
  });

  assert.deepEqual(
    result.scenarios.map((item) => ({
      offsetMinutes: item.offsetMinutes,
      localLeaveTime: item.localLeaveTime,
      localStationReadyTime: item.localStationReadyTime,
      canReachDestination: item.canReachDestination,
      nextTrain: item.nextTrain,
      lastTrain: item.lastTrain,
      minutesUntilLastTrain: item.minutesUntilLastTrain
    })),
    [
      {
        offsetMinutes: 0,
        localLeaveTime: "23:20",
        localStationReadyTime: "23:28",
        canReachDestination: true,
        nextTrain: "23:32",
        lastTrain: "00:02",
        minutesUntilLastTrain: 34
      },
      {
        offsetMinutes: 15,
        localLeaveTime: "23:35",
        localStationReadyTime: "23:43",
        canReachDestination: true,
        nextTrain: "23:52",
        lastTrain: "00:02",
        minutesUntilLastTrain: 19
      },
      {
        offsetMinutes: 30,
        localLeaveTime: "23:50",
        localStationReadyTime: "23:58",
        canReachDestination: true,
        nextTrain: "00:02",
        lastTrain: "00:02",
        minutesUntilLastTrain: 4
      },
      {
        offsetMinutes: 60,
        localLeaveTime: "00:20",
        localStationReadyTime: "00:28",
        canReachDestination: false,
        nextTrain: null,
        lastTrain: "00:02",
        minutesUntilLastTrain: -26
      }
    ]
  );
});


test("same-minute platform arrival does not count as boardable by default", () => {
  const result = evaluateSakaeToFujigaokaWithAccess({
    departureTime: "2026-09-04T23:35:00+09:00",
    dayType: "weekday",
    offsetMinutes: [0],
    walkMinutes: 4,
    stationBufferMinutes: 3
  });

  const scenario = result.scenarios[0];

  assert.equal(scenario.localStationReadyTime, "23:42");
  assert.equal(scenario.minimumBoardingLeadMinutes, 1);
  assert.equal(scenario.nextTrain, "23:52");
  assert.equal(scenario.minutesUntilNextTrain, 10);
});


test("train scenarios include official 21-minute Fujigaoka arrival estimate", () => {
  const result = evaluateSakaeToFujigaokaWithAccess({
    departureTime: "2026-09-04T23:20:00+09:00",
    dayType: "weekday",
    offsetMinutes: [0, 30],
    walkMinutes: 4,
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1
  });

  assert.equal(result.route.trainRideMinutes, 21);

  assert.equal(result.scenarios[0].nextTrain, "23:32");
  assert.equal(
    result.scenarios[0].localDestinationStationArrivalTime,
    "23:53"
  );

  assert.equal(result.scenarios[1].nextTrain, "00:02");
  assert.equal(
    result.scenarios[1].localDestinationStationArrivalTime,
    "00:23"
  );
});

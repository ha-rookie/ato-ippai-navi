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


test("generated Higashiyama boundaries cover west and east destinations", () => {
  assert.equal(
    Object.keys(dataset.destinations).filter((code) => code.startsWith("H")).length,
    22
  );

  assert.equal(
    dataset.destinations.H01.routes.sakae.weekday.lastDeparture,
    "00:02"
  );
  assert.equal(
    dataset.destinations.H01.routes.fushimi.weekday.lastDeparture,
    "00:04"
  );

  assert.equal(
    dataset.destinations.H08.routes.sakae.weekday.lastDeparture,
    "00:16"
  );
  assert.equal(
    dataset.destinations.H08.routes.fushimi.weekday.lastDeparture,
    "00:17"
  );

  assert.equal(
    dataset.destinations.H18.routes.sakae.weekday.lastDeparture,
    "00:16"
  );
  assert.equal(
    dataset.destinations.H18.routes.fushimi.weekday.lastDeparture,
    "00:10"
  );
});

test("stations without last-arrival data still evaluate the boundary", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-05T00:05:00+09:00",
    dayType: "weekday",
    destinationCode: "H18",
    offsetMinutes: [0],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      sakae: { walkMinutes: 4 },
      fushimi: { walkMinutes: 14 }
    }
  });

  const scenario = result.scenarios[0];

  assert.equal(scenario.canReachDestination, true);
  assert.equal(scenario.recommendedOriginId, "sakae");
  assert.equal(scenario.lastDeparture, "00:16");
  assert.equal(scenario.lastArrival, null);
  assert.equal(scenario.localLastTrainArrivalTime, null);
});


test("Tsurumai direct boundary uses Fushimi only", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:50:00+09:00",
    dayType: "weekday",
    destinationCode: "T15",
    offsetMinutes: [0, 15],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      sakae: { walkMinutes: 4 },
      fushimi: { walkMinutes: 14 }
    }
  });

  assert.equal(result.destination.name, "八事");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "fushimi");
  assert.equal(result.scenarios[0].lastDeparture, "00:14");
  assert.equal(result.scenarios[1].canReachDestination, false);
});

test("Tsurumai Fushimi hub is enabled now that walk-only handling exists", () => {
  assert.equal(dataset.destinations.T07.enabled, true);
});


test("Meijo direct boundaries cover the full M01-M28 station set", () => {
  assert.equal(
    Object.keys(dataset.destinations).filter((code) => code.startsWith("M")).length,
    28
  );

  const expected = {
    M01: ["00:10", "left", "新瑞橋"],
    M06: ["00:14", "right", "大曽根"],
    M12: ["00:14", "right", "大曽根"],
    M13: ["00:04", "right", "ナゴヤドーム前矢田"],
    M14: ["23:52", "right", "名城線右回り"],
    M22: ["00:02", "left", "瑞穂運動場東"],
    M23: ["00:10", "left", "新瑞橋"],
    M28: ["00:10", "left", "新瑞橋"]
  };

  for (const [code, [lastDeparture, direction, terminal]] of Object.entries(expected)) {
    const route = dataset.destinations[code].routes.sakae.weekday;
    assert.equal(route.lastDeparture, lastDeparture, code);
    assert.equal(route.direction, direction, code);
    assert.equal(route.trainTerminal, terminal, code);
    assert.equal(route.transfers, 0, code);
  }
});

test("Meijo M05 Sakae destination is enabled for walk-home handling", () => {
  assert.equal(dataset.destinations.M05.enabled, true);
  assert.deepEqual(dataset.destinations.M05.routes, {});
});

test("Meijo M12 Ozone boundary uses Sakae direct route", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:50:00+09:00",
    dayType: "weekday",
    destinationCode: "M12",
    offsetMinutes: [0, 30],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      sakae: { walkMinutes: 4 },
      fushimi: { walkMinutes: 14 }
    }
  });

  assert.equal(result.destination.name, "大曽根");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "sakae");
  assert.equal(result.scenarios[0].lastDeparture, "00:14");
  assert.equal(result.scenarios[1].canReachDestination, false);
});


test("Meiko boundaries cover E01-E07 with verified Kanayama transfer", () => {
  assert.equal(
    Object.keys(dataset.destinations).filter((code) => code.startsWith("E")).length,
    7
  );

  const e01 = dataset.destinations.E01.routes.sakae.weekday;
  assert.equal(e01.lastDeparture, "00:10");
  assert.equal(e01.lastArrival, "00:18");
  assert.equal(e01.transfers, 0);

  for (const code of ["E02", "E03", "E04", "E05", "E06", "E07"]) {
    const route = dataset.destinations[code].routes.sakae.weekday;
    assert.equal(route.lastDeparture, "00:02", code);
    assert.equal(route.transferAt, "金山", code);
    assert.deepEqual(route.transferStationCodes, ["M01", "E01"], code);
    assert.equal(route.transferReadyTime, "00:10", code);
    assert.equal(route.connectionDeparture, "00:18", code);
    assert.equal(route.transferMarginMinutes, 8, code);
    assert.equal(route.minimumTransferLeadMinutes, 1, code);
    assert.equal(route.transfers, 1, code);
    assert.equal(route.status, "verified", code);
  }
});

test("Meiko E07 Nagoyako uses Sakae 00:02 boundary", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:45:00+09:00",
    dayType: "weekday",
    destinationCode: "E07",
    offsetMinutes: [0, 15],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      sakae: { walkMinutes: 4 },
      fushimi: { walkMinutes: 14 }
    }
  });

  assert.equal(result.destination.name, "名古屋港");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "sakae");
  assert.equal(result.scenarios[0].lastDeparture, "00:02");
  assert.equal(result.scenarios[1].canReachDestination, false);
});

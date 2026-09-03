import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  clockToServiceMinutes,
  eligibleOriginIds,
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


test("eligible hubs are limited to origins with verified routes", () => {
  assert.deepEqual(
    eligibleOriginIds(dataset, "H22"),
    ["sakae", "fushimi"]
  );
  assert.deepEqual(
    eligibleOriginIds(dataset, "T15"),
    ["fushimi"]
  );
  assert.deepEqual(
    eligibleOriginIds(dataset, "M12"),
    ["sakae"]
  );
  assert.deepEqual(
    eligibleOriginIds(dataset, "E07"),
    ["sakae"]
  );
  assert.deepEqual(
    eligibleOriginIds(dataset, "S21"),
    ["marunouchi", "hisayaodori"]
  );
});

test("Sakuradori boundaries cover S01-S21 from two walk hubs", () => {
  assert.equal(
    Object.keys(dataset.destinations).filter((code) => /^S\d{2}$/.test(code)).length,
    21
  );

  const expected = {
    S01: {
      marunouchi: ["00:25", "太閤通"],
      hisayaodori: ["00:23", "太閤通"]
    },
    S08: {
      marunouchi: ["00:22", "今池"],
      hisayaodori: ["00:24", "今池"]
    },
    S09: {
      marunouchi: ["00:06", "野並"],
      hisayaodori: ["00:08", "野並"]
    },
    S17: {
      marunouchi: ["00:06", "野並"],
      hisayaodori: ["00:08", "野並"]
    },
    S18: {
      marunouchi: ["23:55", "徳重"],
      hisayaodori: ["23:56", "徳重"]
    },
    S21: {
      marunouchi: ["23:55", "徳重"],
      hisayaodori: ["23:56", "徳重"]
    }
  };

  for (const [code, origins] of Object.entries(expected)) {
    for (const [originId, [lastDeparture, terminal]] of Object.entries(origins)) {
      const route = dataset.destinations[code].routes[originId].weekday;
      assert.equal(route.lastDeparture, lastDeparture, `${code}/${originId}`);
      assert.equal(route.trainTerminal, terminal, `${code}/${originId}`);
      assert.equal(route.transfers, 0, `${code}/${originId}`);
      assert.equal(route.status, "verified", `${code}/${originId}`);
    }
  }
});

test("Sakuradori S21 chooses the safer walk hub", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:40:00+09:00",
    dayType: "weekday",
    destinationCode: "S21",
    offsetMinutes: [0, 15],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      marunouchi: { walkMinutes: 10 },
      hisayaodori: { walkMinutes: 5 }
    }
  });

  assert.equal(result.destination.name, "徳重");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "hisayaodori");
  assert.equal(result.scenarios[0].lastDeparture, "23:56");
  assert.equal(result.scenarios[1].canReachDestination, false);
});

test("Marunouchi and Hisaya-odori codes are home walk hubs", () => {
  assert.ok(dataset.origins.marunouchi.stationCodes.includes("T06"));
  assert.ok(dataset.origins.marunouchi.stationCodes.includes("S04"));
  assert.ok(dataset.origins.hisayaodori.stationCodes.includes("M06"));
  assert.ok(dataset.origins.hisayaodori.stationCodes.includes("S05"));
});


test("Kamiida K01 uses the conservative Sakae 00:04 boundary", () => {
  const route = dataset.destinations.K01.routes.sakae.weekday;

  assert.equal(route.lastDeparture, "00:04");
  assert.equal(route.lastArrival, "00:29");
  assert.equal(route.transferAt, "平安通");
  assert.deepEqual(route.transferStationCodes, ["M11", "K02"]);
  assert.equal(route.transferReadyTime, "00:16");
  assert.equal(route.connectionDeparture, "00:28");
  assert.equal(route.minimumTransferLeadMinutes, 3);
  assert.equal(route.transferMarginMinutes, 12);
  assert.equal(route.transfers, 1);
  assert.equal(route.status, "verified");
});

test("Kamiida K01 only needs the Sakae walk hub", () => {
  assert.deepEqual(
    eligibleOriginIds(dataset, "K01"),
    ["sakae"]
  );
});

test("Kamiida K01 boundary is reachable before midnight but not after", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:45:00+09:00",
    dayType: "weekday",
    destinationCode: "K01",
    offsetMinutes: [0, 15],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      sakae: { walkMinutes: 4 }
    }
  });

  assert.equal(result.destination.name, "上飯田");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "sakae");
  assert.equal(result.scenarios[0].lastDeparture, "00:04");
  assert.equal(result.scenarios[0].routeSummary, "名城線 右回り → 平安通乗換 → 上飯田線");
  assert.equal(result.scenarios[0].transfers, 1);
  assert.equal(result.scenarios[1].canReachDestination, false);
});


test("Meitetsu Seto boundaries cover Nagoya-city ST01-ST12", () => {
  assert.equal(
    Object.keys(dataset.destinations).filter((code) => /^ST\d{2}$/.test(code)).length,
    12
  );

  assert.deepEqual(dataset.destinations.ST01.routes, {});
  assert.ok(dataset.origins.sakaemachi.stationCodes.includes("ST01"));

  for (const code of [
    "ST02", "ST03", "ST04", "ST05", "ST06",
    "ST07", "ST08", "ST09", "ST10", "ST11"
  ]) {
    const route = dataset.destinations[code].routes.sakaemachi.weekday;
    assert.equal(route.lastDeparture, "00:00", code);
    assert.equal(route.trainTerminal, "喜多山", code);
    assert.equal(route.transfers, 0, code);
    assert.equal(route.status, "verified", code);
  }

  const st12 = dataset.destinations.ST12.routes.sakaemachi.weekday;
  assert.equal(st12.lastDeparture, "23:45");
  assert.equal(st12.trainTerminal, "尾張瀬戸");
  assert.equal(st12.transfers, 0);
  assert.equal(st12.status, "verified");
});

test("Meitetsu Seto destinations only need the Sakaemachi walk hub", () => {
  assert.deepEqual(eligibleOriginIds(dataset, "ST11"), ["sakaemachi"]);
  assert.deepEqual(eligibleOriginIds(dataset, "ST12"), ["sakaemachi"]);
});

test("Meitetsu Seto ST11 keeps the 00:00 Kitayama boundary", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:40:00+09:00",
    dayType: "weekday",
    destinationCode: "ST11",
    offsetMinutes: [0, 15],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      sakaemachi: { walkMinutes: 5 }
    }
  });

  assert.equal(result.destination.name, "喜多山");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "sakaemachi");
  assert.equal(result.scenarios[0].lastDeparture, "00:00");
  assert.equal(result.scenarios[1].canReachDestination, false);
});

test("Meitetsu Seto ST12 boundary is 23:45", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:30:00+09:00",
    dayType: "weekday",
    destinationCode: "ST12",
    offsetMinutes: [0, 15],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      sakaemachi: { walkMinutes: 5 }
    }
  });

  assert.equal(result.destination.name, "大森・金城学院前");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "sakaemachi");
  assert.equal(result.scenarios[0].lastDeparture, "23:45");
  assert.equal(result.scenarios[1].canReachDestination, false);
});

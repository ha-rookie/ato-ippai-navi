import test from "node:test";
import assert from "node:assert/strict";

import {
  LAST_TRAIN_OPS_HEADERS,
  flattenLastTrainBoundaries,
  lastTrainBoundariesCsv
} from "../src/ops-csv.js";

const sample = {
  origins: {
    sakae: { name: "栄" }
  },
  destinations: {
    H22: {
      name: "藤が丘",
      routes: {
        sakae: {
          weekday: {
            lastDeparture: "00:02",
            lastArrival: "00:23",
            routeSummary: "東山線 直通",
            trainTerminal: "藤が丘",
            transfers: 0,
            status: "verified",
            sourceIds: ["subway-source"]
          }
        }
      }
    },
    KM12: {
      name: "味鋺",
      routes: {
        sakae: {
          saturday_holiday: {
            lastDeparture: "23:42",
            lastArrival: "00:10",
            routeSummary: "名城線 → 平安通乗換 → 上飯田線・名鉄小牧線直通",
            trainTerminal: "小牧,終",
            transfers: 1,
            transferAt: "平安通",
            connectionDeparture: "00:06",
            transferMarginMinutes: 12,
            status: "verified",
            sourceIds: ["meijo-source", "komaki-source"]
          }
        }
      }
    }
  }
};

test("flattens one row for each destination/origin/day boundary", () => {
  const rows = flattenLastTrainBoundaries(sample);

  assert.equal(rows.length, 2);
  assert.deepEqual(rows[0].slice(0, 6), [
    "H22",
    "藤が丘",
    "名古屋市交通局",
    "東山線",
    "栄",
    "平日"
  ]);
  assert.deepEqual(rows[1].slice(0, 6), [
    "KM12",
    "味鋺",
    "名古屋鉄道",
    "小牧線",
    "栄",
    "土休日"
  ]);
});

test("emits stable Google Sheets CSV columns and escapes CSV values", () => {
  const csv = lastTrainBoundariesCsv(sample);

  assert.equal(LAST_TRAIN_OPS_HEADERS.length, 16);
  assert.match(csv, /^"目的駅コード","駅名","事業者","路線"/);
  assert.match(csv, /"KM12","味鋺","名古屋鉄道","小牧線"/);
  assert.match(csv, /"小牧,終"/);
  assert.match(csv, /"meijo-source \/ komaki-source"/);
});

test("prefixes formula-like values before CSV serialization", () => {
  const malicious = structuredClone(sample);
  malicious.destinations.H22.routes.sakae.weekday.routeSummary = "=IMPORTDATA(\"x\")";

  const csv = lastTrainBoundariesCsv(malicious);
  assert.match(csv, /"'=IMPORTDATA\(""x""\)"/);
});

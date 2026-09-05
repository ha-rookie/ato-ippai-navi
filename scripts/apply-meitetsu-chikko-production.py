#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "meitetsu-chikko-official-transfer-timetable"

BOUNDARIES = {
    "weekday": {
        "lastDeparture": "19:25",
        "lastArrival": "19:47",
        "transferReadyTime": "19:36",
        "connectionDeparture": "19:44",
        "transferMarginMinutes": 8,
    },
    "saturday_holiday": {
        "lastDeparture": "16:55",
        "lastArrival": "17:23",
        "transferReadyTime": "17:06",
        "connectionDeparture": "17:20",
        "transferMarginMinutes": 14,
    },
}


def update_dataset() -> None:
    path = ROOT / "src/data/last-trains-nagoya.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    source = {
        "id": SOURCE_ID,
        "publisher": "名古屋鉄道",
        "checkedAt": "2026-09-05",
        "url": "https://trainbus.meitetsu.co.jp/meitetsu-transfer/pc/transfer/DepArrTimeList",
    }
    for i, item in enumerate(data["sources"]):
        if item.get("id") == SOURCE_ID:
            data["sources"][i] = source
            break
    else:
        data["sources"].append(source)

    routes = {}
    for day_type, boundary in BOUNDARIES.items():
        routes[day_type] = {
            "lastDeparture": boundary["lastDeparture"],
            "lastArrival": boundary["lastArrival"],
            "routeSummary": "名鉄名古屋本線 → 大江乗換 → 築港線",
            "trainTerminal": "東名古屋港",
            "transferAt": "大江",
            "transferStationCodes": ["TA03"],
            "transferReadyTime": boundary["transferReadyTime"],
            "connectionDeparture": boundary["connectionDeparture"],
            "connectionTerminal": "東名古屋港",
            "minimumTransferLeadMinutes": 3,
            "transferMarginMinutes": boundary["transferMarginMinutes"],
            "transfers": 1,
            "status": "verified",
            "sourceIds": [SOURCE_ID],
        }

    data["destinations"]["CH01"] = {
        "operator": "meitetsu",
        "line": "chikko",
        "officialStationCode": "CH01",
        "name": "東名古屋港",
        "city": "名古屋市",
        "stationCodes": ["CH01"],
        "enabled": True,
        "routes": {"nagoya": routes},
    }

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_html() -> None:
    path = ROOT / "public/index.html"
    text = path.read_text(encoding="utf-8")

    anchor = '        <optgroup label="JR関西本線（名古屋から直通）">'
    block = '''        <optgroup label="名鉄築港線（大江乗換）">
          <option value="CH01" data-name="東名古屋港">CH01 東名古屋港</option>
        </optgroup>
'''
    if 'value="CH01"' not in text:
        if anchor not in text:
            raise RuntimeError("JR Kansai optgroup anchor not found")
        text = text.replace(anchor, block + anchor, 1)

    old = "名鉄名古屋本線（名古屋市内）・名鉄常滑線（名古屋市内）・名鉄犬山線（名古屋市内）・あおなみ線"
    new = "名鉄名古屋本線（名古屋市内）・名鉄常滑線（名古屋市内）・名鉄犬山線（名古屋市内）・名鉄築港線（東名古屋港）・あおなみ線"
    if old in text:
        text = text.replace(old, new, 1)

    path.write_text(text, encoding="utf-8")


def update_settings() -> None:
    path = ROOT / "public/js/settings.js"
    text = path.read_text(encoding="utf-8")

    old_error = '  "S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, IY02-IY03, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68";'
    new_error = '  "S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, IY02-IY03, CH01, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68";'
    if old_error in text:
        text = text.replace(old_error, new_error, 1)

    marker = "  const operatorMatch = /^(KT)-E(\\d{1,2})$/.exec(code);"
    block = '''  const meitetsuChikkoMatch = /^CH(\\d{1,2})$/.exec(code);

  if (meitetsuChikkoMatch) {
    const number = Number(meitetsuChikkoMatch[1]);
    if (number !== 1) {
      throw new Error(DESTINATION_STATION_ERROR);
    }
    return `CH${String(number).padStart(2, "0")}`;
  }

'''
    if "const meitetsuChikkoMatch" not in text:
        if marker not in text:
            raise RuntimeError("settings anchor not found")
        text = text.replace(marker, block + marker, 1)

    path.write_text(text, encoding="utf-8")


def update_last_train_logic() -> None:
    path = ROOT / "src/last-train.js"
    text = path.read_text(encoding="utf-8")

    old_hub = '''    routeSummary: context.route.routeSummary,
    transfers: context.route.transfers,
    minutesUntilLastDeparture:
      lastDepartureServiceMinutes - readyServiceMinutes,
    usableMarginMinutes:
      lastDepartureServiceMinutes - requiredServiceMinutes,
    sourceIds: context.route.sourceIds
'''
    new_hub = '''    routeSummary: context.route.routeSummary,
    transfers: context.route.transfers,
    transferAt: context.route.transferAt ?? null,
    transferStationCodes: context.route.transferStationCodes ?? [],
    transferReadyTime: context.route.transferReadyTime ?? null,
    connectionDeparture: context.route.connectionDeparture ?? null,
    connectionTerminal: context.route.connectionTerminal ?? null,
    minimumTransferLeadMinutes:
      context.route.minimumTransferLeadMinutes ?? null,
    transferMarginMinutes: context.route.transferMarginMinutes ?? null,
    minutesUntilLastDeparture:
      lastDepartureServiceMinutes - readyServiceMinutes,
    usableMarginMinutes:
      lastDepartureServiceMinutes - requiredServiceMinutes,
    sourceIds: context.route.sourceIds
'''
    if "transferStationCodes: context.route.transferStationCodes" not in text:
        if old_hub not in text:
            raise RuntimeError("last-train evaluateHub anchor not found")
        text = text.replace(old_hub, new_hub, 1)

    old_scenario = '''      routeSummary: recommended?.routeSummary ?? null,
      transfers: recommended?.transfers ?? null,
      options
'''
    new_scenario = '''      routeSummary: recommended?.routeSummary ?? null,
      transfers: recommended?.transfers ?? null,
      transferAt: recommended?.transferAt ?? null,
      transferStationCodes: recommended?.transferStationCodes ?? [],
      transferReadyTime: recommended?.transferReadyTime ?? null,
      connectionDeparture: recommended?.connectionDeparture ?? null,
      connectionTerminal: recommended?.connectionTerminal ?? null,
      minimumTransferLeadMinutes:
        recommended?.minimumTransferLeadMinutes ?? null,
      transferMarginMinutes: recommended?.transferMarginMinutes ?? null,
      options
'''
    if "transferStationCodes: recommended?.transferStationCodes" not in text:
        if old_scenario not in text:
            raise RuntimeError("last-train scenario anchor not found")
        text = text.replace(old_scenario, new_scenario, 1)

    path.write_text(text, encoding="utf-8")


def update_settings_tests() -> None:
    path = ROOT / "test/settings.test.js"
    text = path.read_text(encoding="utf-8")

    old = "/H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, IY02-IY03, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68/;"
    new = "/H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, IY02-IY03, CH01, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68/;"
    if old in text:
        text = text.replace(old, new, 1)

    if 'accepts Meitetsu Chikko CH01' not in text:
        text += '''

test("destination station accepts Meitetsu Chikko CH01 code", () => {
  assert.equal(normalizeDestinationStation("ch1"), "CH01");
  assert.equal(normalizeDestinationStation("CH01"), "CH01");
  assert.throws(() => normalizeDestinationStation("CH02"), /CH01/);
});

test("Meitetsu Chikko destination is stored and restored locally", () => {
  const storage = memoryStorage();
  assert.equal(saveDestinationStation("ch1", storage), "CH01");
  assert.equal(loadDestinationStation(storage), "CH01");
});
'''

    path.write_text(text, encoding="utf-8")


def update_last_train_tests() -> None:
    path = ROOT / "test/last-train.test.js"
    text = path.read_text(encoding="utf-8")

    if 'Meitetsu Chikko CH01 keeps Oe transfer boundaries' in text:
        return

    text += '''


test("Meitetsu Chikko CH01 keeps Oe transfer boundaries", () => {
  const destination = dataset.destinations.CH01;
  assert.equal(destination.operator, "meitetsu");
  assert.equal(destination.line, "chikko");
  assert.equal(destination.officialStationCode, "CH01");
  assert.equal(destination.name, "東名古屋港");
  assert.deepEqual(eligibleOriginIds(dataset, "CH01"), ["nagoya"]);

  const expected = {
    weekday: ["19:25", "19:47", "19:36", "19:44", 8],
    saturday_holiday: ["16:55", "17:23", "17:06", "17:20", 14]
  };

  for (const [dayType, values] of Object.entries(expected)) {
    const [departure, arrival, ready, connection, margin] = values;
    const route = destination.routes.nagoya[dayType];
    assert.equal(route.lastDeparture, departure, dayType);
    assert.equal(route.lastArrival, arrival, dayType);
    assert.equal(route.routeSummary, "名鉄名古屋本線 → 大江乗換 → 築港線", dayType);
    assert.equal(route.trainTerminal, "東名古屋港", dayType);
    assert.equal(route.transferAt, "大江", dayType);
    assert.deepEqual(route.transferStationCodes, ["TA03"], dayType);
    assert.equal(route.transferReadyTime, ready, dayType);
    assert.equal(route.connectionDeparture, connection, dayType);
    assert.equal(route.connectionTerminal, "東名古屋港", dayType);
    assert.equal(route.minimumTransferLeadMinutes, 3, dayType);
    assert.equal(route.transferMarginMinutes, margin, dayType);
    assert.equal(route.transfers, 1, dayType);
    assert.equal(route.status, "verified", dayType);
    assert.deepEqual(route.sourceIds, ["meitetsu-chikko-official-transfer-timetable"], dayType);
  }
});

test("Meitetsu Chikko CH01 exposes transfer metadata in boundary API model", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T18:55:00+09:00",
    dayType: "weekday",
    destinationCode: "CH01",
    offsetMinutes: [0, 20],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: { nagoya: { walkMinutes: 8 } }
  });

  const before = result.scenarios[0];
  assert.equal(before.canReachDestination, true);
  assert.equal(before.recommendedOriginId, "nagoya");
  assert.equal(before.lastDeparture, "19:25");
  assert.equal(before.lastArrival, "19:47");
  assert.equal(before.transfers, 1);
  assert.equal(before.transferAt, "大江");
  assert.deepEqual(before.transferStationCodes, ["TA03"]);
  assert.equal(before.transferReadyTime, "19:36");
  assert.equal(before.connectionDeparture, "19:44");
  assert.equal(before.connectionTerminal, "東名古屋港");
  assert.equal(before.minimumTransferLeadMinutes, 3);
  assert.equal(before.transferMarginMinutes, 8);

  assert.equal(result.scenarios[1].canReachDestination, false);
});
'''

    path.write_text(text, encoding="utf-8")


def main() -> None:
    update_dataset()
    update_html()
    update_settings()
    update_last_train_logic()
    update_settings_tests()
    update_last_train_tests()
    print("Meitetsu Chikko production migration applied")


if __name__ == "__main__":
    main()

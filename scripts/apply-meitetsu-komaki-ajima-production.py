#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "meitetsu-komaki-official-direct-timetable"
MEIJO_SOURCE_ID = "nagoya-subway-pocket-timetable-meijo"

BOUNDARIES = {
    "weekday": {
        "lastDeparture": "23:42",
        "lastArrival": "00:10",
        "transferReadyTime": "23:54",
        "connectionDeparture": "00:06",
        "transferMarginMinutes": 12,
    },
    "saturday_holiday": {
        "lastDeparture": "23:42",
        "lastArrival": "00:10",
        "transferReadyTime": "23:54",
        "connectionDeparture": "00:06",
        "transferMarginMinutes": 12,
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
            "routeSummary": "名城線 → 平安通乗換 → 上飯田線・名鉄小牧線直通",
            "trainTerminal": "小牧",
            "transferAt": "平安通",
            "transferStationCodes": ["M11", "K02"],
            "transferReadyTime": boundary["transferReadyTime"],
            "connectionDeparture": boundary["connectionDeparture"],
            "connectionTerminal": "小牧",
            "minimumTransferLeadMinutes": 3,
            "transferMarginMinutes": boundary["transferMarginMinutes"],
            "transfers": 1,
            "status": "verified",
            "sourceIds": [MEIJO_SOURCE_ID, SOURCE_ID],
        }

    data["destinations"]["KM12"] = {
        "operator": "meitetsu",
        "line": "komaki",
        "officialStationCode": "KM12",
        "name": "味鋺",
        "city": "名古屋市",
        "stationCodes": ["KM12"],
        "enabled": True,
        "routes": {"sakae": routes},
    }

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_html() -> None:
    path = ROOT / "public/index.html"
    text = path.read_text(encoding="utf-8")

    anchor = '        <optgroup label="名鉄瀬戸線（栄町から直通）">'
    block = '''        <optgroup label="名鉄小牧線（平安通で乗換）">
          <option value="KM12" data-name="味鋺">KM12 味鋺</option>
        </optgroup>
'''
    if 'value="KM12"' not in text:
        if anchor not in text:
            raise RuntimeError("Meitetsu Seto optgroup anchor not found")
        text = text.replace(anchor, block + anchor, 1)

    old = "名鉄名古屋本線（名古屋市内）・名鉄常滑線（名古屋市内）・名鉄犬山線（名古屋市内）・名鉄築港線（東名古屋港）・あおなみ線"
    new = "名鉄名古屋本線（名古屋市内）・名鉄常滑線（名古屋市内）・名鉄犬山線（名古屋市内）・名鉄築港線（東名古屋港）・名鉄小牧線（味鋺）・あおなみ線"
    if old in text:
        text = text.replace(old, new, 1)

    path.write_text(text, encoding="utf-8")


def update_settings() -> None:
    path = ROOT / "public/js/settings.js"
    text = path.read_text(encoding="utf-8")

    old_error = '  "S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, IY02-IY03, CH01, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68";'
    new_error = '  "S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, IY02-IY03, CH01, KM12, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68";'
    if old_error in text:
        text = text.replace(old_error, new_error, 1)

    marker = "  const operatorMatch = /^(KT)-E(\\d{1,2})$/.exec(code);"
    block = '''  const meitetsuKomakiMatch = /^KM(\\d{1,2})$/.exec(code);

  if (meitetsuKomakiMatch) {
    const number = Number(meitetsuKomakiMatch[1]);
    if (number !== 12) {
      throw new Error(DESTINATION_STATION_ERROR);
    }
    return `KM${String(number).padStart(2, "0")}`;
  }

'''
    if "const meitetsuKomakiMatch" not in text:
        if marker not in text:
            raise RuntimeError("settings anchor not found")
        text = text.replace(marker, block + marker, 1)

    path.write_text(text, encoding="utf-8")


def update_settings_tests() -> None:
    path = ROOT / "test/settings.test.js"
    text = path.read_text(encoding="utf-8")

    old = "/H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, IY02-IY03, CH01, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68/;"
    new = "/H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, IY02-IY03, CH01, KM12, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68/;"
    if old in text:
        text = text.replace(old, new, 1)

    if 'accepts Meitetsu Komaki KM12' not in text:
        text += '''

test("destination station accepts Meitetsu Komaki KM12 code", () => {
  assert.equal(normalizeDestinationStation("km12"), "KM12");
  assert.equal(normalizeDestinationStation("KM12"), "KM12");
  assert.throws(() => normalizeDestinationStation("KM11"), /KM12/);
  assert.throws(() => normalizeDestinationStation("KM13"), /KM12/);
});

test("Meitetsu Komaki destination is stored and restored locally", () => {
  const storage = memoryStorage();
  assert.equal(saveDestinationStation("km12", storage), "KM12");
  assert.equal(loadDestinationStation(storage), "KM12");
});
'''

    path.write_text(text, encoding="utf-8")


def update_last_train_tests() -> None:
    path = ROOT / "test/last-train.test.js"
    text = path.read_text(encoding="utf-8")

    if 'Meitetsu Komaki KM12 keeps Heian-dori transfer boundary' in text:
        return

    text += '''


test("Meitetsu Komaki KM12 keeps Heian-dori transfer boundary", () => {
  const destination = dataset.destinations.KM12;
  assert.equal(destination.operator, "meitetsu");
  assert.equal(destination.line, "komaki");
  assert.equal(destination.officialStationCode, "KM12");
  assert.equal(destination.name, "味鋺");
  assert.deepEqual(eligibleOriginIds(dataset, "KM12"), ["sakae"]);

  for (const dayType of ["weekday", "saturday_holiday"]) {
    const route = destination.routes.sakae[dayType];
    assert.equal(route.lastDeparture, "23:42", dayType);
    assert.equal(route.lastArrival, "00:10", dayType);
    assert.equal(route.routeSummary, "名城線 → 平安通乗換 → 上飯田線・名鉄小牧線直通", dayType);
    assert.equal(route.trainTerminal, "小牧", dayType);
    assert.equal(route.transferAt, "平安通", dayType);
    assert.deepEqual(route.transferStationCodes, ["M11", "K02"], dayType);
    assert.equal(route.transferReadyTime, "23:54", dayType);
    assert.equal(route.connectionDeparture, "00:06", dayType);
    assert.equal(route.connectionTerminal, "小牧", dayType);
    assert.equal(route.minimumTransferLeadMinutes, 3, dayType);
    assert.equal(route.transferMarginMinutes, 12, dayType);
    assert.equal(route.transfers, 1, dayType);
    assert.equal(route.status, "verified", dayType);
    assert.deepEqual(route.sourceIds, [
      "nagoya-subway-pocket-timetable-meijo",
      "meitetsu-komaki-official-direct-timetable"
    ], dayType);
  }
});

test("Meitetsu Komaki KM12 exposes transfer metadata in boundary API model", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:20:00+09:00",
    dayType: "weekday",
    destinationCode: "KM12",
    offsetMinutes: [0, 20],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: { sakae: { walkMinutes: 8 } }
  });

  const before = result.scenarios[0];
  assert.equal(before.canReachDestination, true);
  assert.equal(before.recommendedOriginId, "sakae");
  assert.equal(before.lastDeparture, "23:42");
  assert.equal(before.lastArrival, "00:10");
  assert.equal(before.transfers, 1);
  assert.equal(before.transferAt, "平安通");
  assert.deepEqual(before.transferStationCodes, ["M11", "K02"]);
  assert.equal(before.transferReadyTime, "23:54");
  assert.equal(before.connectionDeparture, "00:06");
  assert.equal(before.connectionTerminal, "小牧");
  assert.equal(before.minimumTransferLeadMinutes, 3);
  assert.equal(before.transferMarginMinutes, 12);

  assert.equal(result.scenarios[1].canReachDestination, false);
});
'''

    path.write_text(text, encoding="utf-8")


def main() -> None:
    update_dataset()
    update_html()
    update_settings()
    update_settings_tests()
    update_last_train_tests()
    print("Meitetsu Komaki KM12 production migration applied")


if __name__ == "__main__":
    main()

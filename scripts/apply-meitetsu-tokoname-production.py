#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "meitetsu-tokoname-official-direct-timetable"

BOUNDARIES = {
    "TA01": ("豊田本町", "23:43", "23:54", "普通", "太田川"),
    "TA02": ("道徳", "23:43", "23:55", "普通", "太田川"),
    "TA03": ("大江", "23:59", "00:10", "急行", "知多半田"),
    "TA04": ("大同町", "23:43", "00:00", "普通", "太田川"),
    "TA05": ("柴田", "23:43", "00:01", "普通", "太田川"),
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

    for code, (name, departure, arrival, train_class, terminal) in BOUNDARIES.items():
        route = {
            "lastDeparture": departure,
            "lastArrival": arrival,
            "routeSummary": f"名鉄名古屋本線→常滑線 {train_class} 直通",
            "trainClass": train_class,
            "trainTerminal": terminal,
            "transfers": 0,
            "status": "verified",
            "sourceIds": [SOURCE_ID],
        }
        data["destinations"][code] = {
            "operator": "meitetsu",
            "line": "tokoname",
            "officialStationCode": code,
            "name": name,
            "city": "名古屋市",
            "stationCodes": [code],
            "enabled": True,
            "routes": {
                "nagoya": {
                    "weekday": dict(route),
                    "saturday_holiday": dict(route),
                }
            },
        }

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_html() -> None:
    path = ROOT / "public/index.html"
    text = path.read_text(encoding="utf-8")
    anchor = '        <optgroup label="JR関西本線（名古屋から直通）">'
    block = '''        <optgroup label="名鉄常滑線（名鉄名古屋から直通）">
          <option value="TA01" data-name="豊田本町">TA01 豊田本町</option>
          <option value="TA02" data-name="道徳">TA02 道徳</option>
          <option value="TA03" data-name="大江">TA03 大江</option>
          <option value="TA04" data-name="大同町">TA04 大同町</option>
          <option value="TA05" data-name="柴田">TA05 柴田</option>
        </optgroup>
'''
    if 'value="TA01"' not in text:
        if anchor not in text:
            raise RuntimeError("JR Kansai optgroup anchor not found")
        text = text.replace(anchor, block + anchor, 1)

    old = "名鉄瀬戸線（名古屋市内）・名鉄名古屋本線（名古屋市内）・あおなみ線"
    new = "名鉄瀬戸線（名古屋市内）・名鉄名古屋本線（名古屋市内）・名鉄常滑線（名古屋市内）・あおなみ線"
    if old in text:
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def update_settings() -> None:
    path = ROOT / "public/js/settings.js"
    text = path.read_text(encoding="utf-8")
    old_error = '  "S01-S21, K01, ST01-ST12, NH24-NH38, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68";'
    new_error = '  "S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68";'
    if old_error in text:
        text = text.replace(old_error, new_error, 1)

    marker = "  const operatorMatch = /^(KT)-E(\\d{1,2})$/.exec(code);"
    block = '''  const meitetsuTokonameMatch = /^TA(\\d{1,2})$/.exec(code);

  if (meitetsuTokonameMatch) {
    const number = Number(meitetsuTokonameMatch[1]);
    if (number < 1 || number > 5) {
      throw new Error(DESTINATION_STATION_ERROR);
    }
    return `TA${String(number).padStart(2, "0")}`;
  }

'''
    if "const meitetsuTokonameMatch" not in text:
        if marker not in text:
            raise RuntimeError("settings anchor not found")
        text = text.replace(marker, block + marker, 1)
    path.write_text(text, encoding="utf-8")


def update_settings_tests() -> None:
    path = ROOT / "test/settings.test.js"
    text = path.read_text(encoding="utf-8")
    old = "/H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, NH24-NH38, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68/;"
    new = "/H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68/;"
    if old in text:
        text = text.replace(old, new, 1)
    if 'accepts Meitetsu Tokoname TA01-TA05' not in text:
        text += '''

test("destination station accepts Meitetsu Tokoname TA01-TA05 codes", () => {
  assert.equal(normalizeDestinationStation("ta1"), "TA01");
  assert.equal(normalizeDestinationStation("TA05"), "TA05");
  assert.throws(() => normalizeDestinationStation("TA00"), /TA01-TA05/);
  assert.throws(() => normalizeDestinationStation("TA06"), /TA01-TA05/);
});

test("Meitetsu Tokoname destination is stored and restored locally", () => {
  const storage = memoryStorage();
  assert.equal(saveDestinationStation("ta3", storage), "TA03");
  assert.equal(loadDestinationStation(storage), "TA03");
});
'''
    path.write_text(text, encoding="utf-8")


def update_last_train_tests() -> None:
    path = ROOT / "test/last-train.test.js"
    text = path.read_text(encoding="utf-8")
    if 'Meitetsu Tokoname boundaries cover TA01-TA05' in text:
        return
    text += '''


test("Meitetsu Tokoname boundaries cover TA01-TA05 from Nagoya hub", () => {
  const expected = {
    TA01: ["豊田本町", "23:43", "23:54", "普通", "太田川"],
    TA02: ["道徳", "23:43", "23:55", "普通", "太田川"],
    TA03: ["大江", "23:59", "00:10", "急行", "知多半田"],
    TA04: ["大同町", "23:43", "00:00", "普通", "太田川"],
    TA05: ["柴田", "23:43", "00:01", "普通", "太田川"]
  };

  for (const [code, [name, departure, arrival, trainClass, terminal]] of Object.entries(expected)) {
    const destination = dataset.destinations[code];
    assert.equal(destination.operator, "meitetsu", code);
    assert.equal(destination.line, "tokoname", code);
    assert.equal(destination.officialStationCode, code, code);
    assert.equal(destination.name, name, code);
    for (const dayType of ["weekday", "saturday_holiday"]) {
      const route = destination.routes.nagoya[dayType];
      assert.equal(route.lastDeparture, departure, `${code}/${dayType}`);
      assert.equal(route.lastArrival, arrival, `${code}/${dayType}`);
      assert.equal(route.trainClass, trainClass, `${code}/${dayType}`);
      assert.equal(route.trainTerminal, terminal, `${code}/${dayType}`);
      assert.equal(route.routeSummary, `名鉄名古屋本線→常滑線 ${trainClass} 直通`, `${code}/${dayType}`);
      assert.equal(route.transfers, 0, `${code}/${dayType}`);
      assert.equal(route.status, "verified", `${code}/${dayType}`);
    }
  }
});

test("Meitetsu Tokoname destinations only need Nagoya walk hub", () => {
  assert.deepEqual(eligibleOriginIds(dataset, "TA01"), ["nagoya"]);
  assert.deepEqual(eligibleOriginIds(dataset, "TA03"), ["nagoya"]);
  assert.deepEqual(eligibleOriginIds(dataset, "TA05"), ["nagoya"]);
});

test("Meitetsu Tokoname TA03 keeps the 23:59 Chita-Handa express boundary", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:30:00+09:00",
    dayType: "weekday",
    destinationCode: "TA03",
    offsetMinutes: [0, 30],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: { nagoya: { walkMinutes: 8 } }
  });
  assert.equal(result.destination.name, "大江");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "nagoya");
  assert.equal(result.scenarios[0].lastDeparture, "23:59");
  assert.equal(result.scenarios[0].lastArrival, "00:10");
  assert.equal(result.scenarios[0].routeSummary, "名鉄名古屋本線→常滑線 急行 直通");
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
    print("Meitetsu Tokoname production migration applied")


if __name__ == "__main__":
    main()

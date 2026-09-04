#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "meitetsu-inuyama-official-direct-timetable"

BOUNDARIES = {
    "IY02": ("中小田井", "23:41", "23:49", "普通", "犬山"),
    "IY03": ("上小田井", "23:59", "00:06", "急行", "新鵜沼"),
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
            "routeSummary": f"名鉄名古屋本線→犬山線 {train_class} 直通",
            "trainClass": train_class,
            "trainTerminal": terminal,
            "transfers": 0,
            "status": "verified",
            "sourceIds": [SOURCE_ID],
        }
        data["destinations"][code] = {
            "operator": "meitetsu",
            "line": "inuyama",
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
    block = '''        <optgroup label="名鉄犬山線（名鉄名古屋から直通）">
          <option value="IY02" data-name="中小田井">IY02 中小田井</option>
          <option value="IY03" data-name="上小田井">IY03 上小田井</option>
        </optgroup>
'''
    if 'value="IY02"' not in text:
        if anchor not in text:
            raise RuntimeError("JR Kansai optgroup anchor not found")
        text = text.replace(anchor, block + anchor, 1)

    old = "名鉄名古屋本線（名古屋市内）・名鉄常滑線（名古屋市内）・あおなみ線"
    new = "名鉄名古屋本線（名古屋市内）・名鉄常滑線（名古屋市内）・名鉄犬山線（名古屋市内）・あおなみ線"
    if old in text:
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def update_settings() -> None:
    path = ROOT / "public/js/settings.js"
    text = path.read_text(encoding="utf-8")

    old_error = '  "S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68";'
    new_error = '  "S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, IY02-IY03, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68";'
    if old_error in text:
        text = text.replace(old_error, new_error, 1)

    marker = "  const operatorMatch = /^(KT)-E(\\d{1,2})$/.exec(code);"
    block = '''  const meitetsuInuyamaMatch = /^IY(\\d{1,2})$/.exec(code);

  if (meitetsuInuyamaMatch) {
    const number = Number(meitetsuInuyamaMatch[1]);
    if (number < 2 || number > 3) {
      throw new Error(DESTINATION_STATION_ERROR);
    }
    return `IY${String(number).padStart(2, "0")}`;
  }

'''
    if "const meitetsuInuyamaMatch" not in text:
        if marker not in text:
            raise RuntimeError("settings anchor not found")
        text = text.replace(marker, block + marker, 1)
    path.write_text(text, encoding="utf-8")


def update_settings_tests() -> None:
    path = ROOT / "test/settings.test.js"
    text = path.read_text(encoding="utf-8")
    old = "/H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68/;"
    new = "/H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, IY02-IY03, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68/;"
    if old in text:
        text = text.replace(old, new, 1)

    if 'accepts Meitetsu Inuyama IY02-IY03' not in text:
        text += '''

test("destination station accepts Meitetsu Inuyama IY02-IY03 codes", () => {
  assert.equal(normalizeDestinationStation("iy2"), "IY02");
  assert.equal(normalizeDestinationStation("IY03"), "IY03");
  assert.throws(() => normalizeDestinationStation("IY01"), /IY02-IY03/);
  assert.throws(() => normalizeDestinationStation("IY04"), /IY02-IY03/);
});

test("Meitetsu Inuyama destination is stored and restored locally", () => {
  const storage = memoryStorage();
  assert.equal(saveDestinationStation("iy3", storage), "IY03");
  assert.equal(loadDestinationStation(storage), "IY03");
});
'''
    path.write_text(text, encoding="utf-8")


def update_last_train_tests() -> None:
    path = ROOT / "test/last-train.test.js"
    text = path.read_text(encoding="utf-8")
    if 'Meitetsu Inuyama boundaries cover IY02-IY03' in text:
        return

    text += '''


test("Meitetsu Inuyama boundaries cover IY02-IY03 from Nagoya hub", () => {
  const expected = {
    IY02: ["中小田井", "23:41", "23:49", "普通", "犬山"],
    IY03: ["上小田井", "23:59", "00:06", "急行", "新鵜沼"]
  };

  for (const [code, [name, departure, arrival, trainClass, terminal]] of Object.entries(expected)) {
    const destination = dataset.destinations[code];
    assert.equal(destination.operator, "meitetsu", code);
    assert.equal(destination.line, "inuyama", code);
    assert.equal(destination.officialStationCode, code, code);
    assert.equal(destination.name, name, code);

    for (const dayType of ["weekday", "saturday_holiday"]) {
      const route = destination.routes.nagoya[dayType];
      assert.equal(route.lastDeparture, departure, `${code}/${dayType}`);
      assert.equal(route.lastArrival, arrival, `${code}/${dayType}`);
      assert.equal(route.trainClass, trainClass, `${code}/${dayType}`);
      assert.equal(route.trainTerminal, terminal, `${code}/${dayType}`);
      assert.equal(route.routeSummary, `名鉄名古屋本線→犬山線 ${trainClass} 直通`, `${code}/${dayType}`);
      assert.equal(route.transfers, 0, `${code}/${dayType}`);
      assert.equal(route.status, "verified", `${code}/${dayType}`);
    }
  }
});

test("Meitetsu Inuyama destinations only need Nagoya walk hub", () => {
  assert.deepEqual(eligibleOriginIds(dataset, "IY02"), ["nagoya"]);
  assert.deepEqual(eligibleOriginIds(dataset, "IY03"), ["nagoya"]);
});

test("Meitetsu Inuyama IY02 keeps the early 23:41 Inuyama local boundary", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:10:00+09:00",
    dayType: "weekday",
    destinationCode: "IY02",
    offsetMinutes: [0, 30],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: { nagoya: { walkMinutes: 8 } }
  });
  assert.equal(result.destination.name, "中小田井");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "nagoya");
  assert.equal(result.scenarios[0].lastDeparture, "23:41");
  assert.equal(result.scenarios[0].lastArrival, "23:49");
  assert.equal(result.scenarios[0].routeSummary, "名鉄名古屋本線→犬山線 普通 直通");
  assert.equal(result.scenarios[1].canReachDestination, false);
});

test("Meitetsu Inuyama IY03 keeps the 23:59 Shin-Unuma express boundary", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:30:00+09:00",
    dayType: "weekday",
    destinationCode: "IY03",
    offsetMinutes: [0, 30],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: { nagoya: { walkMinutes: 8 } }
  });
  assert.equal(result.destination.name, "上小田井");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "nagoya");
  assert.equal(result.scenarios[0].lastDeparture, "23:59");
  assert.equal(result.scenarios[0].lastArrival, "00:06");
  assert.equal(result.scenarios[0].routeSummary, "名鉄名古屋本線→犬山線 急行 直通");
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
    print("Meitetsu Inuyama production migration applied")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE_ID = "meitetsu-main-official-direct-timetable"

BOUNDARIES = {
    "NH24": ("中京競馬場前", "23:49", "00:08", "準急", "豊明"),
    "NH25": ("有松", "23:49", "00:06", "準急", "豊明"),
    "NH26": ("左京山", "23:21", "23:50", "普通", "新安城"),
    "NH27": ("鳴海", "00:01", "00:21", "普通", "鳴海"),
    "NH28": ("本星崎", "00:01", "00:18", "普通", "鳴海"),
    "NH29": ("本笠寺", "00:01", "00:16", "普通", "鳴海"),
    "NH30": ("桜", "00:01", "00:15", "普通", "鳴海"),
    "NH31": ("呼続", "00:01", "00:13", "普通", "鳴海"),
    "NH32": ("堀田", "00:01", "00:11", "普通", "鳴海"),
    "NH33": ("神宮前", "00:01", "00:09", "普通", "鳴海"),
    "NH34": ("金山", "00:06", "00:10", "急行", "金山（愛知県）"),
    "NH35": ("山王", "00:01", "00:03", "普通", "鳴海"),
    "NH36": ("名鉄名古屋", None, None, None, None),
    "NH37": ("栄生", "00:01", "00:03", "急行", "津島"),
    "NH38": ("東枇杷島", "23:50", "23:54", "普通", "須ケ口"),
}


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"anchor not found in {path}: {old[:100]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_dataset() -> None:
    path = ROOT / "src/data/last-trains-nagoya.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    source = {
        "id": SOURCE_ID,
        "publisher": "名古屋鉄道",
        "checkedAt": "2026-09-04",
        "url": "https://trainbus.meitetsu.co.jp/meitetsu-transfer/pc/transfer/DepArrTimeList",
    }
    sources = data["sources"]
    for index, item in enumerate(sources):
        if item.get("id") == SOURCE_ID:
            sources[index] = source
            break
    else:
        sources.append(source)

    station_codes = data["origins"]["nagoya"]["stationCodes"]
    if "NH36" not in station_codes:
        station_codes.append("NH36")

    for code, (name, departure, arrival, train_class, terminal) in BOUNDARIES.items():
        destination = {
            "operator": "meitetsu",
            "officialStationCode": code,
            "name": name,
            "city": "名古屋市",
            "stationCodes": [code],
            "enabled": True,
            "routes": {},
        }
        if code != "NH36":
            route = {
                "lastDeparture": departure,
                "lastArrival": arrival,
                "routeSummary": f"名鉄名古屋本線 {train_class} 直通",
                "trainClass": train_class,
                "trainTerminal": terminal,
                "transfers": 0,
                "status": "verified",
                "sourceIds": [SOURCE_ID],
            }
            destination["routes"] = {
                "nagoya": {
                    "weekday": dict(route),
                    "saturday_holiday": dict(route),
                }
            }
        data["destinations"][code] = destination

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def update_html() -> None:
    path = ROOT / "public/index.html"
    anchor = '        <optgroup label="JR関西本線（名古屋から直通）">'
    block = '''        <optgroup label="名鉄名古屋本線（名鉄名古屋から直通）">
          <option value="NH24" data-name="中京競馬場前">NH24 中京競馬場前</option>
          <option value="NH25" data-name="有松">NH25 有松</option>
          <option value="NH26" data-name="左京山">NH26 左京山</option>
          <option value="NH27" data-name="鳴海">NH27 鳴海</option>
          <option value="NH28" data-name="本星崎">NH28 本星崎</option>
          <option value="NH29" data-name="本笠寺">NH29 本笠寺</option>
          <option value="NH30" data-name="桜">NH30 桜</option>
          <option value="NH31" data-name="呼続">NH31 呼続</option>
          <option value="NH32" data-name="堀田">NH32 堀田</option>
          <option value="NH33" data-name="神宮前">NH33 神宮前</option>
          <option value="NH34" data-name="金山">NH34 金山</option>
          <option value="NH35" data-name="山王">NH35 山王</option>
          <option value="NH36" data-name="名鉄名古屋">NH36 名鉄名古屋</option>
          <option value="NH37" data-name="栄生">NH37 栄生</option>
          <option value="NH38" data-name="東枇杷島">NH38 東枇杷島</option>
        </optgroup>
'''
    text = path.read_text(encoding="utf-8")
    if 'value="NH24"' not in text:
        if anchor not in text:
            raise RuntimeError("JR Kansai optgroup anchor not found")
        text = text.replace(anchor, block + anchor, 1)

    old_hint = "名古屋市営地下鉄・名鉄瀬戸線（名古屋市内）・あおなみ線・近鉄名古屋線（名古屋市内）・JR関西本線"
    new_hint = "名古屋市営地下鉄・名鉄瀬戸線（名古屋市内）・名鉄名古屋本線（名古屋市内）・あおなみ線・近鉄名古屋線（名古屋市内）・JR関西本線"
    if old_hint in text:
        text = text.replace(old_hint, new_hint, 1)
    path.write_text(text, encoding="utf-8")


def update_settings() -> None:
    path = ROOT / "public/js/settings.js"
    text = path.read_text(encoding="utf-8")

    old_error = (
        '  "S01-S21, K01, ST01-ST12, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68";'
    )
    new_error = (
        '  "S01-S21, K01, ST01-ST12, NH24-NH38, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68";'
    )
    if old_error in text:
        text = text.replace(old_error, new_error, 1)

    marker = "  const operatorMatch = /^(KT)-E(\\d{1,2})$/.exec(code);"
    nh_block = '''  const meitetsuMainMatch = /^NH(\\d{1,2})$/.exec(code);

  if (meitetsuMainMatch) {
    const number = Number(meitetsuMainMatch[1]);

    if (number < 24 || number > 38) {
      throw new Error(DESTINATION_STATION_ERROR);
    }

    return `NH${String(number).padStart(2, "0")}`;
  }

'''
    if "const meitetsuMainMatch" not in text:
        if marker not in text:
            raise RuntimeError("settings operatorMatch anchor not found")
        text = text.replace(marker, nh_block + marker, 1)

    path.write_text(text, encoding="utf-8")


def update_settings_tests() -> None:
    path = ROOT / "test/settings.test.js"
    text = path.read_text(encoding="utf-8")
    old = "/H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68/;"
    new = "/H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, NH24-NH38, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68/;"
    if old in text:
        text = text.replace(old, new, 1)

    if 'normalizeDestinationStation("nh24")' not in text:
        text += '''

test("destination station accepts Meitetsu Main NH24-NH38 codes", () => {
  assert.equal(normalizeDestinationStation("nh24"), "NH24");
  assert.equal(normalizeDestinationStation("NH38"), "NH38");
  assert.throws(() => normalizeDestinationStation("NH23"), /NH24-NH38/);
  assert.throws(() => normalizeDestinationStation("NH39"), /NH24-NH38/);
});

test("Meitetsu Main destination is stored and restored locally", () => {
  const storage = memoryStorage();
  assert.equal(saveDestinationStation("nh34", storage), "NH34");
  assert.equal(loadDestinationStation(storage), "NH34");
});
'''
    path.write_text(text, encoding="utf-8")


def update_last_train_tests() -> None:
    path = ROOT / "test/last-train.test.js"
    text = path.read_text(encoding="utf-8")
    if 'Meitetsu Main boundaries cover NH24-NH38' in text:
        return

    text += '''


test("Meitetsu Main boundaries cover NH24-NH38 from Nagoya hub", () => {
  const expected = {
    NH24: ["中京競馬場前", "23:49", "00:08", "準急", "豊明"],
    NH25: ["有松", "23:49", "00:06", "準急", "豊明"],
    NH26: ["左京山", "23:21", "23:50", "普通", "新安城"],
    NH27: ["鳴海", "00:01", "00:21", "普通", "鳴海"],
    NH28: ["本星崎", "00:01", "00:18", "普通", "鳴海"],
    NH29: ["本笠寺", "00:01", "00:16", "普通", "鳴海"],
    NH30: ["桜", "00:01", "00:15", "普通", "鳴海"],
    NH31: ["呼続", "00:01", "00:13", "普通", "鳴海"],
    NH32: ["堀田", "00:01", "00:11", "普通", "鳴海"],
    NH33: ["神宮前", "00:01", "00:09", "普通", "鳴海"],
    NH34: ["金山", "00:06", "00:10", "急行", "金山（愛知県）"],
    NH35: ["山王", "00:01", "00:03", "普通", "鳴海"],
    NH37: ["栄生", "00:01", "00:03", "急行", "津島"],
    NH38: ["東枇杷島", "23:50", "23:54", "普通", "須ケ口"]
  };

  assert.equal(
    Object.keys(dataset.destinations).filter((code) => /^NH\\d{2}$/.test(code)).length,
    15
  );
  assert.deepEqual(dataset.destinations.NH36.routes, {});
  assert.ok(dataset.origins.nagoya.stationCodes.includes("NH36"));

  for (const [code, [name, departure, arrival, trainClass, terminal]] of Object.entries(expected)) {
    const destination = dataset.destinations[code];
    assert.equal(destination.operator, "meitetsu", code);
    assert.equal(destination.officialStationCode, code, code);
    assert.equal(destination.name, name, code);

    for (const dayType of ["weekday", "saturday_holiday"]) {
      const route = destination.routes.nagoya[dayType];
      assert.equal(route.lastDeparture, departure, `${code}/${dayType}`);
      assert.equal(route.lastArrival, arrival, `${code}/${dayType}`);
      assert.equal(route.trainClass, trainClass, `${code}/${dayType}`);
      assert.equal(route.trainTerminal, terminal, `${code}/${dayType}`);
      assert.equal(route.routeSummary, `名鉄名古屋本線 ${trainClass} 直通`, `${code}/${dayType}`);
      assert.equal(route.transfers, 0, `${code}/${dayType}`);
      assert.equal(route.status, "verified", `${code}/${dayType}`);
    }
  }
});

test("Meitetsu Main destinations only need Nagoya walk hub", () => {
  assert.deepEqual(eligibleOriginIds(dataset, "NH26"), ["nagoya"]);
  assert.deepEqual(eligibleOriginIds(dataset, "NH34"), ["nagoya"]);
});

test("Meitetsu Main NH26 keeps the early 23:21 Shin-Anjo local boundary", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:00:00+09:00",
    dayType: "weekday",
    destinationCode: "NH26",
    offsetMinutes: [0, 15],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      nagoya: { walkMinutes: 8 }
    }
  });

  assert.equal(result.destination.name, "左京山");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "nagoya");
  assert.equal(result.scenarios[0].lastDeparture, "23:21");
  assert.equal(result.scenarios[0].lastArrival, "23:50");
  assert.equal(result.scenarios[0].routeSummary, "名鉄名古屋本線 普通 直通");
  assert.equal(result.scenarios[1].canReachDestination, false);
});

test("Meitetsu Main NH34 keeps the 00:06 Kanayama express boundary", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:35:00+09:00",
    dayType: "weekday",
    destinationCode: "NH34",
    offsetMinutes: [0, 30],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      nagoya: { walkMinutes: 8 }
    }
  });

  assert.equal(result.destination.name, "金山");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "nagoya");
  assert.equal(result.scenarios[0].lastDeparture, "00:06");
  assert.equal(result.scenarios[0].lastArrival, "00:10");
  assert.equal(result.scenarios[0].routeSummary, "名鉄名古屋本線 急行 直通");
  assert.equal(result.scenarios[1].canReachDestination, false);
});
'''
    path.write_text(text, encoding="utf-8")


def update_deploy_smoke() -> None:
    path = ROOT / ".github/workflows/deploy-worker.yml"
    text = path.read_text(encoding="utf-8")
    marker = "          cat > /tmp/h10-walk-request.json <<'JSON'\n"
    if "Meitetsu Main NH26 safe boundary smoke test: OK" in text:
        return
    if marker not in text:
        raise RuntimeError("deploy smoke H10 anchor not found")

    block = '''          cat > /tmp/nh26-boundary-request.json <<'JSON'
          {
            "origin": {
              "latitude": 35.1715,
              "longitude": 136.9057
            },
            "departureTime": "2026-09-04T22:30:00+09:00",
            "dayType": "weekday",
            "destinationCode": "NH26",
            "offsetMinutes": [0, 30],
            "stationBufferMinutes": 3,
            "minimumBoardingLeadMinutes": 1
          }
          JSON

          curl -fsS \\
            -H "content-type: application/json" \\
            --data @/tmp/nh26-boundary-request.json \\
            "$BASE_URL/api/last-train-boundary" \\
            -o /tmp/nh26-boundary.json

          cat /tmp/nh26-boundary.json

          python3 - <<'PY'
          import json

          with open("/tmp/nh26-boundary.json", encoding="utf-8") as f:
              data = json.load(f)

          scenarios = data["scenarios"]
          assert data["destination"]["code"] == "NH26", data
          assert data["destination"]["name"] == "左京山", data
          assert set(data["walkOptions"]) == {"nagoya"}, data["walkOptions"]
          assert scenarios[0]["canReachDestination"] is True, scenarios
          assert scenarios[0]["recommendedOriginId"] == "nagoya", scenarios
          assert scenarios[0]["lastDeparture"] == "23:21", scenarios
          assert scenarios[0]["lastArrival"] == "23:50", scenarios
          assert scenarios[0]["routeSummary"] == "名鉄名古屋本線 普通 直通", scenarios
          assert scenarios[1]["canReachDestination"] is False, scenarios

          print("Meitetsu Main NH26 safe boundary smoke test: OK")
          PY

'''
    path.write_text(text.replace(marker, block + marker, 1), encoding="utf-8")


def main() -> None:
    update_dataset()
    update_html()
    update_settings()
    update_settings_tests()
    update_last_train_tests()
    update_deploy_smoke()
    print("Meitetsu Main production migration applied")


if __name__ == "__main__":
    main()

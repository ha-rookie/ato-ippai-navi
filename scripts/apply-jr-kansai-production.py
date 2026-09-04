#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"anchor not found in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + block.rstrip() + "\n", encoding="utf-8")


def route() -> dict:
    return {
        "lastDeparture": "23:57",
        "lastArrival": None,
        "routeSummary": "JR関西本線 普通 直通",
        "trainTerminal": "四日市",
        "transfers": 0,
        "status": "verified",
        "sourceIds": ["jr-central-kansai-official-timetable"],
    }


def update_dataset() -> None:
    path = ROOT / "src/data/last-trains-nagoya.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    data["metadata"]["checkedAt"] = "2026-09-04"

    source = {
        "id": "jr-central-kansai-official-timetable",
        "publisher": "東海旅客鉄道",
        "revision": "2026-03-14",
        "url": "https://railway.jr-central.co.jp/time-schedule/srch/_pdf/data/202603/kansai_Nagoya_B_wh_d.pdf",
    }
    source_ids = [item["id"] for item in data["sources"]]
    if source["id"] not in source_ids:
        data["sources"].append(source)

    codes = data["origins"]["nagoya"]["stationCodes"]
    if "JR-CJ00" not in codes:
        codes.append("JR-CJ00")

    stations = [
        ("JR-CJ00", "CJ00", "名古屋"),
        ("JR-CJ01", "CJ01", "八田"),
        ("JR-CJ02", "CJ02", "春田"),
    ]
    for internal, official, name in stations:
        destination = {
            "operator": "jr-central",
            "officialStationCode": official,
            "name": name,
            "city": "名古屋市",
            "stationCodes": [internal],
            "enabled": True,
            "routes": {},
        }
        if internal != "JR-CJ00":
            destination["routes"] = {
                "nagoya": {
                    "weekday": route(),
                    "saturday_holiday": route(),
                }
            }
        data["destinations"][internal] = destination

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def update_settings() -> None:
    path = ROOT / "public/js/settings.js"
    old = (
        'const DESTINATION_STATION_ERROR =\n'
        '  "destination station must be H01-H22, T01-T20, M01-M28, E01-E07, " +\n'
        '  "S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07";'
    )
    new = (
        'const DESTINATION_STATION_ERROR =\n'
        '  "destination station must be H01-H22, T01-T20, M01-M28, E01-E07, " +\n'
        '  "S01-S21, K01, ST01-ST12, AN01-AN11, KT-E01-KT-E07, or JR-CJ00-JR-CJ02";'
    )
    replace_once(path, old, new)

    old = '  const operatorMatch = /^(KT)-E(\\d{1,2})$/.exec(code);\n'
    new = '''  const jrMatch = /^JR-CJ(\\d{1,2})$/.exec(code);\n\n  if (jrMatch) {\n    const number = Number(jrMatch[1]);\n\n    if (number < 0 || number > 2) {\n      throw new Error(DESTINATION_STATION_ERROR);\n    }\n\n    return `JR-CJ${String(number).padStart(2, "0")}`;\n  }\n\n  const operatorMatch = /^(KT)-E(\\d{1,2})$/.exec(code);\n'''
    replace_once(path, old, new)


def update_html() -> None:
    path = ROOT / "public/index.html"
    old = '''        <optgroup label="近鉄名古屋線（近鉄名古屋から直通）">\n          <option value="KT-E01" data-name="近鉄名古屋">E01 近鉄名古屋</option>\n          <option value="KT-E02" data-name="米野">E02 米野</option>\n          <option value="KT-E03" data-name="黄金">E03 黄金</option>\n          <option value="KT-E04" data-name="烏森">E04 烏森</option>\n          <option value="KT-E05" data-name="近鉄八田">E05 近鉄八田</option>\n          <option value="KT-E06" data-name="伏屋">E06 伏屋</option>\n          <option value="KT-E07" data-name="戸田">E07 戸田</option>\n        </optgroup>\n'''
    new = old + '''        <optgroup label="JR関西本線（名古屋から直通）">\n          <option value="JR-CJ00" data-name="名古屋">CJ00 名古屋</option>\n          <option value="JR-CJ01" data-name="八田">CJ01 八田</option>\n          <option value="JR-CJ02" data-name="春田">CJ02 春田</option>\n        </optgroup>\n'''
    replace_once(path, old, new)

    replace_once(
        path,
        "名古屋市営地下鉄・名鉄瀬戸線（名古屋市内）・あおなみ線・近鉄名古屋線（名古屋市内）に対応しています。",
        "名古屋市営地下鉄・名鉄瀬戸線（名古屋市内）・あおなみ線・近鉄名古屋線（名古屋市内）・JR関西本線（名古屋市内）に対応しています。",
    )
    replace_once(
        path,
        "名古屋市交通局・名古屋鉄道・近畿日本鉄道・あおなみ線の公式時刻表",
        "名古屋市交通局・名古屋鉄道・近畿日本鉄道・東海旅客鉄道・あおなみ線の公式時刻表",
    )


def update_settings_tests() -> None:
    path = ROOT / "test/settings.test.js"
    text = path.read_text(encoding="utf-8")
    old_range = "H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07"
    new_range = "H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, KT-E01-KT-E07, or JR-CJ00-JR-CJ02"
    text = text.replace(old_range, new_range)

    anchor = '  assert.equal(normalizeDestinationStation("KT-E07"), "KT-E07");\n'
    addition = anchor + '  assert.equal(normalizeDestinationStation("jr-cj0"), "JR-CJ00");\n  assert.equal(normalizeDestinationStation("JR-CJ2"), "JR-CJ02");\n'
    if 'normalizeDestinationStation("jr-cj0")' not in text:
        if anchor not in text:
            raise RuntimeError("settings test acceptance anchor missing")
        text = text.replace(anchor, addition, 1)

    reject_anchor = '''  assert.throws(\n    () => normalizeDestinationStation("KT01"),\n    /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, KT-E01-KT-E07, or JR-CJ00-JR-CJ02/\n  );\n'''
    rejects = reject_anchor + '''  assert.throws(\n    () => normalizeDestinationStation("JR-CJ03"),\n    /JR-CJ00-JR-CJ02/\n  );\n  assert.throws(\n    () => normalizeDestinationStation("CJ01"),\n    /JR-CJ00-JR-CJ02/\n  );\n  assert.throws(\n    () => normalizeDestinationStation("JRCJ01"),\n    /JR-CJ00-JR-CJ02/\n  );\n'''
    if 'normalizeDestinationStation("JR-CJ03")' not in text:
        if reject_anchor not in text:
            raise RuntimeError("settings test rejection anchor missing")
        text = text.replace(reject_anchor, rejects, 1)

    save_anchor = '  assert.equal(loadDestinationStation(storage), "KT-E07");\n'
    save_add = save_anchor + '\n  assert.equal(saveDestinationStation("jr-cj2", storage), "JR-CJ02");\n  assert.equal(loadDestinationStation(storage), "JR-CJ02");\n'
    if 'saveDestinationStation("jr-cj2"' not in text:
        if save_anchor not in text:
            raise RuntimeError("settings save test anchor missing")
        text = text.replace(save_anchor, save_add, 1)

    path.write_text(text, encoding="utf-8")


def update_last_train_tests() -> None:
    path = ROOT / "test/last-train.test.js"
    block = r'''test("JR Kansai boundaries use namespaced JR-CJ00-JR-CJ02 codes", () => {
  const expected = {
    "JR-CJ01": ["CJ01", "八田"],
    "JR-CJ02": ["CJ02", "春田"]
  };

  assert.deepEqual(dataset.destinations["JR-CJ00"].routes, {});
  assert.equal(dataset.destinations["JR-CJ00"].operator, "jr-central");
  assert.equal(dataset.destinations["JR-CJ00"].officialStationCode, "CJ00");
  assert.ok(dataset.origins.nagoya.stationCodes.includes("JR-CJ00"));

  for (const [code, [officialCode, name]] of Object.entries(expected)) {
    const destination = dataset.destinations[code];
    const route = destination.routes.nagoya.weekday;

    assert.equal(destination.operator, "jr-central", code);
    assert.equal(destination.officialStationCode, officialCode, code);
    assert.equal(destination.name, name, code);
    assert.equal(route.lastDeparture, "23:57", code);
    assert.equal(route.lastArrival, null, code);
    assert.equal(route.trainTerminal, "四日市", code);
    assert.equal(route.routeSummary, "JR関西本線 普通 直通", code);
    assert.equal(route.transfers, 0, code);
    assert.equal(route.status, "verified", code);
  }
});

test("JR Kansai destinations only need Nagoya walk hub", () => {
  assert.deepEqual(eligibleOriginIds(dataset, "JR-CJ02"), ["nagoya"]);
});

test("JR-CJ02 uses the 23:57 Yokkaichi local boundary with nullable arrival", () => {
  const result = evaluateLastTrainBoundary(dataset, {
    departureTime: "2026-09-04T23:35:00+09:00",
    dayType: "weekday",
    destinationCode: "JR-CJ02",
    offsetMinutes: [0, 15],
    stationBufferMinutes: 3,
    minimumBoardingLeadMinutes: 1,
    hubAccess: {
      nagoya: { walkMinutes: 8 }
    }
  });

  assert.equal(result.destination.name, "春田");
  assert.equal(result.scenarios[0].canReachDestination, true);
  assert.equal(result.scenarios[0].recommendedOriginId, "nagoya");
  assert.equal(result.scenarios[0].lastDeparture, "23:57");
  assert.equal(result.scenarios[0].lastArrival, null);
  assert.equal(result.scenarios[0].localLastTrainArrivalTime, null);
  assert.equal(result.scenarios[1].canReachDestination, false);
});'''
    append_once(path, 'test("JR Kansai boundaries use namespaced', block)


def update_generator() -> None:
    path = ROOT / "scripts/generate-jr-kansai-nagoya-last-trains.py"
    replace_once(
        path,
        '        "lastDeparture": LAST_DEPARTURE,\n        "routeSummary": "JR関西本線 普通 直通",',
        '        "lastDeparture": LAST_DEPARTURE,\n        "lastArrival": None,\n        "routeSummary": "JR関西本線 普通 直通",',
    )


def update_poc_workflow() -> None:
    path = ROOT / ".github/workflows/poc-jr-kansai-nagoya.yml"
    replace_once(
        path,
        "      - 'scripts/generate-jr-kansai-nagoya-last-trains.py'\n",
        "      - 'scripts/generate-jr-kansai-nagoya-last-trains.py'\n      - 'src/data/last-trains-nagoya.json'\n",
    )
    replace_once(
        path,
        "                  assert 'lastArrival' not in route, (code, route)\n",
        "                  assert route['lastArrival'] is None, (code, route)\n",
    )

    marker = "      - name: Compare generated JR Kansai boundaries with production JSON"
    text = path.read_text(encoding="utf-8")
    if marker not in text:
        anchor = "      - name: Record station-numbering verification policy\n"
        compare = r'''      - name: Compare generated JR Kansai boundaries with production JSON
        shell: bash
        run: |
          python3 - <<'PY'
          import json

          with open('/tmp/jr-kansai-nagoya-last-trains.json', encoding='utf-8') as f:
              generated = json.load(f)
          with open('src/data/last-trains-nagoya.json', encoding='utf-8') as f:
              production = json.load(f)

          source = next(
              item for item in production['sources']
              if item['id'] == 'jr-central-kansai-official-timetable'
          )
          assert source['publisher'] == '東海旅客鉄道', source
          assert source['revision'] == '2026-03-14', source
          assert 'JR-CJ00' in production['origins']['nagoya']['stationCodes']

          for code in ('JR-CJ00', 'JR-CJ01', 'JR-CJ02'):
              expected = generated['destinations'][code]
              actual = production['destinations'][code]
              assert actual['operator'] == expected['operator'], code
              assert actual['officialStationCode'] == expected['officialStationCode'], code
              assert actual['name'] == expected['name'], code
              assert actual['stationCodes'] == expected['stationCodes'], code
              assert actual['enabled'] is True, code
              assert actual['city'] == '名古屋市', code
              assert actual['routes'] == expected['routes'], code

          print('JR Kansai generated vs production JSON: OK')
          PY

'''
        if anchor not in text:
            raise RuntimeError("PoC workflow compare anchor missing")
        path.write_text(text.replace(anchor, compare + anchor, 1), encoding="utf-8")


def update_deploy_smoke() -> None:
    path = ROOT / ".github/workflows/deploy-worker.yml"
    block = r'''          cat > /tmp/jr-cj02-boundary-request.json <<'JSON'
          {
            "origin": {
              "latitude": 35.1715,
              "longitude": 136.9057
            },
            "departureTime": "2026-09-04T23:20:00+09:00",
            "dayType": "weekday",
            "destinationCode": "JR-CJ02",
            "offsetMinutes": [0, 15],
            "stationBufferMinutes": 3,
            "minimumBoardingLeadMinutes": 1
          }
          JSON

          jr_kansai_ready=0

          for attempt in $(seq 1 5); do
            echo "JR Kansai JR-CJ02 smoke test attempt $attempt/5"

            status=$(curl -sS \
              -o /tmp/jr-cj02-boundary.json \
              -w '%{http_code}' \
              -H "content-type: application/json" \
              --data @/tmp/jr-cj02-boundary-request.json \
              "$BASE_URL/api/last-train-boundary")

            echo "HTTP status: $status"
            cat /tmp/jr-cj02-boundary.json

            if [ "$status" = "200" ]; then
              jr_kansai_ready=1
              break
            fi

            sleep 2
          done

          if [ "$jr_kansai_ready" -ne 1 ]; then
            echo "JR Kansai JR-CJ02 boundary API did not return 200."
            exit 1
          fi

          python3 - <<'PY'
          import json

          with open("/tmp/jr-cj02-boundary.json", encoding="utf-8") as f:
              data = json.load(f)

          scenarios = data["scenarios"]

          assert data["destination"]["code"] == "JR-CJ02", data
          assert data["destination"]["name"] == "春田", data
          assert set(data["walkOptions"]) == {"nagoya"}, data["walkOptions"]

          assert scenarios[0]["canReachDestination"] is True, scenarios
          assert scenarios[0]["recommendedOriginId"] == "nagoya", scenarios
          assert scenarios[0]["lastDeparture"] == "23:57", scenarios
          assert scenarios[0]["lastArrival"] is None, scenarios
          assert scenarios[0]["localLastTrainArrivalTime"] is None, scenarios
          assert scenarios[0]["routeSummary"] == "JR関西本線 普通 直通", scenarios

          assert scenarios[1]["canReachDestination"] is False, scenarios

          print("JR Kansai JR-CJ02 safe boundary smoke test: OK")
          PY'''
    append_once(path, 'echo "JR Kansai JR-CJ02 smoke test attempt', block)


def main() -> None:
    update_dataset()
    update_settings()
    update_html()
    update_settings_tests()
    update_last_train_tests()
    update_generator()
    update_poc_workflow()
    update_deploy_smoke()
    print("JR Kansai production migration applied")


if __name__ == "__main__":
    main()

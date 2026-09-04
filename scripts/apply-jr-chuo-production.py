#!/usr/bin/env python3
"""Temporary migration helper for JR Chuo production support.

This file is intentionally removed before the production PR is merged.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "src/data/last-trains-nagoya.json"
INDEX_PATH = ROOT / "public/index.html"
SETTINGS_PATH = ROOT / "public/js/settings.js"
SETTINGS_TEST_PATH = ROOT / "test/settings.test.js"
LAST_TRAIN_TEST_PATH = ROOT / "test/last-train.test.js"
DOC_PATH = ROOT / "docs/jr-chuo.md"

SOURCE_ID = "jr-central-chuo-official-timetable"


def route() -> dict:
    return {
        "lastDeparture": "00:05",
        "lastArrival": None,
        "routeSummary": "JR中央本線 普通 直通",
        "trainTerminal": "高蔵寺",
        "transfers": 0,
        "status": "verified",
        "sourceIds": [SOURCE_ID],
    }


def update_data() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    if not any(source.get("id") == SOURCE_ID for source in data["sources"]):
        data["sources"].append(
            {
                "id": SOURCE_ID,
                "publisher": "東海旅客鉄道",
                "revision": "2026-03-14",
                "url": "https://railway.jr-central.co.jp/time-schedule/srch/_pdf/data/202603/chuo_Nagoya_A_w_d.pdf",
            }
        )

    nagoya_codes = data["origins"]["nagoya"]["stationCodes"]
    if "JR-CF01" not in nagoya_codes:
        nagoya_codes.append("JR-CF01")

    stations = [
        ("JR-CF01", "CF01", "名古屋"),
        ("JR-CF02", "CF02", "金山"),
        ("JR-CF03", "CF03", "鶴舞"),
        ("JR-CF04", "CF04", "千種"),
        ("JR-CF05", "CF05", "大曽根"),
        ("JR-CF06", "CF06", "新守山"),
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
        if internal != "JR-CF01":
            destination["routes"]["nagoya"] = {
                "weekday": route(),
                "saturday_holiday": route(),
            }
        data["destinations"][internal] = destination

    data["metadata"]["checkedAt"] = "2026-09-04"
    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def update_index() -> None:
    text = INDEX_PATH.read_text(encoding="utf-8")
    if 'value="JR-CF01"' not in text:
        marker = """        <optgroup label=\"JR関西本線（名古屋から直通）\">\n          <option value=\"JR-CJ00\" data-name=\"名古屋\">CJ00 名古屋</option>\n          <option value=\"JR-CJ01\" data-name=\"八田\">CJ01 八田</option>\n          <option value=\"JR-CJ02\" data-name=\"春田\">CJ02 春田</option>\n        </optgroup>\n"""
        addition = marker + """        <optgroup label=\"JR中央本線（名古屋から直通）\">\n          <option value=\"JR-CF01\" data-name=\"名古屋\">CF01 名古屋</option>\n          <option value=\"JR-CF02\" data-name=\"金山\">CF02 金山</option>\n          <option value=\"JR-CF03\" data-name=\"鶴舞\">CF03 鶴舞</option>\n          <option value=\"JR-CF04\" data-name=\"千種\">CF04 千種</option>\n          <option value=\"JR-CF05\" data-name=\"大曽根\">CF05 大曽根</option>\n          <option value=\"JR-CF06\" data-name=\"新守山\">CF06 新守山</option>\n        </optgroup>\n"""
        if marker not in text:
            raise RuntimeError("JR Kansai UI marker not found")
        text = text.replace(marker, addition, 1)

    text = text.replace(
        "・JR関西本線（名古屋市内）に対応しています。",
        "・JR関西本線（名古屋市内）・JR中央本線（名古屋市内）に対応しています。",
    )
    INDEX_PATH.write_text(text, encoding="utf-8")


def update_settings() -> None:
    text = SETTINGS_PATH.read_text(encoding="utf-8")
    text = text.replace(
        '"S01-S21, K01, ST01-ST12, AN01-AN11, KT-E01-KT-E07, or JR-CJ00-JR-CJ02";',
        '"S01-S21, K01, ST01-ST12, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, or JR-CF01-JR-CF06";',
    )
    old = '''  const jrMatch = /^JR-CJ(\\d{1,2})$/.exec(code);\n\n  if (jrMatch) {\n    const number = Number(jrMatch[1]);\n\n    if (number < 0 || number > 2) {\n      throw new Error(DESTINATION_STATION_ERROR);\n    }\n\n    return `JR-CJ${String(number).padStart(2, "0")}`;\n  }\n'''
    new = '''  const jrMatch = /^JR-(CJ|CF)(\\d{1,2})$/.exec(code);\n\n  if (jrMatch) {\n    const line = jrMatch[1];\n    const number = Number(jrMatch[2]);\n    const valid =\n      (line === "CJ" && number >= 0 && number <= 2) ||\n      (line === "CF" && number >= 1 && number <= 6);\n\n    if (!valid) {\n      throw new Error(DESTINATION_STATION_ERROR);\n    }\n\n    return `JR-${line}${String(number).padStart(2, "0")}`;\n  }\n'''
    if old not in text and "const jrMatch = /^JR-(CJ|CF)" not in text:
        raise RuntimeError("JR settings normalizer marker not found")
    text = text.replace(old, new, 1)
    SETTINGS_PATH.write_text(text, encoding="utf-8")


def append_tests() -> None:
    settings_test = SETTINGS_TEST_PATH.read_text(encoding="utf-8")
    if 'normalizeDestinationStation("jr-cf1")' not in settings_test:
        settings_test += '''\n\ntest("destination station accepts JR Chuo namespaced station codes", () => {\n  assert.equal(normalizeDestinationStation("jr-cf1"), "JR-CF01");\n  assert.equal(normalizeDestinationStation("JR-CF6"), "JR-CF06");\n  assert.throws(() => normalizeDestinationStation("JR-CF00"));\n  assert.throws(() => normalizeDestinationStation("JR-CF07"));\n  assert.throws(() => normalizeDestinationStation("CF01"));\n});\n\ntest("JR Chuo destination is stored and restored locally", () => {\n  const storage = memoryStorage();\n  assert.equal(saveDestinationStation("jr-cf6", storage), "JR-CF06");\n  assert.equal(loadDestinationStation(storage), "JR-CF06");\n});\n'''
        SETTINGS_TEST_PATH.write_text(settings_test, encoding="utf-8")

    last_train_test = LAST_TRAIN_TEST_PATH.read_text(encoding="utf-8")
    if 'JR Chuo boundaries use namespaced JR-CF01-JR-CF06 codes' not in last_train_test:
        last_train_test += '''\n\ntest("JR Chuo boundaries use namespaced JR-CF01-JR-CF06 codes", () => {\n  const expected = {\n    "JR-CF01": ["CF01", "名古屋"],\n    "JR-CF02": ["CF02", "金山"],\n    "JR-CF03": ["CF03", "鶴舞"],\n    "JR-CF04": ["CF04", "千種"],\n    "JR-CF05": ["CF05", "大曽根"],\n    "JR-CF06": ["CF06", "新守山"]\n  };\n\n  assert.deepEqual(dataset.destinations["JR-CF01"].routes, {});\n  assert.ok(dataset.origins.nagoya.stationCodes.includes("JR-CF01"));\n\n  for (const [code, [officialCode, name]] of Object.entries(expected)) {\n    const destination = dataset.destinations[code];\n    assert.equal(destination.operator, "jr-central", code);\n    assert.equal(destination.officialStationCode, officialCode, code);\n    assert.equal(destination.name, name, code);\n\n    if (code === "JR-CF01") continue;\n\n    for (const dayType of ["weekday", "saturday_holiday"]) {\n      const route = destination.routes.nagoya[dayType];\n      assert.equal(route.lastDeparture, "00:05", code);\n      assert.equal(route.lastArrival, null, code);\n      assert.equal(route.trainTerminal, "高蔵寺", code);\n      assert.equal(route.routeSummary, "JR中央本線 普通 直通", code);\n      assert.equal(route.transfers, 0, code);\n      assert.equal(route.status, "verified", code);\n    }\n  }\n});\n\ntest("JR Chuo destinations only need Nagoya walk hub", () => {\n  assert.deepEqual(eligibleOriginIds(dataset, "JR-CF06"), ["nagoya"]);\n});\n\ntest("JR Chuo JR-CF06 uses the 00:05 Kozoji local boundary", () => {\n  const result = evaluateLastTrainBoundary(dataset, {\n    departureTime: "2026-09-04T23:20:00+09:00",\n    dayType: "weekday",\n    destinationCode: "JR-CF06",\n    offsetMinutes: [0, 15],\n    stationBufferMinutes: 3,\n    minimumBoardingLeadMinutes: 1,\n    hubAccess: {\n      nagoya: { walkMinutes: 31 }\n    }\n  });\n\n  assert.equal(result.destination.name, "新守山");\n  assert.equal(result.scenarios[0].canReachDestination, true);\n  assert.equal(result.scenarios[0].recommendedOriginId, "nagoya");\n  assert.equal(result.scenarios[0].lastDeparture, "00:05");\n  assert.equal(result.scenarios[0].lastArrival, null);\n  assert.equal(result.scenarios[0].localLastTrainArrivalTime, null);\n  assert.equal(result.scenarios[0].routeSummary, "JR中央本線 普通 直通");\n  assert.equal(result.scenarios[1].canReachDestination, false);\n});\n'''
        LAST_TRAIN_TEST_PATH.write_text(last_train_test, encoding="utf-8")


def write_doc() -> None:
    DOC_PATH.write_text(
        """# JR中央本線（名古屋市内）終電境界\n\n## 対象\n\n既存 `nagoya` 徒歩hubからJR東海・中央本線へ直接乗車するPhase 1方式。\n\n- JR-CF01 / CF01 名古屋（walk-home）\n- JR-CF02 / CF02 金山\n- JR-CF03 / CF03 鶴舞\n- JR-CF04 / CF04 千種\n- JR-CF05 / CF05 大曽根\n- JR-CF06 / CF06 新守山\n\nCF07勝川以降は名古屋市外のため対象外。\n\n## 公式ソース\n\nJR東海 名古屋駅 中央線 多治見・中津川方面 2026-03ダイヤ。\n\n- 平日: `chuo_Nagoya_A_w_d.pdf`\n- 土曜・休日: `chuo_Nagoya_A_h_d.pdf`\n- 駅番号: JR東海公式 station-numbering railway map\n\nCIで公式PDFを取得して `pdftotext -layout` し、0時台最終ブロックと停車駅順を検証する。\n\n## verified boundary\n\n| 目的 | 名古屋発 | 列車 | lastArrival |\n| --- | --- | --- | --- |\n| CF01 名古屋 | 徒歩帰宅 | - | - |\n| CF02〜CF06 | 00:05 | 普通 高蔵寺行 | null |\n\n平日・土曜休日とも同じ。\n\n各駅の正確な最終到着時刻はこのソースから取得していないため、`lastArrival` は推測せず `null` とする。\n\n## fail-closed\n\n以下が変わった場合はofficial-source CIを失敗させる。\n\n- 0:05ブロックの存在\n- 高蔵寺行 / 普通という列車属性\n- 0時台に追加列車が出現\n- 名古屋→金山→鶴舞→千種→大曽根→新守山→勝川の停車駅順\n- 公式PDF構造または必須トークン\n\nランタイムには全時刻表を持たず、目的駅ごとの終電境界のみをproduction JSONへ保持する。\n""",
        encoding="utf-8",
    )


def main() -> None:
    update_data()
    update_index()
    update_settings()
    append_tests()
    write_doc()
    print("JR Chuo production migration applied")


if __name__ == "__main__":
    main()

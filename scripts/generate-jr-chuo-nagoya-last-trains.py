#!/usr/bin/env python3
"""Generate JR Central Chuo Line Nagoya-city last-train boundaries.

Inputs are `pdftotext -layout` outputs from JR Central's official Nagoya
station Chuo Line timetable PDFs for weekdays and Saturdays/Sundays/holidays.
Only the verified last-departure boundary is emitted; the runtime does not
carry a full timetable.

Station numbers are reviewed static metadata from JR Central's current
station-numbering railway map. The map PDF is retained by CI because its
station-number graphics are not reliably machine-readable with pdftotext.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_ID = "jr-central-chuo-official-timetable"
LAST_DEPARTURE = "00:05"
TRAIN_TERMINAL = "高蔵寺"
ROUTE_SUMMARY = "JR中央本線 普通 直通"

STATIONS = [
    ("JR-CF01", "CF01", "名古屋"),
    ("JR-CF02", "CF02", "金山"),
    ("JR-CF03", "CF03", "鶴舞"),
    ("JR-CF04", "CF04", "千種"),
    ("JR-CF05", "CF05", "大曽根"),
    ("JR-CF06", "CF06", "新守山"),
]


def normalize_spaces(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value)


def verify_timetable(path: Path, expected_day_label: str) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    required_tokens = [
        "中央線時刻表",
        "多治見・中津川方面",
        expected_day_label,
        "停車駅のご案内",
        "名古屋",
        "金山",
        "鶴舞",
        "千種",
        "大曽根",
        "新守山",
        "勝川",
        "高蔵寺",
        "普通",
    ]
    for token in required_tokens:
        if token not in text:
            raise RuntimeError(
                f"Official Chuo timetable token changed/missing in {path}: {token}"
            )

    # pdftotext places the hour/minute on one line and the train type,
    # terminal and platform on the following lines:
    #   0 5
    #     普通
    #         高蔵寺
    #         8
    # Treat that exact late-night block shape as the verified boundary.
    zero_rows = [
        line
        for line in lines
        if re.fullmatch(r"\s*0\s+5\s*", line)
    ]
    if len(zero_rows) != 1:
        raise RuntimeError(
            f"Expected exactly one 0:05 row in {path}, got {len(zero_rows)}"
        )

    zero_index = lines.index(zero_rows[0])
    zero_context = "\n".join(lines[zero_index : min(len(lines), zero_index + 6)])
    if "高蔵寺" not in zero_context or "普通" not in zero_context:
        raise RuntimeError(
            f"0:05 service is no longer a Kozoji local in {path}: {zero_context!r}"
        )

    # There must not be a second hour-0 timetable row hidden elsewhere.
    # This deliberately ignores values such as "21 0" because the hour must
    # begin the line after optional whitespace.
    other_zero_rows = [
        line
        for line in lines
        if re.match(r"^\s*0\s+\d+(?:\s|$)", line)
    ]
    if len(other_zero_rows) != 1 or other_zero_rows[0] != zero_rows[0]:
        raise RuntimeError(
            f"Unexpected additional after-midnight service in {path}: {other_zero_rows}"
        )

    # Verify the station segment against the explicit stop-guide portion.
    stop_guide = text.split("停車駅のご案内", 1)[1]
    names = [name for _internal, _official, name in STATIONS] + ["勝川"]
    positions = [stop_guide.find(name) for name in names]
    if any(position < 0 for position in positions):
        raise RuntimeError(
            f"Nagoya-city Chuo station list missing/changed in {path}: {positions}"
        )
    if positions != sorted(positions):
        raise RuntimeError(
            f"Nagoya-city Chuo station order changed in {path}: {positions}"
        )

    # Keep an explicit late-night sanity check before the 0:05 service.
    normalized = normalize_spaces(text)
    for minute in ("7", "19", "31", "43", "57"):
        if not re.search(rf"\b{minute}\b", normalized):
            raise RuntimeError(
                f"Expected late-night minute {minute} missing in {path}"
            )


def route() -> dict:
    return {
        "lastDeparture": LAST_DEPARTURE,
        "lastArrival": None,
        "routeSummary": ROUTE_SUMMARY,
        "trainTerminal": TRAIN_TERMINAL,
        "transfers": 0,
        "status": "verified",
        "sourceIds": [SOURCE_ID],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekday", required=True, type=Path)
    parser.add_argument("--holiday", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default="2026-03-14")
    args = parser.parse_args()

    verify_timetable(args.weekday, "平日")
    verify_timetable(args.holiday, "土曜・休日")

    result = {
        "schemaVersion": 1,
        "operator": {
            "id": "jr-central",
            "name": "東海旅客鉄道",
        },
        "line": {
            "code": "CF",
            "name": "中央本線",
            "revision": args.revision,
        },
        "origin": {
            "id": "nagoya",
            "stationCode": "JR-CF01",
            "officialStationCode": "CF01",
            "stationName": "名古屋",
        },
        "destinations": {},
    }

    for internal_code, official_code, name in STATIONS:
        destination = {
            "operator": "jr-central",
            "officialStationCode": official_code,
            "name": name,
            "stationCodes": [internal_code],
            "routes": {},
        }
        if internal_code != "JR-CF01":
            destination["routes"]["nagoya"] = {
                "weekday": route(),
                "saturday_holiday": route(),
            }
        result["destinations"][internal_code] = destination

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate JR Central Kansai Line Nagoya-city last-train boundaries.

The input is `pdftotext -layout` output from JR Central's official Nagoya
station Kansai Line timetable PDF. The generator intentionally keeps only
the last-departure boundary required by Ato-Ippai Navi, not a full timetable.

JR station numbers are static metadata verified against JR Central's current
official railway map. The railway-map PDF is retained as a CI artifact because
its station-number graphics are not reliably extractable with pdftotext.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_ID = "jr-central-kansai-official-timetable"
LAST_DEPARTURE = "23:57"
TRAIN_TERMINAL = "四日市"

STATIONS = [
    ("JR-CJ00", "CJ00", "名古屋"),
    ("JR-CJ01", "CJ01", "八田"),
    ("JR-CJ02", "CJ02", "春田"),
]


def normalize_spaces(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value)


def verify_timetable(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    normalized = normalize_spaces(text)
    lines = text.splitlines()

    required_tokens = [
        "関西線時刻表",
        "四日市・松阪方面",
        "名古屋",
        "八田",
        "春田",
        "普通",
        "四日市",
        "停車駅のご案内",
    ]

    for token in required_tokens:
        if token not in text:
            raise RuntimeError(f"Official timetable token changed/missing: {token}")

    # The current official PDF prints weekday and Saturday/Sunday/holiday
    # timetables side-by-side. Both 23:00 blocks start with the same 23:11
    # row and end with the same 23:57 local to Yokkaichi.
    anchors = [
        index
        for index, line in enumerate(lines)
        if re.search(r"^\s*23\s+11\b", line)
    ]

    if len(anchors) != 2:
        raise RuntimeError(
            f"Expected exactly two 23:00 blocks, got {len(anchors)}"
        )

    for anchor in anchors:
        block = "\n".join(lines[max(0, anchor - 3):min(len(lines), anchor + 15)])
        block_normalized = normalize_spaces(block)

        if "四日市" not in block:
            raise RuntimeError("23:00 block no longer contains Yokkaichi terminal")
        if "普通" not in block:
            raise RuntimeError("23:00 block no longer contains local-train marker")
        if "11 25 40 57" not in block_normalized:
            raise RuntimeError(
                "Verified late-night minute sequence changed: expected 11 25 40 57"
            )

    # After the 23:57 service the current official PDF has only the empty
    # hour-0 headings for the two day-type columns. A future real minute in
    # that row must fail closed and force a boundary review.
    zero_hour_rows = [
        line for line in lines
        if re.search(r"^\s*0(?:\s|$)", line)
    ]
    if len(zero_hour_rows) != 1:
        raise RuntimeError(
            f"Expected one empty hour-0 row, got {len(zero_hour_rows)}"
        )

    zero_numbers = re.findall(r"\d+", zero_hour_rows[0])
    if not zero_numbers or any(number != "0" for number in zero_numbers):
        raise RuntimeError(
            "After-midnight departure detected; review last-train boundary"
        )

    # Verify the Nagoya-city station segment against the explicit stop-guide
    # portion of the official timetable rather than matching header text.
    stop_guide = text.split("停車駅のご案内", 1)[1]
    positions = [
        stop_guide.find(name)
        for _internal, _official, name in STATIONS
    ]
    if any(position < 0 for position in positions):
        raise RuntimeError(f"Nagoya-city station list missing: {positions}")
    if positions != sorted(positions):
        raise RuntimeError(f"Nagoya-city station order changed: {positions}")

    # Both day-type blocks must independently expose the same final minute row.
    if normalized.count("11 25 40 57") < 2:
        raise RuntimeError("Weekday/holiday final boundary no longer matches")


def route() -> dict:
    return {
        "lastDeparture": LAST_DEPARTURE,
        "routeSummary": "JR関西本線 普通 直通",
        "trainTerminal": TRAIN_TERMINAL,
        "transfers": 0,
        "status": "verified",
        "sourceIds": [SOURCE_ID],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timetable", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default="2026-03-14")
    args = parser.parse_args()

    verify_timetable(args.timetable)

    result = {
        "schemaVersion": 1,
        "operator": {
            "id": "jr-central",
            "name": "東海旅客鉄道",
        },
        "line": {
            "code": "CJ",
            "name": "関西本線",
            "revision": args.revision,
        },
        "origin": {
            "id": "nagoya",
            "stationCode": "JR-CJ00",
            "officialStationCode": "CJ00",
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

        if internal_code != "JR-CJ00":
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

#!/usr/bin/env python3
"""Generate JR Central Tokaido Line Nagoya-city last-train boundaries.

Inputs are `pdftotext -layout` outputs from JR Central's official Nagoya
station Tokaido Line timetable PDFs for weekdays and Saturdays/Sundays/
holidays. Only the verified last-departure boundary is emitted; the runtime
does not carry a full timetable.

Station numbers are reviewed static metadata from JR Central's current
station-numbering railway map. The map PDF is retained by CI because its
station-number graphics are not reliably machine-readable with pdftotext.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_ID = "jr-central-tokaido-official-timetable"
LAST_DEPARTURE = "23:59"
TRAIN_TERMINAL = "岡崎"
ROUTE_SUMMARY = "JR東海道本線 普通 直通"

# Nagoya-city scope from Nagoya toward Toyohashi/Okazaki.
# CA61 Kyowa is outside Nagoya city; CA69 Biwajima is also outside the city.
STATIONS = [
    ("JR-CA68", "CA68", "名古屋"),
    ("JR-CA67", "CA67", "尾頭橋"),
    ("JR-CA66", "CA66", "金山"),
    ("JR-CA65", "CA65", "熱田"),
    ("JR-CA64", "CA64", "笠寺"),
    ("JR-CA63", "CA63", "大高"),
    ("JR-CA62", "CA62", "南大高"),
]


def normalized_block(lines: list[str]) -> str:
    return re.sub(r"\s+", " ", "\n".join(lines)).strip()


def exact_token_position(text: str, token: str) -> int:
    """Return the first whitespace-delimited token position, or -1.

    Japanese station names can contain one another (for example 大高 inside
    南大高), so plain `find`/`rfind` is unsafe for stop-guide validation.
    `pdftotext -layout` separates station labels from neighboring columns with
    whitespace, allowing an exact-token match without OCR.
    """

    match = re.search(rf"(?<!\S){re.escape(token)}(?=\s|$)", text)
    return -1 if match is None else match.start()


def verify_timetable(path: Path, expected_day_label: str) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    required_tokens = [
        "東海道線時刻表",
        "豊橋・武豊方面",
        expected_day_label,
        "停車駅のご案内",
        "名古屋",
        "尾頭橋",
        "金山",
        "熱田",
        "笠寺",
        "大高",
        "南大高",
        "共和",
        "岡崎",
        "普通",
    ]
    for token in required_tokens:
        if token not in text:
            raise RuntimeError(
                f"Official Tokaido timetable token changed/missing in {path}: {token}"
            )

    # Locate the final hour-23 block. In the current official PDF, the last
    # service is 23:59 Okazaki-bound Local. pdftotext lays the minute, type,
    # destination and platform across multiple lines, so validate the block
    # rather than pretending they form one source row.
    hour23_indexes = [
        index for index, line in enumerate(lines)
        if re.search(r"^\s*23(?:\s|$)", line)
    ]
    if not hour23_indexes:
        raise RuntimeError(f"Hour-23 timetable block missing in {path}")

    hour23_index = hour23_indexes[-1]

    # The stop-guide occupies the right-hand side of the same PDF page, so the
    # hour-0 line can look like `0        Araimachi` after pdftotext. Identify
    # the hour marker from the left timetable column only instead of requiring
    # the entire physical line to contain just `0`.
    hour0_index = next(
        (
            index
            for index in range(hour23_index + 1, len(lines))
            if re.match(r"^\s*0(?:\s{8,}|$)", lines[index])
        ),
        None,
    )
    if hour0_index is None:
        raise RuntimeError(f"Empty hour-0 row missing after hour 23 in {path}")

    block = normalized_block(lines[hour23_index:hour0_index])
    if not re.search(r"\b59\b\s+普通\s+岡崎(?:\s|$)", block):
        raise RuntimeError(
            f"Expected final 23:59 Okazaki local missing/changed in {path}: {block!r}"
        )

    # Validate that the timetable side of the hour-0 row contains no minute.
    # Text to the far right belongs to the station stop guide and is ignored.
    hour0_timetable_column = lines[hour0_index][:80]
    if not re.fullmatch(r"\s*0\s*", hour0_timetable_column):
        raise RuntimeError(
            f"Unexpected after-midnight departure in {path}: {hour0_timetable_column!r}"
        )

    # Validate the city-station sequence in the official stop guide. Use exact
    # whitespace-delimited labels so 大高 does not accidentally match 南大高.
    stop_guide = text.split("停車駅のご案内", 1)[1]
    names = [name for _internal, _official, name in STATIONS] + ["共和"]
    positions = [exact_token_position(stop_guide, name) for name in names]
    if any(position < 0 for position in positions):
        raise RuntimeError(
            f"Nagoya-city Tokaido station list missing/changed in {path}: {positions}"
        )
    if positions != sorted(positions):
        raise RuntimeError(
            f"Nagoya-city Tokaido station order changed in {path}: {positions}"
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
            "code": "CA",
            "name": "東海道本線",
            "revision": args.revision,
        },
        "origin": {
            "id": "nagoya",
            "stationCode": "JR-CA68",
            "officialStationCode": "CA68",
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
        if internal_code != "JR-CA68":
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

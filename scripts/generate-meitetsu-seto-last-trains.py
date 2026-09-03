#!/usr/bin/env python3
"""Generate Nagoya-city Meitetsu Seto Line last-train boundaries.

Input is layout-preserving text produced by:
    pdftotext -layout <official PDF> <text>

This generator intentionally fails closed if the late-night table shape changes.
The current 2026-03-14 timetable has a final Sakaemachi departure to Kitayama,
which reaches ST02-ST11, while ST12 Omori/Kinjo-gakuin-mae is reached by the
preceding train.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STATIONS = [
    {"code": "ST01", "name": "栄町"},
    {"code": "ST02", "name": "東大手"},
    {"code": "ST03", "name": "清水"},
    {"code": "ST04", "name": "尼ケ坂"},
    {"code": "ST05", "name": "森下"},
    {"code": "ST06", "name": "大曽根"},
    {"code": "ST07", "name": "矢田"},
    {"code": "ST08", "name": "守山自衛隊前"},
    {"code": "ST09", "name": "瓢箪山"},
    {"code": "ST10", "name": "小幡"},
    {"code": "ST11", "name": "喜多山"},
    {"code": "ST12", "name": "大森・金城学院前"},
]

ORIGIN_ID = "sakaemachi"
SOURCE_ID = "meitetsu-seto-line-timetable"


def clock(token: str) -> str:
    digits = token.strip()

    if not re.fullmatch(r"\d{3,4}", digits):
        raise RuntimeError(f"Invalid timetable clock token: {token}")

    if len(digits) == 3:
        hour = int(digits[0])
        minute = int(digits[1:])
    else:
        hour = int(digits[:2])
        minute = int(digits[2:])

    if hour > 23 or minute > 59:
        raise RuntimeError(f"Invalid timetable clock: {token}")

    return f"{hour:02d}:{minute:02d}"


def service_minutes(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    if hour < 4:
        hour += 24
    return hour * 60 + minute


def last_late_block(text: str) -> str:
    matches = list(re.finditer(r"列\s+車\s+番\s+号", text))

    if not matches:
        raise RuntimeError("No train-number block found")

    # Some official PDFs contain an empty repeated form after the real final
    # timetable. Walk backward and choose the last block that actually has
    # multiple Sakaemachi departure times.
    for index in range(len(matches) - 1, -1, -1):
        start = matches[index].start()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )
        block = text[start:end]

        origin_match = re.search(
            r"栄\s+町\s+発\s+([^\n]+)",
            block,
        )
        if not origin_match:
            continue

        origin_tokens = re.findall(
            r"\b\d{3,4}\b",
            origin_match.group(1),
        )

        if len(origin_tokens) >= 2:
            return block

    raise RuntimeError(
        "No populated late-night train-number block found"
    )


def parse_day(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    block = last_late_block(text)

    origin_match = re.search(
        r"栄\s+町\s+発\s+([^\n]+)",
        block,
    )
    if not origin_match:
        raise RuntimeError(f"Sakaemachi departure row not found in {path}")

    origin_tokens = re.findall(r"\b\d{3,4}\b", origin_match.group(1))
    origin_clocks = [clock(token) for token in origin_tokens]

    if len(origin_clocks) < 2:
        raise RuntimeError(
            f"Too few Sakaemachi late departures in {path}: {origin_clocks}"
        )

    header = block[:origin_match.start()]

    # Fail closed if the final train is no longer shown as Kitayama-bound.
    # The station row for Kitayama appears after the Sakaemachi row, so this
    # header check specifically inspects destination/header content.
    if "喜多山" not in header:
        raise RuntimeError(
            f"Final late-train destination is no longer Kitayama in {path}"
        )

    st12_match = re.search(
        r"大森・金城学院前\s+〃\s+([^\n]+)",
        block,
    )
    if not st12_match:
        raise RuntimeError(f"ST12 row not found in {path}")

    st12_tokens = re.findall(r"\b\d{3,4}\b", st12_match.group(1))
    st12_clocks = [clock(token) for token in st12_tokens]

    # Current table: final Kitayama-bound train has no ST12 time, so ST12
    # contains exactly one fewer time than the Sakaemachi departure row.
    if len(st12_clocks) != len(origin_clocks) - 1:
        raise RuntimeError(
            "Unexpected ST12 reachability shape: "
            f"origin={origin_clocks}, st12={st12_clocks}"
        )

    final_departure = origin_clocks[-1]
    st12_departure = origin_clocks[-2]

    if service_minutes(final_departure) <= service_minutes(st12_departure):
        raise RuntimeError(
            f"Late departures are not increasing: "
            f"{st12_departure}, {final_departure}"
        )

    return {
        "through_st11": {
            "lastDeparture": final_departure,
            "trainTerminal": "喜多山",
        },
        "st12": {
            "lastDeparture": st12_departure,
            "trainTerminal": "尾張瀬戸",
        },
        "diagnostics": {
            "originDepartureCount": len(origin_clocks),
            "st12TimeCount": len(st12_clocks),
            "finalOriginDeparture": final_departure,
            "previousOriginDeparture": st12_departure,
            "lastSt12ObservedTime": st12_clocks[-1],
        },
    }


def route(boundary: dict) -> dict:
    return {
        "lastDeparture": boundary["lastDeparture"],
        "lastArrival": None,
        "routeSummary": "名鉄瀬戸線 直通",
        "trainTerminal": boundary["trainTerminal"],
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

    day_data = {
        "weekday": parse_day(args.weekday),
        "saturday_holiday": parse_day(args.holiday),
    }

    result = {
        "schemaVersion": 1,
        "line": {
            "code": "ST",
            "name": "名鉄瀬戸線",
            "revision": args.revision,
        },
        "origin": {
            "id": ORIGIN_ID,
            "stationCode": "ST01",
            "stationName": "栄町",
        },
        "destinations": {},
        "diagnostics": {
            day_type: data["diagnostics"]
            for day_type, data in day_data.items()
        },
    }

    for station in STATIONS:
        target = {
            "name": station["name"],
            "stationCodes": [station["code"]],
            "routes": {},
        }

        if station["code"] != "ST01":
            routes = {}

            for day_type, parsed in day_data.items():
                boundary = (
                    parsed["st12"]
                    if station["code"] == "ST12"
                    else parsed["through_st11"]
                )
                routes[day_type] = route(boundary)

            target["routes"][ORIGIN_ID] = routes

        result["destinations"][station["code"]] = target

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "line": result["line"],
        "diagnostics": result["diagnostics"],
        "ST02": result["destinations"]["ST02"],
        "ST11": result["destinations"]["ST11"],
        "ST12": result["destinations"]["ST12"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

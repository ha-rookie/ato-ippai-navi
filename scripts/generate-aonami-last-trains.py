#!/usr/bin/env python3
"""Generate Aonami Line last-train boundaries from official 2026 PDFs.

The printable timetable does not show an arrival time in the terminal station
row for the temporary 23:58 Inaei-bound train. Therefore this generator uses:
- official layout-PDF text for the late-night table shape, and
- the official AN01 Nagoya station HTML note confirming 23:58 is Inaei-bound.

It fails closed when either source stops matching the verified structure.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

STATIONS = [
    ("AN01", "名古屋"),
    ("AN02", "ささしまライブ"),
    ("AN03", "小本"),
    ("AN04", "荒子"),
    ("AN05", "南荒子"),
    ("AN06", "中島"),
    ("AN07", "港北"),
    ("AN08", "荒子川公園"),
    ("AN09", "稲永"),
    ("AN10", "野跡"),
    ("AN11", "金城ふ頭"),
]

SOURCE_ID = "aonami-official-timetable"


def normalize_clock(value: str) -> str:
    hour_text, minute_text = value.split(":")
    hour = int(hour_text)
    minute = int(minute_text)

    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise RuntimeError(f"Invalid clock: {value}")

    return f"{hour:02d}:{minute:02d}"


def line_for_station(text: str, station_name: str) -> str:
    matches = [
        line
        for line in text.splitlines()
        if re.match(rf"^\s*{re.escape(station_name)}\s+", line)
    ]

    if not matches:
        raise RuntimeError(f"Station row not found: {station_name}")

    # The printable PDF has multiple time blocks. The last row is the
    # late-night block.
    return matches[-1]


def row_clocks(text: str, station_name: str) -> list[str]:
    row = line_for_station(text, station_name)
    return [
        normalize_clock(token)
        for token in re.findall(r"\b\d{1,2}:\d{2}\b", row)
    ]


def html_text(raw: str) -> str:
    stripped = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(stripped))


def validate_terminal_note(raw_html: str) -> None:
    text = html_text(raw_html)

    if "稲永駅行臨時ダイヤ" not in text:
        raise RuntimeError(
            "Official AN01 page no longer confirms the temporary "
            "Inaei-bound final train"
        )

    if "令和8年3月14日改正ダイヤ" not in text:
        raise RuntimeError(
            "Official AN01 page revision is no longer 2026-03-14"
        )

    # The HTML table stores the hour cell ("23") separately from the
    # departure-minute cells ("17 36 58※"), so do not require "23:58"
    # as a contiguous string.
    if not re.search(r"23.{0,160}58", text):
        raise RuntimeError(
            "Official AN01 page no longer contains 58 minutes in the "
            "23-hour timetable row"
        )


def parse_day(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")

    origin = row_clocks(text, "名古屋")
    an08 = row_clocks(text, "荒子川公園")
    an09 = row_clocks(text, "稲永")
    an10 = row_clocks(text, "野跡")
    an11 = row_clocks(text, "金城ふ頭")

    if origin[-2:] != ["23:36", "23:58"]:
        raise RuntimeError(
            f"Unexpected final Nagoya departures: {origin[-4:]}"
        )

    # The 23:58 train is still running at AN08.
    if an08[-1] != "00:12":
        raise RuntimeError(
            f"Unexpected AN08 final row: {an08[-4:]}"
        )

    # The printable PDF does not show the terminal arrival at AN09 for
    # the temporary Inaei-bound train. The last displayed AN09 time is
    # the previous through train.
    if an09[-1] != "23:53":
        raise RuntimeError(
            f"Unexpected AN09 final displayed time: {an09[-4:]}"
        )

    # The previous 23:36 Nagoya departure reaches AN10/AN11.
    if an10[-1] != "23:57":
        raise RuntimeError(
            f"Unexpected AN10 final displayed time: {an10[-4:]}"
        )
    if an11[-1] != "00:00":
        raise RuntimeError(
            f"Unexpected AN11 final displayed time: {an11[-4:]}"
        )

    return {
        "through_inaei": {
            "lastDeparture": origin[-1],
            "trainTerminal": "稲永",
        },
        "through_kinjofuto": {
            "lastDeparture": origin[-2],
            "trainTerminal": "金城ふ頭",
        },
        "diagnostics": {
            "nagoyaFinalDepartures": origin[-4:],
            "an08FinalDisplayedTime": an08[-1],
            "an09FinalDisplayedTime": an09[-1],
            "an10FinalDisplayedTime": an10[-1],
            "an11FinalDisplayedTime": an11[-1],
        },
    }


def route(boundary: dict) -> dict:
    return {
        "lastDeparture": boundary["lastDeparture"],
        "lastArrival": None,
        "routeSummary": "あおなみ線 直通",
        "trainTerminal": boundary["trainTerminal"],
        "transfers": 0,
        "status": "verified",
        "sourceIds": [SOURCE_ID],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekday", required=True, type=Path)
    parser.add_argument("--holiday", required=True, type=Path)
    parser.add_argument("--an01-html", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default="2026-03-14")
    args = parser.parse_args()

    validate_terminal_note(
        args.an01_html.read_text(encoding="utf-8", errors="replace")
    )

    parsed = {
        "weekday": parse_day(args.weekday),
        "saturday_holiday": parse_day(args.holiday),
    }

    result = {
        "schemaVersion": 1,
        "line": {
            "code": "AN",
            "name": "あおなみ線",
            "revision": args.revision,
        },
        "origin": {
            "id": "nagoya",
            "stationCode": "AN01",
            "stationName": "名古屋",
        },
        "destinations": {},
        "diagnostics": {
            day_type: item["diagnostics"]
            for day_type, item in parsed.items()
        },
    }

    for code, name in STATIONS:
        target = {
            "name": name,
            "stationCodes": [code],
            "routes": {},
        }

        if code != "AN01":
            routes = {}

            for day_type, item in parsed.items():
                boundary = (
                    item["through_inaei"]
                    if int(code[2:]) <= 9
                    else item["through_kinjofuto"]
                )
                routes[day_type] = route(boundary)

            target["routes"]["nagoya"] = routes

        result["destinations"][code] = target

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "line": result["line"],
        "diagnostics": result["diagnostics"],
        "AN02": result["destinations"]["AN02"],
        "AN09": result["destinations"]["AN09"],
        "AN10": result["destinations"]["AN10"],
        "AN11": result["destinations"]["AN11"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

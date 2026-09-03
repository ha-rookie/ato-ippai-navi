#!/usr/bin/env python3
"""Generate Nagoya-city Kintetsu Nagoya Line last-train boundaries.

Inputs are the official Kintetsu 00:04 Tomiyoshi-bound train detail pages
for weekday and Saturday/holiday. The generator fails closed if the train
type, destination, stop order, or verified times change.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

SOURCE_ID = "kintetsu-nagoya-official-timetable"

STATIONS = [
    ("KT-E01", "E01", "近鉄名古屋", "00:04"),
    ("KT-E02", "E02", "米野", "00:06"),
    ("KT-E03", "E03", "黄金", "00:07"),
    ("KT-E04", "E04", "烏森", "00:09"),
    ("KT-E05", "E05", "近鉄八田", "00:11"),
    ("KT-E06", "E06", "伏屋", "00:14"),
    ("KT-E07", "E07", "戸田", "00:16"),
]

THROUGH_STATIONS = [
    ("E08", "近鉄蟹江", "00:18"),
    ("E09", "富吉", "00:22"),
]


def decode(path: Path) -> str:
    raw = path.read_bytes()

    for encoding in ("utf-8", "cp932", "shift_jis"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass

    raise RuntimeError(f"Unable to decode {path}")


def plain(source: str) -> str:
    source = re.sub(
        r"<script.*?</script>",
        " ",
        source,
        flags=re.I | re.S,
    )
    source = re.sub(
        r"<style.*?</style>",
        " ",
        source,
        flags=re.I | re.S,
    )
    source = re.sub(r"<[^>]+>", " ", source)

    return re.sub(
        r"\s+",
        " ",
        html.unescape(source),
    ).strip()


def parse_detail(path: Path) -> dict:
    text = plain(decode(path)).replace("：", ":")

    if "普通" not in text:
        raise RuntimeError(f"Final train is no longer local in {path}")

    if "富吉行き" not in text:
        raise RuntimeError(f"Final train is no longer Tomiyoshi-bound in {path}")

    departure_pos = text.find("0:04発")

    if departure_pos < 0:
        raise RuntimeError(f"00:04 departure not found in {path}")

    train_text = text[departure_pos:]

    expected = [
        ("近鉄名古屋", "00:04", "発"),
        ("米野", "00:06", "着"),
        ("黄金", "00:07", "着"),
        ("烏森", "00:09", "着"),
        ("近鉄八田", "00:11", "着"),
        ("伏屋", "00:14", "着"),
        ("戸田", "00:16", "着"),
        ("近鉄蟹江", "00:18", "着"),
        ("富吉", "00:22", "着"),
    ]

    positions = []

    for station, clock, event in expected:
        # Official HTML omits the leading zero from after-midnight hour.
        short_clock = clock[1:] if clock.startswith("00:") else clock

        token = f"{short_clock}{event} {station}"
        position = train_text.find(token)

        if position < 0:
            raise RuntimeError(
                f"Expected token not found in {path}: {token}"
            )

        positions.append(position)

    if positions != sorted(positions):
        raise RuntimeError(
            f"Verified stop sequence changed in {path}: {positions}"
        )

    return {
        "lastDeparture": "00:04",
        "trainTerminal": "富吉",
        "arrivals": {
            internal_code: arrival
            for internal_code, _official, _name, arrival in STATIONS[1:]
        },
    }


def route(arrival: str) -> dict:
    return {
        "lastDeparture": "00:04",
        "lastArrival": arrival,
        "routeSummary": "近鉄名古屋線 普通 直通",
        "trainTerminal": "富吉",
        "transfers": 0,
        "status": "verified",
        "sourceIds": [SOURCE_ID],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekday-detail", required=True, type=Path)
    parser.add_argument("--holiday-detail", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default="2026-03-14")
    args = parser.parse_args()

    parsed = {
        "weekday": parse_detail(args.weekday_detail),
        "saturday_holiday": parse_detail(args.holiday_detail),
    }

    result = {
        "schemaVersion": 1,
        "operator": {
            "id": "kintetsu",
            "name": "近畿日本鉄道",
        },
        "line": {
            "code": "E",
            "name": "近鉄名古屋線",
            "revision": args.revision,
        },
        "origin": {
            "id": "nagoya",
            "stationCode": "KT-E01",
            "officialStationCode": "E01",
            "stationName": "近鉄名古屋",
        },
        "destinations": {},
    }

    for internal_code, official_code, name, arrival in STATIONS:
        target = {
            "operator": "kintetsu",
            "officialStationCode": official_code,
            "name": name,
            "stationCodes": [internal_code],
            "routes": {},
        }

        if internal_code != "KT-E01":
            target["routes"]["nagoya"] = {
                day_type: route(arrival)
                for day_type in parsed
            }

        result["destinations"][internal_code] = target

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

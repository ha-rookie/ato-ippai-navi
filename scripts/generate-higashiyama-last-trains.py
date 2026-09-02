#!/usr/bin/env python3
"""Generate last-reachable direct routes for the Nagoya Higashiyama Line.

Input files are normalized station timetables produced by
scripts/extract-nagoya-subway.py. Runtime code does not consume the full
schedule; this generator reduces it to one boundary record per
origin/destination/day type.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

STATIONS = [
    {"code": "H01", "name": "高畑"},
    {"code": "H02", "name": "八田"},
    {"code": "H03", "name": "岩塚"},
    {"code": "H04", "name": "中村公園"},
    {"code": "H05", "name": "中村日赤"},
    {"code": "H06", "name": "本陣"},
    {"code": "H07", "name": "亀島"},
    {"code": "H08", "name": "名古屋"},
    {"code": "H09", "name": "伏見"},
    {"code": "H10", "name": "栄"},
    {"code": "H11", "name": "新栄町"},
    {"code": "H12", "name": "千種"},
    {"code": "H13", "name": "今池"},
    {"code": "H14", "name": "池下"},
    {"code": "H15", "name": "覚王山"},
    {"code": "H16", "name": "本山"},
    {"code": "H17", "name": "東山公園"},
    {"code": "H18", "name": "星ヶ丘"},
    {"code": "H19", "name": "一社"},
    {"code": "H20", "name": "上社"},
    {"code": "H21", "name": "本郷"},
    {"code": "H22", "name": "藤が丘"},
]

DAY_TYPES = ("weekday", "saturday_holiday")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def station_indexes() -> tuple[dict[str, int], dict[str, int]]:
    by_code = {station["code"]: i for i, station in enumerate(STATIONS)}
    by_name = {station["name"]: i for i, station in enumerate(STATIONS)}
    return by_code, by_name


def parse_origin_spec(value: str) -> dict:
    # originId:originCode:up.json:down.json
    parts = value.split(":", 3)
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "--origin must be originId:originCode:upJson:downJson"
        )

    origin_id, origin_code, up_path, down_path = parts
    return {
        "id": origin_id,
        "code": origin_code,
        "up": Path(up_path),
        "down": Path(down_path),
    }


def train_reaches_target(
    origin_index: int,
    target_index: int,
    terminal_index: int,
) -> bool:
    if target_index > origin_index:
        return terminal_index >= target_index
    if target_index < origin_index:
        return terminal_index <= target_index
    return False


def build_route(
    *,
    origin_index: int,
    target_index: int,
    schedule: list[dict],
    terminal_indexes: dict[str, int],
) -> dict | None:
    candidates = []

    for departure in schedule:
        terminal = departure["destination"]
        terminal_index = terminal_indexes.get(terminal)

        if terminal_index is None:
            continue

        if train_reaches_target(
            origin_index,
            target_index,
            terminal_index,
        ):
            candidates.append(departure)

    if not candidates:
        return None

    last = max(candidates, key=lambda item: item["serviceMinutes"])

    return {
        "lastDeparture": last["time"],
        "lastArrival": None,
        "routeSummary": "東山線 直通",
        "trainTerminal": last["destination"],
        "transfers": 0,
        "status": "verified",
        "sourceIds": ["nagoya-subway-pocket-timetable"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--origin",
        action="append",
        required=True,
        type=parse_origin_spec,
        help="originId:originCode:upJson:downJson",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default="2025-03-29")
    args = parser.parse_args()

    index_by_code, index_by_name = station_indexes()

    normalized = {}
    unknown_destinations = set()

    for spec in args.origin:
        if spec["code"] not in index_by_code:
            raise RuntimeError(f"Unknown origin station code: {spec['code']}")

        up = load_json(spec["up"])
        down = load_json(spec["down"])

        if up["station"]["code"] != spec["code"]:
            raise RuntimeError(
                f"Up timetable station mismatch: {up['station']['code']} != {spec['code']}"
            )
        if down["station"]["code"] != spec["code"]:
            raise RuntimeError(
                f"Down timetable station mismatch: {down['station']['code']} != {spec['code']}"
            )

        for timetable in (up, down):
            for departures in timetable["schedules"].values():
                for departure in departures:
                    if departure["destination"] not in index_by_name:
                        unknown_destinations.add(departure["destination"])

        normalized[spec["id"]] = {
            "spec": spec,
            "up": up,
            "down": down,
        }

    if unknown_destinations:
        raise RuntimeError(
            "Unknown Higashiyama terminal names in timetable: "
            + ", ".join(sorted(unknown_destinations))
        )

    result = {
        "schemaVersion": 1,
        "line": {
            "code": "H",
            "name": "東山線",
            "revision": args.revision,
        },
        "origins": {},
        "destinations": {},
    }

    for origin_id, item in normalized.items():
        spec = item["spec"]
        result["origins"][origin_id] = {
            "stationCode": spec["code"],
            "stationName": STATIONS[index_by_code[spec["code"]]]["name"],
        }

    for target_index, station in enumerate(STATIONS):
        target = {
            "name": station["name"],
            "stationCodes": [station["code"]],
            "routes": {},
        }

        for origin_id, item in normalized.items():
            spec = item["spec"]
            origin_index = index_by_code[spec["code"]]

            if target_index == origin_index:
                continue

            timetable = (
                item["down"]
                if target_index > origin_index
                else item["up"]
            )

            routes = {}
            for day_type in DAY_TYPES:
                route = build_route(
                    origin_index=origin_index,
                    target_index=target_index,
                    schedule=timetable["schedules"][day_type],
                    terminal_indexes=index_by_name,
                )

                if route is None:
                    raise RuntimeError(
                        f"No direct last train for {origin_id} -> "
                        f"{station['code']} {station['name']} ({day_type})"
                    )

                routes[day_type] = route

            target["routes"][origin_id] = routes

        result["destinations"][station["code"]] = target

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = {
        "destinationCount": len(result["destinations"]),
        "originCount": len(result["origins"]),
        "samples": {
            code: result["destinations"][code]
            for code in ("H01", "H03", "H08", "H18", "H22")
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

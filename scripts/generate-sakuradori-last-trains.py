#!/usr/bin/env python3
"""Generate last-reachable direct routes for Nagoya Sakuradori Line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

STATIONS = [
    {"code": "S01", "name": "太閤通"},
    {"code": "S02", "name": "名古屋"},
    {"code": "S03", "name": "国際センター"},
    {"code": "S04", "name": "丸の内"},
    {"code": "S05", "name": "久屋大通"},
    {"code": "S06", "name": "高岳"},
    {"code": "S07", "name": "車道"},
    {"code": "S08", "name": "今池"},
    {"code": "S09", "name": "吹上"},
    {"code": "S10", "name": "御器所"},
    {"code": "S11", "name": "桜山"},
    {"code": "S12", "name": "瑞穂区役所"},
    {"code": "S13", "name": "瑞穂運動場西"},
    {"code": "S14", "name": "新瑞橋"},
    {"code": "S15", "name": "桜本町"},
    {"code": "S16", "name": "鶴里"},
    {"code": "S17", "name": "野並"},
    {"code": "S18", "name": "鳴子北"},
    {"code": "S19", "name": "相生山"},
    {"code": "S20", "name": "神沢"},
    {"code": "S21", "name": "徳重"},
]

DAY_TYPES = ("weekday", "saturday_holiday")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def station_indexes() -> tuple[dict[str, int], dict[str, int]]:
    by_code = {station["code"]: i for i, station in enumerate(STATIONS)}
    by_name = {station["name"]: i for i, station in enumerate(STATIONS)}
    return by_code, by_name


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
        terminal_index = terminal_indexes.get(departure["destination"])

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
        "routeSummary": "桜通線 直通",
        "trainTerminal": last["destination"],
        "transfers": 0,
        "status": "verified",
        "sourceIds": ["nagoya-subway-pocket-timetable-sakuradori"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--origin",
        action="append",
        required=True,
        type=parse_origin_spec,
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default="2023-09-16")
    args = parser.parse_args()

    index_by_code, index_by_name = station_indexes()
    normalized = {}
    unknown_destinations = set()

    for spec in args.origin:
        if spec["code"] not in index_by_code:
            raise RuntimeError(
                f"Unknown Sakuradori origin code: {spec['code']}"
            )

        up = load_json(spec["up"])
        down = load_json(spec["down"])

        for timetable in (up, down):
            if timetable["station"]["code"] != spec["code"]:
                raise RuntimeError(
                    "Timetable station mismatch: "
                    f"{timetable['station']['code']} != {spec['code']}"
                )

            for departures in timetable["schedules"].values():
                for departure in departures:
                    if departure["destination"] not in index_by_name:
                        unknown_destinations.add(
                            departure["destination"]
                        )

        normalized[spec["id"]] = {
            "spec": spec,
            "up": up,
            "down": down,
        }

    if unknown_destinations:
        raise RuntimeError(
            "Unknown Sakuradori terminal names: "
            + ", ".join(sorted(unknown_destinations))
        )

    result = {
        "schemaVersion": 1,
        "line": {
            "code": "S",
            "name": "桜通線",
            "revision": args.revision,
        },
        "origins": {},
        "destinations": {},
    }

    for origin_id, item in normalized.items():
        spec = item["spec"]
        result["origins"][origin_id] = {
            "stationCode": spec["code"],
            "stationName": STATIONS[
                index_by_code[spec["code"]]
            ]["name"],
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
                        f"No direct Sakuradori last train for "
                        f"{origin_id} -> {station['code']} "
                        f"{station['name']} ({day_type})"
                    )

                routes[day_type] = route

            target["routes"][origin_id] = routes

        result["destinations"][station["code"]] = target

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "destinationCount": len(result["destinations"]),
        "originCount": len(result["origins"]),
        "samples": {
            code: result["destinations"][code]
            for code in ("S01", "S02", "S08", "S09", "S17", "S18", "S21")
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

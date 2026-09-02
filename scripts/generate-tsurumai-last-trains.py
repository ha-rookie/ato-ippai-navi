#!/usr/bin/env python3
"""Generate last-reachable direct routes from Fushimi on Nagoya Tsurumai Line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

STATIONS = [
    {"code": "T01", "name": "上小田井"},
    {"code": "T02", "name": "庄内緑地公園"},
    {"code": "T03", "name": "庄内通"},
    {"code": "T04", "name": "浄心"},
    {"code": "T05", "name": "浅間町"},
    {"code": "T06", "name": "丸の内"},
    {"code": "T07", "name": "伏見"},
    {"code": "T08", "name": "大須観音"},
    {"code": "T09", "name": "上前津"},
    {"code": "T10", "name": "鶴舞"},
    {"code": "T11", "name": "荒畑"},
    {"code": "T12", "name": "御器所"},
    {"code": "T13", "name": "川名"},
    {"code": "T14", "name": "いりなか"},
    {"code": "T15", "name": "八事"},
    {"code": "T16", "name": "塩釜口"},
    {"code": "T17", "name": "植田"},
    {"code": "T18", "name": "原"},
    {"code": "T19", "name": "平針"},
    {"code": "T20", "name": "赤池"},
]

DAY_TYPES = ("weekday", "saturday_holiday")
ORIGIN_CODE = "T07"
ORIGIN_ID = "fushimi"

# Through-service terminals beyond the subway endpoints.
TERMINAL_INDEX_OVERRIDES = {
    "岩倉": -1,
    "犬山": -1,
    "扶桑": -1,
    "豊田市": len(STATIONS),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def station_indexes() -> tuple[dict[str, int], dict[str, int]]:
    by_code = {station["code"]: i for i, station in enumerate(STATIONS)}
    by_name = {station["name"]: i for i, station in enumerate(STATIONS)}
    by_name.update(TERMINAL_INDEX_OVERRIDES)
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
        terminal = departure["destination"]
        terminal_index = terminal_indexes.get(terminal)

        if terminal_index is None:
            continue

        if train_reaches_target(origin_index, target_index, terminal_index):
            candidates.append(departure)

    if not candidates:
        return None

    last = max(candidates, key=lambda item: item["serviceMinutes"])

    return {
        "lastDeparture": last["time"],
        "lastArrival": None,
        "routeSummary": "鶴舞線 直通",
        "trainTerminal": last["destination"],
        "transfers": 0,
        "status": "verified",
        "sourceIds": ["nagoya-subway-pocket-timetable-tsurumai"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--up", required=True, type=Path)
    parser.add_argument("--down", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default="2024-03-16")
    args = parser.parse_args()

    index_by_code, terminal_indexes = station_indexes()
    origin_index = index_by_code[ORIGIN_CODE]

    up = load_json(args.up)
    down = load_json(args.down)

    for timetable in (up, down):
        if timetable["station"]["code"] != ORIGIN_CODE:
            raise RuntimeError(
                f"Timetable station mismatch: {timetable['station']['code']} != {ORIGIN_CODE}"
            )

    known_terminals = set(terminal_indexes)
    unknown = set()
    for timetable in (up, down):
        for departures in timetable["schedules"].values():
            for departure in departures:
                if departure["destination"] not in known_terminals:
                    unknown.add(departure["destination"])

    if unknown:
        raise RuntimeError(
            "Unknown Tsurumai terminal names in timetable: "
            + ", ".join(sorted(unknown))
        )

    result = {
        "schemaVersion": 1,
        "line": {
            "code": "T",
            "name": "鶴舞線",
            "revision": args.revision,
        },
        "origins": {
            ORIGIN_ID: {
                "stationCode": ORIGIN_CODE,
                "stationName": "伏見",
            }
        },
        "destinations": {},
    }

    for target_index, station in enumerate(STATIONS):
        target = {
            "name": station["name"],
            "stationCodes": [station["code"]],
            "routes": {},
        }

        if target_index != origin_index:
            timetable = down if target_index > origin_index else up
            routes = {}

            for day_type in DAY_TYPES:
                route = build_route(
                    origin_index=origin_index,
                    target_index=target_index,
                    schedule=timetable["schedules"][day_type],
                    terminal_indexes=terminal_indexes,
                )

                if route is None:
                    raise RuntimeError(
                        f"No direct last train for {ORIGIN_ID} -> "
                        f"{station['code']} {station['name']} ({day_type})"
                    )

                routes[day_type] = route

            target["routes"][ORIGIN_ID] = routes

        result["destinations"][station["code"]] = target

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "destinationCount": len(result["destinations"]),
        "samples": {
            code: result["destinations"][code]
            for code in ("T01", "T04", "T15", "T20")
        }
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

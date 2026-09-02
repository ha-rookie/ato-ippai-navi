#!/usr/bin/env python3
"""Generate last-reachable direct routes from Sakae on Nagoya Meijo Line.

Input files are normalized Sakae M05 timetables produced by
scripts/extract-nagoya-subway.py.

The Meijo Line is circular, so reachability is evaluated by direction-specific
circular distance rather than a simple station-number comparison.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

STATIONS = [
    {"code": "M01", "name": "金山"},
    {"code": "M02", "name": "東別院"},
    {"code": "M03", "name": "上前津"},
    {"code": "M04", "name": "矢場町"},
    {"code": "M05", "name": "栄"},
    {"code": "M06", "name": "久屋大通"},
    {"code": "M07", "name": "名古屋城"},
    {"code": "M08", "name": "名城公園"},
    {"code": "M09", "name": "黒川"},
    {"code": "M10", "name": "志賀本通"},
    {"code": "M11", "name": "平安通"},
    {"code": "M12", "name": "大曽根"},
    {"code": "M13", "name": "ナゴヤドーム前矢田"},
    {"code": "M14", "name": "砂田橋"},
    {"code": "M15", "name": "茶屋ヶ坂"},
    {"code": "M16", "name": "自由ヶ丘"},
    {"code": "M17", "name": "本山"},
    {"code": "M18", "name": "名古屋大学"},
    {"code": "M19", "name": "八事日赤"},
    {"code": "M20", "name": "八事"},
    {"code": "M21", "name": "総合リハビリセンター"},
    {"code": "M22", "name": "瑞穂運動場東"},
    {"code": "M23", "name": "新瑞橋"},
    {"code": "M24", "name": "妙音通"},
    {"code": "M25", "name": "堀田"},
    {"code": "M26", "name": "熱田神宮伝馬町"},
    {"code": "M27", "name": "熱田神宮西"},
    {"code": "M28", "name": "西高蔵"},
]

DAY_TYPES = ("weekday", "saturday_holiday")
ORIGIN_CODE = "M05"
ORIGIN_ID = "sakae"
FULL_LOOP_TERMINALS = {
    "right": "名城線右回り",
    "left": "名城線左回り",
}
ROUTE_LABELS = {
    "right": "名城線 右回り 直通",
    "left": "名城線 左回り 直通",
}

# Some Sakae departures continue from Kanayama onto the Meiko Line.
# For Meijo-destination reachability, those trains cover the left-direction
# arc only as far as M01 Kanayama before leaving the circular line.
EXTERNAL_TERMINAL_CODE_OVERRIDES = {
    "名古屋港": "M01",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def station_indexes() -> tuple[dict[str, int], dict[str, int]]:
    by_code = {station["code"]: i for i, station in enumerate(STATIONS)}
    by_name = {station["name"]: i for i, station in enumerate(STATIONS)}
    return by_code, by_name


def circular_distance(origin_index: int, target_index: int, direction: str) -> int:
    size = len(STATIONS)

    if direction == "right":
        return (target_index - origin_index) % size
    if direction == "left":
        return (origin_index - target_index) % size

    raise ValueError(f"Unknown direction: {direction}")


def train_reaches_target(
    *,
    origin_index: int,
    target_index: int,
    departure: dict,
    direction: str,
    terminal_indexes: dict[str, int],
) -> bool:
    target_distance = circular_distance(origin_index, target_index, direction)

    if target_distance == 0:
        return False

    terminal = departure["destination"]

    if terminal == FULL_LOOP_TERMINALS[direction]:
        # An unmarked circular-service train can reach every other station
        # before returning to Sakae once.
        terminal_distance = len(STATIONS) - 1
    else:
        terminal_index = terminal_indexes.get(terminal)

        if terminal_index is None:
            return False

        terminal_distance = circular_distance(
            origin_index,
            terminal_index,
            direction,
        )

        if terminal_distance == 0:
            return False

    return target_distance <= terminal_distance


def candidate_route(
    *,
    target_index: int,
    direction: str,
    timetable: dict,
    day_type: str,
    origin_index: int,
    terminal_indexes: dict[str, int],
) -> dict | None:
    candidates = [
        departure
        for departure in timetable["schedules"][day_type]
        if train_reaches_target(
            origin_index=origin_index,
            target_index=target_index,
            departure=departure,
            direction=direction,
            terminal_indexes=terminal_indexes,
        )
    ]

    if not candidates:
        return None

    last = max(candidates, key=lambda item: item["serviceMinutes"])

    return {
        "lastDeparture": last["time"],
        "serviceMinutes": last["serviceMinutes"],
        "lastArrival": None,
        "routeSummary": ROUTE_LABELS[direction],
        "trainTerminal": last["destination"],
        "direction": direction,
        "transfers": 0,
        "status": "verified",
        "sourceIds": ["nagoya-subway-pocket-timetable-meijo"],
    }


def build_route(
    *,
    target_index: int,
    right: dict,
    left: dict,
    day_type: str,
    origin_index: int,
    terminal_indexes: dict[str, int],
) -> dict:
    options = []

    for direction, timetable in (("right", right), ("left", left)):
        route = candidate_route(
            target_index=target_index,
            direction=direction,
            timetable=timetable,
            day_type=day_type,
            origin_index=origin_index,
            terminal_indexes=terminal_indexes,
        )

        if route is not None:
            options.append(route)

    if not options:
        station = STATIONS[target_index]
        raise RuntimeError(
            f"No direct Meijo last train for {station['code']} "
            f"{station['name']} ({day_type})"
        )

    selected = max(options, key=lambda item: item["serviceMinutes"])
    selected = dict(selected)
    selected.pop("serviceMinutes")
    return selected


def validate_input(timetable: dict, expected_default_terminal: str) -> None:
    if timetable["station"]["code"] != ORIGIN_CODE:
        raise RuntimeError(
            f"Timetable station mismatch: "
            f"{timetable['station']['code']} != {ORIGIN_CODE}"
        )

    if timetable["defaultTerminal"] != expected_default_terminal:
        raise RuntimeError(
            f"Unexpected default terminal: "
            f"{timetable['defaultTerminal']} != {expected_default_terminal}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--right", required=True, type=Path)
    parser.add_argument("--left", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default="2025-09-29")
    args = parser.parse_args()

    right = load_json(args.right)
    left = load_json(args.left)

    validate_input(right, FULL_LOOP_TERMINALS["right"])
    validate_input(left, FULL_LOOP_TERMINALS["left"])

    index_by_code, terminal_indexes = station_indexes()
    origin_index = index_by_code[ORIGIN_CODE]

    for terminal_name, station_code in EXTERNAL_TERMINAL_CODE_OVERRIDES.items():
        terminal_indexes[terminal_name] = index_by_code[station_code]

    known_terminals = set(terminal_indexes) | set(FULL_LOOP_TERMINALS.values())
    unknown = set()

    for timetable in (right, left):
        for departures in timetable["schedules"].values():
            for departure in departures:
                if departure["destination"] not in known_terminals:
                    unknown.add(departure["destination"])

    if unknown:
        raise RuntimeError(
            "Unknown Meijo terminal names in timetable: "
            + ", ".join(sorted(unknown))
        )

    result = {
        "schemaVersion": 1,
        "line": {
            "code": "M",
            "name": "名城線",
            "revision": args.revision,
        },
        "origins": {
            ORIGIN_ID: {
                "stationCode": ORIGIN_CODE,
                "stationName": "栄",
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

        if station["code"] != ORIGIN_CODE:
            routes = {}

            for day_type in DAY_TYPES:
                routes[day_type] = build_route(
                    target_index=target_index,
                    right=right,
                    left=left,
                    day_type=day_type,
                    origin_index=origin_index,
                    terminal_indexes=terminal_indexes,
                )

            target["routes"][ORIGIN_ID] = routes

        result["destinations"][station["code"]] = target

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    samples = {
        code: result["destinations"][code]
        for code in ("M01", "M06", "M12", "M13", "M14", "M22", "M23", "M28")
    }

    print(json.dumps({
        "destinationCount": len(result["destinations"]),
        "samples": samples,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate last-reachable routes from Sakae to Nagoya Meiko Line.

The generator uses normalized official station timetables:
- Sakae M05, Meijo left direction
- Kanayama M01/E01, southbound combined Meijo/Meiko direction

It does not hard-code Sakae->Kanayama travel time. Instead it matches the
same train at Sakae and Kanayama by terminal and nearby service time.

A transfer is valid only when at least minimum_transfer_lead_minutes remain
between the matched Kanayama time and the Meiko departure.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DAY_TYPES = ("weekday", "saturday_holiday")
ORIGIN_ID = "sakae"
ORIGIN_CODE = "M05"
TRANSFER_CODE = "M01"
TRANSFER_NAME = "金山"

MEIKO_STATIONS = [
    {"code": "E01", "name": "金山"},
    {"code": "E02", "name": "日比野"},
    {"code": "E03", "name": "六番町"},
    {"code": "E04", "name": "東海通"},
    {"code": "E05", "name": "港区役所"},
    {"code": "E06", "name": "築地口"},
    {"code": "E07", "name": "名古屋港"},
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def matching_kanayama_train(
    sakae_departure: dict,
    kanayama_schedule: list[dict],
) -> dict | None:
    """Find the same train at Kanayama using terminal + time proximity."""

    candidates = [
        item
        for item in kanayama_schedule
        if item["destination"] == sakae_departure["destination"]
        and item["serviceMinutes"] > sakae_departure["serviceMinutes"]
        and item["serviceMinutes"] <= sakae_departure["serviceMinutes"] + 15
    ]

    if not candidates:
        return None

    return min(candidates, key=lambda item: item["serviceMinutes"])


def sakae_to_kanayama_pairs(
    sakae_schedule: list[dict],
    kanayama_schedule: list[dict],
) -> list[dict]:
    pairs = []

    for departure in sakae_schedule:
        at_kanayama = matching_kanayama_train(
            departure,
            kanayama_schedule,
        )

        if at_kanayama is None:
            continue

        pairs.append({
            "sakae": departure,
            "kanayama": at_kanayama,
        })

    return pairs


def latest_direct_meiko_from_sakae(pairs: list[dict]) -> dict | None:
    direct = [
        pair
        for pair in pairs
        if pair["sakae"]["destination"] == "名古屋港"
    ]

    if not direct:
        return None

    return max(
        direct,
        key=lambda pair: pair["sakae"]["serviceMinutes"],
    )


def latest_transfer_to_meiko(
    pairs: list[dict],
    kanayama_schedule: list[dict],
    minimum_transfer_lead_minutes: int,
) -> dict | None:
    meiko_departures = [
        item
        for item in kanayama_schedule
        if item["destination"] == "名古屋港"
    ]

    if not meiko_departures:
        return None

    best = None

    for pair in pairs:
        # Direct Meiko trains are considered separately.
        if pair["sakae"]["destination"] == "名古屋港":
            continue

        ready_minutes = (
            pair["kanayama"]["serviceMinutes"]
            + minimum_transfer_lead_minutes
        )

        connections = [
            item
            for item in meiko_departures
            if item["serviceMinutes"] >= ready_minutes
        ]

        if not connections:
            continue

        connection = max(
            connections,
            key=lambda item: item["serviceMinutes"],
        )

        candidate = {
            "pair": pair,
            "connection": connection,
            "transferMarginMinutes":
                connection["serviceMinutes"]
                - pair["kanayama"]["serviceMinutes"],
        }

        if best is None:
            best = candidate
            continue

        if (
            pair["sakae"]["serviceMinutes"]
            > best["pair"]["sakae"]["serviceMinutes"]
        ):
            best = candidate

    return best


def route_for_kanayama(pairs: list[dict]) -> dict:
    latest = max(
        pairs,
        key=lambda pair: pair["sakae"]["serviceMinutes"],
    )

    return {
        "lastDeparture": latest["sakae"]["time"],
        "lastArrival": latest["kanayama"]["time"],
        "routeSummary": "名城線 左回り 直通",
        "trainTerminal": latest["sakae"]["destination"],
        "transfers": 0,
        "status": "verified",
        "sourceIds": [
            "nagoya-subway-pocket-timetable-meijo",
        ],
    }


def route_for_meiko_destination(
    *,
    pairs: list[dict],
    kanayama_schedule: list[dict],
    minimum_transfer_lead_minutes: int,
) -> dict:
    direct = latest_direct_meiko_from_sakae(pairs)
    transfer = latest_transfer_to_meiko(
        pairs,
        kanayama_schedule,
        minimum_transfer_lead_minutes,
    )

    candidates = []

    if direct is not None:
        candidates.append({
            "type": "direct",
            "sakaeServiceMinutes": direct["sakae"]["serviceMinutes"],
            "route": {
                "lastDeparture": direct["sakae"]["time"],
                "lastArrival": None,
                "routeSummary": "名城線・名港線 直通",
                "trainTerminal": "名古屋港",
                "transfers": 0,
                "status": "verified",
                "sourceIds": [
                    "nagoya-subway-pocket-timetable-meijo",
                    "nagoya-subway-pocket-timetable-meiko",
                ],
            },
        })

    if transfer is not None:
        pair = transfer["pair"]
        connection = transfer["connection"]

        candidates.append({
            "type": "transfer",
            "sakaeServiceMinutes": pair["sakae"]["serviceMinutes"],
            "route": {
                "lastDeparture": pair["sakae"]["time"],
                "lastArrival": None,
                "routeSummary": "名城線 左回り → 金山乗換 → 名港線",
                "trainTerminal": pair["sakae"]["destination"],
                "transferAt": TRANSFER_NAME,
                "transferStationCodes": ["M01", "E01"],
                "transferReadyTime": pair["kanayama"]["time"],
                "connectionDeparture": connection["time"],
                "connectionTerminal": "名古屋港",
                "minimumTransferLeadMinutes":
                    minimum_transfer_lead_minutes,
                "transferMarginMinutes":
                    transfer["transferMarginMinutes"],
                "transfers": 1,
                "status": "verified",
                "sourceIds": [
                    "nagoya-subway-pocket-timetable-meijo",
                    "nagoya-subway-pocket-timetable-meiko",
                ],
            },
        })

    if not candidates:
        raise RuntimeError("No reachable Meiko route from Sakae")

    selected = max(
        candidates,
        key=lambda item: item["sakaeServiceMinutes"],
    )

    return selected["route"]


def validate_inputs(
    sakae: dict,
    kanayama_meijo: dict,
    kanayama_meiko: dict,
) -> None:
    if sakae["station"]["code"] != "M05":
        raise RuntimeError("Sakae input must be M05")

    if kanayama_meijo["station"]["code"] != "M01":
        raise RuntimeError("Kanayama Meijo input must be M01")

    if kanayama_meiko["station"]["code"] != "E01":
        raise RuntimeError("Kanayama Meiko input must be E01")

    # M01/E01 is one physical station. The two official ZIPs should expose
    # the same combined southbound departures. Fail closed if they diverge.
    if kanayama_meijo["schedules"] != kanayama_meiko["schedules"]:
        raise RuntimeError(
            "Kanayama M01 and E01 official schedules do not match"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sakae-left", required=True, type=Path)
    parser.add_argument("--kanayama-meijo-down", required=True, type=Path)
    parser.add_argument("--kanayama-meiko-down", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--minimum-transfer-lead-minutes",
        type=int,
        default=1,
    )
    parser.add_argument("--revision", default="2025-09-29")
    args = parser.parse_args()

    if args.minimum_transfer_lead_minutes < 1:
        raise RuntimeError(
            "minimum-transfer-lead-minutes must be at least 1"
        )

    sakae = load_json(args.sakae_left)
    kanayama_meijo = load_json(args.kanayama_meijo_down)
    kanayama_meiko = load_json(args.kanayama_meiko_down)

    validate_inputs(sakae, kanayama_meijo, kanayama_meiko)

    result = {
        "schemaVersion": 1,
        "line": {
            "code": "E",
            "name": "名港線",
            "revision": args.revision,
        },
        "origins": {
            ORIGIN_ID: {
                "stationCode": ORIGIN_CODE,
                "stationName": "栄",
            }
        },
        "transferPolicy": {
            "station": TRANSFER_NAME,
            "stationCodes": ["M01", "E01"],
            "minimumTransferLeadMinutes":
                args.minimum_transfer_lead_minutes,
            "sameMinuteTransferAllowed": False,
        },
        "destinations": {},
    }

    for day_type in DAY_TYPES:
        pairs = sakae_to_kanayama_pairs(
            sakae["schedules"][day_type],
            kanayama_meijo["schedules"][day_type],
        )

        if not pairs:
            raise RuntimeError(
                f"No Sakae->Kanayama train pairs for {day_type}"
            )

        kanayama_route = route_for_kanayama(pairs)
        meiko_route = route_for_meiko_destination(
            pairs=pairs,
            kanayama_schedule=kanayama_meijo["schedules"][day_type],
            minimum_transfer_lead_minutes=
                args.minimum_transfer_lead_minutes,
        )

        for station in MEIKO_STATIONS:
            target = result["destinations"].setdefault(
                station["code"],
                {
                    "name": station["name"],
                    "stationCodes": [station["code"]],
                    "routes": {ORIGIN_ID: {}},
                },
            )

            target["routes"][ORIGIN_ID][day_type] = (
                kanayama_route
                if station["code"] == "E01"
                else meiko_route
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "transferPolicy": result["transferPolicy"],
        "E01": result["destinations"]["E01"],
        "E02": result["destinations"]["E02"],
        "E07": result["destinations"]["E07"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

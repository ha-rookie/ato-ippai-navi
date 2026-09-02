#!/usr/bin/env python3
"""Generate the safe last-train boundary from Sakae to Kamiida K01."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DAY_TYPES = ("weekday", "saturday_holiday")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def matched_pairs(
    sakae_schedule: list[dict],
    heiandori_schedule: list[dict],
) -> list[tuple[dict, dict]]:
    pairs = []

    for departure in sakae_schedule:
        candidates = [
            item
            for item in heiandori_schedule
            if item["destination"] == departure["destination"]
            and item["serviceMinutes"] > departure["serviceMinutes"]
            and item["serviceMinutes"] <= departure["serviceMinutes"] + 20
        ]

        if not candidates:
            continue

        at_heiandori = min(
            candidates,
            key=lambda item: item["serviceMinutes"],
        )
        pairs.append((departure, at_heiandori))

    return pairs


def latest_safe_connection(
    *,
    pairs: list[tuple[dict, dict]],
    kamiida_departures: list[dict],
    minimum_transfer_lead_minutes: int,
) -> dict:
    feasible = []

    for departure, at_heiandori in pairs:
        connections = [
            item
            for item in kamiida_departures
            if item["serviceMinutes"]
            >= at_heiandori["serviceMinutes"]
            + minimum_transfer_lead_minutes
        ]

        if not connections:
            continue

        connection = max(
            connections,
            key=lambda item: item["serviceMinutes"],
        )

        feasible.append({
            "sakae": departure,
            "heiandori": at_heiandori,
            "connection": connection,
            "transferMarginMinutes":
                connection["serviceMinutes"]
                - at_heiandori["serviceMinutes"],
        })

    if not feasible:
        raise RuntimeError("No safe Sakae -> Kamiida connection found")

    return max(
        feasible,
        key=lambda item: item["sakae"]["serviceMinutes"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sakae-right", required=True, type=Path)
    parser.add_argument("--heiandori-right", required=True, type=Path)
    parser.add_argument("--heiandori-kamiida", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--minimum-transfer-lead-minutes",
        type=int,
        default=3,
    )
    parser.add_argument("--revision-meijo", default="2025-09-29")
    parser.add_argument("--revision-kamiida", default="2024-03-16")
    parser.add_argument("--last-arrival", default="00:29")
    args = parser.parse_args()

    if args.minimum_transfer_lead_minutes < 1:
        raise RuntimeError(
            "minimum-transfer-lead-minutes must be at least 1"
        )

    sakae = load_json(args.sakae_right)
    heiandori = load_json(args.heiandori_right)
    kamiida = load_json(args.heiandori_kamiida)

    if sakae["station"]["code"] != "M05":
        raise RuntimeError("Sakae input must be M05")
    if heiandori["station"]["code"] != "M11":
        raise RuntimeError("Heiandori Meijo input must be M11")
    if kamiida["station"]["code"] != "K02":
        raise RuntimeError("Heiandori Kamiida input must be K02")

    result = {
        "schemaVersion": 1,
        "line": {
            "code": "K",
            "name": "上飯田線",
            "revision": args.revision_kamiida,
        },
        "policy": {
            "minimumTransferLeadMinutes":
                args.minimum_transfer_lead_minutes,
            "transferAt": "平安通",
            "note":
                "名城線ホーム地下2階から上飯田線ホーム地下4階へ移動するため、"
                "公式乗換所要時間ではなくプロダクト安全マージン3分を採用",
        },
        "destinations": {
            "K01": {
                "name": "上飯田",
                "stationCodes": ["K01"],
                "routes": {
                    "sakae": {}
                },
            }
        },
    }

    for day_type in DAY_TYPES:
        pairs = matched_pairs(
            sakae["schedules"][day_type],
            heiandori["schedules"][day_type],
        )

        selected = latest_safe_connection(
            pairs=pairs,
            kamiida_departures=kamiida["schedules"][day_type],
            minimum_transfer_lead_minutes=
                args.minimum_transfer_lead_minutes,
        )

        route = {
            "lastDeparture": selected["sakae"]["time"],
            "lastArrival": args.last_arrival,
            "routeSummary":
                "名城線 右回り → 平安通乗換 → 上飯田線",
            "trainTerminal": selected["sakae"]["destination"],
            "transferAt": "平安通",
            "transferStationCodes": ["M11", "K02"],
            "transferReadyTime": selected["heiandori"]["time"],
            "connectionDeparture": selected["connection"]["time"],
            "connectionTerminal": selected["connection"]["destination"],
            "minimumTransferLeadMinutes":
                args.minimum_transfer_lead_minutes,
            "transferMarginMinutes":
                selected["transferMarginMinutes"],
            "transfers": 1,
            "status": "verified",
            "sourceIds": [
                "nagoya-subway-pocket-timetable-meijo",
                "nagoya-subway-pocket-timetable-kamiida",
                "nagoya-subway-first-last-kamiida",
            ],
        }

        result["destinations"]["K01"]["routes"]["sakae"][day_type] = route

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

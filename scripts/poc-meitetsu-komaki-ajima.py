#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ORIGIN = {"code": "M05", "name": "栄"}
TRANSFER = {"code": "M11/K02", "name": "平安通"}
DESTINATION = {"code": "KM12", "name": "味鋺", "nodeId": "00008545"}
DIRECT_ORIGIN = {"code": "M11", "name": "平安通", "nodeId": "00008059"}
DAY_TYPES = ("weekday", "saturday_holiday")
MINIMUM_TRANSFER_LEAD_MINUTES = 3


def decode(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "cp932", "shift_jis"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise RuntimeError(f"Unable to decode {path}")


def plain(fragment: str) -> str:
    fragment = re.sub(r"<script.*?</script>", " ", fragment, flags=re.I | re.S)
    fragment = re.sub(r"<style.*?</style>", " ", fragment, flags=re.I | re.S)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def extract_spans(block: str, class_name: str) -> list[str]:
    values: list[str] = []
    pattern = rf'<span[^>]*class="[^"]*\b{re.escape(class_name)}\b[^"]*"[^>]*>(.*?)</span>'
    for match in re.finditer(pattern, block, flags=re.I | re.S):
        value = plain(match.group(1))
        if value and value not in values:
            values.append(value)
    return values


def extract_visible_clocks(block: str) -> list[str]:
    clocks: list[str] = []
    for value in re.findall(
        r'<span[^>]*aria-hidden="true"[^>]*>\s*(\d{1,2}:\d{2})\s*</span>',
        block,
        flags=re.I | re.S,
    ):
        value = value.zfill(5)
        if value not in clocks:
            clocks.append(value)
    return clocks


def service_minutes(clock: str) -> int:
    hour, minute = map(int, clock.split(":"))
    value = hour * 60 + minute
    return value + (24 * 60 if hour < 4 else 0)


def parse_direct_services(path: Path) -> dict[str, object]:
    source = decode(path)
    text = plain(source)
    identity = {
        "originPresent": DIRECT_ORIGIN["name"] in text,
        "destinationPresent": DESTINATION["name"] in text,
        "directTimetableMarkerPresent": "乗換なし時刻表" in text,
    }
    if not identity["originPresent"] or not identity["destinationPresent"]:
        print(text[-9000:], file=sys.stderr)
        raise AssertionError(f"unexpected Meitetsu page identity: {identity}")

    blocks = re.findall(
        r'<ul[^>]*class="[^"]*\btime-detail\b[^"]*"[^>]*>(.*?)</ul>',
        source,
        flags=re.I | re.S,
    )
    services: list[dict[str, object]] = []
    for index, block in enumerate(blocks):
        clocks = extract_visible_clocks(block)
        if len(clocks) < 2:
            continue
        row = {
            "rowIndex": index,
            "departure": clocks[0],
            "arrival": clocks[-1],
            "clockTimes": clocks,
            "routeNames": extract_spans(block, "route-name"),
            "terminals": extract_spans(block, "destination"),
            "plainText": plain(block),
        }
        services.append(row)

    services.sort(key=lambda row: service_minutes(str(row["departure"])))
    if not services:
        raise AssertionError("no direct Heian-dori -> Ajima services parsed")
    return {"identity": identity, "services": services}


def match_sakae_to_heiandori(sakae_path: Path, heiandori_path: Path, day_type: str) -> list[dict[str, object]]:
    sakae = json.loads(sakae_path.read_text(encoding="utf-8"))
    heiandori = json.loads(heiandori_path.read_text(encoding="utf-8"))
    pairs: list[dict[str, object]] = []

    for departure in sakae["schedules"][day_type]:
        candidates = [
            item
            for item in heiandori["schedules"][day_type]
            if item["destination"] == departure["destination"]
            and item["serviceMinutes"] > departure["serviceMinutes"]
            and item["serviceMinutes"] <= departure["serviceMinutes"] + 20
        ]
        if not candidates:
            continue
        arrival = min(candidates, key=lambda item: item["serviceMinutes"])
        pairs.append({
            "sakaeDeparture": departure["time"],
            "sakaeServiceMinutes": departure["serviceMinutes"],
            "heiandoriArrival": arrival["time"],
            "heiandoriServiceMinutes": arrival["serviceMinutes"],
            "terminal": departure["destination"],
            "travelMinutes": arrival["serviceMinutes"] - departure["serviceMinutes"],
        })
    return pairs


def main() -> None:
    result: dict[str, object] = {
        "origin": ORIGIN,
        "transfer": TRANSFER,
        "directOrigin": DIRECT_ORIGIN,
        "destination": DESTINATION,
        "minimumTransferLeadMinutes": MINIMUM_TRANSFER_LEAD_MINUTES,
        "verificationStrategy": (
            "Nagoya City official open-data for Sakae -> Heian-dori plus Meitetsu "
            "official destination-specific no-transfer timetable for Heian-dori -> Ajima"
        ),
        "days": {},
    }

    for day_type in DAY_TYPES:
        direct = parse_direct_services(Path(f"/tmp/meitetsu-ajima-direct-{day_type}.html"))
        last_direct = direct["services"][-1]
        # Current official station timetable says the last Ajima-capable service is 00:06 Komaki-bound;
        # a later 00:28 service terminates at Kamiida and must not be treated as Ajima-capable.
        if last_direct["departure"] != "00:06":
            raise AssertionError(
                f"{day_type}: expected current last direct Heian-dori -> Ajima departure 00:06, "
                f"got {last_direct['departure']}"
            )

        connection_minutes = service_minutes(str(last_direct["departure"]))
        pairs = match_sakae_to_heiandori(
            Path("/tmp/sakae-right.json"),
            Path("/tmp/heiandori-right.json"),
            day_type,
        )
        feasible = [
            pair
            for pair in pairs
            if connection_minutes - int(pair["heiandoriServiceMinutes"])
            >= MINIMUM_TRANSFER_LEAD_MINUTES
        ]
        if not feasible:
            raise AssertionError(
                f"{day_type}: no Sakae feeder reaches Heian-dori >= {MINIMUM_TRANSFER_LEAD_MINUTES} min before 00:06"
            )
        feeder = max(feasible, key=lambda pair: int(pair["sakaeServiceMinutes"]))
        margin = connection_minutes - int(feeder["heiandoriServiceMinutes"])

        result["days"][day_type] = {
            "directIdentity": direct["identity"],
            "directServiceCount": len(direct["services"]),
            "lastThreeDirectServices": direct["services"][-3:],
            "boundary": {
                "lastDeparture": feeder["sakaeDeparture"],
                "transferReadyTime": feeder["heiandoriArrival"],
                "connectionDeparture": last_direct["departure"],
                "lastArrival": last_direct["arrival"],
                "transferAt": "平安通",
                "minimumTransferLeadMinutes": MINIMUM_TRANSFER_LEAD_MINUTES,
                "transferMarginMinutes": margin,
                "feeder": feeder,
                "direct": last_direct,
            },
            "lastFiveFeasibleFeeders": feasible[-5:],
        }

    output = Path("/tmp/meitetsu-komaki-ajima-poc.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Meitetsu Komaki KM12 Ajima boundary PoC: OK")
    for day_type in DAY_TYPES:
        b = result["days"][day_type]["boundary"]
        print(
            f"{day_type}: Sakae {b['lastDeparture']} -> Heian-dori {b['transferReadyTime']} / "
            f"direct {b['connectionDeparture']} -> Ajima {b['lastArrival']} / "
            f"margin={b['transferMarginMinutes']} min"
        )


if __name__ == "__main__":
    main()

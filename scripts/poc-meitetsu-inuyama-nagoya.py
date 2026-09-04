#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

STATIONS = {
    "IY02": ("中小田井", "00006073"),
    "IY03": ("上小田井", "00003971"),
}


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
    pattern = rf'<span[^>]*class="{re.escape(class_name)}"[^>]*>(.*?)</span>'
    for match in re.finditer(pattern, block, flags=re.I | re.S):
        value = plain(match.group(1))
        if value and value not in values:
            values.append(value)
    return values


def extract_time(block: str, wrapper_class: str) -> str | None:
    wrapper = re.search(
        rf'<span[^>]*class="{re.escape(wrapper_class)}"[^>]*>(.*?)</span>\s*'
        rf'<span[^>]*class="time-sub-',
        block,
        flags=re.I | re.S,
    )
    fragment = wrapper.group(1) if wrapper else block
    match = re.search(
        r'<span[^>]*aria-hidden="true"[^>]*>\s*(\d{1,2}:\d{2})\s*</span>',
        fragment,
        flags=re.I | re.S,
    )
    return match.group(1).zfill(5) if match else None


def parse_classes(route_names: list[str]) -> list[str]:
    classes: list[str] = []
    for route_name in route_names:
        match = re.search(r"\(([^)]+)\)\s*$", route_name)
        if match and match.group(1) not in classes:
            classes.append(match.group(1))
    return classes


def parse_direct_tail(path: Path, destination: str) -> dict[str, object]:
    source = decode(path)
    text = plain(source)
    identity = {
        "originPresent": "名鉄名古屋" in text,
        "destinationPresent": destination in text,
        "directTimetableMarkerPresent": "乗換なし時刻表" in text,
        "looksLikeRouteSelector": "路線を選択してください" in text,
    }
    if not all(
        identity[key]
        for key in ("originPresent", "destinationPresent", "directTimetableMarkerPresent")
    ):
        print(f"==== unexpected direct page: {path} ====", file=sys.stderr)
        print(text[-7000:], file=sys.stderr)
        raise AssertionError(f"unexpected direct timetable page: {path}; identity={identity}")

    blocks = re.findall(
        r'<ul[^>]*class="time-detail"[^>]*>(.*?)</ul>',
        source,
        flags=re.I | re.S,
    )
    services: list[dict[str, object]] = []
    for index, block in enumerate(blocks):
        dep = extract_time(block, "time-deptime")
        arr = extract_time(block, "time-arrtime")
        route_names = extract_spans(block, "route-name")
        terminals = extract_spans(block, "destination")
        if not dep or not arr or not route_names or not terminals:
            continue
        services.append(
            {
                "rowIndex": index,
                "lastDeparture": dep,
                "lastArrival": arr,
                "routeNames": route_names,
                "trainClasses": parse_classes(route_names),
                "trainTerminal": terminals[-1],
                "terminalsSeen": terminals,
                "plainText": plain(block),
            }
        )

    if not services:
        diagnostic = {
            "identity": identity,
            "timeDetailBlockCount": len(blocks),
            "plainTail": text[-7000:],
        }
        Path(f"/tmp/{path.stem}-diagnostics.json").write_text(
            json.dumps(diagnostic, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise AssertionError(f"no direct service rows parsed: {path}")

    last = dict(services[-1])
    last["matchedServiceCount"] = len(services)
    last["parser"] = "time-detail-html-generic-route"
    return last


def main() -> None:
    output: dict[str, object] = {
        "source": "Meitetsu official DepArrTimeList",
        "origin": {"code": "NH36", "name": "名鉄名古屋", "nodeId": "00004372"},
        "destinations": {},
    }
    diagnostics: dict[str, object] = {}

    for code, (name, node_id) in STATIONS.items():
        destination_record: dict[str, object] = {
            "name": name,
            "officialStationCode": code,
            "officialNodeId": node_id,
            "routes": {},
        }
        route_diagnostics: dict[str, object] = {}

        for day_type in ("weekday", "saturday_holiday"):
            path = Path(f"/tmp/meitetsu-inuyama-{code}-{day_type}.html")
            route = parse_direct_tail(path, name)
            destination_record["routes"][day_type] = route
            route_diagnostics[day_type] = {
                "routeNames": route["routeNames"],
                "trainClasses": route["trainClasses"],
                "trainTerminal": route["trainTerminal"],
                "plainText": route["plainText"],
            }

        output["destinations"][code] = destination_record
        diagnostics[code] = route_diagnostics

    Path("/tmp/meitetsu-inuyama-last-trains.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path("/tmp/meitetsu-inuyama-route-diagnostics.json").write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Meitetsu Inuyama IY02-IY03 destination-specific PoC: OK")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

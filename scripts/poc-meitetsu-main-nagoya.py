#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

STATIONS = {
    "NH24": ("中京競馬場前", "00006039"),
    "NH25": ("有松", "00008842"),
    "NH26": ("左京山", "00002805"),
    "NH27": ("鳴海", "00008608"),
    "NH28": ("本星崎", "00008474"),
    "NH29": ("本笠寺", "00008447"),
    "NH30": ("桜", "00002879"),
    "NH31": ("呼続", "00002182"),
    "NH32": ("堀田", "00008437"),
    "NH33": ("神宮前", "00004438"),
    "NH34": ("金山", "00001879"),
    "NH35": ("山王", "00000095"),
    "NH36": ("名鉄名古屋", "00004372"),
    "NH37": ("栄生", "00000654"),
    "NH38": ("東枇杷島", "00006826"),
}

DAY_TYPES = {
    "weekday": "2026-09-04",
    "saturday_holiday": "2026-09-05",
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


def find_node_candidates(source: str, station_name: str) -> list[str]:
    candidates: list[str] = []
    for match in re.finditer(re.escape(station_name), source):
        left = max(0, match.start() - 700)
        right = min(len(source), match.end() + 700)
        window = html.unescape(source[left:right])
        for node in re.findall(r"(?<!\d)(\d{8})(?!\d)", window):
            if node not in candidates:
                candidates.append(node)
    return candidates


def inspect_origin_timetable(path: Path) -> dict[str, object]:
    text = plain(decode(path))
    identity_ok = (
        "名鉄名古屋" in text
        and "NH36" in text
        and "名古屋本線" in text
        and "東岡崎・豊橋方面" in text
    )
    late_rows_visible = bool(
        re.search(r"23\s+.*?57", text)
        and re.search(r"00\s+.*?01.*?06", text)
    )

    diagnostic = {
        "identityOk": identity_ok,
        "lateRowsVisible": late_rows_visible,
        "staticPageLooksLikeRouteSelector": "路線を選択してください" in text,
        "plainTextTail": text[-2500:],
    }
    Path("/tmp/meitetsu-main-origin-diagnostics.json").write_text(
        json.dumps(diagnostic, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not identity_ok:
        print(text[:5000], file=sys.stderr)
        raise AssertionError(f"unexpected NH36 timetable page: {path}")

    if not late_rows_visible:
        print(
            "NOTE: NH36 TrainDiagram returned route-selection HTML; "
            "keeping it as a non-blocking secondary diagnostic.",
            file=sys.stderr,
        )
    return diagnostic


def extract_span(block: str, class_name: str) -> str | None:
    match = re.search(
        rf'<span[^>]*class="{re.escape(class_name)}"[^>]*>(.*?)</span>',
        block,
        flags=re.I | re.S,
    )
    if not match:
        return None
    return plain(match.group(1))


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


def parse_direct_tail(path: Path, origin: str, destination: str) -> dict[str, object]:
    source = decode(path)
    text = plain(source)
    identity = {
        "originPresent": origin in text,
        "destinationPresent": destination in text,
        "directTimetableMarkerPresent": "乗換なし時刻表" in text,
        "looksLikeRouteSelector": "路線を選択してください" in text,
    }
    if not all(
        identity[key]
        for key in (
            "originPresent",
            "destinationPresent",
            "directTimetableMarkerPresent",
        )
    ):
        print(f"==== unexpected direct page: {path} ====", file=sys.stderr)
        print(text[:3500], file=sys.stderr)
        print("==== tail ====", file=sys.stderr)
        print(text[-7000:], file=sys.stderr)
        raise AssertionError(
            f"unexpected direct timetable page: {path}; identity={identity}"
        )

    blocks = re.findall(
        r'<ul[^>]*class="time-detail"[^>]*>(.*?)</ul>',
        source,
        flags=re.I | re.S,
    )
    services: list[dict[str, str]] = []
    for block in blocks:
        dep = extract_time(block, "time-deptime")
        arr = extract_time(block, "time-arrtime")
        route_name = extract_span(block, "route-name")
        terminal = extract_span(block, "destination")
        if not all((dep, arr, route_name, terminal)):
            continue
        route_match = re.fullmatch(r"名古屋本線\(([^)]+)\)", route_name)
        if not route_match:
            continue
        services.append(
            {
                "lastDeparture": dep,
                "lastArrival": arr,
                "trainClass": route_match.group(1),
                "trainTerminal": terminal,
            }
        )

    if not services:
        diagnostic_path = Path(f"/tmp/{path.stem}-diagnostics.json")
        diagnostic_path.write_text(
            json.dumps(
                {
                    "identity": identity,
                    "timeDetailBlockCount": len(blocks),
                    "plainTail": text[-7000:],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"==== direct plain tail: {path} ====", file=sys.stderr)
        print(text[-7000:], file=sys.stderr)
        raise AssertionError(f"no direct service rows parsed: {path}")

    last = dict(services[-1])
    last["matchedServiceCount"] = len(services)
    last["parser"] = "time-detail-html"
    return last


def main() -> None:
    top_path = Path("/tmp/meitetsu-direct-top.html")
    origin_path = Path("/tmp/meitetsu-nagoya-main-east.html")
    if not top_path.exists() or not origin_path.exists():
        raise SystemExit("official source files are missing")

    top = decode(top_path)
    top_text = plain(top)
    discovery: dict[str, dict[str, object]] = {}
    for code, (name, node_id) in STATIONS.items():
        discovery[code] = {
            "name": name,
            "namePresentInStaticTop": name in top_text,
            "nodeCandidates": find_node_candidates(top, name),
            "officialNodeId": node_id,
        }

    Path("/tmp/meitetsu-main-node-discovery.json").write_text(
        json.dumps(discovery, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    origin_diagnostic = inspect_origin_timetable(origin_path)
    print("NH36 origin diagnostic:")
    print(json.dumps(origin_diagnostic, ensure_ascii=False, indent=2))

    output: dict[str, object] = {
        "source": "Meitetsu official DepArrTimeList",
        "origin": {"code": "NH36", "name": "名鉄名古屋", "nodeId": "00004372"},
        "serviceDates": DAY_TYPES,
        "destinations": {},
    }

    for code, (name, node_id) in STATIONS.items():
        destination_record: dict[str, object] = {
            "name": name,
            "officialStationCode": code,
            "officialNodeId": node_id,
            "routes": {},
        }
        if code == "NH36":
            destination_record["walkHome"] = True
            output["destinations"][code] = destination_record
            continue

        routes = destination_record["routes"]
        assert isinstance(routes, dict)
        for day_type in DAY_TYPES:
            path = Path(f"/tmp/meitetsu-direct-{code}-{day_type}.html")
            routes[day_type] = parse_direct_tail(path, "名鉄名古屋", name)

        output["destinations"][code] = destination_record

    Path("/tmp/meitetsu-main-last-trains.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Meitetsu Main Line NH24-NH38 destination-specific PoC: OK")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

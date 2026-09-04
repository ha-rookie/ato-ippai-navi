#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ORIGIN = {"code": "NH36", "name": "名鉄名古屋", "nodeId": "00004372"}
TRANSFER = {"code": "TA03", "name": "大江", "nodeId": "00005590"}
DESTINATION = {"code": "CH01", "name": "東名古屋港", "nodeId": "00006856"}
DAY_TYPES = ("weekday", "saturday_holiday")


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


def parse_rows(path: Path, expected_origin: str, expected_destination: str) -> dict[str, object]:
    source = decode(path)
    text = plain(source)
    identity = {
        "originPresent": expected_origin in text,
        "destinationPresent": expected_destination in text,
        "directTimetableMarkerPresent": "乗換なし時刻表" in text,
        "transferMarkerPresent": "乗換" in text,
        "routeSelectorPresent": "路線を選択してください" in text,
    }

    if not identity["originPresent"] or not identity["destinationPresent"]:
        print(f"==== unexpected page identity: {path} ====", file=sys.stderr)
        print(text[-9000:], file=sys.stderr)
        raise AssertionError(f"unexpected identity for {path}: {identity}")

    blocks = re.findall(
        r'<ul[^>]*class="[^"]*\btime-detail\b[^"]*"[^>]*>(.*?)</ul>',
        source,
        flags=re.I | re.S,
    )
    rows: list[dict[str, object]] = []
    for index, block in enumerate(blocks):
        clocks = extract_visible_clocks(block)
        route_names = extract_spans(block, "route-name")
        terminals = extract_spans(block, "destination")
        row = {
            "rowIndex": index,
            "clockTimes": clocks,
            "routeNames": route_names,
            "terminals": terminals,
            "mentionsOe": "大江" in plain(block),
            "mentionsChikko": "築港線" in plain(block),
            "plainText": plain(block),
        }
        if clocks or route_names or terminals:
            rows.append(row)

    return {
        "identity": identity,
        "timeDetailBlockCount": len(blocks),
        "parsedRowCount": len(rows),
        "rows": rows,
        "plainTail": text[-5000:],
    }


def service_minutes(clock: str) -> int:
    hour, minute = map(int, clock.split(":"))
    value = hour * 60 + minute
    return value + (24 * 60 if hour < 4 else 0)


def direct_services(
    path: Path,
    origin: str,
    destination: str,
    required_route_prefix: str | None = None,
) -> list[dict[str, object]]:
    parsed = parse_rows(path, origin, destination)
    services: list[dict[str, object]] = []
    for row in parsed["rows"]:
        clocks = row["clockTimes"]
        if len(clocks) < 2:
            continue
        route_names = row["routeNames"]
        if required_route_prefix and not any(
            name.startswith(required_route_prefix) for name in route_names
        ):
            continue
        services.append(
            {
                **row,
                "departure": clocks[0],
                "arrival": clocks[-1],
            }
        )
    services.sort(key=lambda row: service_minutes(str(row["departure"])))
    return services


def inspect_static_timetable(path: Path) -> dict[str, object]:
    text = plain(decode(path))
    identity_ok = all(term in text for term in ("大江", "TA03", "築港線", "東名古屋港"))
    if not identity_ok:
        raise AssertionError(f"unexpected Oe Chikko timetable page: {path}")
    return {
        "identityOk": True,
        "containsIrregularNotice": "臨時列車" in text,
        "containsOperationDateNotice": "運転日" in text,
        "plainTextTail": text[-7000:],
    }


def inspect_solver(path: Path) -> dict[str, object]:
    text = plain(decode(path))
    clocks = re.findall(r"(?<!\d)(\d{1,2}:\d{2})(?!\d)", text)
    normalized: list[str] = []
    for value in clocks:
        value = value.zfill(5)
        if value not in normalized:
            normalized.append(value)
    return {
        "originPresent": ORIGIN["name"] in text,
        "transferPresent": TRANSFER["name"] in text,
        "destinationPresent": DESTINATION["name"] in text,
        "routeFound": "到達可能な経路が見つかりませんでした" not in text,
        "transferOnePresent": "乗換:1回" in text or "乗換：1回" in text,
        "clocks": normalized,
        "plainHead": text[:6000],
        "plainTail": text[-6000:],
    }


def main() -> None:
    result: dict[str, object] = {
        "origin": ORIGIN,
        "transfer": TRANSFER,
        "destination": DESTINATION,
        "days": {},
        "staticTimetable": inspect_static_timetable(Path("/tmp/meitetsu-chikko-oe-timetable.html")),
    }

    for day_type in DAY_TYPES:
        through_path = Path(f"/tmp/meitetsu-chikko-through-{day_type}.html")
        shuttle_path = Path(f"/tmp/meitetsu-chikko-shuttle-{day_type}.html")
        feeder_path = Path(f"/tmp/meitetsu-chikko-feeder-{day_type}.html")

        through = parse_rows(through_path, ORIGIN["name"], DESTINATION["name"])
        shuttles = direct_services(
            shuttle_path,
            TRANSFER["name"],
            DESTINATION["name"],
            "築港線(",
        )
        feeders = direct_services(
            feeder_path,
            ORIGIN["name"],
            TRANSFER["name"],
        )
        if not shuttles:
            raise AssertionError(f"no Oe -> Higashi-Nagoyako shuttle rows: {day_type}")
        if not feeders:
            raise AssertionError(f"no Nagoya -> Oe feeder rows: {day_type}")

        last_shuttle = shuttles[-1]
        shuttle_departure_minutes = service_minutes(str(last_shuttle["departure"]))
        feeder_candidates: list[dict[str, object]] = []
        for feeder in feeders:
            margin = shuttle_departure_minutes - service_minutes(str(feeder["arrival"]))
            if margin < 0:
                continue
            feeder_candidates.append({**feeder, "rawTransferMarginMinutes": margin})

        feeder_candidates.sort(
            key=lambda row: service_minutes(str(row["departure"]))
        )

        solver_path = Path(f"/tmp/meitetsu-chikko-solver-{day_type}.html")
        solver = inspect_solver(solver_path) if solver_path.exists() else None

        result["days"][day_type] = {
            "throughSearch": through,
            "shuttleServiceCount": len(shuttles),
            "lastShuttle": last_shuttle,
            "shuttleServices": shuttles,
            "feederServiceCount": len(feeders),
            "lastFeederBeforeShuttle": feeder_candidates[-1] if feeder_candidates else None,
            "feederCandidates": feeder_candidates[-5:],
            "solver": solver,
        }

    Path("/tmp/meitetsu-chikko-transfer-poc.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Meitetsu Chikko CH01 transfer structure PoC: OK")
    for day_type in DAY_TYPES:
        day = result["days"][day_type]
        last = day["lastShuttle"]
        print(
            f"{day_type}: Oe shuttle last parsed {last['departure']}->{last['arrival']} "
            f"routes={last['routeNames']} terminals={last['terminals']}"
        )
        feeder = day["lastFeederBeforeShuttle"]
        print(f"{day_type}: latest feeder candidate before shuttle={feeder}")
        through = day["throughSearch"]
        print(
            f"{day_type}: NH36->CH01 DepArrTimeList blocks={through['timeDetailBlockCount']} "
            f"rows={through['parsedRowCount']} directMarker={through['identity']['directTimetableMarkerPresent']}"
        )
        if day["solver"]:
            print(f"{day_type}: transfer solver diagnostic={day['solver']}")


if __name__ == "__main__":
    main()

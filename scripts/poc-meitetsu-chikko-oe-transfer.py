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
MINIMUM_TRANSFER_LEAD_MINUTES = 3

# Current 2026 timetable guard. A timetable change must fail closed and be reviewed.
EXPECTED = {
    "weekday": {
        "feederDeparture": "19:25",
        "feederArrival": "19:36",
        "feederRoute": "名古屋本線(急行)",
        "feederTerminal": "河和",
        "shuttleDeparture": "19:44",
        "shuttleArrival": "19:47",
        "shuttleRoute": "築港線(普通)",
        "shuttleTerminal": "東名古屋港",
        "transferMarginMinutes": 8,
    },
    "saturday_holiday": {
        "feederDeparture": "16:55",
        "feederArrival": "17:06",
        "feederRoute": "名古屋本線(急行)",
        "feederTerminal": "河和",
        "shuttleDeparture": "17:20",
        "shuttleArrival": "17:23",
        "shuttleRoute": "築港線(普通)",
        "shuttleTerminal": "東名古屋港",
        "transferMarginMinutes": 14,
    },
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
        services.append({**row, "departure": clocks[0], "arrival": clocks[-1]})
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


def single_value(values: list[str], label: str) -> str:
    if len(values) != 1:
        raise AssertionError(f"expected exactly one {label}, got {values}")
    return values[0]


def assert_expected(day_type: str, boundary: dict[str, object]) -> None:
    expected = EXPECTED[day_type]
    feeder = boundary["feeder"]
    shuttle = boundary["shuttle"]

    actual = {
        "feederDeparture": feeder["departure"],
        "feederArrival": feeder["arrival"],
        "feederRoute": single_value(feeder["routeNames"], "feeder route"),
        "feederTerminal": single_value(feeder["terminals"], "feeder terminal"),
        "shuttleDeparture": shuttle["departure"],
        "shuttleArrival": shuttle["arrival"],
        "shuttleRoute": single_value(shuttle["routeNames"], "shuttle route"),
        "shuttleTerminal": single_value(shuttle["terminals"], "shuttle terminal"),
        "transferMarginMinutes": boundary["transferMarginMinutes"],
    }
    if actual != expected:
        raise AssertionError(
            f"{day_type} boundary changed; expected={expected}, actual={actual}"
        )


def main() -> None:
    result: dict[str, object] = {
        "origin": ORIGIN,
        "transfer": TRANSFER,
        "destination": DESTINATION,
        "minimumTransferLeadMinutes": MINIMUM_TRANSFER_LEAD_MINUTES,
        "verificationStrategy": (
            "official destination-specific no-transfer timetables for each leg; "
            "latest feeder that reaches Oe at least the conservative transfer lead "
            "before the final official Chikko shuttle"
        ),
        "days": {},
        "staticTimetable": inspect_static_timetable(Path("/tmp/meitetsu-chikko-oe-timetable.html")),
    }

    for day_type in DAY_TYPES:
        through_path = Path(f"/tmp/meitetsu-chikko-through-{day_type}.html")
        shuttle_path = Path(f"/tmp/meitetsu-chikko-shuttle-{day_type}.html")
        feeder_path = Path(f"/tmp/meitetsu-chikko-feeder-{day_type}.html")

        through = parse_rows(through_path, ORIGIN["name"], DESTINATION["name"])
        if through["parsedRowCount"] != 0:
            raise AssertionError(
                f"NH36 -> CH01 unexpectedly has a no-transfer service: {day_type}"
            )

        shuttles = direct_services(
            shuttle_path, TRANSFER["name"], DESTINATION["name"], "築港線("
        )
        feeders = direct_services(feeder_path, ORIGIN["name"], TRANSFER["name"])
        if not shuttles:
            raise AssertionError(f"no Oe -> Higashi-Nagoyako shuttle rows: {day_type}")
        if not feeders:
            raise AssertionError(f"no Nagoya -> Oe feeder rows: {day_type}")

        last_shuttle = shuttles[-1]
        shuttle_departure_minutes = service_minutes(str(last_shuttle["departure"]))
        compatible: list[dict[str, object]] = []
        too_tight: list[dict[str, object]] = []

        for feeder in feeders:
            margin = shuttle_departure_minutes - service_minutes(str(feeder["arrival"]))
            candidate = {**feeder, "transferMarginMinutes": margin}
            if margin >= MINIMUM_TRANSFER_LEAD_MINUTES:
                compatible.append(candidate)
            elif margin >= 0:
                too_tight.append(candidate)

        compatible.sort(key=lambda row: service_minutes(str(row["departure"])))
        too_tight.sort(key=lambda row: service_minutes(str(row["departure"])))
        if not compatible:
            raise AssertionError(
                f"no feeder reaches Oe with >= {MINIMUM_TRANSFER_LEAD_MINUTES} min lead: {day_type}"
            )

        feeder = compatible[-1]
        boundary = {
            "lastDeparture": feeder["departure"],
            "lastArrival": last_shuttle["arrival"],
            "transferAt": TRANSFER["name"],
            "transferReadyTime": feeder["arrival"],
            "connectionDeparture": last_shuttle["departure"],
            "transferMarginMinutes": feeder["transferMarginMinutes"],
            "minimumTransferLeadMinutes": MINIMUM_TRANSFER_LEAD_MINUTES,
            "feeder": feeder,
            "shuttle": last_shuttle,
        }
        assert_expected(day_type, boundary)

        result["days"][day_type] = {
            "throughSearch": {
                "identity": through["identity"],
                "timeDetailBlockCount": through["timeDetailBlockCount"],
                "parsedRowCount": through["parsedRowCount"],
            },
            "shuttleServiceCount": len(shuttles),
            "feederServiceCount": len(feeders),
            "compatibleFeederCount": len(compatible),
            "tooTightFeederCount": len(too_tight),
            "boundary": boundary,
            "lastFiveCompatibleFeeders": compatible[-5:],
            "tooTightFeeders": too_tight,
        }

    Path("/tmp/meitetsu-chikko-transfer-poc.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("Meitetsu Chikko CH01 transfer boundary PoC: OK")
    for day_type in DAY_TYPES:
        boundary = result["days"][day_type]["boundary"]
        print(
            f"{day_type}: {boundary['lastDeparture']} Nagoya -> "
            f"{boundary['transferReadyTime']} Oe / "
            f"{boundary['connectionDeparture']} Oe -> "
            f"{boundary['lastArrival']} Higashi-Nagoyako / "
            f"margin={boundary['transferMarginMinutes']} min"
        )


if __name__ == "__main__":
    main()

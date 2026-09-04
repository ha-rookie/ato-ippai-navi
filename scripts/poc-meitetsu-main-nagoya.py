#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

STATIONS = {
    "NH24": "中京競馬場前",
    "NH25": "有松",
    "NH26": "左京山",
    "NH27": "鳴海",
    "NH28": "本星崎",
    "NH29": "本笠寺",
    "NH30": "桜",
    "NH31": "呼続",
    "NH32": "堀田",
    "NH33": "神宮前",
    "NH34": "金山",
    "NH35": "山王",
    "NH36": "名鉄名古屋",
    "NH37": "栄生",
    "NH38": "東枇杷島",
}

KNOWN_NODE_IDS = {
    "NH24": "00006039",
    "NH25": "00008842",
    "NH26": "00002805",
    "NH27": "00008608",
    "NH28": "00008474",
    "NH36": "00004372",
    "NH38": "00006826",
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


def parse_direct_tail(path: Path, origin: str, destination: str) -> dict[str, object]:
    text = plain(decode(path))
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

    patterns = [
        re.compile(
            r"(?P<dep>\d{1,2}:\d{2})\s*発\s*"
            r"(?P<arr>\d{1,2}:\d{2})\s*着.*?"
            r"名古屋本線\((?P<class>[^)]+)\)\s*(?P<terminal>[^\s]+)"
        ),
        re.compile(
            r"(?P<dep>\d{1,2}:\d{2}).{0,80}?"
            r"(?P<arr>\d{1,2}:\d{2}).{0,250}?"
            r"名古屋本線.{0,80}?(?P<class>特急|快速特急|急行|準急|普通).{0,120}?"
            r"(?P<terminal>東岡崎|豊橋|伊奈|鳴海|金山|知立|前後|神宮前)"
        ),
    ]

    matches: list[re.Match[str]] = []
    used_pattern = -1
    for index, pattern in enumerate(patterns):
        matches = list(pattern.finditer(text))
        if matches:
            used_pattern = index
            break

    if not matches:
        times = re.findall(r"\b(?:[01]?\d|2[0-9]):[0-5]\d\b", text)
        Path(f"/tmp/{path.stem}-diagnostics.json").write_text(
            json.dumps(
                {
                    "identity": identity,
                    "timesTail": times[-40:],
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

    last = matches[-1]
    return {
        "lastDeparture": last.group("dep").zfill(5),
        "lastArrival": last.group("arr").zfill(5),
        "trainClass": last.group("class"),
        "trainTerminal": last.group("terminal"),
        "parserPattern": used_pattern,
        "matchedServiceCount": len(matches),
    }


def main() -> None:
    top_path = Path("/tmp/meitetsu-direct-top.html")
    origin_path = Path("/tmp/meitetsu-nagoya-main-east.html")
    if not top_path.exists() or not origin_path.exists():
        raise SystemExit("official source files are missing")

    top = decode(top_path)
    top_text = plain(top)

    discovery: dict[str, dict[str, object]] = {}
    for code, name in STATIONS.items():
        discovery[code] = {
            "name": name,
            "namePresentInStaticTop": name in top_text,
            "nodeCandidates": find_node_candidates(top, name),
            "knownNodeId": KNOWN_NODE_IDS.get(code),
        }

    Path("/tmp/meitetsu-main-node-discovery.json").write_text(
        json.dumps(discovery, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    origin_diagnostic = inspect_origin_timetable(origin_path)
    print("NH36 origin diagnostic:")
    print(json.dumps(origin_diagnostic, ensure_ascii=False, indent=2))

    samples = {
        "NH24": "中京競馬場前",
        "NH27": "鳴海",
    }
    sample_output: dict[str, dict[str, object]] = {}
    for code, name in samples.items():
        path = Path(f"/tmp/meitetsu-direct-{code}.html")
        sample_output[code] = parse_direct_tail(path, "名鉄名古屋", name)

    Path("/tmp/meitetsu-main-sample-boundaries.json").write_text(
        json.dumps(sample_output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Meitetsu Main Line destination-specific official-source inspection: OK")
    print(json.dumps(sample_output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

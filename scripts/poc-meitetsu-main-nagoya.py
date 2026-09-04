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


def assert_origin_timetable(path: Path) -> None:
    text = plain(decode(path))
    required = ["名鉄名古屋", "NH36", "東岡崎", "鳴海", "金山"]
    for token in required:
        if token not in text:
            raise AssertionError(f"origin timetable missing {token}: {path}")

    # Current official timetable guard rails. If these move, stop and review.
    for token in ("23", "57", "00", "01", "06"):
        if token not in text:
            raise AssertionError(f"late-night anchor missing {token}: {path}")


def parse_direct_tail(path: Path, origin: str, destination: str) -> dict[str, str]:
    text = plain(decode(path))
    if origin not in text or destination not in text or "乗換なし時刻表" not in text:
        print(f"==== unexpected direct page head: {path} ====", file=sys.stderr)
        print(text[:3000], file=sys.stderr)
        raise AssertionError(f"unexpected direct timetable page: {path}")

    # Rendered/plain order is: HH:MM 発 HH:MM 着 ... line(class) terminal.
    pattern = re.compile(
        r"(?P<dep>\d{2}:\d{2})\s*発\s*"
        r"(?P<arr>\d{2}:\d{2})\s*着.*?"
        r"名古屋本線\((?P<class>[^)]+)\)\s*(?P<terminal>[^\s]+)"
    )
    matches = list(pattern.finditer(text))
    if not matches:
        print(f"==== direct plain tail: {path} ====", file=sys.stderr)
        print(text[-5000:], file=sys.stderr)
        raise AssertionError(f"no direct service rows parsed: {path}")

    last = matches[-1]
    return {
        "lastDeparture": last.group("dep"),
        "lastArrival": last.group("arr"),
        "trainClass": last.group("class"),
        "trainTerminal": last.group("terminal"),
    }


def main() -> None:
    top_path = Path("/tmp/meitetsu-direct-top.html")
    origin_path = Path("/tmp/meitetsu-nagoya-main-east.html")
    if not top_path.exists() or not origin_path.exists():
        raise SystemExit("official source files are missing")

    top = decode(top_path)
    top_text = plain(top)

    # The search top currently renders station candidates dynamically in some
    # sessions. Do not make its static HTML a production dependency. Keep it as
    # a diagnostic source and learn which opaque node IDs, if any, are exposed.
    discovery: dict[str, dict[str, object]] = {}
    for code, name in STATIONS.items():
        candidates = find_node_candidates(top, name)
        discovery[code] = {
            "name": name,
            "namePresentInStaticTop": name in top_text,
            "nodeCandidates": candidates,
            "knownNodeId": KNOWN_NODE_IDS.get(code),
        }

    Path("/tmp/meitetsu-main-node-discovery.json").write_text(
        json.dumps(discovery, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Static Top diagnostics:")
    print(json.dumps(discovery, ensure_ascii=False, indent=2))

    assert_origin_timetable(origin_path)

    samples = {
        "NH24": "中京競馬場前",
        "NH27": "鳴海",
    }
    sample_output: dict[str, dict[str, str]] = {}
    for code, name in samples.items():
        path = Path(f"/tmp/meitetsu-direct-{code}.html")
        sample_output[code] = parse_direct_tail(path, "名鉄名古屋", name)

    Path("/tmp/meitetsu-main-sample-boundaries.json").write_text(
        json.dumps(sample_output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Meitetsu Main Line official-source inspection: OK")
    print(json.dumps(sample_output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

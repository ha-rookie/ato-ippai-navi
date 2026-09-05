#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "src/index.js"
DECISION = ROOT / "src/decision.js"
DECISION_TEST = ROOT / "test/decision.test.js"


def remove_once(text: str, pattern: str, description: str, flags: int = 0) -> str:
    updated, count = re.subn(pattern, "", text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"expected exactly one {description}, found {count}")
    return updated


def update_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    text = remove_once(
        text,
        r'import \{\n  evaluateSakaeToFujigaoka,\n  evaluateSakaeToFujigaokaWithAccess\n\} from "\.\/decision\.js";\n',
        "decision.js import",
    )

    text = remove_once(
        text,
        r'function allSteps\(route\) \{.*?\n\}\n\n(?=async function googleRoutes)',
        "legacy transit normalization helpers",
        re.S,
    )

    text = remove_once(
        text,
        r'async function transit\(env, input\) \{.*?\n\}\n\n(?=async function walk)',
        "legacy transit function",
        re.S,
    )

    text = remove_once(
        text,
        r'function addMinutes\(iso, minutes\) \{.*?\n\}\n\n(?=async function lastTrainBoundaryFromCurrentLocation)',
        "legacy addMinutes helper",
        re.S,
    )

    text = remove_once(
        text,
        r'async function decisionFromCurrentLocation\(env, input\) \{.*?\n\}\n\n(?=async function tonightDecision)',
        "legacy Fujigaoka current-location decision",
        re.S,
    )

    text = remove_once(
        text,
        r'async function evaluate\(env, input\) \{.*?\n\}\n\n(?=export default)',
        "legacy evaluate function",
        re.S,
    )

    route_blocks = [
        (
            r'\n      if \(url\.pathname === "/api/transit"\) \{\n        return json\(await transit\(env, input\)\);\n      \}\n',
            "/api/transit route",
        ),
        (
            r'\n      if \(url\.pathname === "/api/evaluate"\) \{\n        return json\(await evaluate\(env, input\)\);\n      \}\n',
            "/api/evaluate route",
        ),
        (
            r'\n      if \(url\.pathname === "/api/decision-poc"\) \{\n        return json\(evaluateSakaeToFujigaoka\(input\)\);\n      \}\n',
            "/api/decision-poc route",
        ),
        (
            r'\n      if \(url\.pathname === "/api/decision-from-current-location"\) \{\n        return json\(await decisionFromCurrentLocation\(env, input\)\);\n      \}\n',
            "/api/decision-from-current-location route",
        ),
    ]
    for pattern, description in route_blocks:
        text = remove_once(text, pattern, description)

    forbidden = [
        "evaluateSakaeToFujigaoka",
        "decisionFromCurrentLocation",
        'url.pathname === "/api/transit"',
        'url.pathname === "/api/evaluate"',
        'url.pathname === "/api/decision-poc"',
        'url.pathname === "/api/decision-from-current-location"',
        "travelMode: \"TRANSIT\"",
    ]
    for token in forbidden:
        if token in text:
            raise RuntimeError(f"legacy token remains in src/index.js: {token}")

    required = [
        "async function googleRoutes",
        "async function walk",
        "async function drive",
        "async function lastTrainBoundaryFromCurrentLocation",
        "async function tonightDecision",
        "export default",
        'url.pathname === "/api/walk"',
        'url.pathname === "/api/drive"',
        'url.pathname === "/api/last-train-boundary"',
        'url.pathname === "/api/taxi-estimate"',
        'url.pathname === "/api/tonight-decision"',
    ]
    for token in required:
        if token not in text:
            raise RuntimeError(f"required production token missing: {token}")

    INDEX.write_text(text, encoding="utf-8")


def delete_legacy_files() -> None:
    for path in (DECISION, DECISION_TEST):
        if not path.exists():
            raise RuntimeError(f"expected legacy file not found: {path.relative_to(ROOT)}")
        path.unlink()


def main() -> None:
    update_index()
    delete_legacy_files()
    print("Legacy Google TRANSIT / Fujigaoka PoC API removed")


if __name__ == "__main__":
    main()

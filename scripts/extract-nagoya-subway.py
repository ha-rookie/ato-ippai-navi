#!/usr/bin/env python3
"""Extract a normalized timetable from Nagoya City subway pocket timetable XLSX files.

This script intentionally uses only Python's standard library. XLSX is a ZIP
container of XML files, so no spreadsheet runtime dependency is required.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def recover_zip_name(name: str) -> str:
    """Recover Japanese filenames stored in legacy CP932 ZIP metadata."""
    try:
        return name.encode("cp437").decode("cp932")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value)


def col_letters_to_num(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def cell_ref_to_parts(ref: str) -> tuple[int, int]:
    match = re.fullmatch(r"([A-Z]+)(\d+)", ref)
    if not match:
        raise ValueError(f"Invalid cell reference: {ref}")
    return col_letters_to_num(match.group(1)), int(match.group(2))


def shared_strings(book: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in book.namelist():
        return []

    root = ET.fromstring(book.read(path))
    result = []
    for si in root.findall("m:si", NS):
        result.append("".join(t.text or "" for t in si.findall(".//m:t", NS)))
    return result


def cell_value(cell: ET.Element, strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(".//m:t", NS))

    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return ""

    raw = value.text

    if cell_type == "s":
        try:
            return strings[int(raw)]
        except (ValueError, IndexError):
            return raw

    return raw


def read_sheet_cells(book: zipfile.ZipFile, sheet_path: str) -> dict[tuple[int, int], str]:
    strings = shared_strings(book)
    root = ET.fromstring(book.read(sheet_path))
    cells: dict[tuple[int, int], str] = {}

    for cell in root.findall(".//m:sheetData/m:row/m:c", NS):
        ref = cell.attrib.get("r", "")
        if not ref:
            continue
        value = cell_value(cell, strings)
        if value in ("", None):
            continue
        col, row = cell_ref_to_parts(ref)
        cells[(col, row)] = str(value)

    return cells


def sheet_names(book: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(book.read("xl/workbook.xml"))
    return [
        sheet.attrib.get("name", "")
        for sheet in root.findall(".//m:sheets/m:sheet", NS)
    ]


def find_workbook(
    outer: zipfile.ZipFile,
    station_code: str,
    station_name: str,
) -> tuple[zipfile.ZipInfo, str]:
    target_code = normalize_text(station_code).upper()
    target_name = normalize_text(station_name)

    for info in outer.infolist():
        if info.is_dir() or not info.filename.lower().endswith(".xlsx"):
            continue

        recovered = recover_zip_name(info.filename)
        normalized = normalize_text(recovered)

        if target_code in normalized.upper() and target_name in normalized:
            return info, recovered

    raise RuntimeError(f"Workbook not found for {station_code} {station_name}")


def marker_destinations(cells: dict[tuple[int, int], str]) -> dict[str, str]:
    result: dict[str, str] = {}

    for value in cells.values():
        text = normalize_text(value)
        for marker, destination in re.findall(r"([^\s…、]+)…([^\s、]+?)行", text):
            result[marker] = destination

    return result


def detect_timetable_blocks(cells: dict[tuple[int, int], str]) -> list[int]:
    """Find hour columns by locating repeated '4' entries in row 4.

    The pocket timetable places weekday and Saturday/holiday blocks side by side.
    H10 Sakae currently yields columns B and AX.
    """
    candidates = [
        col
        for (col, row), value in cells.items()
        if row == 4 and normalize_text(value) == "4"
    ]
    candidates.sort()

    if len(candidates) < 2:
        raise RuntimeError(f"Expected at least two timetable blocks, got {candidates}")

    return candidates[:2]


def parse_block(
    cells: dict[tuple[int, int], str],
    hour_col: int,
    block_end_col: int,
    default_terminal: str,
    marker_map: dict[str, str],
) -> list[dict]:
    departures: list[dict] = []
    current_hour: int | None = None

    # Each departure slot uses three columns. The minute is in hour_col + 3,
    # +6, +9, ... and an optional destination marker is immediately left.
    minute_cols = range(hour_col + 3, block_end_col, 3)

    for row in range(4, 40):
        hour_raw = cells.get((hour_col, row), "")
        hour_text = normalize_text(hour_raw)

        if re.fullmatch(r"\d{1,2}", hour_text):
            hour_num = int(hour_text)
            if 0 <= hour_num <= 23:
                current_hour = hour_num

        if current_hour is None:
            continue

        for minute_col in minute_cols:
            minute_raw = normalize_text(cells.get((minute_col, row), ""))
            if not re.fullmatch(r"\d{1,2}", minute_raw):
                continue

            minute_num = int(minute_raw)
            if not 0 <= minute_num <= 59:
                continue

            marker = normalize_text(cells.get((minute_col - 1, row), "")).strip()
            destination = marker_map.get(marker, default_terminal)

            service_hour = current_hour + 24 if current_hour < 4 else current_hour
            departures.append(
                {
                    "time": f"{current_hour:02d}:{minute_num:02d}",
                    "serviceMinutes": service_hour * 60 + minute_num,
                    "destination": destination,
                    "marker": marker or None,
                }
            )

    departures.sort(key=lambda item: item["serviceMinutes"])
    return departures


def extract_schedule(
    source_zip: Path,
    station_code: str,
    station_name: str,
    direction_sheet: str,
    default_terminal: str,
    source_url: str,
    revision: str,
) -> dict:
    with zipfile.ZipFile(source_zip) as outer:
        info, recovered_name = find_workbook(outer, station_code, station_name)

        with zipfile.ZipFile(io.BytesIO(outer.read(info))) as book:
            names = sheet_names(book)
            if direction_sheet not in names:
                raise RuntimeError(
                    f"Sheet {direction_sheet!r} not found; available sheets: {names}"
                )

            sheet_index = names.index(direction_sheet) + 1
            sheet_path = f"xl/worksheets/sheet{sheet_index}.xml"
            cells = read_sheet_cells(book, sheet_path)

            marker_map = marker_destinations(cells)
            blocks = detect_timetable_blocks(cells)

            # The second block extends to the worksheet's far right. 120 is
            # intentionally above CR (96) and harmless because absent cells are ignored.
            block_ranges = [
                (blocks[0], blocks[1]),
                (blocks[1], 120),
            ]

            day_types = ["weekday", "saturday_holiday"]
            schedules = {}

            for day_type, (hour_col, end_col) in zip(day_types, block_ranges):
                schedules[day_type] = parse_block(
                    cells,
                    hour_col,
                    end_col,
                    default_terminal,
                    marker_map,
                )

            return {
                "source": {
                    "publisher": "名古屋市交通局",
                    "license": "CC BY 4.0",
                    "url": source_url,
                    "revision": revision,
                    "workbook": recovered_name,
                },
                "station": {
                    "code": station_code,
                    "name": station_name,
                },
                "directionSheet": direction_sheet,
                "defaultTerminal": default_terminal,
                "markerDestinations": marker_map,
                "schedules": schedules,
            }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--station-code", default="H10")
    parser.add_argument("--station-name", default="栄")
    parser.add_argument("--direction-sheet", default="下り")
    parser.add_argument("--default-terminal", default="藤が丘")
    parser.add_argument("--revision", default="2025-03-29")
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args()

    data = extract_schedule(
        source_zip=args.zip,
        station_code=args.station_code,
        station_name=args.station_name,
        direction_sheet=args.direction_sheet,
        default_terminal=args.default_terminal,
        source_url=args.source_url,
        revision=args.revision,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for day_type, departures in data["schedules"].items():
        to_default = [
            item for item in departures
            if item["destination"] == data["defaultTerminal"]
        ]
        last = to_default[-1] if to_default else None
        print(
            json.dumps(
                {
                    "dayType": day_type,
                    "departureCount": len(departures),
                    "lastToDefaultTerminal": last,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()

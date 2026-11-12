"""Extract a small, local SIA2 metadata fixture from the WISE 0855 HTML export.

The output belongs under data/ and must not be committed. It contains observed
SIA2 metadata only; it does not contain pixels or measured fluxes.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

SOURCE_COLUMNS = (
    "obs_id",
    "obs_publisher_did",
    "obs_collection",
    "energy_bandpassname",
    "s_ra",
    "s_dec",
    "t_min",
    "t_max",
    "access_url",
    "access_format",
    "s_region",
    "s_fov",
    "em_min",
    "em_max",
)
NUMBER_COLUMNS = {"s_ra", "s_dec", "t_min", "t_max", "s_fov", "em_min", "em_max"}
BANDS = tuple(f"SPHEREx-D{number}" for number in range(1, 7))


class SiaTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def extract_sources(html_path: Path) -> list[dict[str, str | float]]:
    parser = SiaTableParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    if len(parser.rows) < 2:
        raise ValueError("No SIA2 data rows found in the HTML file")

    headers = parser.rows[0]
    if len(headers) != len(set(headers)) or not set(SOURCE_COLUMNS) <= set(headers):
        raise ValueError("The SIA2 table is missing required columns or has duplicate headers")

    sources: list[dict[str, str | float]] = []
    for values in parser.rows[1:]:
        if len(values) != len(headers):
            raise ValueError("A SIA2 row does not match the table header")
        row = dict(zip(headers, values, strict=True))
        if row["obs_collection"] != "spherex_qr2":
            continue
        if row["energy_bandpassname"] not in BANDS:
            continue
        if not all(row[column] for column in SOURCE_COLUMNS):
            continue
        source = {
            column: float(row[column]) if column in NUMBER_COLUMNS else row[column]
            for column in SOURCE_COLUMNS
        }
        sources.append(source)
    if not sources:
        raise ValueError("No complete QR2 source metadata found")
    return sources


def select_spread(
    sources: list[dict[str, str | float]], per_band: int
) -> list[dict[str, str | float]]:
    by_band: dict[str, list[dict[str, str | float]]] = defaultdict(list)
    for source in sources:
        by_band[str(source["energy_bandpassname"])].append(source)

    selected: list[dict[str, str | float]] = []
    for band in BANDS:
        candidates = sorted(
            by_band[band], key=lambda row: (float(row["t_min"]), str(row["obs_publisher_did"]))
        )
        if not candidates:
            continue
        count = min(per_band, len(candidates))
        indices = (
            [round(index * (len(candidates) - 1) / (count - 1)) for index in range(count)]
            if count > 1
            else [0]
        )
        selected.extend(candidates[index] for index in indices)
    return sorted(selected, key=lambda row: (float(row["t_min"]), str(row["energy_bandpassname"])))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path, help="Locally saved SIA2 HTML table")
    parser.add_argument("--output", type=Path, default=Path("data/wise0855_qr2_sources.json"))
    parser.add_argument("--per-band", type=int, default=4)
    args = parser.parse_args()
    if args.per_band < 1:
        parser.error("--per-band must be at least 1")

    all_sources = extract_sources(args.html)
    selected = select_spread(all_sources, args.per_band)
    fixture = {
        "fixture_kind": "real_sia2_metadata_only",
        "target_name": "WISE 0855",
        "target_s_ra": 133.79513,
        "target_s_dec": -7.24515,
        "sia2_row_count": len(all_sources),
        "sources": selected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"Extracted {len(selected)} source rows across {len(BANDS)} bands from {len(all_sources)} SIA2 rows"
    )
    print(f"Saved local fixture: {args.output}")


if __name__ == "__main__":
    main()

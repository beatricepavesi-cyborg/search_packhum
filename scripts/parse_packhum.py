#!/usr/bin/env python3
"""
Parse all HTML files under packhum/ and write them to data/curation/packhum.csv.

Usage:
  python scripts/parse_packhum.py
  python scripts/parse_packhum.py --in packhum --out data/curation/packhum.csv
"""

import argparse
import csv
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from tqdm import tqdm

INVALID_MARKER = "Invalid PHI Inscription Number"

FIELDS = [
    "id",
    "text",
    "metadata",
    "region_main_id",
    "region_main",
    "region_sub_id",
    "region_sub",
    "reference",
]


def parse_html(phi_id: int, html: str) -> dict | None:
    if INVALID_MARKER in html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    lines = []
    table = soup.find("table", attrs={"class": "grk"})
    if table:
        for row in table.find_all("tr"):
            for td in row.find_all("td"):
                if td.attrs.get("class", [""])[0] == "id":
                    continue
                lines.append(td.get_text().strip())
    text = "\n".join(lines).strip()

    if not text:
        return None

    region_main = region_sub = ""
    region_main_id = region_sub_id = ""
    hdr1 = soup.find("div", attrs={"class": "hdr1"})
    if hdr1:
        links = hdr1.find_all("a")
        if len(links) >= 2:
            region_main_id = links[1]["href"].replace("/regions/", "")
            region_main = links[1].get_text()
        if len(links) >= 3:
            region_sub_id = links[2]["href"].replace("/regions/", "")
            region_sub = links[2].get_text()

    meta_span = soup.find("span", attrs={"class": "ti"})
    metadata = meta_span.get_text().strip() if meta_span else ""

    docref_div = soup.find("div", attrs={"class": "docref"})
    reference = docref_div.get_text().strip() if docref_div else ""

    return {
        "id": phi_id,
        "text": text,
        "metadata": metadata,
        "region_main_id": region_main_id,
        "region_main": region_main,
        "region_sub_id": region_sub_id,
        "region_sub": region_sub,
        "reference": reference,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Parse packhum HTML files into a CSV"
    )
    ap.add_argument("--in", dest="in_dir", default="packhum",
                    help="Directory of HTML files (default: packhum)")
    ap.add_argument("--out", default="data/curation/packhum.csv",
                    help="Output CSV path (default: data/curation/packhum.csv)")
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_path = Path(args.out)

    if not in_dir.is_dir():
        print(f"Error: input directory not found: {in_dir}", file=sys.stderr)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    html_files = sorted(in_dir.glob("*.html"), key=lambda p: int(p.stem))
    print(f"HTML files found: {len(html_files):,}")

    written = skipped = 0
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for path in tqdm(html_files, unit="file"):
            phi_id = int(path.stem)
            html = path.read_text(encoding="utf-8")
            row = parse_html(phi_id, html)
            if row is None:
                skipped += 1
                continue
            writer.writerow(row)
            written += 1

    print(f"Written: {written:,}  Skipped (invalid/empty): {skipped:,}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Parse all HTML files under packhum/ and write them to data/curation/packhum.csv.

Usage:
  python scripts/parse_packhum.py
  python scripts/parse_packhum.py --in packhum --out data/curation/packhum.csv
"""

import json
import re
import argparse
import csv
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from tqdm import tqdm

from iphi_dates import date_parser_phi

INVALID_MARKER = "Invalid PHI Inscription Number"

FIELDS = [
    "id",
    "text",
    "fragment_name",
    "metadata",
    "region_main_id",
    "region_main",
    "region_sub_id",
    "region_sub",
    "reference",
    "date_str",
    "date_min",
    "date_max",
    "date_circa",
    "book_name",
    "book_link",
    "note",
]


def parse_html(phi_id: int, html: str) -> list[dict] | None:
    if INVALID_MARKER in html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    fragment_rows = []
    table = soup.find("table", attrs={"class": "grk"})
    if table:
        current_fragment = ""
        current_text_lines = []

        for row in table.find_all("tr"):
            fragment_name = None
            text_lines = []

            for td in row.find_all("td"):
                if td.attrs.get("class", [""])[0] == "id":
                    frag = td.get_text().strip()
                    if frag and not frag.isdigit():
                        fragment_name = frag
                else:
                    text_lines.append(td.get_text().strip())

            if fragment_name is not None:
                if current_text_lines:
                    text = "\n".join(current_text_lines).strip()
                    fragment_rows.append((current_fragment, text))
                current_fragment = fragment_name
                current_text_lines = text_lines
            else:
                current_text_lines.extend(text_lines)

        if current_text_lines:
            text = "\n".join(current_text_lines).strip()
            fragment_rows.append((current_fragment, text))

    if not fragment_rows:
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

    # Time
    date_str = ""
    date_min = None
    date_max = None
    date_circa = None
    for tok in metadata.split("—"):
        if re.search(
                r"\W(BC|AD|period|reign|a\.|p\.(?!\s+\d)|aet\.)(\W|$)", tok):
            date_str = tok
            date_range, circa = date_parser_phi(tok)
            if date_range is not None:
                parts = date_range.split(" ")
                if len(parts) >= 2:
                    try:
                        date_min = int(parts[0])
                        date_max = int(parts[1])
                    except ValueError:
                        date_min = None
                        date_max = None
                date_circa = circa
    
    # Extract book name and link from the a.booklink tag
    book_name = book_link = ""
    book_node = soup.select_one("div.hdr2 span.fullref a.booklink")
    if book_node:
        book_name = book_node.get_text().strip()
        book_link = book_node.get("href", "").strip()

    # Extract the descriptive note
    note = ""
    note_node = soup.select_one("div.small.light.note span")
    if note_node:
        note = note_node.get_text().strip()

    result = []
    for fragment_name, text in fragment_rows:
        result.append({
            "id": phi_id,
            "text": text,
            "fragment_name": fragment_name,
            "metadata": metadata,
            "region_main_id": region_main_id,
            "region_main": region_main,
            "region_sub_id": region_sub_id,
            "region_sub": region_sub,
            "date_str": date_str,
            "date_min": date_min,
            "date_max": date_max,
            "date_circa": date_circa,
            "reference": reference,
            "book_name": book_name,
            "book_link": book_link,
            "note": note,
        })

    return result


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

    skipped_html = []
    written = skipped = 0
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for path in tqdm(html_files, unit="file", disable=False):
            phi_id = int(path.stem)
            html = path.read_text(encoding="utf-8")
            rows = parse_html(phi_id, html)
            if rows is None:
                skipped += 1
                skipped_html.append((phi_id, path))
                continue
            for row in rows:
                writer.writerow(row)
                written += 1
            
    # Save CSV file to a JSON file too
    json_path = out_path.with_suffix(".json")
    with out_path.open("r", encoding="utf-8") as csv_fh, json_path.open("w", encoding="utf-8") as json_fh:
        reader = csv.DictReader(csv_fh)
        data = list(reader)
        json.dump(data, json_fh, ensure_ascii=False, indent=2)

    # Write skipped HTML files to a log for review
    if skipped_html:
        log_path = out_path.parent / "skipped_packhum.log"
        with log_path.open("w", encoding="utf-8") as log_fh:
            for phi_id, path in skipped_html:
                log_fh.write(f"{phi_id}\t{path}\n")
        print(f"Skipped {skipped:,} invalid/empty inscriptions. "
              f"Details logged to: {log_path}")

    print(f"Written: {written:,}  Skipped (invalid/empty): {skipped:,}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
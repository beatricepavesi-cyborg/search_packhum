#!/usr/bin/env python3
"""
Scraper for PHI Greek Inscriptions (epigraphy.packhum.org)

Iterates PHI IDs 1..MAX_ID, downloads each inscription page, and saves valid
ones as packhum/{id}.html.  Invalid IDs (404 / "Invalid PHI Inscription Number")
are skipped.  Already-downloaded files are never re-fetched, so the script is
fully resumable.

Adapted from the original I.PHI downloader by Sommerschield et al.
(https://github.com/sommerschield/iphi), stripped of ithaca dependencies.

Usage:
  pip install requests beautifulsoup4 tqdm
  pip install cloudscraper        # optional, helps bypass Cloudflare at --workers > 1
  python scrape_packhum.py
  python scrape_packhum.py --workers 4 --max_id 400000 --timeout 10
"""

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

BASE_URL = "https://epigraphy.packhum.org/text/{}"
INVALID_MARKER = "Invalid PHI Inscription Number"


def make_client(use_cloudscraper: bool):
    if use_cloudscraper and HAS_CLOUDSCRAPER:
        return cloudscraper.create_scraper(), {}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; Googlebot/2.1; "
            "+http://www.google.com/bot.html)"
        )
    }
    return requests.Session(), headers


def fetch_inscription(phi_id: int, out_dir: Path, client, headers: dict,
                      timeout: int, max_retries: int, parse: bool = False) -> dict | None:
    """
    Download one inscription page.  Returns a dict with basic parsed fields,
    or None if the ID is invalid or the text is too short.
    Saves raw HTML to out_dir/{phi_id}.html.
    """
    file_path = out_dir / f"{phi_id}.html"

    if file_path.exists():
        html = file_path.read_text(encoding="utf-8")
    else:
        html = None
        for attempt in range(max_retries):
            try:
                resp = client.get(BASE_URL.format(phi_id),
                                  timeout=timeout, headers=headers)
                html = resp.text
                if INVALID_MARKER not in html:
                    break
            except Exception as exc:
                if attempt == max_retries - 1:
                    print(f"\n  [{phi_id}] failed after {max_retries} retries: {exc}",
                          file=sys.stderr)
                    return None
                time.sleep(2 ** attempt)

        if html is None or INVALID_MARKER in html:
            return None

        file_path.write_text(html, encoding="utf-8")

    if INVALID_MARKER in html:
        return None

    # ── Parse with BeautifulSoup ──────────────────────────────────────────
    if not parse:
        return {
            "id": phi_id,
            "text": None,
            "metadata": None,
            "region_main_id": None,
            "region_main": None,
            "region_sub_id": None,
            "region_sub": None,
        }

    soup = BeautifulSoup(html, "html.parser")

    # Greek inscription text
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

    # Region breadcrumb
    region_main = region_sub = ""
    region_main_id = region_sub_id = -1
    hdr1 = soup.find("div", attrs={"class": "hdr1"})
    if hdr1:
        links = hdr1.find_all("a")
        if len(links) >= 2:
            region_main_id = links[1]["href"].replace("/regions/", "")
            region_main = links[1].get_text()
        if len(links) >= 3:
            region_sub_id = links[2]["href"].replace("/regions/", "")
            region_sub = links[2].get_text()

    # Metadata line (provenance, date, publication)
    meta_span = soup.find("span", attrs={"class": "ti"})
    metadata = meta_span.get_text().strip() if meta_span else ""

    return {
        "id": phi_id,
        "text": text,
        "metadata": metadata,
        "region_main_id": region_main_id,
        "region_main": region_main,
        "region_sub_id": region_sub_id,
        "region_sub": region_sub,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Download PHI Greek Inscriptions to packhum/"
    )
    ap.add_argument("--workers", type=int, default=1,
                    help="Parallel workers (default: 1). Use >1 with cloudscraper.")
    ap.add_argument("--timeout", type=int, default=10,
                    help="Request timeout in seconds (default: 10)")
    ap.add_argument("--max_id", type=int, default=400_000,
                    help="Highest PHI ID to try (default: 400000)")
    ap.add_argument("--max_retries", type=int, default=5,
                    help="Retries per inscription (default: 5)")
    ap.add_argument("--out", type=str, default="packhum",
                    help="Output directory (default: packhum)")
    ap.add_argument("--parse", action="store_true",
                    help="Parse text and metadata with BeautifulSoup (default: False)")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(exist_ok=True)

    if args.workers > 1 and not HAS_CLOUDSCRAPER:
        print("Warning: cloudscraper not installed. Multi-worker mode may hit "
              "Cloudflare. Install with: pip install cloudscraper",
              file=sys.stderr)

    client, headers = make_client(use_cloudscraper=args.workers > 1)

    ids = list(range(1, args.max_id + 1))
    # Skip IDs that are already saved and parsed (valid inscriptions only;
    # missing files are re-tried so invalid ones are not permanently skipped).
    already = {int(p.stem) for p in out_dir.glob("*.html")}
    ids_to_fetch = [i for i in ids if i not in already]

    print(f"PHI IDs to check: {len(ids_to_fetch):,}  "
          f"(already on disk: {len(already):,})")

    results = []
    errors = 0

    def task(phi_id):
        return fetch_inscription(
            phi_id, out_dir, client, headers,
            args.timeout, args.max_retries, args.parse
        )

    if args.workers == 1:
        for phi_id in tqdm(ids_to_fetch, unit="id"):
            result = task(phi_id)
            if result:
                results.append(result)
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(task, i): i for i in ids_to_fetch}
            for fut in tqdm(as_completed(futures),
                            total=len(ids_to_fetch), unit="id"):
                try:
                    result = fut.result()
                    if result:
                        results.append(result)
                except Exception as exc:
                    errors += 1
                    print(f"\n  Error: {exc}", file=sys.stderr)

    print(f"\nValid inscriptions downloaded: {len(results):,}")
    if errors:
        print(f"Errors: {errors}")
    print(f"HTML files saved in: {out_dir}/")


if __name__ == "__main__":
    main()

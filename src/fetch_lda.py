"""Download quarterly lobbying filings from the official LDA API (lda.gov).

Saves one slim gzipped CSV per quarter in data/lda/. Resumable: finished
quarters are skipped. Uses LDA_API_KEY if set (120 req/min), else anonymous
(15 req/min). Stops cleanly before the GitHub job time limit.
"""
import csv
import gzip
import math
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import requests

BASE = "https://lda.gov/api/v1/filings/"
OUT = Path(__file__).resolve().parent.parent / "data" / "lda"
KEY = os.environ.get("LDA_API_KEY", "").strip()
GAP = 0.55 if KEY else 4.2          # seconds between request starts (stay under 120/min)
WORKERS = 6 if KEY else 1           # requests in flight at once (each takes ~2.5s)
_lock, _next_slot = threading.Lock(), [0.0]
STATS = {"429": 0}


def _wait_turn():
    """Global pacing across threads: one request start every GAP seconds."""
    with _lock:
        now = time.time()
        slot = max(now, _next_slot[0])
        _next_slot[0] = slot + GAP
    time.sleep(max(0.0, slot - now))
BUDGET = float(os.environ.get("TIME_BUDGET_MIN", "320")) * 60
START_YEAR = int(os.environ.get("START_YEAR", "2008"))
PERIODS = ["first_quarter", "second_quarter", "third_quarter", "fourth_quarter"]
FIELDS = ["filing_uuid", "filing_type", "filing_year", "filing_period", "dt_posted",
          "registrant_id", "registrant_name", "client_id", "client_name",
          "self_filer", "income", "expenses"]
T0 = time.time()


def headers():
    h = {"User-Agent": "lobbying-signal research (github.com/qanicuq/lobbying-signal)"}
    if KEY:
        h["Authorization"] = f"Token {KEY}"
    return h


def get(url, params=None):
    for attempt in range(8):
        _wait_turn()
        try:
            r = requests.get(url, params=params, headers=headers(), timeout=120)
        except requests.RequestException:
            time.sleep(30 * (attempt + 1))
            continue
        if r.status_code == 429:
            STATS["429"] += 1
            wait = int(r.headers.get("Retry-After", "60"))
            time.sleep(min(max(wait, 30), 600))
            continue
        if r.status_code >= 500:
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"gave up on {url}")


def row(f):
    c, g = f.get("client") or {}, f.get("registrant") or {}
    return [f.get("filing_uuid"), f.get("filing_type"), f.get("filing_year"), f.get("filing_period"),
            f.get("dt_posted"), g.get("id"), g.get("name"), c.get("id"), c.get("name"),
            c.get("client_self_select"), f.get("income"), f.get("expenses")]


def quarters_due():
    today = date.today()
    out = []
    for y in range(today.year, START_YEAR - 1, -1):          # newest first
        for qi in range(3, -1, -1):
            q_end_month = 3 * (qi + 1)
            # report due ~20 days after quarter end; wait ~40 days for late filers
            ready = date(y + (q_end_month == 12), (q_end_month % 12) + 1, 1)
            if (today - ready).days >= 40:
                out.append((y, PERIODS[qi]))
    return out


def fetch_quarter(year, period):
    path = OUT / f"{year}_{period}.csv.gz"
    part = OUT / f"{year}_{period}.partial.csv.gz"
    if path.exists():
        return "skip"
    params = {"filing_year": year, "filing_period": period, "page_size": 25, "ordering": "dt_posted"}
    for attempt in range(2):
        first = get(BASE, params)
        total = first.get("count", 0)
        pages = math.ceil(total / 25)
        print(f"  {year} {period}: {total} filings, {pages} pages", flush=True)
        if time.time() - T0 + pages * GAP > BUDGET:
            return "out_of_time"
        with ThreadPoolExecutor(WORKERS) as ex:
            rest = list(ex.map(lambda n: get(BASE, {**params, "page": n}), range(2, pages + 1)))
        by_uuid = {}
        for d in [first] + rest:
            for f in d.get("results", []):
                by_uuid[f["filing_uuid"]] = row(f)
        rows = list(by_uuid.values())
        if len(rows) == total:
            break
        print(f"  {year} {period}: got {len(rows)} unique of {total} (filings posted mid-download?), retrying", flush=True)
    if len(rows) < total * 0.999:
        raise RuntimeError(f"{year} {period}: got {len(rows)} of {total}")
    tmp = part
    with gzip.open(tmp, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(FIELDS)
        w.writerows(rows)
    tmp.rename(path)
    return f"saved {len(rows)}"


def commit(msg):
    subprocess.run(["git", "add", "data/lda"], check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode:
        subprocess.run(["git", "commit", "-qm", msg], check=True)
        for _ in range(3):
            if subprocess.run(["git", "pull", "--rebase", "--autostash", "-q"]).returncode == 0 and \
               subprocess.run(["git", "push", "-q"]).returncode == 0:
                return
            time.sleep(10)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not KEY:
        # Anonymous access is 8x slower and would use ~5,500 GitHub Actions minutes,
        # more than the free monthly allowance shared with the user's other bots.
        print("No LDA_API_KEY secret yet - waiting. Add it to start downloading.", flush=True)
        return
    print("mode: API key", flush=True)
    for y, p in quarters_due():
        t = time.time()
        res = fetch_quarter(y, p)
        print(y, p, res, f"{(time.time() - t) / 60:.1f} min, 429s so far: {STATS['429']}", flush=True)
        if res == "out_of_time":
            break
        if res.startswith("saved") and "--no-commit" not in sys.argv:
            commit(f"LDA filings {y} {p} [skip ci]")
    missing = [q for q in quarters_due() if not (OUT / f"{q[0]}_{q[1]}.csv.gz").exists()]
    print("quarters still missing:", len(missing))


if __name__ == "__main__":
    main()

"""SEC data: listed companies (with former names) and point-in-time fundamentals."""
import json
import os
import time
from pathlib import Path

import requests

UA = {"User-Agent": f"lobbying-signal research {os.environ.get('SEC_EMAIL', '')}"}
CACHE = Path(__file__).resolve().parent.parent / "data" / "sec"
LISTED = {"NYSE", "Nasdaq", "CBOE", "NYSE American", "NYSE Arca"}


def get(url):
    for i in range(6):
        time.sleep(0.13)                       # SEC asks for <= 10 requests/second
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code == 404:
            return None
        if r.status_code in (429, 503):
            time.sleep(10 * (i + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(url)


def companies():
    """Exchange-listed companies (no OTC), with former names from SEC submissions."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "companies.json"
    if path.exists() and time.time() - path.stat().st_mtime < 7 * 86400:
        return json.loads(path.read_text())
    d = get("https://www.sec.gov/files/company_tickers_exchange.json")
    seen, out = set(), []
    for cik, name, ticker, exch in d["data"]:
        if exch not in LISTED or cik in seen or not ticker:
            continue
        seen.add(cik)
        out.append({"cik": cik, "name": name, "ticker": ticker.replace(".", "-"), "exchange": exch})
    for c in out:
        s = get(f"https://data.sec.gov/submissions/CIK{c['cik']:010d}.json") or {}
        c["former_names"] = [f["name"] for f in s.get("formerNames", [])]
        c["sic"] = s.get("sic")
        c["sic_desc"] = s.get("sicDescription")
    path.write_text(json.dumps(out))
    return out


def _series(facts, ns, concepts, unit, annual=False):
    for concept in concepts:
        items = facts.get(ns, {}).get(concept, {}).get("units", {}).get(unit, [])
        rows = []
        for it in items:
            if it.get("form") not in ("10-K", "10-Q", "10-K/A", "10-Q/A", "20-F", "40-F"):
                continue
            if annual:
                if not it.get("start"):
                    continue
                days = (_d(it["end"]) - _d(it["start"]))
                if not 330 <= days <= 400:
                    continue
            rows.append([it["end"], it["filed"], it["val"]])
        if rows:
            return rows
    return []


def _d(s):
    from datetime import date
    return date.fromisoformat(s).toordinal()


def fundamentals(ciks):
    """{cik: {'ni': [[end, filed, val]], 'eq': [...], 'sh': [...]}} cached on disk."""
    path = CACHE / "fundamentals.json"
    have = json.loads(path.read_text()) if path.exists() else {}
    for cik in ciks:
        if str(cik) in have:
            continue
        f = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json")
        facts = (f or {}).get("facts", {})
        sh = _series(facts, "dei", ["EntityCommonStockSharesOutstanding"], "shares")
        # several share classes reported for the same date/filing -> add them up
        agg = {}
        for end, filed, val in sh:
            agg[(end, filed)] = agg.get((end, filed), 0) + val
        have[str(cik)] = {
            "ni": _series(facts, "us-gaap", ["NetIncomeLoss", "ProfitLoss",
                                             "NetIncomeLossAvailableToCommonStockholdersBasic"], "USD", annual=True),
            "eq": _series(facts, "us-gaap", ["StockholdersEquity",
                                             "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], "USD"),
            "sh": [[e, fl, v] for (e, fl), v in agg.items()],
        }
    path.write_text(json.dumps(have))
    return have


def as_of(rows, day_iso):
    """Latest value known on day_iso: newest period end among rows filed by then."""
    known = [r for r in rows if r[1] <= day_iso]
    if not known:
        return None
    known.sort(key=lambda r: (r[0], r[1]))
    return known[-1]

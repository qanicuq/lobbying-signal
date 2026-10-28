"""Turn raw LDA filings into lobbying spend per public company per quarter.

Point-in-time: spend for a quarter is computed only from filings posted on or
before a cutoff date, and for each (registrant, client, quarter) only the most
recent filing posted by then counts (so amendments replace originals).
Company spend = in-house 'expenses' + outside firms' 'income'.
"""
import csv
import gzip
import re
from collections import defaultdict
from pathlib import Path

PERIOD_Q = {"first_quarter": 1, "second_quarter": 2, "third_quarter": 3, "fourth_quarter": 4}
SKIP_TYPES = {"RR", "RA"}           # registrations, not activity reports

LEGAL = {"INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LLC", "LP", "LLP",
         "LTD", "LIMITED", "PLC", "NA", "N", "A", "SA", "NV", "AG", "SE", "THE", "HOLDINGS",
         "HOLDING", "DE", "DEL", "DELAWARE"}
AFFIL = re.compile(r"\b(AND|&)\s+(ITS\s+)?(AFFILIATES|SUBSIDIARIES|SUBSIDIARY|AFFILIATED COMPANIES)\b")
PAREN = re.compile(r"\(([^)]*)\)?")
FKA = re.compile(r"^\s*(F/?K/?A|FORMERLY( KNOWN AS)?|FKA:?|ON BEHALF OF|OBO|DBA|D/B/A)\s*", re.I)


def norm(name):
    """Normalise a company name for exact matching (no fuzzy matching on purpose)."""
    s = (name or "").upper().replace("&AMP;", "&")
    s = AFFIL.sub(" ", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    words = [w for w in s.split() if w not in LEGAL]
    return " ".join(words)


def name_keys(client_name):
    """Main name plus any former name written in parentheses, e.g. '(FKA RAYTHEON ...)'."""
    raw = client_name or ""
    keys = []
    inner = PAREN.findall(raw)
    main = PAREN.sub(" ", raw)
    for part in [main] + inner:
        part = FKA.sub("", part)
        k = norm(part)
        if k and k not in keys:
            keys.append(k)
    return keys


def load_filings(folder):
    """{(year, quarter): [(registrant_id, client_id, client_name, dt_posted, amount), ...]}"""
    by_q = defaultdict(list)
    for f in sorted(Path(folder).glob("*.csv.gz")):
        if ".partial" in f.name:
            continue
        with gzip.open(f, "rt", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["filing_type"] in SKIP_TYPES:
                    continue
                amt = r["expenses"] or r["income"]
                q = (int(r["filing_year"]), PERIOD_Q[r["filing_period"]])
                by_q[q].append((r["registrant_id"], r["client_id"], r["client_name"],
                                r["dt_posted"], float(amt) if amt else 0.0))
    return by_q


def spend_by_client(by_q, quarter, cutoff_iso):
    """{client_name: spend} for one quarter, using filings posted by cutoff."""
    latest = {}
    for r in by_q.get(quarter, []):
        if r[3][:10] > cutoff_iso:
            continue
        k = (r[0], r[1])
        if k not in latest or r[3] > latest[k][3]:
            latest[k] = r
    out = defaultdict(float)
    for r in latest.values():
        out[r[2]] += r[4]
    return out


def build_name_index(companies):
    """companies: list of dicts with cik, ticker, name, former_names (list).
    Returns {normalised key: cik}; keys shared by 2+ companies are dropped."""
    idx = defaultdict(set)
    for c in companies:
        names = [c["name"]] + list(c.get("former_names", []))
        for n in names:
            k = norm(n)
            if not k:
                continue
            idx[k].add(c["cik"])
            if k.endswith(" GROUP") and len(k) > 10:      # 'AMERICAN AIRLINES GROUP' ~ 'AMERICAN AIRLINES'
                idx[k[:-6]].add(c["cik"])
    return {k: next(iter(v)) for k, v in idx.items() if len(v) == 1}


def company_spend(client_spend, index):
    """Roll client-level spend up to SEC CIKs. Unmatched clients are ignored."""
    out = defaultdict(float)
    matched = {}
    for client, amt in client_spend.items():
        for k in name_keys(client):
            if k in index:
                out[index[k]] += amt
                matched[client] = index[k]
                break
    return out, matched

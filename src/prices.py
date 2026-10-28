"""Daily prices from Yahoo (via yfinance), cached as one gzipped CSV per ticker."""
import gzip
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE = Path(__file__).resolve().parent.parent / "data" / "prices"


def load(tickers, start="2008-01-01"):
    """{ticker: DataFrame[date index; adj, close, split]}; missing tickers are left out."""
    CACHE.mkdir(parents=True, exist_ok=True)
    need = [t for t in tickers if not (CACHE / f"{t}.csv.gz").exists()]
    for i in range(0, len(need), 80):
        batch = need[i:i + 80]
        df = yf.download(batch, start=start, auto_adjust=False, actions=True,
                         progress=False, group_by="ticker", threads=True)
        for t in batch:
            try:
                sub = df[t] if len(batch) > 1 else df
                sub = sub.dropna(subset=["Close"])
            except KeyError:
                sub = pd.DataFrame()
            out = pd.DataFrame({"adj": sub.get("Adj Close"), "close": sub.get("Close"),
                                "split": sub.get("Stock Splits")}) if len(sub) else \
                pd.DataFrame(columns=["adj", "close", "split"])
            with gzip.open(CACHE / f"{t}.csv.gz", "wt") as fh:
                out.to_csv(fh, index_label="date")
        time.sleep(2)
    res = {}
    for t in tickers:
        p = CACHE / f"{t}.csv.gz"
        if p.exists():
            d = pd.read_csv(p, index_col="date", parse_dates=True)
            if len(d):
                d["split"] = d["split"].fillna(0)
                res[t] = d
    return res


def price_on_or_after(df, day):
    """(row position, row) of the first trading day on/after `day`, or None."""
    pos = df.index.searchsorted(pd.Timestamp(day))
    if pos >= len(df):
        return None
    return pos, df.iloc[pos]


def split_factor_after(df, day):
    """Product of split ratios strictly after `day` (to undo Yahoo's split adjustment)."""
    s = df.loc[df.index > pd.Timestamp(day), "split"]
    s = s[s > 0]
    return float(s.prod()) if len(s) else 1.0

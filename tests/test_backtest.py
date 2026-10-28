"""End-to-end run on synthetic data (no network)."""
import csv, gzip, json, sys, tempfile, types, random, pathlib
from datetime import date
import pandas as pd
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.modules["yfinance"] = types.SimpleNamespace(Ticker=lambda t: types.SimpleNamespace(options=("2026-01-16", "2028-01-21")))
import backtest as bt, sec, prices, panel

def main():
    tmp = pathlib.Path(tempfile.mkdtemp())
    bt.ROOT, bt.RES = tmp, tmp / "results"
    (tmp / "data" / "lda").mkdir(parents=True)
    random.seed(1)
    cos = [{"cik": i, "name": f"Company{i} Inc", "ticker": f"T{i}", "former_names": [], "sic_desc": "x"} for i in range(60)]
    sec.companies = lambda: cos
    # filings 2015-2018; companies 0-4 triple their spend in 2016Q2
    periods = ["first_quarter", "second_quarter", "third_quarter", "fourth_quarter"]
    for y in (2015, 2016, 2017, 2018):
        for k, per in enumerate(periods, 1):
            with gzip.open(tmp / "data" / "lda" / f"{y}_{per}.csv.gz", "wt", newline="") as fh:
                w = csv.writer(fh); w.writerow(["filing_uuid","filing_type","filing_year","filing_period","dt_posted","registrant_id","client_id","client_name","self_filer","income","expenses"])
                m = 3 * k + 1; post = date(y + (m > 12), (m - 1) % 12 + 1, 15).isoformat() + "T09:00:00-05:00"
                for c in cos:
                    amt = 200000 * (3 if (c["cik"] < 5 and (y, k) == (2016, 2)) else 1)
                    w.writerow([f"u{y}{k}{c['cik']}", f"Q{k}", y, per, post, "r" + str(c["cik"]), "c" + str(c["cik"]), f"COMPANY{c['cik']}, INC.", "True", "", amt])
                w.writerow(["x", "RR", y, per, post, "r", "c", "COMPANY1 INC", "", "", "999999999"])
    idx = pd.bdate_range("2014-01-01", "2020-12-31")
    def fake_load(tickers, start=None):
        out = {}
        for t in tickers:
            base = [100.0] * len(idx)
            if t in ("T0", "T1", "T2", "T3", "T4"):     # winners after the 2016Q2 signal (2016-07-22)
                base = [100.0 if d < pd.Timestamp("2016-07-25") else 150.0 for d in idx]
            df = pd.DataFrame({"adj": base, "close": base, "split": 0.0}, index=idx)
            out[t] = df
        return out
    prices.load = fake_load
    sec.fundamentals = lambda ciks: {str(c): {"ni": [["2015-12-31", "2016-02-20", 1e8]], "eq": [["2015-12-31", "2016-02-20", 1e9]], "sh": [["2016-02-01", "2016-02-20", 1e6]]} for c in ciks}
    bt.run()
    rows = json.loads((bt.RES / "backtest_rows.json").read_text())
    r = [x for x in rows if x["quarter"] == "2016Q2" and x["variant"] == "qoq" and x["filter"] == "all"][0]
    assert sorted(p["ticker"] for p in r["picks"])[:5] == ["T0", "T1", "T2", "T3", "T4"], r["picks"]
    assert abs(r["12m"]["picks"] - 0.25) < 1e-9 and abs(r["12m"]["universe"] - 5 * 0.5 / 60) < 1e-9
    # mcap = 100 * 1e6 = 1e8; P/E = 1, P/B = .1 -> cheap
    assert r["picks"][0]["cheap"] is True and r["picks"][0]["mcap"] == 1e8
    print((bt.RES / "summary.md").read_text()[:1500])
    print("backtest test passed")
main()

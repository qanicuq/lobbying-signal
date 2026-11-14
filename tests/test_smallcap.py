"""End-to-end checks for the small-company slice (no network)."""
import sys, pathlib, types
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.modules["yfinance"] = types.SimpleNamespace()
import smallcap_check as sc


def main():
    idx = pd.bdate_range("2010-01-04", periods=300)
    adj = [100.0]
    for _ in range(299):
        adj.append(adj[-1] * 1.01)
    df = pd.DataFrame({"adj": adj, "close": adj, "split": 0.0}, index=idx)
    r, _complete = sc.pick_returns(df, idx[0], 0.0)
    assert len(r) == 252
    assert all(abs(float(x) - 0.01) < 1e-9 for x in r)
    r2, _complete = sc.pick_returns(df, idx[0], 0.01)
    assert abs(float(r2.iloc[0]) - (0.01 - 0.005)) < 1e-9
    assert abs(float(r2.iloc[-1]) - (0.01 - 0.005)) < 1e-9
    days = pd.bdate_range("2019-04-01", periods=3)
    daily = pd.Series([0.10, 0.10, 0.10], index=days)
    month = sc.to_monthly(daily)
    assert abs(float(month.iloc[0]) - (1.1 * 1.1 * 1.1 - 1)) < 1e-12
    d0 = pd.Timestamp("2020-01-06")
    d1 = pd.Timestamp("2020-01-07")
    a = pd.Series([0.20], index=[d0])
    b = pd.Series([0.40, 0.10], index=[d0, d1])
    avg, cnt = sc.portfolio_daily([a, b])
    assert abs(float(avg.loc[d0]) - (0.20 + 0.40) / 2) < 1e-12
    assert int(cnt.loc[d0]) == 2
    gap_idx = pd.bdate_range("2020-03-02", periods=3)
    gap_df = pd.DataFrame({"adj": [1.0, 1.0, 1.0], "close": [1.0, 1.0, 1.0], "split": 0.0}, index=gap_idx)
    assert sc.prices.price_on_or_after(gap_df, "2020-02-28")[0] == 0
    assert sc.prices.price_on_or_after(gap_df, "2020-02-20") is None
    assert sc.prices.price_on_or_after(gap_df, "2020-03-10") is None
    print("smallcap test passed")


main()

"""Strict re-check of the small-company lobbying-jump slice."""
import json
import math
import sys
from pathlib import Path
from statistics import mean, median

import pandas as pd

import prices

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
SMALL_CAP = 2e9
HOLD_DAYS = 252
COSTS = [0.0, 0.005, 0.01, 0.02]
MAIN_COST = 0.01
LOOKS = 16
T_BAR = 2.95
SPLIT = "2018-01"
FROZEN_ON = "2026-11-14"


def load_picks():
    rows = json.loads((RES / "backtest_rows.json").read_text())
    kept = []
    for row in rows:
        if row["variant"] != "qoq":
            continue
        if row["filter"] != "all":
            continue
        for pick in row["picks"]:
            if pick["mcap"] is None:
                continue
            if pick["mcap"] >= SMALL_CAP:
                continue
            kept.append({"ticker": pick["ticker"], "signal_day": row["signal_day"]})
    return kept


def pick_returns(df, signal_day, cost):
    got = prices.price_on_or_after(df, signal_day)
    if got is None:
        return (None, False)
    pos = got[0]
    end = min(pos + HOLD_DAYS, len(df) - 1)
    complete = pos + HOLD_DAYS <= len(df) - 1
    if end <= pos:
        return (None, False)
    window = df["adj"].pct_change().iloc[pos + 1:end + 1]
    vals = [float(x) for x in window]
    if len(vals) == 1:
        vals[0] = vals[0] - cost
    else:
        vals[0] = vals[0] - cost / 2
        vals[-1] = vals[-1] - cost / 2
    return (pd.Series(vals, index=window.index), complete)


def portfolio_daily(series_list):
    table = pd.concat(series_list, axis=1)
    average = table.mean(axis=1)
    count = table.count(axis=1)
    keep = count > 0
    return average[keep], count[keep]


def to_monthly(daily):
    vals = []
    labels = []
    for per, part in daily.groupby(daily.index.to_period("M")):
        labels.append(str(per))
        vals.append(float((1.0 + part).prod() - 1.0))
    return pd.Series(vals, index=labels)


def stats(xs):
    if len(xs) < 2:
        return None
    n = len(xs)
    m = mean(xs)
    med = median(xs)
    sd = (sum((x - m) ** 2 for x in xs) / (n - 1)) ** 0.5
    t = None if sd == 0 else m / (sd / math.sqrt(n))
    win = sum(1 for x in xs if x > 0) / n
    return {"n": n, "mean": m, "median": med, "t": t, "win": win}


def run_once(picks, px, cost):
    series_list = []
    for pick in picks:
        ticker = pick["ticker"]
        if ticker not in px:
            continue
        r, _complete = pick_returns(px[ticker], pick["signal_day"], cost)
        if r is None:
            continue
        series_list.append(r)
    cols = ["month", "picks_held", "portfolio", "iwm", "spy", "excess_vs_iwm"]
    if not series_list:
        return pd.DataFrame(columns=cols)
    port, counts = portfolio_daily(series_list)
    iwm_d = px["IWM"]["adj"].pct_change()
    iwm_d = iwm_d.loc[iwm_d.index.isin(port.index)].dropna()
    spy_d = px["SPY"]["adj"].pct_change()
    spy_d = spy_d.loc[spy_d.index.isin(port.index)].dropna()
    port_m = to_monthly(port)
    iwm_m = to_monthly(iwm_d)
    spy_m = to_monthly(spy_d)
    held = {}
    for per, part in counts.groupby(counts.index.to_period("M")):
        held[str(per)] = int(part.max())
    rows = []
    for month in port_m.index:
        portfolio = float(port_m.loc[month])
        iwm = float(iwm_m.loc[month]) if month in iwm_m.index else float("nan")
        spy = float(spy_m.loc[month]) if month in spy_m.index else float("nan")
        excess = portfolio - iwm if month in iwm_m.index else float("nan")
        rows.append({
            "month": month,
            "picks_held": held.get(month, 0),
            "portfolio": portfolio,
            "iwm": iwm,
            "spy": spy,
            "excess_vs_iwm": excess,
        })
    return pd.DataFrame(rows, columns=cols)


def per_pick(picks, px):
    out = []
    for pick in picks:
        ticker = pick["ticker"]
        if ticker not in px:
            continue
        r, complete = pick_returns(px[ticker], pick["signal_day"], MAIN_COST)
        if r is None or not complete:
            continue
        ret = float((1.0 + r).prod() - 1.0)
        iwm = px["IWM"]["adj"].pct_change().reindex(r.index)
        iwm_ret = float((1.0 + iwm).prod() - 1.0)
        out.append({
            "ticker": ticker,
            "signal_day": pick["signal_day"],
            "ret": ret,
            "iwm": iwm_ret,
            "excess": ret - iwm_ret,
        })
    return out


def open_picks(picks, px):
    out = []
    for pick in picks:
        ticker = pick["ticker"]
        if ticker not in px:
            continue
        r, complete = pick_returns(px[ticker], pick["signal_day"], MAIN_COST)
        if r is None or complete:
            continue
        ret = float((1.0 + r).prod() - 1.0)
        iwm = px["IWM"]["adj"].pct_change().reindex(r.index)
        iwm_ret = float((1.0 + iwm).prod() - 1.0)
        out.append({
            "ticker": ticker,
            "signal_day": pick["signal_day"],
            "ret_so_far": ret,
            "iwm_so_far": iwm_ret,
        })
    return out


def _missing(x):
    return x is None or pd.isna(x)


def _pct(x):
    if _missing(x):
        return "n/a"
    return f"{float(x) * 100:+.1f}%"


def _tfmt(t):
    if _missing(t):
        return "n/a"
    return f"{float(t):.2f}"


def _cost_label(cost):
    return f"{cost * 100:.1f}%".replace(".0%", "%")


def _grow(values):
    g = 1.0
    for x in values:
        if _missing(x):
            continue
        g *= 1.0 + float(x)
    return g


def _excesses(df):
    if df is None or len(df) == 0:
        return []
    return [float(x) for x in df["excess_vs_iwm"] if pd.notna(x)]


def _picks_used(picks, px, cost, lo=None, hi=None):
    n = 0
    for pick in picks:
        ticker = pick["ticker"]
        if ticker not in px:
            continue
        r, _complete = pick_returns(px[ticker], pick["signal_day"], cost)
        if r is None:
            continue
        if lo is None and hi is None:
            n += 1
            continue
        months = {str(per) for per in r.index.to_period("M")}
        if any((lo is None or m >= lo) and (hi is None or m < hi) for m in months):
            n += 1
    return n


def _summary_row(label, df, n_picks):
    xs = _excesses(df)
    st = stats(xs)
    months = len(df)
    mean_x = mean(xs) if xs else None
    win = (sum(1 for x in xs if x > 0) / len(xs)) if xs else None
    t = None if st is None else st["t"]
    g_p = _grow(df["portfolio"]) if len(df) else 1.0
    g_i = _grow(df["iwm"]) if len(df) else 1.0
    return (
        f"| {label} | {months} | {n_picks} | {g_p:.4f} | {g_i:.4f} | "
        f"{_pct(mean_x)} | {_pct(win)} | {_tfmt(t)} |"
    )


def _so_far(px, pick):
    ticker = pick["ticker"]
    if ticker not in px:
        return None, None
    r, _complete = pick_returns(px[ticker], pick["signal_day"], MAIN_COST)
    if r is None:
        return None, None
    ret = float((1.0 + r).prod() - 1.0)
    iwm = px["IWM"]["adj"].pct_change().reindex(r.index)
    iwm_ret = float((1.0 + iwm).prod() - 1.0)
    return ret, iwm_ret


def main():
    if not (RES / "backtest_rows.json").exists():
        print("backtest_rows.json missing; skipping.")
        return
    picks = load_picks()
    tickers = [p["ticker"] for p in picks]
    tickers.append("IWM")
    tickers.append("SPY")
    px = prices.load(tickers)
    if "IWM" not in px or "SPY" not in px:
        print("IWM or SPY prices missing; skipping.")
        return
    tables = {}
    for cost in COSTS:
        tables[cost] = run_once(picks, px, cost)
    monthly = tables[MAIN_COST]
    out = monthly.copy()
    for col in ("portfolio", "iwm", "spy", "excess_vs_iwm"):
        out[col] = out[col].round(4)
    out.to_csv(RES / "smallcap_monthly.csv", index=False)
    done = per_pick(picks, px)
    still = open_picks(picks, px)

    lines = []
    lines.append("# Small-company lobbying-jump re-check")
    lines.append("")
    lines.append(
        "Rule tested: quarter-over-quarter top-10 lobbying jumps, only companies worth under $2B "
        "on the signal day, bought on the first trading day on/after the signal day, held 252 trading days, "
        "equal weight across whatever is held each day."
    )
    lines.append(
        "Baseline: IWM (small-company index fund), measured on exactly the same days. "
        "SPY is measured on exactly the same days."
    )
    lines.append(
        f"Versions looked at before choosing this slice: {LOOKS}. "
        f"Because of that, the 'not luck' bar is t >= {T_BAR}, not 2."
    )
    lines.append("No bet sizing is used. If this is ever traded, size at half-Kelly or less, never full Kelly.")
    lines.append("")
    header = (
        "| round-trip cost | months | picks used | growth of $1 in portfolio | "
        "growth of $1 in IWM | average monthly excess vs IWM | months beating IWM (%) | t-stat |"
    )
    rule = "|---|---|---|---|---|---|---|---|"
    lines.append("## Results by trading cost (all months)")
    lines.append("")
    lines.append(header)
    lines.append(rule)
    for cost in COSTS:
        lines.append(_summary_row(_cost_label(cost), tables[cost], _picks_used(picks, px, cost)))
    lines.append("")
    lines.append("## Older half vs newer half (cost 1%)")
    lines.append("")
    lines.append(header)
    lines.append(rule)
    if len(monthly):
        older = monthly[monthly["month"] < SPLIT]
        newer = monthly[monthly["month"] >= SPLIT]
    else:
        older = monthly
        newer = monthly
    lines.append(_summary_row(
        f"{_cost_label(MAIN_COST)} before {SPLIT}",
        older,
        _picks_used(picks, px, MAIN_COST, hi=SPLIT),
    ))
    lines.append(_summary_row(
        f"{_cost_label(MAIN_COST)} from {SPLIT}",
        newer,
        _picks_used(picks, px, MAIN_COST, lo=SPLIT),
    ))
    lines.append("")
    lines.append("## Per pick (complete 12-month holds, cost 1%)")
    lines.append("")
    excesses = [p["excess"] for p in done if not _missing(p["excess"])]
    lines.append(f"Number of picks: {len(done)}")
    if excesses:
        lines.append(f"Average excess vs IWM: {_pct(mean(excesses))}")
        lines.append(f"Median excess vs IWM: {_pct(median(excesses))}")
        lines.append(f"Share of picks beating IWM: {_pct(sum(1 for x in excesses if x > 0) / len(excesses))}")
    else:
        lines.append("Average excess vs IWM: n/a")
        lines.append("Median excess vs IWM: n/a")
        lines.append("Share of picks beating IWM: n/a")
    ordered = sorted(done, key=lambda p: p["excess"], reverse=True)
    rest = [p["excess"] for p in ordered[3:] if not _missing(p["excess"])]
    dropped = mean(rest) if rest else None
    lines.append(f"Average excess vs IWM with the 3 best picks removed: {_pct(dropped)}")
    lines.append("")
    lines.append("3 best picks:")
    if not ordered:
        lines.append("None.")
    else:
        for p in ordered[:3]:
            lines.append(f"- {p['ticker']} {p['signal_day']} {_pct(p['excess'])}")
    lines.append("")
    lines.append(f"## Never-seen picks (signal day after {FROZEN_ON})")
    lines.append("")
    frozen = [p for p in picks if p["signal_day"] > FROZEN_ON]
    if not frozen:
        lines.append("None yet. The first will be the Q4 2026 filings (signal day 2027-01-22).")
    else:
        lines.append("| ticker | signal day | return so far | IWM so far |")
        lines.append("|---|---|---|---|")
        for p in frozen:
            ret, iwm_ret = _so_far(px, p)
            lines.append(f"| {p['ticker']} | {p['signal_day']} | {_pct(ret)} | {_pct(iwm_ret)} |")
    lines.append("")
    lines.append("## Open picks (12 months not finished)")
    lines.append("")
    if not still:
        lines.append("None.")
    else:
        lines.append("| ticker | signal day | return so far | IWM so far |")
        lines.append("|---|---|---|---|")
        for p in still:
            lines.append(
                f"| {p['ticker']} | {p['signal_day']} | {_pct(p['ret_so_far'])} | {_pct(p['iwm_so_far'])} |"
            )
    lines.append("")
    lines.append("## Month by month (cost 1%)")
    lines.append("")
    lines.append("| month | picks held | portfolio | IWM | SPY | excess vs IWM |")
    lines.append("|---|---|---|---|---|---|")
    for _, row in monthly.iterrows():
        lines.append(
            f"| {row['month']} | {int(row['picks_held'])} | {_pct(row['portfolio'])} | "
            f"{_pct(row['iwm'])} | {_pct(row['spy'])} | {_pct(row['excess_vs_iwm'])} |"
        )
    lines.append("")
    all_st = stats(_excesses(monthly))
    old_xs = _excesses(older)
    new_xs = _excesses(newer)
    old_mean = mean(old_xs) if old_xs else None
    new_mean = mean(new_xs) if new_xs else None
    passes = (
        all_st is not None
        and all_st["t"] is not None
        and all_st["t"] >= T_BAR
        and old_mean is not None
        and old_mean > 0
        and new_mean is not None
        and new_mean > 0
    )
    if passes:
        lines.append("Verdict: PASSES the strict check.")
    else:
        lines.append("Verdict: NOT PROVEN.")
    lines.append(
        "Limits: only companies still listed today have prices, so failed or bought-out companies are missing. "
        "Picks with unknown size (mostly 2008–2010) are left out. Both halves were already seen when this slice "
        "was chosen, so only the never-seen picks are a true out-of-sample test."
    )
    lines.append("")
    report = "\n".join(lines)
    (RES / "smallcap_check.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()

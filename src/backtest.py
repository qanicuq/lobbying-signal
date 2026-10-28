"""Backtest: do big jumps in lobbying spend come before better stock returns?

For each quarter, on the 22nd of the month after the quarter ends (2 days after
the filing deadline), rank public companies by lobbying growth using only
filings posted by the 21st. Buy the top N equally; measure returns over
3, 6 and 12 months against (a) every lobbying company in the same universe and
(b) SPY. Variants: quarter-over-quarter vs year-over-year growth, and with or
without a Graham cheapness test (P/E x P/B <= 22.5, positive earnings/equity).
"""
import json
import math
import os
from datetime import date
from pathlib import Path
from statistics import mean, median

import panel
import prices
import sec

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
TOP_N = int(os.environ.get("TOP_N", "10"))
MIN_SPEND = float(os.environ.get("MIN_SPEND", "100000"))   # this quarter, to skip tiny bases
MIN_PREV = float(os.environ.get("MIN_PREV", "20000"))      # comparison quarter
HORIZONS = {"3m": 63, "6m": 126, "12m": 252}
SMALL_CAP = 2e9


def quarter_shift(q, n):
    y, k = q
    i = y * 4 + (k - 1) + n
    return (i // 4, i % 4 + 1)


def signal_day(q):
    y, k = q
    m = 3 * k + 1
    return date(y + (m > 12), (m - 1) % 12 + 1, 22)


def fwd_return(df, day, n):
    a = prices.price_on_or_after(df, day)
    if a is None:
        return None, False
    pos, row = a
    if not row["close"] or row["close"] < 1:
        return None, False
    end = min(pos + n, len(df) - 1)
    full = pos + n <= len(df) - 1
    return float(df.iloc[end]["adj"] / row["adj"] - 1), full


def market_cap(df, f, day_iso):
    sh = sec.as_of(f.get("sh", []), day_iso)
    a = prices.price_on_or_after(df, day_iso)
    if not sh or a is None:
        return None
    return float(a[1]["close"]) * sh[2] * prices.split_factor_after(df, sh[0])


def cheap(mcap, f, day_iso):
    ni, eq = sec.as_of(f.get("ni", []), day_iso), sec.as_of(f.get("eq", []), day_iso)
    if not mcap or not ni or not eq or ni[2] <= 0 or eq[2] <= 0:
        return None if (not ni or not eq or not mcap) else False
    return (mcap / ni[2]) * (mcap / eq[2]) <= 22.5


def run():
    RES.mkdir(exist_ok=True)
    if len(list((ROOT / "data" / "lda").glob("*.csv.gz"))) < 12:
        print("Not enough lobbying history downloaded yet (need 12+ quarters); skipping.")
        return
    cos = sec.companies()
    by_cik = {c["cik"]: c for c in cos}
    index = panel.build_name_index(cos)
    filings = panel.load_filings(ROOT / "data" / "lda")
    quarters = sorted(filings)
    print("quarters with data:", len(quarters), quarters[:1], quarters[-1:])

    # point-in-time spend for each signal quarter and its comparison quarters
    spend = {}
    for q in quarters:
        cut = signal_day(q).replace(day=21).isoformat()
        for back in (0, 1, 4):
            qq = quarter_shift(q, -back)
            if qq not in quarters:
                continue
            cs = panel.spend_by_client(filings, qq, cut)
            spend[(q, back)], _ = panel.company_spend(cs, index)
    ever = sorted({cik for (q, b), s in spend.items() if b == 0 for cik, v in s.items() if v >= MIN_SPEND})
    print("public companies with >= min spend in some quarter:", len(ever))
    px = prices.load([by_cik[c]["ticker"] for c in ever] + ["SPY"])
    funda = sec.fundamentals(ever)

    variants = {"qoq": 1, "yoy": 4}
    rows = []
    for q in quarters:
        cur = spend.get((q, 0))
        if not cur:
            continue
        day = signal_day(q)
        if day > date.today():
            continue
        dayi = day.isoformat()
        universe = []
        for cik, v in cur.items():
            t = by_cik[cik]["ticker"]
            if v < MIN_SPEND or t not in px:
                continue
            rets = {h: fwd_return(px[t], day, n) for h, n in HORIZONS.items()}
            if rets["3m"][0] is None:
                continue
            mc = market_cap(px[t], funda.get(str(cik), {}), dayi)
            universe.append({"cik": cik, "ticker": t, "spend": v, "rets": rets, "mcap": mc,
                             "cheap": cheap(mc, funda.get(str(cik), {}), dayi)})
        if len(universe) < 30:
            continue
        spy = {h: fwd_return(px["SPY"], day, n) for h, n in HORIZONS.items()}
        for vname, back in variants.items():
            prev = spend.get((q, back))
            if not prev:
                continue
            ranked = []
            for u in universe:
                p = prev.get(u["cik"], 0)
                if p >= MIN_PREV:
                    ranked.append({**u, "prev": p, "growth": u["spend"] / p - 1})
            ranked.sort(key=lambda r: r["growth"], reverse=True)
            for filt in ("all", "cheap"):
                pool = ranked if filt == "all" else [r for r in ranked if r["cheap"]]
                picks = pool[:TOP_N]
                if len(picks) < 3:
                    continue
                rec = {"quarter": f"{q[0]}Q{q[1]}", "signal_day": dayi, "variant": vname, "filter": filt,
                       "n_picks": len(picks), "n_universe": len(universe),
                       "picks": [{"ticker": p["ticker"], "growth": round(p["growth"], 2),
                                  "spend": p["spend"], "prev": p["prev"], "mcap": p["mcap"],
                                  "cheap": p["cheap"], **{h: p["rets"][h][0] for h in HORIZONS}}
                                 for p in picks]}
                for h in HORIZONS:
                    full = all(p["rets"][h][1] for p in picks) and spy[h][1]
                    rec[h] = {"full_period": full,
                              "picks": mean(p["rets"][h][0] for p in picks),
                              "universe": mean(u["rets"][h][0] for u in universe),
                              "spy": spy[h][0]}
                rows.append(rec)
    (RES / "backtest_rows.json").write_text(json.dumps(rows, indent=1, default=str))
    summarise(rows)
    candidates(spend, quarters, by_cik, px, funda)
    sample_check(spend, quarters, by_cik)


def stats(xs):
    if len(xs) < 2:
        return None
    m, s = mean(xs), (sum((x - mean(xs)) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
    return {"n": len(xs), "mean": m, "median": median(xs), "t": m / (s / math.sqrt(len(xs))) if s else None,
            "win": sum(x > 0 for x in xs) / len(xs)}


def summarise(rows):
    out = {}
    lines = ["# Lobbying-jump backtest", "",
             f"Top {TOP_N} by lobbying growth each quarter; this-quarter spend >= ${MIN_SPEND:,.0f}, "
             f"comparison-quarter spend >= ${MIN_PREV:,.0f}. Returns include dividends.", "",
             "Excess = picks minus the average of every lobbying company in the same universe that quarter "
             "(both groups are today's survivors, which cancels much of the survivorship bias). "
             "Only fully completed holding periods are counted.", "",
             "| Variant | Filter | Hold | Quarters | Avg picks | Avg universe | Avg SPY | Avg excess vs universe | Quarters beating universe | t-stat* |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for v in ("qoq", "yoy"):
        for f in ("all", "cheap"):
            for h in HORIZONS:
                sel = [r for r in rows if r["variant"] == v and r["filter"] == f and r[h]["full_period"]]
                ex = [r[h]["picks"] - r[h]["universe"] for r in sel]
                st = stats(ex)
                if not st:
                    continue
                out[f"{v}_{f}_{h}"] = {**st, "picks": mean(r[h]["picks"] for r in sel),
                                       "universe": mean(r[h]["universe"] for r in sel),
                                       "spy": mean(r[h]["spy"] for r in sel)}
                o = out[f"{v}_{f}_{h}"]
                tval = f"{st['t']:.2f}" if st["t"] is not None else "n/a"
                lines.append(f"| {v.upper()} | {f} | {h} | {st['n']} | {o['picks']:+.1%} | {o['universe']:+.1%} | "
                             f"{o['spy']:+.1%} | {st['mean']:+.1%} | {st['win']:.0%} | {tval} |")
    lines += ["", "*t-stat: roughly, above 2 suggests the result is unlikely to be luck. For 6- and 12-month holds "
              "the quarterly periods overlap, which overstates it.", ""]
    # small vs large caps, pooled across picks (qoq, all, 12m)
    for v in ("qoq", "yoy"):
        sel = [r for r in rows if r["variant"] == v and r["filter"] == "all" and r["12m"]["full_period"]]
        for label, test in (("small (<$2B)", lambda m: m and m < SMALL_CAP), ("large (>=$2B)", lambda m: m and m >= SMALL_CAP)):
            ex = [p["12m"] - r["12m"]["universe"] for r in sel for p in r["picks"] if test(p["mcap"]) and p["12m"] is not None]
            st = stats(ex)
            if st:
                lines.append(f"- {v.upper()} 12-month, {label} picks: {st['n']} picks, avg excess {st['mean']:+.1%}, "
                             f"median {st['median']:+.1%}, beat universe {st['win']:.0%} of the time")
        big = [p["12m"] for r in sel for p in r["picks"] if p["12m"] is not None]
        if big:
            lines.append(f"- {v.upper()} 12-month: {sum(x >= 0.25 for x in big) / len(big):.0%} of individual picks rose 25%+ "
                         f"(a rough bar for a LEAP to pay off); {sum(x <= -0.25 for x in big) / len(big):.0%} fell 25%+")
    lines += ["", "Limits: Yahoo and the SEC ticker list only cover companies still listed today, so firms that went "
              "bust or were bought are missing. Lobbying clients are matched to companies by exact normalised name "
              "(including former names); subsidiaries lobbying under their own names are missed. Cheapness uses the "
              "latest annual net income and latest equity filed before the signal date."]
    (RES / "summary.json").write_text(json.dumps(out, indent=1))
    (RES / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def candidates(spend, quarters, by_cik, px, funda):
    """Newest quarter's biggest jumps, with cheapness and whether LEAPs are listed."""
    import yfinance as yf
    q = quarters[-1]
    cur, prev, yago = spend.get((q, 0), {}), spend.get((q, 1), {}), spend.get((q, 4), {})
    day = signal_day(q)
    dayi = min(day, date.today()).isoformat()
    rows = []
    for cik, v in cur.items():
        p = prev.get(cik, 0)
        if v < MIN_SPEND or p < MIN_PREV:
            continue
        t = by_cik[cik]["ticker"]
        f = funda.get(str(cik), {})
        mc = market_cap(px[t], f, dayi) if t in px else None
        rows.append({"ticker": t, "name": by_cik[cik]["name"], "sector": by_cik[cik].get("sic_desc"),
                     "spend": v, "prev_q": p, "qoq": v / p - 1,
                     "yoy": (v / yago[cik] - 1) if yago.get(cik, 0) >= MIN_PREV else None,
                     "mcap": mc, "cheap": cheap(mc, f, dayi)})
    rows.sort(key=lambda r: r["qoq"], reverse=True)
    top = rows[:25]
    cutoff = date.today().replace(year=date.today().year + 1).isoformat()
    for r in top:
        try:
            exps = yf.Ticker(r["ticker"]).options
            r["leaps"] = [e for e in exps if e >= cutoff]
        except Exception:
            r["leaps"] = None
    (RES / "latest_candidates.json").write_text(json.dumps({"quarter": f"{q[0]}Q{q[1]}", "rows": top}, indent=1, default=str))


def sample_check(spend, quarters, by_cik):
    """Spend for a few well-known lobbyers, to compare by hand with lda.gov."""
    want = {"RTX", "LMT", "BA", "GD", "NOC", "GOOGL", "AMZN", "META", "PFE", "KO"}
    q = quarters[-1]
    out = {by_cik[c]["ticker"]: v for c, v in spend.get((q, 0), {}).items() if by_cik[c]["ticker"] in want}
    (RES / "sample_check.json").write_text(json.dumps({"quarter": f"{q[0]}Q{q[1]}", "spend": out}, indent=1))


if __name__ == "__main__":
    run()

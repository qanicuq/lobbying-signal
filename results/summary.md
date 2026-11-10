# Lobbying-jump backtest

Top 10 by lobbying growth each quarter; this-quarter spend >= $100,000, comparison-quarter spend >= $20,000. Returns include dividends.

Excess = picks minus the average of every lobbying company in the same universe that quarter (both groups are today's survivors, which cancels much of the survivorship bias). Only fully completed holding periods are counted.

| Variant | Filter | Hold | Quarters | Avg picks | Avg universe | Avg SPY | Avg excess vs universe | Quarters beating universe | t-stat* |
|---|---|---|---|---|---|---|---|---|---|
| QOQ | all | 3m | 70 | +5.2% | +4.2% | +3.3% | +1.0% | 47% | 0.95 |
| QOQ | all | 6m | 67 | +9.7% | +8.6% | +7.3% | +1.1% | 48% | 0.85 |
| QOQ | all | 12m | 63 | +19.6% | +17.4% | +15.2% | +2.3% | 48% | 1.07 |
| QOQ | cheap | 3m | 65 | +4.7% | +4.2% | +3.5% | +0.4% | 45% | 0.41 |
| QOQ | cheap | 6m | 60 | +9.2% | +7.9% | +7.2% | +1.3% | 52% | 1.06 |
| QOQ | cheap | 12m | 58 | +18.3% | +16.1% | +14.7% | +2.2% | 41% | 0.83 |
| YOY | all | 3m | 68 | +4.2% | +4.8% | +4.0% | -0.6% | 49% | -0.51 |
| YOY | all | 6m | 64 | +8.6% | +9.1% | +8.1% | -0.5% | 45% | -0.30 |
| YOY | all | 12m | 62 | +17.1% | +17.7% | +15.7% | -0.6% | 40% | -0.26 |
| YOY | cheap | 3m | 64 | +4.2% | +4.5% | +3.8% | -0.3% | 47% | -0.37 |
| YOY | cheap | 6m | 57 | +9.8% | +8.5% | +7.9% | +1.3% | 44% | 1.07 |
| YOY | cheap | 12m | 55 | +19.8% | +16.9% | +15.5% | +2.9% | 56% | 1.23 |

*t-stat: roughly, above 2 suggests the result is unlikely to be luck. For 6- and 12-month holds the quarterly periods overlap, which overstates it.

- QOQ 12-month, small (<$2B) picks: 53 picks, avg excess +34.5%, median +14.9%, beat universe 57% of the time
- QOQ 12-month, large (>=$2B) picks: 410 picks, avg excess -0.7%, median -5.2%, beat universe 42% of the time
- QOQ 12-month: 36% of individual picks rose 25%+ (a rough bar for a LEAP to pay off); 13% fell 25%+
- YOY 12-month, small (<$2B) picks: 75 picks, avg excess +11.3%, median -16.0%, beat universe 40% of the time
- YOY 12-month, large (>=$2B) picks: 390 picks, avg excess -1.6%, median -5.4%, beat universe 39% of the time
- YOY 12-month: 33% of individual picks rose 25%+ (a rough bar for a LEAP to pay off); 17% fell 25%+

Limits: Yahoo and the SEC ticker list only cover companies still listed today, so firms that went bust or were bought are missing. Lobbying clients are matched to companies by exact normalised name (including former names); subsidiaries lobbying under their own names are missed. Cheapness uses the latest annual net income and latest equity filed before the signal date.

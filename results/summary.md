# Lobbying-jump backtest

Top 10 by lobbying growth each quarter; this-quarter spend >= $100,000, comparison-quarter spend >= $20,000. Returns include dividends.

Excess = picks minus the average of every lobbying company in the same universe that quarter (both groups are today's survivors, which cancels much of the survivorship bias). Only fully completed holding periods are counted.

| Variant | Filter | Hold | Quarters | Avg picks | Avg universe | Avg SPY | Avg excess vs universe | Quarters beating universe | t-stat* |
|---|---|---|---|---|---|---|---|---|---|
| QOQ | all | 3m | 70 | +5.3% | +4.3% | +3.3% | +0.9% | 50% | 0.91 |
| QOQ | all | 6m | 68 | +9.1% | +8.0% | +6.9% | +1.1% | 49% | 0.88 |
| QOQ | all | 12m | 65 | +19.1% | +17.3% | +15.1% | +1.8% | 48% | 0.85 |
| QOQ | cheap | 3m | 60 | +5.5% | +4.3% | +3.4% | +1.2% | 48% | 1.17 |
| QOQ | cheap | 6m | 60 | +9.2% | +7.9% | +7.2% | +1.3% | 52% | 1.03 |
| QOQ | cheap | 12m | 58 | +18.3% | +16.1% | +14.7% | +2.2% | 41% | 0.83 |
| YOY | all | 3m | 67 | +4.6% | +4.9% | +4.0% | -0.3% | 49% | -0.26 |
| YOY | all | 6m | 64 | +8.8% | +8.9% | +7.8% | -0.1% | 47% | -0.05 |
| YOY | all | 12m | 62 | +17.7% | +17.8% | +15.7% | -0.1% | 40% | -0.04 |
| YOY | cheap | 3m | 58 | +5.0% | +4.5% | +3.8% | +0.5% | 52% | 0.61 |
| YOY | cheap | 6m | 57 | +9.8% | +8.5% | +7.9% | +1.3% | 46% | 1.06 |
| YOY | cheap | 12m | 55 | +19.8% | +16.9% | +15.5% | +2.9% | 56% | 1.25 |

*t-stat: roughly, above 2 suggests the result is unlikely to be luck. For 6- and 12-month holds the quarterly periods overlap, which overstates it.

- QOQ 12-month, small (<$2B) picks: 55 picks, avg excess +34.8%, median +14.9%, beat universe 58% of the time
- QOQ 12-month, large (>=$2B) picks: 425 picks, avg excess -1.4%, median -6.3%, beat universe 41% of the time
- QOQ 12-month: 35% of individual picks rose 25%+ (a rough bar for a LEAP to pay off); 13% fell 25%+
- YOY 12-month, small (<$2B) picks: 74 picks, avg excess +11.7%, median -17.3%, beat universe 41% of the time
- YOY 12-month, large (>=$2B) picks: 389 picks, avg excess -2.1%, median -5.9%, beat universe 39% of the time
- YOY 12-month: 32% of individual picks rose 25%+ (a rough bar for a LEAP to pay off); 17% fell 25%+

Limits: Yahoo and the SEC ticker list only cover companies still listed today, so firms that went bust or were bought are missing. Lobbying clients are matched to companies by exact normalised name (including former names); subsidiaries lobbying under their own names are missed. Cheapness uses the latest annual net income and latest equity filed before the signal date.

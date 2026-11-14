# Lobbying-jump backtest

Top 10 by lobbying growth each quarter; this-quarter spend >= $100,000, comparison-quarter spend >= $20,000. Returns include dividends.

Excess = picks minus the average of every lobbying company in the same universe that quarter (both groups are today's survivors, which cancels much of the survivorship bias). Only fully completed holding periods are counted.

| Variant | Filter | Hold | Quarters | Avg picks | Avg universe | Avg SPY | Avg excess vs universe | Quarters beating universe | t-stat* |
|---|---|---|---|---|---|---|---|---|---|
| QOQ | all | 3m | 73 | +5.2% | +4.0% | +3.3% | +1.2% | 53% | 1.38 |
| QOQ | all | 6m | 72 | +9.6% | +8.1% | +7.2% | +1.5% | 53% | 1.33 |
| QOQ | all | 12m | 70 | +19.1% | +17.2% | +15.1% | +1.9% | 50% | 1.08 |
| QOQ | cheap | 3m | 66 | +4.8% | +3.8% | +3.5% | +1.0% | 47% | 1.06 |
| QOQ | cheap | 6m | 65 | +8.3% | +7.5% | +7.3% | +0.8% | 55% | 0.65 |
| QOQ | cheap | 12m | 63 | +16.9% | +15.7% | +14.8% | +1.3% | 40% | 0.52 |
| YOY | all | 3m | 70 | +4.8% | +4.4% | +3.9% | +0.4% | 51% | 0.40 |
| YOY | all | 6m | 69 | +8.9% | +8.5% | +7.7% | +0.5% | 51% | 0.31 |
| YOY | all | 12m | 67 | +17.0% | +16.9% | +15.3% | +0.1% | 43% | 0.03 |
| YOY | cheap | 3m | 66 | +4.3% | +3.8% | +3.5% | +0.5% | 48% | 0.67 |
| YOY | cheap | 6m | 65 | +8.9% | +7.5% | +7.3% | +1.4% | 52% | 1.26 |
| YOY | cheap | 12m | 63 | +18.2% | +15.7% | +14.8% | +2.6% | 56% | 1.28 |

*t-stat: roughly, above 2 suggests the result is unlikely to be luck. For 6- and 12-month holds the quarterly periods overlap, which overstates it.

- QOQ 12-month, small (<$2B) picks: 59 picks, avg excess +42.2%, median +22.5%, beat universe 61% of the time
- QOQ 12-month, large (>=$2B) picks: 494 picks, avg excess -1.8%, median -4.8%, beat universe 41% of the time
- QOQ 12-month: 34% of individual picks rose 25%+ (a rough bar for a LEAP to pay off); 13% fell 25%+
- YOY 12-month, small (<$2B) picks: 82 picks, avg excess +7.6%, median -12.7%, beat universe 40% of the time
- YOY 12-month, large (>=$2B) picks: 462 picks, avg excess -1.6%, median -5.1%, beat universe 39% of the time
- YOY 12-month: 31% of individual picks rose 25%+ (a rough bar for a LEAP to pay off); 17% fell 25%+

Limits: Yahoo and the SEC ticker list only cover companies still listed today, so firms that went bust or were bought are missing. Lobbying clients are matched to companies by exact normalised name (including former names); subsidiaries lobbying under their own names are missed. Cheapness uses the latest annual net income and latest equity filed before the signal date.

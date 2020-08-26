# asset-doctor
Simple Financial Portfolio tools in Python3

Copyright (c) 2020 Eric Colton

## Portfolio Rebalancer

The markets may have made you rich but something feels lacking.  Will money not bring true happiness?  Unfortunately, true happiness can only be achieved with beauty.  A beautiful perfectly-weigthed portfolio.

Use *portfolio_rebalancer.py* to rebalance your portfolio with ease.

This tool compares your financial portfolio with a hypothetical "model" portfolio with which you have populated with securities with ideal weights.

This tool supports the following rebalancing styles:

* Simple whole-share rebalancing
* Fractional-share rebalancing
* Rebalancing by exchanging shares (e.g. Vanguard mutual funds)
* Optionally takes into account cash infusion or withdrawl

### excel_rebalancer.py

*excel_rebalancer.py* is an example command-line-oriented program that wraps *Portfolio Rebalancer*.  It assumes a very specific spreadsheet format that details your "model" and "current" portfolios, as well as asset prices.  (This format is not at all standard - I created this so I can copy/paste directly from a spreadsheet I created.)

Expected format for *excel_rebalancer.py*:

The first input requested via *stdin* should be a tab-formatted like the spreadsheet diagramed below.  (Do not include the header titles).  The program uses this to determine the model portfolio, and uses the other data to validate the "balanced" and "actual" portfolios later on.

**Summary Rows:**

| Ticker | Target % | Balanced $ | Actual $   |
|--------|----------|------------|------------|
| VTI    | 33%      | $3,254.10  | $3,302.07  |
| VEA    | 15%      | $1,479.77  | $1,359.95  |
| VWO    | 12%      | $1,183.22  | $1,144.96  |
| VIG    | 6%       | $591.11    | $639.80    |
| XLE    | 5%       | $493.92    | $255.68    |
| MUB    | 29%      | $2,859.36  | $3,160.02  |

The next input *excel_rebalancer.py* requires are the quantities and prices of the positions in the "current" portfolio.  These need to be in the following 3-row tab-delimited format.  Note that the listing of securities extends horizonatally.

| VTI | VTI     | VEA | VEA    | VWO | VWO    | VIG | VIG     | XLE | XLE    | MUB | MUB     |
|-----|---------|-----|--------|-----|--------|-----|---------|-----|--------|-----|---------|
|     | $16.26  |     | $4.03  |     | $4.28  |     | $12.29  |     | $3.75  |     | $11.66  |
|     | 203     |     | 337    |     | 267    |     | 52      |     | 68     |     | 271     |

Each security consists of two rows.  The "ticker" on the first row for each column pair must match.  On the second row is the share price, and on the third row is the current portfolio's position (# of shares) in that security.

Following these inputs, the program asks about the following options:

* Whether or not rebalance instructions can based on share exchanges (e.g. Vanguard mutual funds)
* Whether or not rebalancing should take into account an infusion or withdraw of cash
* Whether or not purchase or sale of fractional shares is allowed
* If fractional shares are not allowed, then the rounding behavior can be customized.

The program generates a report including buy, sell, and/or exhange instructions and a summary of the rebalanced portfolio.

## Whole-Share Rebalancing Report (Example)
```
Rebalance Instructions:

        MUB     SELL    26      shares  (-$303.16)
        VIG     SELL    4       shares  (-$ 48.80)
        VTI     SELL    3       shares  (-$ 48.78)
        XLE     BUY     63      shares  ( $236.25)
        VEA     BUY     30      shares  ( $120.90)
        VWO     BUY     9       shares  ( $ 38.52)

Value of rebalanced portfolio:  $9,845.84
        vs target value:        $9,850.91
        vs current value:       $9,850.91

Options Applied:
        Allow Share Exchanges: NO
        Fractional Shares: NO
        Rounding Behavior: NEAREST
```

## Fractional-Share Rebalancing Report (Example)
```
Rebalance Instructions:

        MUB     SELL    25.99   shares  (-$303.10)
        VTI     SELL    3.07    shares  (-$ 49.98)
        VIG     SELL    3.55    shares  (-$ 43.35)
        XLE     BUY     63.35   shares  ( $237.55)
        VEA     BUY     29.66   shares  ( $119.53)
        VWO     BUY     9.19    shares  ( $ 39.35)

Value of rebalanced portfolio:  $9,850.91
        vs target value:        $9,850.91
        vs current value:       $9,850.91

Options Applied:
        Allow Share Exchanges: NO
        Fractional Shares: YES
```

## Rebalancing with Share Exchanges (Example)
```
Rebalance Instructions:

        MUB     EXCHANGE        20.37   shares  ($237.55)       for     XLE     63.35   shares
        MUB     EXCHANGE        5.62    shares  ($ 65.55)       for     VEA     16.27   shares
        VTI     EXCHANGE        3.07    shares  ($ 49.98)       for     VEA     12.40   shares
        VIG     EXCHANGE        3.23    shares  ($ 39.35)       for     VWO     9.19    shares
        VIG     EXCHANGE        0.33    shares  ($  4.00)       for     VEA     0.99    shares

Value of rebalanced portfolio:  $9,850.91
        vs target value:        $9,850.91
        vs current value:       $9,850.91

Options Applied:
        Allow Share Exchanges: YES
        Fractional Shares: YES
```


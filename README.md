# asset-doctor
Simple Financial Portfolio tools in Python3

## Portfolio Rebalancer

The markets may have made you rich but something feels lacking.  Will money not bring true happiness?  Unfortunately, true happiness can only be achieved with beauty.  And by beauty I mean a beautifially-weigthed portfolio.

Use *portfolio_rebalancer.py* to rebalance your portfolio with ease.

This tool compares your financial portfolio with a hypothetical "model" portfolio with which you have populated with securities with ideal weights.

This tool supports the following rebalancing styles:

* Simple whole-share rebalancing
* Fractional-share rebalancing
* Rebalancing by exchanging shares (e.g. Vanguard mutual funds)
* Optionally takes into account cash infusion or withdrawl

### excel_rebalancer.py

*excel_rebalancer.py* is an example command-line oriented application that wraps *Portfolio Rebalancer*.  This assumes a very specific spreadsheet format that details your model and "live" portfolios, as well as asset prices.  Maybe someday I'll get around to generalizing this thing!


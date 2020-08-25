
import math
from enum import Enum
from collections import namedtuple
from assetdoctor import Portfolio, Position

RebalanceOptions = namedtuple('RebalanceOptions', ['desired_total_value', 'allow_fractional_shares', 'rounding_behavior'])

class RoundingBehavior(Enum):
    UP = 'UP'
    DOWN = 'DOWN'
    NEAREST = 'NEAREST'

class PortfolioRebalancer:

    def __init__(self, options: RebalanceOptions):
        self.options = options
        self.live_portfolio = None
        self.model_portfolio = None

    def set_live_portfolio(self, live_portfolio: Portfolio):
        self.live_portfolio = live_portfolio

    def set_model_portfolio(self, model_portfolio: Portfolio):
        self.model_portfolio = model_portfolio

    def build_rebalance_instructions(self) -> dict:
        if not (self.live_portfolio and self.model_portfolio):
            raise Exception("live_portfolio and model_portfolio must both be set")

        delta_shares = {}
        for mp_ticker in self.model_portfolio.all_tickers():
            mp_quantity = self.model_portfolio.get_quantity(mp_ticker)
            live_quantity = self.live_portfolio.get_quantity(mp_ticker)
            ticker_delta = mp_quantity - live_quantity
            if not self.options.allow_fractional_shares:
                if self.options.rounding_behavior == RoundingBehavior.NEAREST:
                    ticker_delta = round(ticker_delta)
                elif self.options.rounding_behavior == RoundingBehavior.UP:
                    ticker_delta = math.ceil(ticker_delta)
                elif self.options.rounding_behavior == RoundingBehavior.DOWN:
                    ticker_delta = math.floor(ticker_delta)
                else:
                    raise Exception("Rounding behavior required but not specified")
            delta_shares[mp_ticker] = ticker_delta

        for live_ticker in self.live_portfolio.all_tickers():
            if not self.model_portfolio.contains_ticker(live_ticker):
                delta_shares[live_ticker] = -1 * self.live_portfolio.get_quantity(live_ticker)
        return delta_shares

    def build_rebalanced_portfolio(self) -> Portfolio:
        instructions = self.build_rebalance_instructions()
        rebalanced_portfolio = Portfolio()
        for ticker in self.live_portfolio.all_tickers():
            adjusted_quantity = self.live_portfolio.get_quantity(ticker)
            if ticker in instructions:
                adjusted_quantity += instructions[ticker]
                del instructions[ticker]
            if adjusted_quantity != 0.0:
                rebalanced_portfolio.add_position(Position(ticker, adjusted_quantity))
        for ticker in instructions.keys():
            rebalanced_portfolio.add_position(Position(ticker, instructions[ticker]))
        return rebalanced_portfolio

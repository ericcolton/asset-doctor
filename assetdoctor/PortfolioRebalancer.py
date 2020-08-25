'''
Author: Eric Colton
Copyright (c) 2020 Eric Colton
'''

import math
from enum import Enum
from collections import namedtuple, deque, defaultdict
from . import Portfolio, Position

RebalanceOptions = namedtuple('RebalanceOptions', ['target_total_value', 'allow_share_exchanges', 'allow_fractional_shares', 'rounding_behavior'])
RebalanceInstruction = namedtuple('RebalanceInstruction', ['ticker', 'transaction_type', 'quantity', 'exchange_ticker', 'exchange_quantity'])

class TransactionType(Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    EXCHANGE = 'EXCHANGE'

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

    def build_rebalance_instructions(self) -> list:
        if not (self.live_portfolio and self.model_portfolio):
            raise Exception("live_portfolio and model_portfolio must both be set")

        instructions = []
        if self.options.allow_share_exchanges:
            live_portfolio = self.live_portfolio.deepcopy()
            model_portfolio = self.model_portfolio.deepcopy()
        else:
            live_portfolio = self.live_portfolio
            model_portfolio = self.model_portfolio

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
            direction = TransactionType.BUY if ticker_delta > 0 else TransactionType.SELL
            instructions.append(RebalanceInstruction(mp_ticker, direction, abs(ticker_delta), None, None))

        for live_ticker in live_portfolio.all_tickers():
            if not model_portfolio.contains_ticker(live_ticker):
                instructions.append(RebalanceInstruction(live_ticker, TransactionType.SELL, self.live_portfolio.get_quantity(live_ticker), None, None))
        return instructions

    def build_rebalanced_portfolio(self) -> Portfolio:
        instructions = self.build_rebalance_instructions()
        rebalanced = defaultdict(float)
        for ticker in self.live_portfolio.all_tickers():
            rebalanced[ticker] = self.live_portfolio.get_quantity(ticker)
        
        for i in instructions:
            if i.transaction_type == TransactionType.BUY:
                rebalanced[i.ticker] += i.quantity
            elif i.transaction_type == TransactionType.SELL:
                rebalanced[i.ticker] -= i.quantity
            elif i.transaction_type == TransactionType.EXCHANGE:
                rebalanced[i.ticker] -= i.quantity
                rebalanced[i.exchange_ticker] += i.exchange_quantity
            else:
                raise Exception(f"Unexpected transaction type: '{i.transaction_type}'")
            
        rebalanced_portfolio = Portfolio()
        for ticker, quantity in rebalanced.items():
            if quantity != 0.0:
                rebalanced_portfolio.add_position(Position(ticker, quantity))
        return rebalanced_portfolio

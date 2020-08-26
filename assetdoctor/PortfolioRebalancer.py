'''
Author: Eric Colton
Copyright (c) 2020 Eric Colton
'''

import math
import heapq
from enum import Enum
from collections import namedtuple, defaultdict
from . import Portfolio, Position, PriceLookup

DEFAULT_TOLERANCE = .01

RebalanceOptions = namedtuple('RebalanceOptions', ['target_total_value', 'allow_share_exchanges', 'allow_fractional_shares', 'rounding_behavior'])
RebalanceInstruction = namedtuple('RebalanceInstruction', ['transaction_type', 'ticker', 'quantity', 'counter_ticker', 'counter_quantity'])

class TransactionType(Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    EXCHANGE = 'EXCHANGE'

class RoundingBehavior(Enum):
    UP = 'UP'
    DOWN = 'DOWN'
    NEAREST = 'NEAREST'

class PortfolioRebalancer:

    def __init__(self, prices: PriceLookup, options: RebalanceOptions, tolerance: float = DEFAULT_TOLERANCE):
        self.prices = prices
        self.options = options
        self.tolerance = tolerance
        self.live_portfolio = None
        self.model_portfolio = None

    def set_live_portfolio(self, live_portfolio: Portfolio):
        self.live_portfolio = live_portfolio

    def set_model_portfolio(self, model_portfolio: Portfolio):
        self.model_portfolio = model_portfolio

    def build_rebalance_instructions(self) -> list:
        if not (self.live_portfolio and self.model_portfolio):
            raise Exception("live_portfolio and model_portfolio must both be set")

        deltas = defaultdict(float)
        for mp_ticker in self.model_portfolio.all_tickers():
            mp_quantity = self.model_portfolio.get_quantity(mp_ticker)
            live_quantity = self.live_portfolio.get_quantity(mp_ticker)
            delta = mp_quantity - live_quantity
            if not self.options.allow_fractional_shares:
                if self.options.rounding_behavior == RoundingBehavior.NEAREST:
                    delta = round(delta)
                elif self.options.rounding_behavior == RoundingBehavior.UP:
                    delta = math.ceil(delta)
                elif self.options.rounding_behavior == RoundingBehavior.DOWN:
                    delta = math.floor(delta)
                else:
                    raise Exception("Rounding behavior required but not specified")
            if abs(delta) < self.tolerance:
                continue
            deltas[mp_ticker] = delta

        for live_ticker in self.live_portfolio.all_tickers():
            if not self.model_portfolio.contains_ticker(live_ticker):
                quantity = self.live_portfolio.get_quantity(live_ticker)
                if quantity > self.tolerance:
                    deltas[live_ticker] = -quantity
        
        instructions = []
        if self.options.allow_share_exchanges:
            self.__populate_exchange_trades(deltas, instructions)
   
        for ticker, quantity in deltas.items():
            transaction_type = TransactionType.BUY if quantity > 0 else TransactionType.SELL
            instructions.append(RebalanceInstruction(transaction_type, ticker, abs(quantity), None, None))
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
                rebalanced[i.counter_ticker] += i.counter_quantity
            else:
                raise Exception(f"Unexpected transaction type: '{i.transaction_type}'")
            
        rebalanced_portfolio = Portfolio()
        for ticker, quantity in rebalanced.items():
            if quantity != 0.0:
                rebalanced_portfolio.add_position(Position(ticker, quantity))
        return rebalanced_portfolio

    def validate(self):
        validator = PortfolioRebalancer(self.prices, self.options)
        validator.set_model_portfolio(self.model_portfolio)
        validator.set_live_portfolio(self.build_rebalanced_portfolio())
        instructions = validator.build_rebalance_instructions()
        if len(instructions) > 0:
            raise Exception(f"Live portfolio did not rebalance cleanly (re-running the rebalance still generated {len(instructions)} rebalance instructions)")

    def __populate_exchange_trades(self, deltas: dict, instructions: list):
        buys, sells = [], []
        for ticker, quantity in deltas.items():
            value = abs(quantity * self.prices.get_price(ticker))
            if quantity < 0:
                sells.append((-value, ticker))
            else:
                buys.append((-value, ticker))
        heapq.heapify(buys)
        heapq.heapify(sells)
        
        while len(buys) > 0 and len(sells) > 0:
            buy = heapq.heappop(buys)
            buy_value, buy_ticker = abs(buy[0]), buy[1], 
            buy_price = self.prices.get_price(buy_ticker)
            sell = heapq.heappop(sells)                
            sell_value, sell_ticker = abs(sell[0]), sell[1]
            sell_price = self.prices.get_price(sell_ticker)

            if sell_value > buy_value:
                instructions.append(RebalanceInstruction(TransactionType.EXCHANGE, sell_ticker, buy_value / sell_price, buy_ticker, buy_value / buy_price))
                residual_sell_value = sell_value - buy_value
                if residual_sell_value / sell_value > self.tolerance:
                    heapq.heappush(sells, (-residual_sell_value, sell_ticker))
            else:
                instructions.append(RebalanceInstruction(TransactionType.EXCHANGE, sell_ticker, sell_value / sell_price, buy_ticker, sell_value / buy_price))
                residual_buy_value = buy_value - sell_value
                if residual_buy_value / buy_value > self.tolerance:
                    heapq.heappush(buys, (-residual_buy_value, buy_ticker))

        # re-populate deltas with tickers that couldn't be exchanged
        deltas.clear()
        for buy in buys:
            buy_value, buy_ticker = abs(buy[0]), buy[1]
            deltas[buy_ticker] = buy_value / self.prices.get_price(buy_ticker)
        for sell in sells:
            sell_value, sell_ticker = abs(sell[0]), sell[1]
            deltas[sell_ticker] = -sell_value / self.prices.get_price(sell_ticker)

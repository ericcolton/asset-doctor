
from collections import namedtuple
from assetdoctor import PriceLookup

Position = namedtuple('Position', ['ticker', 'quantity'])

class Portfolio:

    def __init__(self):
        self.positions = {}

    def add_position(self, position: Position):
        ticker = position.ticker
        if position.ticker in self.positions:
            raise Exception(f"Ticker '{ticker}' was already added")
        self.positions[ticker] = position

    def get_quantity(self, ticker: str):
        if ticker in self.positions:
            return self.positions[ticker].quantity
        else:
            return 0

    def contains_ticker(self, ticker: str):
        return ticker in self.positions

    def all_tickers(self):
        return self.positions.keys()

    def calc_total_value(self, prices: PriceLookup):
        return sum([prices.get_price(p.ticker) * p.quantity for p in self.positions.values()])


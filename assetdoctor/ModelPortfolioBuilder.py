
from collections import namedtuple
from assetdoctor import Portfolio, Position, PriceLookup

ModelPosition = namedtuple('ModelPosition', ['ticker', 'target_percentage'])

DEFAULT_TOLERANCE = 0.01

class ModelPortfolioBuilder:
    def __init__(self, target_value: float, prices: PriceLookup, tolerance: float = DEFAULT_TOLERANCE):
        self.prices = prices
        self.target_value = target_value
        self.tolerance = tolerance
        self.model_positions = {}

    def add_model_position(self, model_position: ModelPosition):
        ticker = model_position.ticker
        if ticker in self.model_positions:
            raise Exception(f"Ticker '{ticker}' was already added in model positions")
        self.model_positions[ticker] = model_position

    def generate_model_portfolio(self):
        if abs(sum([mp.target_percentage for mp in self.model_positions.values()]) - 100) > self.tolerance:
            raise Exception("Sum of model portfolio target_percentages does not sum to 100%")

        portfolio = Portfolio()
        for mp in self.model_positions.values():
            price = self.prices.get_price(mp.ticker)
            quantity = (self.target_value * mp.target_percentage / 100) / price
            if quantity > 0:
                portfolio.add_position(Position(mp.ticker, quantity))
        return portfolio
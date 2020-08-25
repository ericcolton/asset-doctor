
class PriceLookup:
    def __init__(self):
        self.prices = {}

    def add_price(self, ticker, price):
        if ticker in self.prices:
            raise Exception(f"Ticker '{ticker}' was already added")
        self.prices[ticker] = price

    def get_price(self, ticker):
        if ticker not in self.prices:
            raise Exception(f"Ticker '{ticker}' has associated price")
        return self.prices[ticker]
        
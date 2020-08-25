#!/usr/bin/env python3

import sys
import re
import math
from enum import Enum
from collections import namedtuple, defaultdict


class RoundingBehavior(Enum):
    UP = 'UP'
    DOWN = 'DOWN'
    NEAREST = 'NEAREST'

VALUE_TOLERANCE = 10
PERCENT_TOLERANCE = 0.01

SummaryRecord = namedtuple('Record', ['ticker', 'target_percentage', 'balanced_amount', 'actual_amount'])
ImplementationRecord = namedtuple('ImplementationRecord', ['ticker', 'price', 'quantity'])
Position = namedtuple('Position', ['ticker', 'quantity'])
ModelPosition = namedtuple('ModelPosition', ['ticker', 'target_percentage'])
RebalanceOptions = namedtuple('RebalanceOptions', ['desired_total_value', 'allow_fractional_shares', 'rounding_behavior'])
RebalanceInstruction = namedtuple('RebalanceInstruction', ['ticker','op','quantity_str', 'shares_str', 'sign', 'value_str'])

class NoImplmentationRecordException(Exception):
    pass
class UnusedImplmentationRecordException(Exception):
    pass

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

class ModelPortfolioBuilder:
    def __init__(self, target_value: float, prices: PriceLookup):
        self.prices = prices
        self.target_value = target_value
        self.model_positions = {}

    def add_model_position(self, model_position: ModelPosition):
        ticker = model_position.ticker
        if ticker in self.model_positions:
            raise Exception(f"Ticker '{ticker}' was already added in model positions")
        self.model_positions[ticker] = model_position

    def generate_model_portfolio(self):
        if abs(sum([mp.target_percentage for mp in self.model_positions.values()]) - 100) > PERCENT_TOLERANCE:
            raise Exception("Sum of model portfolio target_percentages does not sum to 100%")

        portfolio = Portfolio()
        for mp in self.model_positions.values():
            price = self.prices.get_price(mp.ticker)
            quantity = (self.target_value * mp.target_percentage / 100) / price
            if quantity > 0:
                portfolio.add_position(Position(mp.ticker, quantity))
        return portfolio

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
            if not options.allow_fractional_shares:
                if options.rounding_behavior == RoundingBehavior.NEAREST:
                    ticker_delta = round(ticker_delta)
                elif options.rounding_behavior == RoundingBehavior.UP:
                    ticker_delta = math.ceil(ticker_delta)
                elif options.rounding_behavior == RoundingBehavior.DOWN:
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

def build_price_lookup(implementation_records: dict) -> PriceLookup:
    prices = PriceLookup()
    for ir in implementation_records.values():
        prices.add_price(ir.ticker, ir.price)
    return prices

def build_live_portfolio(implementation_lookup: dict) -> Portfolio:
    portfolio = Portfolio()
    for ticker, ir in implementation_lookup.items():
        if ir.quantity > 0:
            portfolio.add_position(Position(ticker, ir.quantity))
    return portfolio

def build_model_portfolio(options: RebalanceOptions, summary_records: list, implementation_lookup: dict, prices: PriceLookup) -> Portfolio:
    builder = ModelPortfolioBuilder(options.desired_total_value, prices)
    for sr in summary_records:
        if sr.target_percentage > 0:
            builder.add_model_position(ModelPosition(sr.ticker, sr.target_percentage))
    return builder.generate_model_portfolio()

def validate_impl_record_value(ticker, implementation_lookup: dict):
    if ticker not in implementation_lookup:
        raise NoImplmentationRecordException(f"No record for '{ticker}'")
    impl = implementation_lookup[ticker]
    return impl.price * impl.quantity

def validate_and_value_summary_records(summary_records: list, implementation_lookup: dict):
    # check that the sum of target percentages is 100%
    total_percentage = sum([float(r.target_percentage) for r in summary_records])
    if abs(100.0 - total_percentage) > PERCENT_TOLERANCE:
        raise Exception("target percentage for summary records must total to 100%")
    
    # check that value of implementation positions sum to summary values
    summary_tickers_used = dict()
    for sr in summary_records:
        if sr.actual_amount == 0:
            try:
                total_impl_value = validate_impl_record_value(sr.ticker, implementation_lookup)
                summary_tickers_used[sr.ticker] = total_impl_value
            except NoImplmentationRecordException:
                total_impl_value = 0
        else:
            total_impl_value = validate_impl_record_value(sr.ticker, implementation_lookup)
            summary_tickers_used[sr.ticker] = total_impl_value
        
        if abs(sr.actual_amount - total_impl_value) > VALUE_TOLERANCE:
            raise Exception(f"Value of implementation record {sr.ticker} (${total_impl_value}) does not match "
            f"value reflected in summary record (${sr.actual_amount})")
    
    for impl_record in implementation_lookup.values():
        ticker = impl_record.ticker
        if impl_record.quantity > 0 and ticker not in summary_tickers_used:
            raise UnusedImplmentationRecordException(f"Ticker '{ticker}' is not included in any summary record")

    total_summary_values = sum([sr.actual_amount for sr in summary_records])
    total_ticker_values = sum([summary_tickers_used[ticker] for ticker in summary_tickers_used.keys()])
    if abs(total_summary_values - total_ticker_values) > VALUE_TOLERANCE:
        raise Exception(f"Total summary values ({total_summary_values}) does not equal total instument values ({total_ticker_values})")
    
    return total_summary_values

def capture_desired_portfolio_value(live_portfolio_value: float) -> float:
    print("")
    print(f"Your current portfolio value is ${live_portfolio_value:,.2f}.\n"
    "Please input your desired total value.\n"
    "(Prefix '+' or '-' to specify an offset from the portfolio's current value.)\n"
    "Press return to default to the portfolio's current value:")
    line = sys.stdin.readline().rstrip()
    if line == "":
        return live_portfolio_value
            
    match = re.search(r'^([\+\-])?\$?([\d.,]+)', line)
    if match is None:
        raise Exception(f"Unable to parse desired portfolio value: '{line}'")
    value_specified = float(match.group(2).replace(',',''))
    if match.group(1) == '+':
        return live_portfolio_value + value_specified
    elif match.group(1) == '-':
        return live_portfolio_value - value_specified
    else:
        return value_specified

def capture_allow_fractional_shares() -> bool:
    print("Allow fractional shares (yes/NO)?: ", end = '')
    line = sys.stdin.readline()
    answer = line[0].lower() == 'y'
    return answer

def capture_rounding_behavior() -> RoundingBehavior:
    print("")
    print("How should partial shares be rounded?\n"
        "\t'+'\tAlways round up: Rebalancing may require additional cash\n"
        "\t'-'\tAlways round down: Rebalancing may leave cash uninveseted\n"
        "\t''\tRound to nearest: Rebalancing may either leave or require additional cash\n"

        "Enter '+', '-', or press return for the default behavior: ", end='')
    line = sys.stdin.readline().rstrip()
    if line == "":
        return RoundingBehavior.NEAREST
    if line[0] == '+':
        return RoundingBehavior.UP
    elif line[0] == '-':
        return RoundingBehavior.DOWN
    raise Exception(f"Unrecognized rounding behavior '{line[0]}'")

def capture_rebalance_options(live_portfolio_value: float) -> RebalanceOptions:
    desired_portfolio_value = capture_desired_portfolio_value(live_portfolio_value)
    allow_fractional_shares = capture_allow_fractional_shares()
    rounding_behavior = RoundingBehavior.NEAREST if allow_fractional_shares else capture_rounding_behavior()
    return RebalanceOptions(desired_portfolio_value, allow_fractional_shares, rounding_behavior)

def capture_summary_records():
    print('''Expected Format (columns seperated by tabs):
        <Ticker Description (string)>,
        <Target Percentage From Model (% float)>,
        <$ Amount for Balanaced Portfolio ($ float)>
        <$ Amount for Actual Portfolio ($ float)")

        Enter an extra empty newline to signal records are complete.
        ''')

    line_count = 1
    summary_records = []
    for line in sys.stdin:
        if line == "\n":
            break
        line = line.rstrip('\n')
        regex = r"^(?P<ticker>[^\t]*)\s*?\t"\
            r"(?P<target_percentage>[^\t]*)\s*?\t"\
            r"(?P<balanced_amount>[^\t]*)\s*?\t"\
            r"(?P<actual_amount>[^\t]*)"
        match = re.search(regex, line)
        if match is None:
            raise Exception(f"Unable to read input line {line_count}: '{line}'")
        raw = match.groupdict()

        # ticker
        ticker = raw['ticker'].strip()
        
        # target_percentage
        tp_match = re.search(r'^([\d.]+)\%$', raw['target_percentage'])
        if tp_match is None:
            raise Exception(f"Unable to parse target percentage on line {line_count}: '{raw['target_percentage']}'")
        target_percentage = float(tp_match.group(1))

        # balanced_amount
        ba_match = re.search(r'^\$?([\d.,]+)', raw['balanced_amount'])
        if ba_match is None:
            raise Exception(f"Unable to parse balanced amount on line {line_count}: '{raw['balanced_amount']}'")
        balanced_amount = ba_match.group(1).replace(',', '')
        balanced_amount = float(balanced_amount)

        # actual_amount
        if raw['actual_amount'] == '':
            actual_amount = 0
        else:
            aa_match = re.search(r'^\$?([\d.,]+)', raw['actual_amount'])
            if aa_match is None:
                raise Exception(f"Unable to parse actual amount on line {line_count}: '{raw['actual_amount']}'")
            actual_amount = aa_match.group(1).replace(',', '')
            actual_amount = float(actual_amount)

        record = SummaryRecord(ticker, target_percentage, balanced_amount, actual_amount)
        summary_records.append(record)
        line_count += 1
    return summary_records

def build_implementation_lookup(records: list):
    lookup = {}
    for r in records:
        if r['symbol_1'] != r['symbol_2']:
            raise Exception(f"Ticker symbols must match between columns 1 and 2.\
                 '{r['symbol_1']}' and '{r['symbol_2']}' do not match")
        lookup[r['symbol_1']] = ImplementationRecord(r['symbol_1'], float(r['price']), float(r['quantity']))
    return lookup

def capture_implementation_records():
    print('''Expected Format (Sets of 2-column 3-row entries, repeated horizontally, columns separated by tabs):
    <Ticker>\\t<Ticker>
            \\t<Price>
            \\t<Quantity Held>
    ''')
    
    implementation_records = []
    line_count = 0
    for line in sys.stdin:
        line_count += 1
        if line_count == 1:
            regex_line_1 = re.compile(r'^\s*?(?P<symbol_1>[^\t]+)\s*?\t\s*?(?P<symbol_2>[^\t]+)\s*')
            while len(line) > 0:
                match = regex_line_1.match(line)
                if match:
                    record = {'symbol_1': match.group(1).strip(), 'symbol_2': match.group(2).strip()}
                    implementation_records.append(record)
                    line = regex_line_1.sub('', line)
                else:
                    raise Exception("Unable to parse implementation record on line {line_count}: '{line}'")
        elif line_count == 2:
            regex_line_2 = re.compile(r'^\s*?\t\s*\$?(?P<price>[^\t]+)')
            record_index = 0            
            while len(line) > 0:
                if record_index >= len(implementation_records):
                    raise Exception("Unexpected record #{record_index} on line {line_count}")
                match = regex_line_2.match(line)
                if match:
                    price = match.group('price').strip().replace(',', '')
                    implementation_records[record_index]['price'] = float(price)
                    line = regex_line_2.sub('', line)
                else:
                    raise Exception("Unable to parse implementation record on line {line_count}: '{line}'")
                record_index += 1
        elif line_count == 3:
            regex_line_3 = re.compile(r'^\s*?\t\s*(?P<quantity>[^\t]+)')
            record_index = 0            
            while len(line) > 0:
                if record_index >= len(implementation_records):
                    raise Exception("Unexpected record #{record_index} on line {line_count}")
                match = regex_line_3.match(line)
                if match:
                    quantity = match.group('quantity').strip().replace(',', '')
                    implementation_records[record_index]['quantity'] = float(quantity)
                    line = regex_line_3.sub('', line)
                else:
                    raise Exception("Unable to parse implementation record on line {line_count}: '{line}'")
                record_index += 1
            return build_implementation_lookup(implementation_records)
        else:
            raise Exception("Unexpected reading past line 3")

def output_rebalance_instructions(rebalancer: PortfolioRebalancer, prices: PriceLookup) -> None:
    instructions = rebalancer.build_rebalance_instructions()
    if len(instructions) == 0:
        print("No rebalance actions required.")
        return
    
    print("Rebalance Instructions:")
    sorter = defaultdict(set)
    for ticker, quantity in instructions.items():
        if quantity != 0:
            sorter[prices.get_price(ticker) * quantity].add(ticker)

    formatted_instructions = []
    for value in sorted(sorter.keys()):
        for ticker in sorter[value]:
            quantity = instructions[ticker]
            quantity_str = f"{abs(quantity):,.2f}" if rebalancer.options.allow_fractional_shares else f"{int(abs(quantity)):,}"
            value = quantity * prices.get_price(ticker)
            op = "BUY" if quantity > 0 else "SELL"
            sign = "" if quantity > 0 else "-"
            shares_str = "share" if abs(quantity) == 1.0 else "shares"
            value_str = f"{abs(value):,.2f}"
            formatted_instructions.append(RebalanceInstruction(ticker, op, quantity_str, shares_str, sign, value_str))

    print("")
    max_value_len = max([len(i.value_str) for i in formatted_instructions])
    contains_sells = sum([len(i.sign) for i in formatted_instructions]) > 0
    for i in formatted_instructions:
        value_justified = i.value_str.rjust(max_value_len)
        if contains_sells:
            sign_justified = "-" if i.sign == '-' else " "
        else:
            sign_justified = ""
        print(f"\t{i.ticker}\t{i.op}\t{i.quantity_str}\t{i.shares_str}\t({sign_justified}${value_justified})")
    

def output_rebalance_summary(rebalancer: PortfolioRebalancer, prices: PriceLookup) -> None:
    print("")
    output_rebalance_instructions(rebalancer, prices)
    print("")

    rebalanced_value = rebalancer.build_rebalanced_portfolio().calc_total_value(prices)
    rebalanced_value_str = f"{rebalanced_value:,.2f}"
    target_value = rebalancer.model_portfolio.calc_total_value(prices)
    target_value_str = f"{target_value:,.2f}"
    live_value = rebalancer.live_portfolio.calc_total_value(prices)
    live_value_str = f"{live_value:,.2f}"
    max_total_value_len = max(len(i) for i in [rebalanced_value_str, target_value_str, live_value_str])
    rebalanced_value_str = rebalanced_value_str.rjust(max_total_value_len)
    target_value_str = target_value_str.rjust(max_total_value_len)
    live_value_str = live_value_str.rjust(max_total_value_len)
    print(f"Value of rebalanced portfolio:\t${rebalanced_value_str}\n"
        f"\tvs target value:\t${target_value_str}\n"
        f"\tvs current value:\t${live_value_str}\n")

    print("Options Applied:")
    if rebalancer.options.allow_fractional_shares:
        print("Fractional Shares: YES")
    else:
        print("\tFractional Shares: NO")
        print(f"\tRounding Behavior: {rebalancer.options.rounding_behavior.name}")
    print("")


if __name__ == '__main__':
    print("\nWelcome to Portfolio Rebalancer\n")

    summary_records = capture_summary_records()
    implementation_lookup = capture_implementation_records()
    live_portfolio_value = validate_and_value_summary_records(summary_records, implementation_lookup)
    prices = build_price_lookup(implementation_lookup)
    live_portfolio = build_live_portfolio(implementation_lookup)
    
    options = capture_rebalance_options(live_portfolio_value)
    model_portfolio = build_model_portfolio(options, summary_records, implementation_lookup, prices)

    rebalancer = PortfolioRebalancer(options)
    rebalancer.set_live_portfolio(live_portfolio)
    rebalancer.set_model_portfolio(model_portfolio)
    output_rebalance_summary(rebalancer, prices)

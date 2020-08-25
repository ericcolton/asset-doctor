#!/usr/bin/env python3
'''
Author: Eric Colton
Copyright (c) 2020 Eric Colton
'''

import sys
import re
from collections import namedtuple, defaultdict
from assetdoctor import PriceLookup, Portfolio, Position, ModelPosition, PortfolioRebalancer, \
    ModelPortfolioBuilder, RoundingBehavior, RebalanceOptions, RebalanceInstruction, TransactionType

VALUE_TOLERANCE = 10
PERCENT_TOLERANCE = 0.01

SummaryRecord = namedtuple('Record', ['ticker', 'target_percentage', 'balanced_amount', 'actual_amount'])
ImplementationRecord = namedtuple('ImplementationRecord', ['ticker', 'price', 'quantity'])
FormattedRebalanceInstruction = namedtuple('FormattedRebalanceInstruction', ['ticker','op','quantity_str', 'plural_s', 'sign', 'value_str'])

class NoImplmentationRecordException(Exception):
    pass
class UnusedImplmentationRecordException(Exception):
    pass

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
    builder = ModelPortfolioBuilder(options.target_total_value, prices, PERCENT_TOLERANCE)
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

def capture_allow_share_exchanges() -> bool:
    print("Allow share exchanges (yes/NO)?: ", end = '')
    line = sys.stdin.readline()
    return line[0].lower() == 'y'

def capture_allow_fractional_shares() -> bool:
    print("Allow fractional shares (yes/NO)?: ", end = '')
    line = sys.stdin.readline()
    return line[0].lower() == 'y'

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
    raise Exception(f"Unrecognized rounding behavior '{line}'")

def capture_rebalance_options(live_portfolio_value: float) -> RebalanceOptions:
    desired_portfolio_value = capture_desired_portfolio_value(live_portfolio_value)
    allow_share_exchanges = capture_allow_share_exchanges()
    allow_fractional_shares = True if allow_share_exchanges else capture_allow_fractional_shares()
    rounding_behavior = RoundingBehavior.NEAREST if allow_fractional_shares else capture_rounding_behavior()
    return RebalanceOptions(desired_portfolio_value, allow_share_exchanges, allow_fractional_shares, rounding_behavior)

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
    for instr in instructions:
        if instr.quantity != 0:
            value = prices.get_price(instr.ticker) * instr.quantity
            if instr.transaction_type == TransactionType.SELL:
                value *= -1
            sorter[value].add(instr)

    formatted_instructions = []
    for value in sorted(sorter.keys()):
        for instr in sorter[value]:
            quantity_str = f"{abs(instr.quantity):,.2f}" if rebalancer.options.allow_fractional_shares else f"{int(abs(instr.quantity)):,}"
            value = abs(value)
            op = instr.transaction_type.name
            sign = "-" if instr.transaction_type == TransactionType.SELL else ""
            plural_s = "" if abs(instr.quantity) == 1.0 else "s"
            value_str = f"{abs(value):,.2f}"
            formatted_instructions.append(FormattedRebalanceInstruction(instr.ticker, op, quantity_str, plural_s, sign, value_str))

    print("")
    max_value_len = max([len(i.value_str) for i in formatted_instructions])
    contains_sells = sum([len(i.sign) for i in formatted_instructions]) > 0
    for i in formatted_instructions:
        value_justified = i.value_str.rjust(max_value_len)
        if contains_sells:
            sign_justified = "-" if i.sign == '-' else " "
        else:
            sign_justified = ""
        print(f"\t{i.ticker}\t{i.op}\t{i.quantity_str}\tshare{i.plural_s}\t({sign_justified}${value_justified})")

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

    allow_share_exchanges = "YES" if rebalancer.options.allow_share_exchanges else "NO"
    print("Options Applied:")
    print(f"\tAllow Share Exchanges: {allow_share_exchanges}")
    if rebalancer.options.allow_fractional_shares:
        print("\tFractional Shares: YES")
    else:
        print("\tFractional Shares: NO")
        print(f"\tRounding Behavior: {rebalancer.options.rounding_behavior.name}")
    print("")


if __name__ == '__main__':
    print("\nWelcome to Portfolio Rebalancer\n")

    summary_records = capture_summary_records()
    implementation_lookup = capture_implementation_records()
    validate_and_value_summary_records(summary_records, implementation_lookup)
    prices = build_price_lookup(implementation_lookup)
    live_portfolio = build_live_portfolio(implementation_lookup)
    
    options = capture_rebalance_options(live_portfolio.calc_total_value(prices))
    model_portfolio = build_model_portfolio(options, summary_records, implementation_lookup, prices)

    rebalancer = PortfolioRebalancer(options)
    rebalancer.set_live_portfolio(live_portfolio)
    rebalancer.set_model_portfolio(model_portfolio)
    output_rebalance_summary(rebalancer, prices)

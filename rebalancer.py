#!/usr/bin/env python3

import sys
import re
from collections import namedtuple

VALUE_TOLERANCE = 1
PERCENT_TOLERANCE = 0.01

SummaryRecord = namedtuple('Record', ['asset_class', 'instrument', 'target_percent', 'balanced_amount', 'actual_amount'])
ImplementationRecord = namedtuple('ImplementationRecord', ['instrument', 'price', 'quantity'])

class NoImplmentationRecordException(Exception):
    pass
class UnusedImplmentationRecordException(Exception):
    pass

def validate_impl_record_value(instrument, implementation_lookup: dict):
    if instrument not in implementation_lookup:
        raise NoImplmentationRecordException(f"No record for '{instrument}'")
    impl = implementation_lookup[instrument]
    return impl.price * impl.quantity

def validate_summary_records(summary_records: list, implementation_lookup: dict):

    # check that the sum of target percentages is 100%
    total_percentage = sum([float(r.target_percent) for r in summary_records])
    if abs(100.0 - total_percentage) > PERCENT_TOLERANCE:
        raise Exception("target percentage for summary records must total to 100%")
    
    # check that value of implementation positions sum to summary values
    summary_instruments_used = dict()
    for sr in summary_records:
        # At most two securities can be combined in a 'compound entry'
        compound_match = re.match(r'^(\w+)\s*\+\s*(\w+)$', sr.instrument)
        if compound_match:
            symbol_1, symbol_2 = compound_match.group(1), compound_match.group(2)
            symbol_1_value = validate_impl_record_value(symbol_1, implementation_lookup)
            symbol_2_value = validate_impl_record_value(symbol_2, implementation_lookup)
            summary_instruments_used[symbol_1] = symbol_1_value
            summary_instruments_used[symbol_2] = symbol_2_value
            total_impl_value = symbol_1_value + symbol_2_value
        elif sr.actual_amount == 0:
            try:
                total_impl_value = validate_impl_record_value(sr.instrument, implementation_lookup)
                summary_instruments_used[sr.instrument] = total_impl_value
            except NoImplmentationRecordException:
                total_impl_value = 0
        else:
            total_impl_value = validate_impl_record_value(sr.instrument, implementation_lookup)
            summary_instruments_used[sr.instrument] = total_impl_value
        
        if abs(sr.actual_amount - total_impl_value) > VALUE_TOLERANCE:
            raise Exception(f"Value of implementation record {sr.instrument} (${total_impl_value}) does not match "
            "value reflected in summary record (${sr.actual_amount})")
    
    for impl_record in implementation_lookup.values():
        instrument = impl_record.instrument
        if impl_record.quantity > 0 and instrument not in summary_instruments_used:
            raise UnusedImplmentationRecordException(f"Instrument '{instrument}' is not included in any summary record")

    total_summary_values = sum([sr.actual_amount for sr in summary_records])
    total_instrument_values = sum([summary_instruments_used[instrument] for instrument in summary_instruments_used.keys()])
    if abs(total_summary_values - total_instrument_values) > VALUE_TOLERANCE:
        raise Exception(f"Total summary values ({total_summary_values}) does not equal total instument values ({total_instrument_values})")
    else:
        print(f"SUMMARY: {total_summary_values} IMPL: {total_instrument_values}")

def capture_summary_records():
    print('''Expected Format (columns seperated by tabs):
        <Asset Class Description (string)>,
        <Implemention Instrument Description (string)>,
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
        regex = r"^(?P<asset_class>[^\t]*)\s*?\t"\
            r"(?P<instrument>[^\t]*)\s*?\t"\
            r"(?P<target_percent>[^\t]*)\s*?\t"\
            r"(?P<balanced_amount>[^\t]*)\s*?\t"\
            r"(?P<actual_amount>[^\t]*)"
        match = re.search(regex, line)
        if match is None:
            raise Exception(f"Unable to read input line {line_count}: '{line}'")
        raw = match.groupdict()

        # asset_class
        asset_class = raw['asset_class'].strip()

        # instrument
        instrument = raw['instrument'].strip()
        
        # target_percent
        tp_match = re.search(r'^([\d.]+)\%$', raw['target_percent'])
        if tp_match is None:
            raise Exception(f"Unable to parse target percentage on line {line_count}: '{raw['target_percent']}'")
        target_percent = float(tp_match.group(1))

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

        record = SummaryRecord(asset_class, instrument, target_percent, balanced_amount, actual_amount)
        summary_records.append(record)
        line_count += 1
    return summary_records

def build_implementation_lookup(records: list):
    lookup = {}
    for r in records:
        if r['symbol_1'] != r['symbol_2']:
            raise Exception(f"Instrument symbols must match between columns 1 and 2.\
                 '{r['symbol_1']}' and '{r['symbol_2']}' do not match")
        lookup[r['symbol_1']] = ImplementationRecord(r['symbol_1'], r['price'], r['quantity'])
    return lookup

def capture_implementation_records():
    print('''Expected Format (Sets of 2-column 3-row entries, repeated horizontally, columns separated by tabs):
    <Instrument>\\t<Instrument>
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

if __name__ == '__main__':
    print("\nWelcome to Portfolio Rebalancer\n")

    summary_records = capture_summary_records()
    implementation_lookup = capture_implementation_records()
    validate_summary_records(summary_records, implementation_lookup)


    



    

        
    



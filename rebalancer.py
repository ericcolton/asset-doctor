#!/usr/bin/env python3

import sys
import re
from collections import namedtuple

SummaryRecord = namedtuple('Record', ['asset_class', 'instrament', 'target_percent', 'balanced_amount', 'actual_amount'])

def capture_summary_records():
    print('''Expected Format (columns seperated by tabs):
        <Asset Class Description (string)>,
        <Implemention Instrument Description (string)>,
        <Target Percentage From Model (% float)>,
        <$ Amount for Balanaced Portfolio ($ float)>
        <$ Amount for Actual Portfolio ($ float)")
        ''')

    running_percentage = 0
    line_count = 1
    summary_records = []
    for line in sys.stdin:
        regex = r"^(?P<asset_class>[^\t]*)\s*?\t"\
            r"(?P<instrament>[^\t]*)\s*?\t"\
            r"(?P<target_percent>[^\t]*)\s*?\t"\
            r"(?P<balanced_amount>[^\t]*)\s*?\t"\
            r"(?P<actual_amount>[^\t]*)"
        match = re.search(regex, line)
        if match is None:
            raise Exception(f"Unable to read input line {line_count}: '{line}'")
        raw = match.groupdict()

        # asset_class
        asset_class = raw['asset_class'].strip()

        # instrament
        instrament = raw['instrament'].strip()
        
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
        aa_match = re.search(r'^\$?([\d.,]+)', raw['actual_amount'])
        if aa_match is None:
            raise Exception(f"Unable to parse actual amount on line {line_count}: '{raw['actual_amount']}'")
        actual_amount = aa_match.group(1).replace(',', '')
        actual_amount = float(actual_amount)

        record = SummaryRecord(asset_class, instrament, target_percent, balanced_amount, actual_amount)
        summary_records.append(record)
        
        running_percentage += target_percent
        if running_percentage == 100:
            break
        elif running_percentage > 100:
            raise Exception("Sum total of target percentages cannot exceed 100%")

        line_count += 1
    return summary_records

ImplementationRecord = namedtuple('ImplementationRecord', ['instrument', 'price', 'quantity'])

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
                    implementation_records[record_index]['price'] = price
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
                    implementation_records[record_index]['quantity'] = quantity
                    line = regex_line_3.sub('', line)
                else:
                    raise Exception("Unable to parse implementation record on line {line_count}: '{line}'")
                record_index += 1
            return implementation_records
        else:
            raise Exception("Unexpected reading past line 3")

if __name__ == '__main__':
    print("\nWelcome to Portfolio Rebalancer\n")

    # summary_records = capture_summary_records()
    implementation_records = capture_implementation_records()
    print(implementation_records)

    



    

        
    



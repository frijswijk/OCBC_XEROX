#!/usr/bin/env python3
"""
DFA Simulation Test - Simulates how Papyrus would process the data with the generated DFA
"""
import re

def simulate_dfa_processing(dfa_file, data_file):
    """Simulate DFA processing of data file."""

    # Read DFA and data
    with open(dfa_file, 'r') as f:
        dfa_content = f.read()

    with open(data_file, 'r') as f:
        data_lines = f.readlines()

    print("=" * 80)
    print("DFA PROCESSING SIMULATION")
    print("=" * 80)
    print(f"DFA File: {dfa_file}")
    print(f"Data File: {data_file}")
    print(f"Total lines: {len(data_lines)}")
    print()

    # Extract condition patterns from DFA
    conditions = []
    for line in dfa_content.split('\n'):
        # Pattern: IF SUBSTR(CONTENT, pos, len, '') == 'value'; THEN;
        match = re.search(r"IF SUBSTR\(CONTENT, (\d+), (\d+), ''\) == '([^']+)'", line)
        if match:
            pos, length, value = match.groups()
            # Extract format name from next line
            next_match = re.search(r"USE FORMAT ([^;]+);", line)
            if next_match:
                fmt = next_match.group(1)
            else:
                fmt = "UNKNOWN"
            conditions.append({
                'pos': int(pos),
                'len': int(length),
                'value': value,
                'format': fmt
            })

    print(f"Extracted {len(conditions)} conditional routing rules from DFA")
    print()

    # Process data
    page_count = 0
    line_count = 0
    format_usage = {}

    for line_num, line in enumerate(data_lines, 1):
        if not line.strip():
            continue

        line_count += 1
        cc = line[0] if len(line) > 0 else ' '
        content = line[1:] if len(line) > 1 else ''

        # Check for page break
        if cc == '1':
            page_count += 1
            print(f"\n{'='*60}")
            print(f"PAGE {page_count} - Line {line_num}")
            print(f"{'='*60}")
            continue

        # Apply carriage control
        spacing = {
            '0': 'DOUBLE',
            '-': 'TRIPLE',
            '+': 'OVERPRINT',
            ' ': 'SINGLE'
        }.get(cc, 'SINGLE')

        # Check conditions to determine format
        matched_format = 'FMT_DEFAULT'
        for cond in conditions:
            pos = cond['pos']
            length = cond['len']
            value = cond['value']

            if pos < len(content):
                extracted = content[pos:pos+length]
                if extracted == value or extracted.startswith(value):
                    matched_format = cond['format']
                    break

        # Track format usage
        format_usage[matched_format] = format_usage.get(matched_format, 0) + 1

        # Display interesting lines
        if matched_format != 'FMT_DEFAULT' or page_count <= 1:
            if line_count <= 50:  # Show first 50 lines
                print(f"L{line_num:3} [{cc}] {spacing:8} -> {matched_format:12} | {content[:50]}")

    print()
    print("=" * 80)
    print("PROCESSING SUMMARY")
    print("=" * 80)
    print(f"Total pages: {page_count}")
    print(f"Total lines processed: {line_count}")
    print()
    print("Format usage:")
    for fmt, count in sorted(format_usage.items(), key=lambda x: -x[1]):
        pct = (count / line_count * 100) if line_count > 0 else 0
        print(f"  {fmt:20} : {count:4} times ({pct:5.1f}%)")
    print()

    # Font validation
    print("=" * 80)
    print("FONT DEFINITIONS CHECK")
    print("=" * 80)
    fonts = re.findall(r'FONT (\S+) NOTDEF AS \'([^\']+)\' DBCS ROTATION \d+ HEIGHT ([\d.]+);', dfa_content)
    print(f"Found {len(fonts)} font definitions:")
    for alias, name, size in fonts[:10]:  # Show first 10
        print(f"  {alias:10} -> {name:15} @ {size:5}pt")
    if len(fonts) > 10:
        print(f"  ... and {len(fonts) - 10} more")
    print()

    return {
        'pages': page_count,
        'lines': line_count,
        'formats': format_usage,
        'fonts': len(fonts)
    }

if __name__ == '__main__':
    result = simulate_dfa_processing(
        'output/final_test.dfa/merstmtd.dfa',
        'SAMPLES/FIN886/FIN886P1 - raw data.txt'
    )

    print("=" * 80)
    print("TEST RESULT: PASS" if result['pages'] > 0 else "TEST RESULT: FAIL")
    print("=" * 80)

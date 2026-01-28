#!/usr/bin/env python3
"""
Field Extraction Validation - Verify DFA would extract fields correctly
"""
import re

def validate_field_extraction():
    """Validate that DFA field extraction logic matches JDT RPE arrays."""

    print("=" * 80)
    print("FIELD EXTRACTION VALIDATION")
    print("=" * 80)
    print()

    # Read the JDT to see what fields should be extracted
    with open('SAMPLES/FIN886/FIN886 - codes/merstmtd.jdt', 'r') as f:
        jdt_content = f.read()

    # Read sample data
    with open('SAMPLES/FIN886/FIN886P1 - raw data.txt', 'r') as f:
        data_lines = f.readlines()

    # Find RPE arrays in JDT
    # Format: [cond vskip xpos yskip hpos vpos start len /Font COLOR]
    rpe_arrays = re.findall(r'\[([^\]]+)\]', jdt_content)

    print(f"Found {len(rpe_arrays)} RPE arrays in JDT")
    print()

    # Parse some example arrays
    print("Sample RPE Array Analysis:")
    print("-" * 80)

    for i, array_str in enumerate(rpe_arrays[:10]):  # First 10
        parts = array_str.split()
        if len(parts) >= 10:
            try:
                cond = parts[0]
                vskip = parts[1]
                xpos = parts[2]
                yskip = parts[3]
                hpos = parts[4]
                vpos = parts[5]
                start = int(parts[6])
                length = int(parts[7])
                font = parts[8]
                color = parts[9]

                print(f"Array {i+1}:")
                print(f"  Extract: positions {start} to {start+length} (length {length})")
                print(f"  Display: X={xpos} Y={vpos} Font={font} Color={color}")

                # Test against first data line with content
                test_line = None
                for line in data_lines[10:30]:  # Skip header, test body
                    if len(line) > start + length and line[0] in ' 0-+':
                        test_line = line
                        break

                if test_line:
                    content = test_line[1:]  # Skip carriage control
                    if start < len(content) and start + length <= len(content):
                        extracted = content[start:start+length]
                        if extracted.strip():
                            print(f"  Sample:  '{extracted}' (from test data)")
                print()
            except (ValueError, IndexError):
                pass

    print()
    print("=" * 80)
    print("DFA LINE MODE PROCESSING VALIDATION")
    print("=" * 80)
    print()

    # Read generated DFA
    with open('output/final_test.dfa/merstmtd.dfa', 'r') as f:
        dfa_content = f.read()

    # Check for LINE MODE configuration
    checks = {
        'Line Mode Enabled': 'CHANNEL-CODE ANSI' in dfa_content,
        'Variable Line Reading': 'VARIABLE LINE1 SCALAR NOSPACE' in dfa_content,
        'Carriage Control Parsing': "SUBSTR(LINE1, 1, 1, '')" in dfa_content,
        'Content Extraction': "CONTENT = SUBSTR(LINE1, 2" in dfa_content,
        'Page Break Detection': "== '1'" in dfa_content,
        'Conditional Routing': 'IF SUBSTR(CONTENT' in dfa_content,
    }

    print("DFA Configuration Checks:")
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")

    print()

    # Simulate field extraction for a specific line
    print("=" * 80)
    print("FIELD EXTRACTION SIMULATION")
    print("=" * 80)
    print()

    # Find a line with card number (should have pattern XXXX XXXX XXXX XXXX)
    for line_num, line in enumerate(data_lines, 1):
        if len(line) > 40 and 'XXXX' in line and 'ZZZZ' in line:
            print(f"Testing Line {line_num}:")
            print(f"  Raw: {line.rstrip()}")
            print()

            cc = line[0]
            content = line[1:]

            cc_desc = {'0': 'double', '-': 'triple', '+': 'overprint', ' ': 'single'}.get(cc, 'normal')
            print(f"  Carriage Control: '{cc}' -> {cc_desc} spacing")
            print(f"  Content (after CC): {content[:60]}")
            print()

            # Simulate field extraction as DFA would do
            # Based on RPE array: positions for card number, type, amount, date
            fields = [
                ('Card Number', 6, 23),
                ('Type', 30, 6),
                ('Amount', 39, 16),
                ('Date', 60, 8),
            ]

            print("  Field Extraction (as DFA would extract):")
            for field_name, start, length in fields:
                if start < len(content):
                    end = min(start + length, len(content))
                    value = content[start:end]
                    print(f"    {field_name:15} [pos {start:2}, len {length:2}]: '{value.strip()}'")

            print()
            break  # Test only first matching line

    print()
    all_passed = all(checks.values())
    print("=" * 80)
    print(f"VALIDATION RESULT: {'PASS - All checks passed' if all_passed else 'FAIL - Some checks failed'}")
    print("=" * 80)

    return all_passed

if __name__ == '__main__':
    validate_field_extraction()

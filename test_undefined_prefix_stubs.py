#!/usr/bin/env python3
"""
Test script to verify undefined PREFIX stub generation.
"""

import os
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universal_xerox_parser import XeroxParser, VIPPToDFAConverter

def test_undefined_prefix_stubs():
    """Test that undefined PREFIX cases generate stub DOCFORMATs."""

    # Create a test DBM content with:
    # 1. A PREFIX reference (PREFIX eq (XX)) but no CASE XX
    # 2. A CASE block for YY
    test_dbm_content = """
%%Title: Test Undefined PREFIX
%%Creator: Test
%%CreationDate: 2024-01-01

%%WIZVAR:BEGIN
%%WIZVAR PREFIX,FIELD1,FIELD2
%%WIZVAR:END

% Reference PREFIX XX but don't define it
PREFIX eq (XX) {
    % This is commented out or missing
} IF

% Define PREFIX YY
PREFIX eq (YY) {
    CASE (YY)
    10 20 MOVETO
    (Text for YY) OUTPUT
    ENDPAGE
} IF
"""

    print("Testing undefined PREFIX stub generation...")
    print("=" * 60)

    # Parse the DBM
    parser = XeroxParser()
    dbm = parser.parse_dbm("test.dbm", test_dbm_content)

    # Convert to DFA
    converter = VIPPToDFAConverter(dbm)
    dfa_code = converter.generate_dfa_code()

    # Check results
    print("\nParsing complete!")
    print(f"Referenced prefixes: {converter.referenced_prefixes}")
    print(f"Defined prefixes: {converter.defined_prefixes}")

    # Find stub DOCFORMATs in output
    if "DOCFORMAT DF_XX" in dfa_code:
        print("\n[SUCCESS] Found stub DOCFORMAT for undefined PREFIX XX")

        # Extract and display the stub
        lines = dfa_code.split('\n')
        in_stub = False
        stub_lines = []
        for line in lines:
            if "DOCFORMAT DF_XX" in line:
                in_stub = True
            if in_stub:
                stub_lines.append(line)
                if "ENDFORMAT" in line:
                    break

        print("\nGenerated stub:")
        print("-" * 60)
        for line in stub_lines:
            print(line)
        print("-" * 60)
    else:
        print("\n[FAIL] FAIL: Stub DOCFORMAT for PREFIX XX not found")
        print("\nSearching for 'DF_XX' in output:")
        if "DF_XX" in dfa_code:
            print("Found 'DF_XX' references but not as DOCFORMAT definition")
        else:
            print("'DF_XX' not found anywhere in output")

    # Check that YY has a proper DOCFORMAT
    if "DOCFORMAT DF_YY" in dfa_code and "Text for YY" in dfa_code:
        print("\n[OK] SUCCESS: Found proper DOCFORMAT for defined PREFIX YY")
    else:
        print("\n[FAIL] FAIL: DOCFORMAT for PREFIX YY not found or incomplete")

    # Check for stub section header
    if "Stub DOCFORMATs for undefined PREFIX cases" in dfa_code:
        print("\n[OK] SUCCESS: Found stub section header comment")
    else:
        print("\n[FAIL] FAIL: Stub section header comment not found")

    print("\n" + "=" * 60)
    print("Test complete!")

    return dfa_code

if __name__ == "__main__":
    dfa_output = test_undefined_prefix_stubs()

    # Optionally save the output
    output_file = "test_undefined_prefix_output.dfa"
    with open(output_file, 'w') as f:
        f.write(dfa_output)
    print(f"\nFull DFA output saved to: {output_file}")

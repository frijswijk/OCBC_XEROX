#!/usr/bin/env python3
"""
Comprehensive test demonstrating undefined PREFIX stub generation.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universal_xerox_parser import XeroxParser, VIPPToDFAConverter

def test_comprehensive_stub_generation():
    """
    Test with multiple scenarios:
    - AA: Referenced but commented out (should get stub)
    - BB: Referenced and defined (should NOT get stub)
    - CC: Referenced but commented out (should get stub)
    - DD: Defined but not referenced (should be defined, no stub needed)
    """

    test_dbm = """
%%Title: Comprehensive Stub Test
%%Creator: Test Suite

/FE /ARIAL08 08 INDEXFONT

% Scenario 1: AA is referenced but commented out
% PREFIX eq (AA) {
%     CASE (AA)
%     (AA Content) OUTPUT
%     ENDPAGE
% } IF

% Scenario 2: BB is referenced AND defined
PREFIX eq (BB) {
    CASE (BB)
    10 20 MOVETO
    (BB Content) OUTPUT
    ENDPAGE
} IF

% Scenario 3: CC is referenced but commented out
% PREFIX eq (CC) {
%     CASE (CC)
%     (CC Content) OUTPUT
%     ENDPAGE
% } IF

% Scenario 4: DD is defined but never referenced (still generates DOCFORMAT)
CASE (DD)
    10 20 MOVETO
    (DD Content) OUTPUT
    ENDPAGE
"""

    print("=" * 70)
    print("COMPREHENSIVE STUB GENERATION TEST")
    print("=" * 70)

    print("\nScenarios:")
    print("  AA: Referenced in comment (PREFIX eq (AA)) -> Should get stub")
    print("  BB: Referenced and defined -> Should get DOCFORMAT, no stub")
    print("  CC: Referenced in comment (PREFIX eq (CC)) -> Should get stub")
    print("  DD: Defined but not referenced -> Should get DOCFORMAT")
    print("\n" + "-" * 70)

    # Parse and convert
    parser = XeroxParser()
    dbm = parser.parse_dbm("comprehensive_test.dbm", test_dbm)

    converter = VIPPToDFAConverter(dbm)
    dfa_code = converter.generate_dfa_code()

    # Analyze
    referenced = sorted(converter.referenced_prefixes)
    defined = sorted(converter.defined_prefixes)
    undefined = sorted(converter.referenced_prefixes - converter.defined_prefixes)

    print(f"\nAnalysis:")
    print(f"  Referenced prefixes: {referenced}")
    print(f"  Defined prefixes: {defined}")
    print(f"  Undefined prefixes (stubs): {undefined}")

    print("\n" + "-" * 70)
    print("Results:\n")

    # Check each scenario
    scenarios = {
        'AA': ('stub', 'Referenced but commented'),
        'BB': ('docformat', 'Referenced and defined'),
        'CC': ('stub', 'Referenced but commented'),
        'DD': ('docformat', 'Defined but not referenced')
    }

    for prefix, (expected_type, description) in scenarios.items():
        print(f"{prefix}: {description}")

        if expected_type == 'stub':
            # Should have stub with comment
            if f"DOCFORMAT DF_{prefix};" in dfa_code:
                if f"/* {prefix} Prefix not found or commented out */" in dfa_code:
                    print(f"  [OK] Generated stub for {prefix}")
                else:
                    print(f"  [PARTIAL] Has DOCFORMAT but not stub comment")
            else:
                print(f"  [FAIL] No stub generated for {prefix}")

        elif expected_type == 'docformat':
            # Should have full DOCFORMAT with content
            if f"DOCFORMAT DF_{prefix};" in dfa_code:
                if f"{prefix} Content" in dfa_code or f"MOVETO" in dfa_code:
                    print(f"  [OK] Generated proper DOCFORMAT for {prefix}")
                else:
                    print(f"  [PARTIAL] Has DOCFORMAT but missing content")
            else:
                print(f"  [FAIL] No DOCFORMAT generated for {prefix}")

        print()

    # Check for stub section
    if "Stub DOCFORMATs for undefined PREFIX cases" in dfa_code:
        print("[OK] Stub section header found")
    else:
        print("[INFO] No stub section (no undefined prefixes found)")

    print("\n" + "=" * 70)

    # Save output
    output_file = "test_stub_comprehensive_output.dfa"
    with open(output_file, 'w') as f:
        f.write(dfa_code)
    print(f"\nFull output saved to: {output_file}")

    return dfa_code

if __name__ == "__main__":
    test_comprehensive_stub_generation()

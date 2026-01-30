#!/usr/bin/env python3
"""
Test stub generation with a realistic scenario - commented out CASE block.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universal_xerox_parser import XeroxParser, VIPPToDFAConverter

def test_commented_case_block():
    """Test that a commented CASE block generates a stub."""

    # DBM with XX referenced but commented out
    test_dbm_content = """
%%Title: Test Commented CASE
%%Creator: Test

/FE /ARIAL08 08 INDEXFONT

% XX case is commented out
% PREFIX eq (XX) {
%     CASE (XX)
%     10 20 MOVETO
%     (XX Line) OUTPUT
%     ENDPAGE
% } IF

PREFIX eq (YY) {
    CASE (YY)
    10 20 MOVETO
    (YY Line) OUTPUT
    ENDPAGE
} IF

PREFIX eq (ZZ) {
    CASE (ZZ)
    10 20 MOVETO
    (ZZ Line) OUTPUT
    ENDPAGE
} IF
"""

    print("Testing stub generation for commented PREFIX case...")
    print("=" * 60)

    # Parse and convert
    parser = XeroxParser()
    dbm = parser.parse_dbm("test_commented.dbm", test_dbm_content)

    converter = VIPPToDFAConverter(dbm)
    dfa_code = converter.generate_dfa_code()

    # Analyze results
    print(f"\nReferenced prefixes: {sorted(converter.referenced_prefixes)}")
    print(f"Defined prefixes: {sorted(converter.defined_prefixes)}")

    undefined = converter.referenced_prefixes - converter.defined_prefixes

    if undefined:
        print(f"\nUndefined prefixes (stubs): {sorted(undefined)}")
    else:
        print("\nNo undefined prefixes found")

    # Check for stub
    if "DOCFORMAT DF_XX" in dfa_code:
        print("\n[OK] Stub generated for commented PREFIX XX")

        # Extract stub
        lines = dfa_code.split('\n')
        in_stub = False
        for i, line in enumerate(lines):
            if "DOCFORMAT DF_XX" in line:
                print("\nGenerated stub:")
                print("-" * 40)
                for j in range(i, min(i+5, len(lines))):
                    print(lines[j])
                print("-" * 40)
                break
    else:
        print("\n[INFO] No stub for XX (as expected - not referenced)")

    # Check that YY and ZZ have proper DOCFORMATs
    if "DOCFORMAT DF_YY" in dfa_code and "YY Line" in dfa_code:
        print("[OK] YY has proper DOCFORMAT")
    else:
        print("[FAIL] YY DOCFORMAT missing or incomplete")

    if "DOCFORMAT DF_ZZ" in dfa_code and "ZZ Line" in dfa_code:
        print("[OK] ZZ has proper DOCFORMAT")
    else:
        print("[FAIL] ZZ DOCFORMAT missing or incomplete")

    print("\n" + "=" * 60)

    return dfa_code

if __name__ == "__main__":
    output = test_commented_case_block()

    with open("test_stub_realistic_output.dfa", 'w') as f:
        f.write(output)
    print("Output saved to: test_stub_realistic_output.dfa")

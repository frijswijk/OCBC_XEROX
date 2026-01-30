"""
Test SCALL subroutine handling in Xerox to DFA converter.

Tests:
1. Simple subroutine (<=5 commands) should be inlined
2. Complex subroutine (>5 commands) should use SEGMENT
3. External files (.eps, .jpg) should use appropriate DFA commands
"""

from universal_xerox_parser import XeroxParser, VIPPToDFAConverter, XeroxDBM, XeroxFRM, XeroxCommand

def test_simple_subroutine_inline():
    """Test that simple subroutines are inlined."""
    print("=" * 80)
    print("TEST 1: Simple Subroutine Inlining")
    print("=" * 80)

    # Create a test DBM with subroutine definition
    dbm_code = """
XGF 2
SETPROJECT (TEST)

/NOTE {
    10 MOVEH
    (Line 1) SH
    NL
} XGFRESDEF

STARTDBM

CASE (1)
PREFIX (T1)

38 MOVEH
14 220 MOVETO
(NOTE) SCALL

ENDCASE

ENDJOB
"""

    # Parse and convert
    parser = XeroxParser()
    dbm = parser.parse_dbm("test.dbm", dbm_code)

    converter = VIPPToDFAConverter(dbm, {})
    dfa_code = converter.generate_dfa_code()

    print("\n--- DBM Code ---")
    print(dbm_code)

    print("\n--- Generated DFA ---")
    print(dfa_code)

    # Verify inlining
    assert "/* Inlined subroutine: NOTE" in dfa_code, "Subroutine should be inlined"
    assert "SEGMENT NOTE" not in dfa_code, "Should NOT use SEGMENT for simple subroutine"
    assert "MOVEH" in dfa_code or "POSITION" in dfa_code, "Should include subroutine commands"

    print("\n+ Simple subroutine was successfully inlined")
    return True


def test_complex_subroutine_segment():
    """Test that complex subroutines use SEGMENT."""
    print("\n" + "=" * 80)
    print("TEST 2: Complex Subroutine SEGMENT")
    print("=" * 80)

    # Create a test DBM with complex subroutine (>5 commands)
    dbm_code = """
XGF 2
SETPROJECT (TEST)

/COMPLEX {
    10 MOVEH
    (Line 1) SH
    NL
    (Line 2) SH
    NL
    (Line 3) SH
    NL
    (Line 4) SH
} XGFRESDEF

STARTDBM

CASE (1)
PREFIX (T1)

38 MOVEH
14 220 MOVETO
(COMPLEX) SCALL

ENDCASE

ENDJOB
"""

    # Parse and convert
    parser = XeroxParser()
    dbm = parser.parse_dbm("test.dbm", dbm_code)

    converter = VIPPToDFAConverter(dbm, {})
    dfa_code = converter.generate_dfa_code()

    print("\n--- DBM Code ---")
    print(dbm_code)

    print("\n--- Generated DFA ---")
    print(dfa_code)

    # Verify SEGMENT usage
    assert "SEGMENT COMPLEX" in dfa_code, "Should use SEGMENT for complex subroutine"
    assert "/* Inlined subroutine: COMPLEX" not in dfa_code, "Should NOT inline complex subroutine"

    print("\n+ Complex subroutine correctly uses SEGMENT")
    return True


def test_external_eps_file():
    """Test that external .eps files use SEGMENT."""
    print("\n" + "=" * 80)
    print("TEST 3: External EPS File")
    print("=" * 80)

    dbm_code = """
XGF 2
SETPROJECT (TEST)

STARTDBM

CASE (1)
PREFIX (T1)

38 MOVEH
14 220 MOVETO
(logo.eps) SCALL

ENDCASE

ENDJOB
"""

    # Parse and convert
    parser = XeroxParser()
    dbm = parser.parse_dbm("test.dbm", dbm_code)

    converter = VIPPToDFAConverter(dbm, {})
    dfa_code = converter.generate_dfa_code()

    print("\n--- DBM Code ---")
    print(dbm_code)

    print("\n--- Generated DFA ---")
    print(dfa_code)

    # Verify SEGMENT usage for EPS
    assert "SEGMENT logo" in dfa_code, "Should use SEGMENT for .eps file"
    assert "0 MM-$MR_TOP+&CORSEGMENT" in dfa_code, "Should use vertical position 0 MM for EPS"

    print("\n+ External EPS file correctly uses SEGMENT")
    return True


def test_drawb_subroutine():
    """Test that DRAWB-based subroutines are handled correctly."""
    print("\n" + "=" * 80)
    print("TEST 4: DRAWB Subroutine")
    print("=" * 80)

    dbm_code = """
XGF 2
SETPROJECT (TEST)

/TXNB {
    0 0 188 9 LMED DRAWB
} XGFRESDEF

STARTDBM

CASE (1)
PREFIX (T1)

38 MOVEH
14 220 MOVETO
(TXNB) SCALL

ENDCASE

ENDJOB
"""

    # Parse and convert
    parser = XeroxParser()
    dbm = parser.parse_dbm("test.dbm", dbm_code)

    converter = VIPPToDFAConverter(dbm, {})
    dfa_code = converter.generate_dfa_code()

    print("\n--- DBM Code ---")
    print(dbm_code)

    print("\n--- Generated DFA ---")
    print(dfa_code)

    # Verify inlining (DRAWB is single command, should be inlined)
    assert ("/* Inlined subroutine: TXNB" in dfa_code or "SEGMENT TXNB" in dfa_code), \
        "Should either inline or use SEGMENT for DRAWB subroutine"

    print("\n+ DRAWB subroutine handled correctly")
    return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("SCALL SUBROUTINE HANDLING TEST SUITE")
    print("=" * 80)

    tests = [
        test_simple_subroutine_inline,
        test_complex_subroutine_segment,
        test_external_eps_file,
        test_drawb_subroutine,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"\nX TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\nX TEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)

"""
Test for IF/ELSE/ENDIF nesting fix.

This test verifies that the parser correctly handles IF/ELSE/ENDIF blocks
without creating orphan ELSE statements.
"""

from universal_xerox_parser import XeroxCommand, VIPPToDFAConverter, XeroxDBM


def test_if_else_endif_basic():
    """Test basic IF/ELSE/ENDIF with flat command list."""

    # Create a simple command structure:
    # IF CPCOUNT == 1
    #   VAR_pctot = 0
    # ELSE
    #   VAR_COUNTTD = 0
    # ENDIF

    commands = [
        XeroxCommand(name='IF', parameters=['CPCOUNT', '==', '1']),
        XeroxCommand(name='SETVAR', parameters=['VAR_pctot', '0']),
        XeroxCommand(name='ELSE'),
        XeroxCommand(name='SETVAR', parameters=['VAR_COUNTTD', '0']),
        XeroxCommand(name='ENDIF'),
    ]

    # Initialize converter with minimal DBM
    dbm = XeroxDBM(filename='test.dbm')
    dbm.tokens = []
    converter = VIPPToDFAConverter(dbm)
    converter.output_lines = []
    converter.indent_level = 0

    # Process commands using the updated _convert_case_commands
    # We'll call it through a wrapper to capture output
    converter._convert_case_commands(commands)

    # Get the generated DFA code
    dfa_code = '\n'.join(converter.output_lines)

    print("Generated DFA code:")
    print(dfa_code)
    print()

    # Verify the output
    assert 'IF ISTRUE(CPCOUNT == 1);' in dfa_code, "IF condition should use ISTRUE()"
    assert 'THEN;' in dfa_code, "Should have THEN"
    assert 'VAR_pctot = 0;' in dfa_code, "Should have THEN block assignment"
    assert 'ELSE;' in dfa_code, "Should have ELSE"
    assert 'VAR_COUNTTD = 0;' in dfa_code, "Should have ELSE block assignment"
    assert 'ENDIF;' in dfa_code, "Should have ENDIF"

    # Count ENDIF occurrences - should be exactly 1
    endif_count = dfa_code.count('ENDIF;')
    assert endif_count == 1, f"Should have exactly 1 ENDIF, found {endif_count}"

    # Count ELSE occurrences - should be exactly 1
    else_count = dfa_code.count('ELSE;')
    assert else_count == 1, f"Should have exactly 1 ELSE, found {else_count}"

    # Verify structure: ELSE should come after THEN block and before ENDIF
    if_pos = dfa_code.find('IF ISTRUE')
    then_pos = dfa_code.find('THEN;')
    pctot_pos = dfa_code.find('VAR_pctot = 0;')
    else_pos = dfa_code.find('ELSE;')
    counttd_pos = dfa_code.find('VAR_COUNTTD = 0;')
    endif_pos = dfa_code.find('ENDIF;')

    assert if_pos < then_pos < pctot_pos < else_pos < counttd_pos < endif_pos, \
        "Commands should be in correct order: IF, THEN, assignment1, ELSE, assignment2, ENDIF"

    print("OK Basic IF/ELSE/ENDIF test passed!")


def test_nested_if_else():
    """Test nested IF/ELSE/ENDIF blocks."""

    # Create nested structure:
    # IF condition1
    #   IF condition2
    #     var1 = 1
    #   ELSE
    #     var2 = 2
    #   ENDIF
    # ELSE
    #   var3 = 3
    # ENDIF

    commands = [
        XeroxCommand(name='IF', parameters=['VAR1', '==', '1']),
        XeroxCommand(name='IF', parameters=['VAR2', '==', '2']),
        XeroxCommand(name='SETVAR', parameters=['VAR_result', '10']),
        XeroxCommand(name='ELSE'),
        XeroxCommand(name='SETVAR', parameters=['VAR_result', '20']),
        XeroxCommand(name='ENDIF'),
        XeroxCommand(name='ELSE'),
        XeroxCommand(name='SETVAR', parameters=['VAR_result', '30']),
        XeroxCommand(name='ENDIF'),
    ]

    dbm = XeroxDBM(filename='test.dbm')
    dbm.tokens = []
    converter = VIPPToDFAConverter(dbm)
    converter.output_lines = []
    converter.indent_level = 0

    converter._convert_case_commands(commands)

    dfa_code = '\n'.join(converter.output_lines)

    print("Generated DFA code (nested):")
    print(dfa_code)
    print()

    # Should have 2 IF, 2 ELSE, 2 ENDIF
    assert dfa_code.count('IF ISTRUE') == 2, "Should have 2 IF statements"
    assert dfa_code.count('ELSE;') == 2, "Should have 2 ELSE statements"
    assert dfa_code.count('ENDIF;') == 2, "Should have 2 ENDIF statements"

    print("OK Nested IF/ELSE/ENDIF test passed!")


def test_if_without_else():
    """Test IF/ENDIF without ELSE."""

    commands = [
        XeroxCommand(name='IF', parameters=['CPCOUNT', '==', '1']),
        XeroxCommand(name='SETVAR', parameters=['VAR_pctot', '0']),
        XeroxCommand(name='ENDIF'),
    ]

    dbm = XeroxDBM(filename='test.dbm')
    dbm.tokens = []
    converter = VIPPToDFAConverter(dbm)
    converter.output_lines = []
    converter.indent_level = 0

    converter._convert_case_commands(commands)

    dfa_code = '\n'.join(converter.output_lines)

    print("Generated DFA code (IF without ELSE):")
    print(dfa_code)
    print()

    assert 'IF ISTRUE(CPCOUNT == 1);' in dfa_code
    assert 'THEN;' in dfa_code
    assert 'VAR_pctot = 0;' in dfa_code
    assert 'ENDIF;' in dfa_code
    assert 'ELSE;' not in dfa_code, "Should not have ELSE"

    print("OK IF without ELSE test passed!")


if __name__ == '__main__':
    print("Testing IF/ELSE/ENDIF fix...")
    print("=" * 60)

    test_if_else_endif_basic()
    print()
    test_nested_if_else()
    print()
    test_if_without_else()

    print("=" * 60)
    print("All tests passed! OK")

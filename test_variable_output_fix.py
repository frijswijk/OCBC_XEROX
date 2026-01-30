"""
Test to verify that variable references in OUTPUT commands are not quoted.

This test verifies the fix for the bug where variables were being output as
literal strings instead of their values.

Example:
    VIPP: /VAR_SCCL SHR
    DFA (WRONG): OUTPUT 'VAR_SCCL' FONT ... ALIGN RIGHT;
    DFA (CORRECT): OUTPUT VAR_SCCL FONT ... ALIGN RIGHT;
"""

import sys
import os

# Add parent directory to path to import the parser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universal_xerox_parser import XeroxCommand, VIPPToDFAConverter, XeroxDBM


def test_variable_output_no_quotes():
    """Test that variable references in OUTPUT are not quoted."""

    # Create a minimal DBM object for testing
    dbm = XeroxDBM()
    dbm.commands = []

    # Create a converter instance
    parser = VIPPToDFAConverter(dbm)
    parser.output_lines = []

    # Test case 1: Variable reference with SHR (right-aligned)
    print("Test 1: Variable reference with SHR")
    cmd = XeroxCommand(
        name='SHR',
        parameters=['/VAR_SCCL'],
        line_number=1
    )

    # Call the conversion method
    parser._convert_output_command_dfa(cmd, 10.0, 20.0, 'ARIAL8', True, True, False)

    # Check the output
    output = '\n'.join(parser.output_lines)
    print("Generated DFA:")
    print(output)
    print()

    # Verify: Should NOT have quotes around VAR_SCCL
    if "'VAR_SCCL'" in output:
        print("❌ FAIL: Variable is quoted (wrong!)")
        return False
    elif "OUTPUT VAR_SCCL" in output:
        print("✓ PASS: Variable is not quoted (correct!)")
    else:
        print("❌ FAIL: Variable not found in output")
        return False

    # Test case 2: String literal with SHR (should have quotes)
    print("\nTest 2: String literal with SHR")
    parser.output_lines = []
    cmd2 = XeroxCommand(
        name='SHR',
        parameters=['(Some text)'],
        line_number=2
    )

    parser._convert_output_command_dfa(cmd2, 10.0, 20.0, 'ARIAL8', True, True, False)

    output2 = '\n'.join(parser.output_lines)
    print("Generated DFA:")
    print(output2)
    print()

    # Verify: String literal SHOULD have quotes
    if "OUTPUT 'Some text'" in output2:
        print("✓ PASS: String literal is quoted (correct!)")
    else:
        print("❌ FAIL: String literal not properly quoted")
        return False

    # Test case 3: Variable with system variable prefix
    print("\nTest 3: System variable with SHL")
    parser.output_lines = []
    cmd3 = XeroxCommand(
        name='SHL',
        parameters=['$SL_CURRX'],
        line_number=3
    )

    parser._convert_output_command_dfa(cmd3, 10.0, 20.0, 'ARIAL8', True, True, False)

    output3 = '\n'.join(parser.output_lines)
    print("Generated DFA:")
    print(output3)
    print()

    # Verify: System variable should NOT have quotes
    if "'$SL_CURRX'" in output3:
        print("❌ FAIL: System variable is quoted (wrong!)")
        return False
    elif "OUTPUT $SL_CURRX" in output3:
        print("✓ PASS: System variable is not quoted (correct!)")
    else:
        print("❌ FAIL: System variable not found in output")
        return False

    print("\n" + "="*60)
    print("ALL TESTS PASSED! ✓")
    print("="*60)
    return True


if __name__ == '__main__':
    success = test_variable_output_no_quotes()
    sys.exit(0 if success else 1)

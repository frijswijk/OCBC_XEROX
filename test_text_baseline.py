#!/usr/bin/env python3
"""
Test TEXT vs OUTPUT decision logic implementation.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universal_xerox_parser import VIPPToDFAConverter, XeroxCommand, XeroxDBM

def test_should_use_text_baseline():
    """Test the _should_use_text_baseline method."""
    # Create a minimal DBM object
    dbm = XeroxDBM(
        filename="test.dbm",
        fonts={},
        colors={},
        variables={},
        commands=[]
    )

    parser = VIPPToDFAConverter(dbm)

    print("Testing _should_use_text_baseline method:\n")

    # Test 1: Short text, no special features -> False
    text1 = "Short text"
    params1 = []
    result1 = parser._should_use_text_baseline(text1, params1, alignment=0)
    print(f"Test 1 - Short text, LEFT align: {result1} (expected: False)")
    assert result1 == False, "Test 1 failed"

    # Test 2: Long text (> 50 chars) -> True
    text2 = "This is a very long text string that exceeds fifty characters in length"
    params2 = []
    result2 = parser._should_use_text_baseline(text2, params2, alignment=0)
    print(f"Test 2 - Long text (>50 chars): {result2} (expected: True)")
    assert result2 == True, "Test 2 failed"

    # Test 3: JUSTIFY alignment -> True
    text3 = "Any text"
    params3 = []
    result3 = parser._should_use_text_baseline(text3, params3, alignment=3)
    print(f"Test 3 - JUSTIFY alignment: {result3} (expected: True)")
    assert result3 == True, "Test 3 failed"

    # Test 4: Font markers in text -> True
    text4 = "Text with **BOLD marker"
    params4 = []
    result4 = parser._should_use_text_baseline(text4, params4, alignment=0)
    print(f"Test 4 - Font markers (**): {result4} (expected: True)")
    assert result4 == True, "Test 4 failed"

    # Test 5: Multiple font references -> True
    text5 = "Normal text"
    params5 = ['/F3', '/F5', 'other', 'params']
    result5 = parser._should_use_text_baseline(text5, params5, alignment=0)
    print(f"Test 5 - Multiple fonts in params: {result5} (expected: True)")
    assert result5 == True, "Test 5 failed"

    print("\nAll tests passed!")

def test_generate_text_baseline():
    """Test the _generate_text_baseline method output."""
    # Create a minimal DBM object
    dbm = XeroxDBM(
        filename="test.dbm",
        fonts={},
        colors={},
        variables={},
        commands=[]
    )

    parser = VIPPToDFAConverter(dbm)

    print("\n\nTesting _generate_text_baseline method:\n")

    # Test 1: Simple short text
    print("Test 1 - Simple short text with LEFT alignment:")
    parser.output_lines = []
    parser.indent_level = 0
    text1 = "This is a test"
    parser._generate_text_baseline(text1, "F3_3", ('SAME', 'SAME'), alignment=0)
    print('\n'.join(parser.output_lines))

    # Test 2: Long text that should be split
    print("\n\nTest 2 - Long text that should be split:")
    parser.output_lines = []
    parser.indent_level = 0
    text2 = "Please issue separate cheque payment(s) for each of your card account(s) when mailing with this payment slip"
    parser._generate_text_baseline(text2, "F3_3", ('SAME', 'SAME'), alignment=0)
    print('\n'.join(parser.output_lines))

    # Test 3: JUSTIFY alignment with width
    print("\n\nTest 3 - JUSTIFY alignment with width:")
    parser.output_lines = []
    parser.indent_level = 0
    text3 = "Text with justify alignment and width parameter set"
    parser._generate_text_baseline(text3, "F3_3", ('SAME', 'SAME'), alignment=3, width=193.0)
    print('\n'.join(parser.output_lines))

    print("\n\nAll generation tests completed!")

def test_integration():
    """Test the integration with _convert_output_command_dfa."""
    # Create a minimal DBM object
    dbm = XeroxDBM(
        filename="test.dbm",
        fonts={},
        colors={},
        variables={},
        commands=[]
    )

    parser = VIPPToDFAConverter(dbm)

    print("\n\nTesting integration with _convert_output_command_dfa:\n")

    # Test 1: Short text (should use OUTPUT)
    print("Test 1 - Short text (should use OUTPUT):")
    parser.output_lines = []
    parser.indent_level = 0
    cmd1 = XeroxCommand(name='SHL', parameters=['(Short text)'])
    parser._convert_output_command_dfa(cmd1, 24.0, 50.0, 'F3_3')
    print('\n'.join(parser.output_lines))

    # Test 2: Long text (should use TEXT BASELINE)
    print("\n\nTest 2 - Long text (should use TEXT BASELINE):")
    parser.output_lines = []
    parser.indent_level = 0
    long_text = "Please issue separate cheque payment(s) for each of your card account(s)"
    cmd2 = XeroxCommand(name='SHL', parameters=[f'({long_text})'])
    parser._convert_output_command_dfa(cmd2, 24.0, 50.0, 'F3_3')
    print('\n'.join(parser.output_lines))

    print("\n\nIntegration tests completed!")

if __name__ == '__main__':
    try:
        test_should_use_text_baseline()
        test_generate_text_baseline()
        test_integration()
        print("\n" + "="*60)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("="*60)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

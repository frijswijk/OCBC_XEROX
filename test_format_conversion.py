#!/usr/bin/env python3
"""
Test FORMAT conversion from VIPP to DFA NUMPICTURE.
"""

from universal_xerox_parser import VIPPToDFAConverter, XeroxCommand, XeroxDBM, XeroxProject

def test_format_conversion():
    """Test VIPP FORMAT to DFA NUMPICTURE conversion."""
    # Create a minimal DBM and project for the converter
    dbm = XeroxDBM(filename="test.dbm")
    project = XeroxProject(name="test_project")
    parser = VIPPToDFAConverter(dbm, project)

    # Test format conversion function
    print("Testing format conversion function:")
    test_cases = [
        ("(@@@,@@@,@@@,@@#.##)", "'#,##0.00'"),
        ("(@@#)", "'##0'"),
        ("(@@@,@@#)", "'###,##0'"),
        ("(@@#.#)", "'##0.0'"),
        ("(#,###.##)", "'0,000.00'"),
    ]

    for vipp, expected in test_cases:
        result = parser._convert_vipp_format_to_dfa(vipp)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status} {vipp} -> {result} (expected: {expected})")

    print("\nTesting MOVEHR with FORMAT (simple):")
    # Test case from the issue: 183 MOVEHR VAR_LSB (@@@,@@@,@@@,@@#.##) FORMAT SHr
    cmd = XeroxCommand(
        name='SHr',
        parameters=['VAR_LSB', 'FORMAT', '(@@@,@@@,@@@,@@#.##)'],
        line_number=183
    )

    # Reset parser state for clean output
    parser.output_lines = []
    parser._convert_output_command(cmd)

    print("\nGenerated DFA output (simple method):")
    for line in parser.output_lines:
        print(f"  {line}")

    # Check if NUMPICTURE was used
    output_line = " ".join(parser.output_lines)
    if "NUMPICTURE" in output_line:
        print("PASS: NUMPICTURE wrapper detected")
    else:
        print("FAIL: NUMPICTURE wrapper NOT detected")

    if "VAR_LSB" in output_line:
        print("PASS: Variable name preserved")
    else:
        print("FAIL: Variable name NOT preserved")

    if "'#,##0.00'" in output_line:
        print("PASS: Format converted correctly")
    else:
        print("FAIL: Format NOT converted correctly")

    if "ALIGN RIGHT" in output_line:
        print("PASS: Alignment preserved (SHr -> RIGHT)")
    else:
        print("FAIL: Alignment NOT preserved")

    print("\n" + "="*60)
    print("\nTesting MOVEHR with FORMAT (DFA method with position):")
    # Test with _convert_output_command_dfa
    parser.output_lines = []
    parser._convert_output_command_dfa(
        cmd,
        x_pos=183.0,
        y_pos=50.0,
        current_font='ARIAL8',
        x_was_set=True,
        y_was_set=True
    )

    print("\nGenerated DFA output (DFA method):")
    for line in parser.output_lines:
        print(f"  {line}")

    # Check if NUMPICTURE was used
    output_line = " ".join(parser.output_lines)
    if "NUMPICTURE" in output_line:
        print("PASS: NUMPICTURE wrapper detected")
    else:
        print("FAIL: NUMPICTURE wrapper NOT detected")

    if "VAR_LSB" in output_line:
        print("PASS: Variable name preserved")
    else:
        print("FAIL: Variable name NOT preserved")

    if "'#,##0.00'" in output_line:
        print("PASS: Format converted correctly")
    else:
        print("FAIL: Format NOT converted correctly")

    if "ALIGN RIGHT" in output_line:
        print("PASS: Alignment preserved")
    else:
        print("FAIL: Alignment NOT preserved")

    if "POSITION" in output_line:
        print("PASS: Position included")
    else:
        print("FAIL: Position NOT included")

    print("\n" + "="*60)
    print("\nExpected output format:")
    print("OUTPUT NUMPICTURE(VAR_LSB,'#,##0.00')")
    print("    FONT ARIAL8 NORMAL")
    print("    POSITION 183 MM 50 MM")
    print("    ALIGN RIGHT NOPAD;")

if __name__ == "__main__":
    test_format_conversion()

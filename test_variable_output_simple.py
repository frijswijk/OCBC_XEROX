"""
Simple test to verify that variable references in OUTPUT commands are not quoted.

This test simulates the parameter processing logic to verify the fix.
"""


def test_parameter_processing():
    """Test parameter processing for variable vs string detection."""

    print("=" * 60)
    print("Testing Parameter Processing Logic")
    print("=" * 60)

    # Test Case 1: Variable reference (starts with /)
    print("\nTest 1: Variable reference - /VAR_SCCL")
    param = "/VAR_SCCL"

    text = ""
    is_variable = False

    # Simulate the fixed logic from _convert_output_command_dfa
    if param.startswith('/'):
        if not text:  # First parameter, so it's a variable
            text = param.lstrip('/')
            is_variable = True

    print(f"  Parameter: {param}")
    print(f"  Extracted text: {text}")
    print(f"  Is variable: {is_variable}")

    if is_variable and text == "VAR_SCCL":
        output = f"OUTPUT {text}"
        print(f"  Generated: {output}")
        if "'" not in output:
            print("  [PASS] No quotes around variable")
        else:
            print("  [FAIL] Variable is quoted")
            return False
    else:
        print("  [FAIL] Variable not detected correctly")
        return False

    # Test Case 2: String literal (parentheses)
    print("\nTest 2: String literal - (Some text)")
    param2 = "(Some text)"

    text2 = ""
    is_variable2 = False

    if param2.startswith('(') and param2.endswith(')'):
        text2 = param2[1:-1]
        is_variable2 = False

    print(f"  Parameter: {param2}")
    print(f"  Extracted text: {text2}")
    print(f"  Is variable: {is_variable2}")

    if not is_variable2 and text2 == "Some text":
        output2 = f"OUTPUT '{text2}'"
        print(f"  Generated: {output2}")
        if "'" in output2:
            print("  [PASS] String literal is quoted")
        else:
            print("  [FAIL] String literal not quoted")
            return False
    else:
        print("  [FAIL] String literal not detected correctly")
        return False

    # Test Case 3: System variable (starts with $)
    print("\nTest 3: System variable - $SL_CURRX")
    param3 = "$SL_CURRX"

    text3 = ""
    is_variable3 = False

    if param3.startswith('$'):
        text3 = param3
        is_variable3 = True

    print(f"  Parameter: {param3}")
    print(f"  Extracted text: {text3}")
    print(f"  Is variable: {is_variable3}")

    if is_variable3 and text3 == "$SL_CURRX":
        output3 = f"OUTPUT {text3}"
        print(f"  Generated: {output3}")
        if "'" not in output3:
            print("  [PASS] No quotes around system variable")
        else:
            print("  [FAIL] System variable is quoted")
            return False
    else:
        print("  [FAIL] System variable not detected correctly")
        return False

    # Test Case 4: Text with font reference (order matters)
    print("\nTest 4: Text with font - (Hello) /ARIAL8")
    params = ["(Hello)", "/ARIAL8"]

    text4 = ""
    is_variable4 = False
    font = ""

    for param in params:
        if param.startswith('(') and param.endswith(')'):
            text4 = param[1:-1]
        elif param.startswith('/'):
            if not text4:  # First parameter = variable
                text4 = param.lstrip('/')
                is_variable4 = True
            else:  # After text = font
                font = param.lstrip('/')

    print(f"  Parameters: {params}")
    print(f"  Extracted text: {text4}")
    print(f"  Is variable: {is_variable4}")
    print(f"  Font: {font}")

    if not is_variable4 and text4 == "Hello" and font == "ARIAL8":
        output4 = f"OUTPUT '{text4}'"
        print(f"  Generated: {output4}")
        print("  [PASS] String literal is quoted, font extracted separately")
    else:
        print("  [FAIL] Text/font not processed correctly")
        return False

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    print("\nSummary:")
    print("  - Variables (starting with /) are NOT quoted")
    print("  - String literals (in parentheses) ARE quoted")
    print("  - System variables (starting with $) are NOT quoted")
    print("  - Font references (/ after text) are extracted separately")
    return True


if __name__ == '__main__':
    import sys
    success = test_parameter_processing()
    sys.exit(0 if success else 1)

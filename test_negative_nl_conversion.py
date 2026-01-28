import sys
sys.path.insert(0, r'C:\Users\freddievr\claude-projects\OCBC_XEROX')

from universal_xerox_parser import XeroxParser, XeroxCommand

# Create parser instance
parser = XeroxParser()

# Simulate a negative NL command with -04 parameter
cmd = XeroxCommand('NL', 1, 1)
cmd.parameters = ['-04']

# Test the conversion by checking what position it would generate
print("Testing negative NL conversion:")
print(f"Input: {cmd.parameters[0]} NL")

# Simulate the calculation from the code
spacing_val = float(cmd.parameters[0])
if spacing_val < 0:
    lines_back = abs(int(spacing_val))
    if lines_back > 1:
        y_position = f"NEXT-($LINESP*#{lines_back-1})"
    else:
        y_position = "NEXT"
    print(f"Output Y position: {y_position}")
    print(f"Expected: NEXT-($LINESP*#3)")
    print(f"Match: {y_position == 'NEXT-($LINESP*#3)'}")
else:
    print(f"Output: SETUNITS LINESP {spacing_val} MM + POSITION (SAME) (NEXT)")

print("\n---")
print("Testing with -01 NL:")
cmd.parameters = ['-01']
spacing_val = float(cmd.parameters[0])
if spacing_val < 0:
    lines_back = abs(int(spacing_val))
    if lines_back > 1:
        y_position = f"NEXT-($LINESP*#{lines_back-1})"
    else:
        y_position = "NEXT"
    print(f"Output Y position: {y_position}")
    print(f"Note: -01 results in NEXT (no subtraction needed)")

print("\n---")
print("Testing with -05 NL:")
cmd.parameters = ['-05']
spacing_val = float(cmd.parameters[0])
if spacing_val < 0:
    lines_back = abs(int(spacing_val))
    if lines_back > 1:
        y_position = f"NEXT-($LINESP*#{lines_back-1})"
    else:
        y_position = "NEXT"
    print(f"Output Y position: {y_position}")
    print(f"Expected: NEXT-($LINESP*#4)")
    print(f"Match: {y_position == 'NEXT-($LINESP*#4)'}")

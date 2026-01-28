import sys
sys.path.insert(0, r'C:\Users\freddievr\claude-projects\OCBC_XEROX')

from universal_xerox_parser import XeroxParser

# Create a simple mock command
class MockCommand:
    def __init__(self, name, parameters):
        self.name = name
        self.parameters = parameters

# Test the parameters as they would be parsed
cmd = MockCommand('SHP', ['(STATEMENT OF $$VAR_CAE.)', 'VSUB', '0'])

# Simulate what happens in _convert_frm_output
text = ""
is_variable = False
has_vsub = False
vsub_alignment = None

for i, param in enumerate(cmd.parameters):
    if param == 'VSUB':
        has_vsub = True
        if i + 1 < len(cmd.parameters):
            try:
                vsub_alignment = int(cmd.parameters[i + 1])
            except (ValueError, IndexError):
                pass
        continue
    elif param.startswith('(') and param.endswith(')'):
        text = param[1:-1]
    elif param.startswith('VAR_') or param.startswith('FLD'):
        text = param
        is_variable = True

print(f"After parameter loop:")
print(f"  text: {text}")
print(f"  has_vsub: {has_vsub}")
print(f"  is_variable: {is_variable}")
print(f"  vsub_alignment: {vsub_alignment}")

# Now simulate the VSUB conversion
parser = XeroxParser()
if has_vsub and not is_variable:
    print(f"\nConverting VSUB...")
    converted_text = parser._convert_vsub(text)
    print(f"  Original: {text}")
    print(f"  Converted: {converted_text}")
    if ' ! ' in converted_text:
        print(f"  Setting is_variable = True")
        is_variable = True
    text = converted_text

print(f"\nFinal:")
print(f"  text: {text}")
print(f"  is_variable: {is_variable}")

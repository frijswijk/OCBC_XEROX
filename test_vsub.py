import re

def convert_vsub(text: str) -> str:
    vsub_pattern = r'\$\$([A-Za-z_][A-Za-z0-9_]*)\.'

    # Split text into parts: literals and variables
    parts = []
    last_end = 0

    for match in re.finditer(vsub_pattern, text):
        # Add literal text before this variable (if any)
        if match.start() > last_end:
            literal = text[last_end:match.start()]
            if literal:
                parts.append(('literal', literal))

        # Add variable
        var_name = match.group(1)
        parts.append(('variable', var_name))

        last_end = match.end()

    # Add any remaining literal text after last variable
    if last_end < len(text):
        literal = text[last_end:]
        if literal:
            parts.append(('literal', literal))

    # If no variables found, return original text
    if not parts or all(p[0] == 'literal' for p in parts):
        return text

    # Build DFA concatenation expression
    result_parts = []
    for part_type, part_value in parts:
        if part_type == 'literal':
            result_parts.append(f"'{part_value}'")
        else:
            result_parts.append(part_value)

    return ' ! '.join(result_parts)

text = 'STATEMENT OF $$VAR_CAE.'
print(f'Input: {text}')
result = convert_vsub(text)
print(f'Output: {result}')
print(f'Expected: \'STATEMENT OF \' ! VAR_CAE')
print(f'Match: {result == "\'STATEMENT OF \' ! VAR_CAE"}')

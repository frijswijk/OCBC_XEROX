# Color Support and PRINTFOOTER Enhancement

**Date:** January 9, 2026
**Issues:**
1. Color commands (R, B, W, etc.) not generating COLOR output in DFA
2. PRINTFOOTER page number output needs updated positioning and font

## Problem Statement

### Issue 1: Missing Color Support

Color commands in VIPP (R, B, W, G, C, M, Y, K) were not being converted to DFA COLOR statements in OUTPUT commands.

#### Source Pattern (VIPP)
```vipp
R
NL
(https://www.ocbc.com.my) SHR
B
```

#### OLD Output (Incorrect)
```dfa
OUTPUT ''
    FONT F2 NORMAL
    POSITION (SAME) (NEXT);
OUTPUT 'https://www.ocbc.com.my'
    FONT F2_1 NORMAL
    POSITION (SAME) (NEXT)
    ALIGN RIGHT NOPAD;
```

**Problem:** Missing COLOR R directive in the OUTPUT statement.

#### NEW Output (Correct)
```dfa
OUTPUT ''
    FONT F2 NORMAL
    POSITION (SAME) (NEXT);
OUTPUT 'https://www.ocbc.com.my'
    FONT F2_1 NORMAL
    POSITION (SAME) (NEXT)
    COLOR R
    ALIGN RIGHT NOPAD;
```

**Result:** COLOR R is now properly included in the OUTPUT.

### Issue 2: PRINTFOOTER Page Number Format

PRINTFOOTER needed specific font and position formatting for page numbers.

#### OLD Output (Incorrect)
```dfa
PRINTFOOTER
    P = P + 1;
    OUTLINE
        POSITION RIGHT (TOP-10 MM)
        DIRECTION ACROSS;
        OUTPUT 'Page '!P!' of '!PP
            POSITION -5 MM 5 MM
            ALIGN RIGHT NOPAD;
    ENDIO;
```

#### NEW Output (Correct)
```dfa
PRINTFOOTER
    P = P + 1;
    OUTLINE
        POSITION RIGHT (TOP-10 MM)
        DIRECTION ACROSS;
        OUTPUT 'Page '!P!' of '!PP
            FONT F5_1
            POSITION (RIGHT-11 MM) 297 MM
            ALIGN RIGHT NOPAD;
    ENDIO;
```

**Result:** Page numbers now use F5_1 font and correct positioning.

## Solution 1: Color Support Implementation

Added comprehensive color tracking and output throughout the FRM conversion pipeline.

### Changes Overview

1. **Color Command Parsing**: Added SETCOLOR command recognition for color identifiers
2. **Color Tracking**: Track current color state during FRM conversion
3. **Color Output**: Generate COLOR directive in OUTPUT commands

### Location 1: Color Command Parsing (lines 1052-1060)

**File:** universal_xerox_parser.py
**Method:** _parse_vipp_block()

**Added Code:**
```python
elif token.value.upper() in ('R', 'B', 'W', 'G', 'C', 'M', 'Y', 'K'):
    # Color alias (R=Red, B=Black, W=White, etc.) - create color command
    cmd = XeroxCommand(
        name='SETCOLOR',
        line_number=token.line_number + line_offset,
        column=token.column
    )
    cmd.parameters = [token.value.upper()]
    commands.append(cmd)
```

**Logic:**
- Recognize single-letter color identifiers (R, B, W, G, C, M, Y, K)
- Create SETCOLOR command with color identifier as parameter
- Add to command list for processing

### Location 2: Color Tracking in FRM Conversion (lines 1847-1861)

**File:** universal_xerox_parser.py
**Method:** _convert_frm_commands()

**Added Code:**
```python
# Track current color
current_color = None

for cmd in frm.commands:
    # Handle font changes
    if cmd.name == 'SETFONT':
        if cmd.parameters:
            current_font = cmd.parameters[0].upper()
        continue

    # Handle color changes
    if cmd.name == 'SETCOLOR':
        if cmd.parameters:
            current_color = cmd.parameters[0].upper()
        continue
```

**Logic:**
- Initialize current_color tracking variable
- Update current_color when SETCOLOR command is encountered
- Persist color state until next SETCOLOR command

### Location 3: Color Tracking in Command List (lines 2049-2065)

**File:** universal_xerox_parser.py
**Method:** _convert_frm_command_list()

**Added Code:**
```python
# Track current color
current_color = None

self.indent()

for cmd in commands:
    # Handle font changes
    if cmd.name == 'SETFONT':
        if cmd.parameters:
            current_font = cmd.parameters[0].upper()
        continue

    # Handle color changes
    if cmd.name == 'SETCOLOR':
        if cmd.parameters:
            current_color = cmd.parameters[0].upper()
        continue
```

**Logic:**
- Mirror color tracking in recursive command processing
- Ensures color state is maintained in IF block children

### Location 4: Color Parameter Threading (lines 2209-2296)

**File:** universal_xerox_parser.py
**Method:** _convert_frm_output()

**Modified Signature:**
```python
def _convert_frm_output(self, cmd: XeroxCommand, x: float, y: float, font: str, frm: XeroxFRM,
                       x_was_set: bool = True, y_was_set: bool = True, y_is_next: bool = False,
                       color: str = None):
```

**Modified Calls:**
```python
# For font switches
self._generate_text_with_font_switches(text, x, y, font, frm, vsub_alignment,
                                       x_was_set, y_was_set, y_is_next, color)

# For simple output
self._generate_simple_output(text, x, y, font, is_variable, vsub_alignment,
                            x_was_set, y_was_set, y_is_next, frm, color)
```

**Logic:**
- Added color parameter to method signature
- Thread color through to output generation methods

### Location 5: Color Parameter in Text with Font Switches (lines 2383-2397)

**File:** universal_xerox_parser.py
**Method:** _generate_text_with_font_switches()

**Modified Signature:**
```python
def _generate_text_with_font_switches(self, text: str, x, y,
                                       default_font: str, frm: XeroxFRM, alignment: int = None,
                                       x_was_set: bool = True, y_was_set: bool = True, y_is_next: bool = False,
                                       color: str = None):
```

**Modified Call:**
```python
if len(segments) <= 1:
    # No switches, use simple OUTPUT
    self._generate_simple_output(text, x, y, default_font, False, alignment,
                                x_was_set, y_was_set, y_is_next, frm, color)
    return
```

**Logic:**
- Accept color parameter
- Pass to _generate_simple_output when no font switches present

### Location 6: Color Output Generation (lines 2522-2570)

**File:** universal_xerox_parser.py
**Method:** _generate_simple_output()

**Modified Signature:**
```python
def _generate_simple_output(self, text: str, x, y,
                           default_font: str, is_variable: bool, alignment: int = None,
                           x_was_set: bool = True, y_was_set: bool = True, y_is_next: bool = False,
                           frm: XeroxFRM = None, color: str = None):
```

**Added Output:**
```python
# Add position using helper method (handles both keywords and numeric with margin correction)
self.add_line(self._format_position(x_pos, y_pos))

# Add color if specified
if color:
    self.add_line(f"COLOR {color}")

# Add alignment if specified
```

**Logic:**
- Accept color parameter
- Generate COLOR directive in OUTPUT if color is specified
- Insert COLOR line after POSITION, before ALIGN

### Location 7: Caller Updates (lines 1975-1977, 2122-2124)

**File:** universal_xerox_parser.py
**Methods:** _convert_frm_commands(), _convert_frm_command_list()

**Modified Calls:**
```python
# In _convert_frm_commands (line 1975)
self._convert_frm_output(cmd, current_x, current_y, current_font, frm,
                        x_was_explicitly_set, y_was_explicitly_set, y_is_next_line,
                        current_color)

# In _convert_frm_command_list (line 2122)
self._convert_frm_output(cmd, current_x, current_y, current_font, frm,
                        x_was_explicitly_set, y_was_explicitly_set, y_is_next_line,
                        current_color)
```

**Logic:**
- Pass current_color to _convert_frm_output in both main and recursive processing

## Solution 2: PRINTFOOTER Enhancement

Updated PRINTFOOTER page number output with specific font and positioning.

### Location: PRINTFOOTER Generation (lines 3299-3307)

**File:** universal_xerox_parser.py
**Method:** _generate_printfooter()

**OLD Code:**
```python
self.add_line("        P = P + 1;")
self.add_line("        OUTLINE")
self.add_line("            POSITION RIGHT (TOP-10 MM)")
self.add_line("            DIRECTION ACROSS;")
self.add_line("            OUTPUT 'Page '!P!' of '!PP")
self.add_line("                POSITION -5 MM 5 MM")
self.add_line("                ALIGN RIGHT NOPAD;")
self.add_line("        ENDIO;")
```

**NEW Code:**
```python
self.add_line("        P = P + 1;")
self.add_line("        OUTLINE")
self.add_line("            POSITION RIGHT (TOP-10 MM)")
self.add_line("            DIRECTION ACROSS;")
self.add_line("            OUTPUT 'Page '!P!' of '!PP")
self.add_line("                FONT F5_1")
self.add_line("                POSITION (RIGHT-11 MM) 297 MM")
self.add_line("                ALIGN RIGHT NOPAD;")
self.add_line("        ENDIO;")
```

**Changes:**
- Added FONT F5_1 directive
- Changed POSITION from `-5 MM 5 MM` to `(RIGHT-11 MM) 297 MM`

## Color Identifiers Supported

| Color | Full Name | VIPP Code |
|-------|-----------|-----------|
| R     | Red       | R         |
| B     | Black     | B         |
| W     | White     | W         |
| G     | Green     | G         |
| C     | Cyan      | C         |
| M     | Magenta   | M         |
| Y     | Yellow    | Y         |
| K     | Black     | K         |

## Implementation Flow

### Color State Tracking
```
VIPP Input: R
    ↓
Parse: Create SETCOLOR command
    ↓
Process: Update current_color = 'R'
    ↓
VIPP Input: (text) SHR
    ↓
Process: Call _convert_frm_output with current_color='R'
    ↓
Generate: _generate_simple_output with color='R'
    ↓
DFA Output: COLOR R
```

### Color Persistence
```
Initial State: current_color = None
    ↓
SETCOLOR 'R': current_color = 'R'
    ↓
OUTPUT 1: COLOR R (uses current_color)
    ↓
OUTPUT 2: COLOR R (still uses current_color)
    ↓
SETCOLOR 'B': current_color = 'B'
    ↓
OUTPUT 3: COLOR B (uses new current_color)
```

## Code Changes Summary

### Files Modified: 1
- `universal_xerox_parser.py`

### Changes Made:

1. **_parse_vipp_block()** (lines 1052-1060)
   - Added color identifier recognition (R, B, W, G, C, M, Y, K)
   - Create SETCOLOR commands for color identifiers

2. **_convert_frm_commands()** (lines 1847-1861)
   - Added current_color tracking variable
   - Handle SETCOLOR commands to update current_color
   - Pass current_color to _convert_frm_output

3. **_convert_frm_command_list()** (lines 2049-2065)
   - Added current_color tracking for recursive processing
   - Handle SETCOLOR commands in IF block children
   - Pass current_color to _convert_frm_output

4. **_convert_frm_output()** (lines 2209-2296)
   - Added color parameter to method signature
   - Pass color to _generate_text_with_font_switches
   - Pass color to _generate_simple_output

5. **_generate_text_with_font_switches()** (lines 2383-2397)
   - Added color parameter to method signature
   - Pass color to _generate_simple_output

6. **_generate_simple_output()** (lines 2522-2570)
   - Added color parameter to method signature
   - Generate COLOR directive when color is specified
   - Insert COLOR after POSITION, before ALIGN

7. **_generate_printfooter()** (lines 3299-3307)
   - Updated FONT to F5_1
   - Updated POSITION to (RIGHT-11 MM) 297 MM

## Verification Results

### Color Support Test

**Test File:** SIBS_CASTF.FRM

**VIPP Input:**
```vipp
R
NL
(https://www.ocbc.com.my) SHR
```

**DFA Output:**
```dfa
OUTPUT ''
    FONT F2 NORMAL
    POSITION (SAME) (NEXT);
OUTPUT 'https://www.ocbc.com.my'
    FONT F2_1 NORMAL
    POSITION (SAME) (NEXT)
    COLOR R
    ALIGN RIGHT NOPAD;
```

✅ **Verification Passed:** COLOR R is correctly generated

### PRINTFOOTER Test

**Test File:** SIBS_CAST.DBM

**DFA Output:**
```dfa
PRINTFOOTER
  /*Put here the layout forms (.FRM)*/
      IF P<1;
      THEN;
        USE
          FORMAT SIBS_CASTF EXTERNAL;
      ELSE;
        USE
          FORMAT SIBS_CASTS EXTERNAL;
      ENDIF;
        P = P + 1;
        OUTLINE
            POSITION RIGHT (TOP-10 MM)
            DIRECTION ACROSS;
            OUTPUT 'Page '!P!' of '!PP
                FONT F5_1
                POSITION (RIGHT-11 MM) 297 MM
                ALIGN RIGHT NOPAD;
        ENDIO;
    PRINTEND;
```

✅ **Verification Passed:** FONT F5_1 and POSITION (RIGHT-11 MM) 297 MM correctly generated

## Benefits

### Color Support
1. **Correct Color Output:** Color commands now generate proper DFA COLOR directives
2. **State Tracking:** Color state persists across multiple OUTPUT commands
3. **Complete Coverage:** All standard color identifiers supported
4. **Clean Integration:** Color seamlessly integrated into output generation pipeline

### PRINTFOOTER Enhancement
1. **Proper Font:** Page numbers use appropriate font F5_1
2. **Correct Positioning:** Absolute positioning at 297 MM with right offset
3. **Consistent Format:** Matches expected DFA formatting standards

## Technical Notes

### Why Color Parameter Threading

The color parameter is threaded through multiple method layers to maintain separation of concerns:

1. **State Management**: Color state is managed at the command processing level
2. **Output Generation**: Color is applied at the output generation level
3. **Clean Architecture**: Each method has a single responsibility

### Why PRINTFOOTER Uses Absolute Position

- **POSITION (RIGHT-11 MM) 297 MM**: Uses absolute Y position (297 MM) for consistency
- **Font F5_1**: Uses renamed font to avoid conflicts with DBM fonts
- Ensures page numbers appear at the same position on every page

---

**Implementation Status:** ✅ Complete and Verified
**Test Status:** ✅ Passed (SIBS_CAST, SIBS_CASTF, SIBS_CASTS)
**Breaking Changes:** None (only adds missing COLOR output and improves PRINTFOOTER)

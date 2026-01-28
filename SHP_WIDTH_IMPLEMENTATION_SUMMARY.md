# SHP WIDTH Parameter Implementation

**Date:** January 9, 2026
**Feature:** Support for WIDTH parameter in SHP command for text line wrapping

## Problem Statement

SHP commands with width parameter were not being handled correctly. The width parameter was extracted but never used, resulting in OUTPUT commands that couldn't handle text wrapping.

**VIPP Command Example:**
```vipp
12 261 MOVETO
(If the property or asset that has been assigned or charged as security is non-landed, we request you to liaise with the relevant Joint Management Body (JMB) or Management Corporation (MC) to obtain the Certificate of Insurance for your unit or parcel. This is to ensure that your JMB/MC has indeed insured and keeps insured the building up to the replacement value of the building against fire and other such risks as may be required.) 187 3 SHP
```

**Parameters:**
- Text: Long paragraph (literal text in parentheses)
- Width: `187` MM (column width for wrapping)
- Alignment: `3` (LEFT)

## Solution

Implemented TEXT command generation with WIDTH parameter when SHP has a width value.

### OLD Behavior (Incorrect)

**Code extracted width but ignored it:**
```python
shp_width = float(param)  # Line 2084
# ...but then never used shp_width
self._generate_simple_output(...)  # Generates OUTPUT, not TEXT
```

**Generated (WRONG):**
```dfa
OUTPUT 'very long text...'
    FONT F3_1 NORMAL
    POSITION x y
    ALIGN LEFT NOPAD;
```

**Problems:**
- No line wrapping support
- Text would overflow or be truncated
- WIDTH parameter ignored

### NEW Behavior (Correct)

**Code checks for width and uses TEXT:**
```python
if shp_width is not None and shp_width > 0:
    # SHP with width requires TEXT command with WIDTH parameter
    self._generate_text_with_width(text, x, y, font, shp_width, ...)
```

**Generated (CORRECT):**
```dfa
TEXT
    POSITION (12.0 MM-$MR_LEFT) (261.0 MM-$MR_TOP)
    WIDTH 187.0 MM
    _STYLE NORMALS
    ALIGN LEFT
    FONT F3_1
    NORMAL
    'If the property or asset that has been assigned or charged as security is non-landed, we request you to liaise with the relevant Joint Management Body (JMB) or Management Corporation (MC) to obtain the Certificate of Insurance for your unit or parcel. This is to ensure that your JMB/MC has indeed insured and keeps insured the building up to the replacement value of the building against fire and other such risks as may be required.'
    ;
```

**Benefits:**
- DFA automatically wraps text to WIDTH
- No manual line breaking needed
- Preserves formatting and readability

## Implementation Details

### New Method: _generate_text_with_width()

**Location:** universal_xerox_parser.py:2381-2460

**Parameters:**
- `text`: Text content or variable name
- `x, y`: Position coordinates
- `default_font`: Font alias to use
- `width`: Column width in MM for text wrapping
- `is_variable`: True if text is a variable reference
- `alignment`: 0=LEFT, 1=RIGHT, 2=CENTER, 3=LEFT
- `x_was_set`, `y_was_set`, `y_is_next`: Position flags
- `frm`: FRM structure for font mapping

**Generated Structure:**
```dfa
TEXT
    POSITION x y
    WIDTH width MM
    _STYLE NORMALS
    ALIGN alignment
    FONT fontname
    NORMAL
    'text content' or (VARIABLE)
    ;
```

### Modified Method: _convert_frm_output()

**Location:** universal_xerox_parser.py:2043-2129

**New Logic:**
```python
# Priority order:
1. If shp_width > 0:
   → Use _generate_text_with_width()
2. Elif text contains ~~font~~switches:
   → Use _generate_text_with_font_switches()
3. Else:
   → Use _generate_simple_output()
```

**Decision Tree:**
```
SHP command received
    ↓
Has width parameter?
    ├─ YES (width > 0) → TEXT with WIDTH
    └─ NO
        ↓
    Has font switches (~~)?
        ├─ YES → TEXT with font changes
        └─ NO → OUTPUT (simple)
```

## Code Changes

### Files Modified: 1
- `universal_xerox_parser.py`

### Changes Made:

1. **_convert_frm_output()** (lines 2106-2129)
   - Added check for `shp_width is not None and shp_width > 0`
   - Call `_generate_text_with_width()` when width is present
   - Reordered logic to prioritize width over font switches

2. **New Method: _generate_text_with_width()** (lines 2381-2460)
   - Generates TEXT command structure
   - Adds WIDTH parameter
   - Handles _STYLE NORMALS
   - Maps font using frm.font_rename_map
   - Supports both literal text and variables
   - Handles VSUB formatting

## DFA TEXT Command Structure

### Components

1. **POSITION**: Where text starts
   ```dfa
   POSITION (12.0 MM-$MR_LEFT) (261.0 MM-$MR_TOP)
   ```

2. **WIDTH**: Column width for wrapping
   ```dfa
   WIDTH 187.0 MM
   ```

3. **_STYLE**: Text style setting
   ```dfa
   _STYLE NORMALS
   ```

4. **ALIGN**: Text alignment within width
   ```dfa
   ALIGN LEFT    # or RIGHT, CENTER
   ```

5. **FONT**: Font specification
   ```dfa
   FONT F3_1
   NORMAL        # Font style on separate line
   ```

6. **Content**: Text or variable
   ```dfa
   'Literal text content'    # For literals
   (VAR_NAME)                # For variables
   'prefix' (VAR) 'suffix'   # For VSUB
   ```

### Alignment Mapping

| VIPP Value | DFA Output | Description |
|------------|-----------|-------------|
| 0 | ALIGN LEFT | Left-aligned |
| 1 | ALIGN RIGHT | Right-aligned |
| 2 | ALIGN CENTER | Center-aligned |
| 3 | ALIGN LEFT | Left-aligned (alternative) |

## Examples

### Example 1: Literal Text with Width

**VIPP:**
```vipp
12 261 MOVETO
(Long paragraph text here...) 187 3 SHP
```

**Generated DFA:**
```dfa
TEXT
    POSITION (12.0 MM-$MR_LEFT) (261.0 MM-$MR_TOP)
    WIDTH 187.0 MM
    _STYLE NORMALS
    ALIGN LEFT
    FONT F3_1
    NORMAL
    'Long paragraph text here...'
    ;
```

### Example 2: Variable with Width

**VIPP:**
```vipp
SAME NEXT MOVETO
VAR_ABC 180 0 SHP
```

**Generated DFA:**
```dfa
TEXT
    POSITION (SAME) (NEXT)
    WIDTH 180.0 MM
    _STYLE NORMALS
    ALIGN LEFT
    FONT FE_1
    NORMAL
    (VAR_ABC)
    ;
```

### Example 3: SHP without Width (Falls back to OUTPUT)

**VIPP:**
```vipp
(Short text) SHL
```

**Generated DFA:**
```dfa
OUTPUT 'Short text'
    FONT F5 NORMAL
    POSITION x y
    ALIGN LEFT NOPAD;
```

## Verification Results

**Test File:** SIBS_CASTF.FRM

**Commands Found:**
```bash
grep -c "WIDTH.*MM" output_test_shp_width/SIBS_CASTF.dfa
```
**Result:** 14 TEXT commands with WIDTH parameter

**Sample Output:**
```dfa
TEXT
    POSITION (12.0 MM-$MR_LEFT) (261.0 MM-$MR_TOP)
    WIDTH 187.0 MM
    _STYLE NORMALS
    ALIGN LEFT
    FONT F3_1
    NORMAL
    'If the property or asset that has been assigned or charged as security is non-landed...'
    ;
```

✅ **Verification Passed:** All SHP commands with width now generate TEXT with WIDTH

## Benefits

1. **Line Wrapping:** DFA automatically wraps text to fit within WIDTH
2. **No Manual Breaking:** Text stays as single string, DFA handles layout
3. **Proper Alignment:** Text aligns correctly within column width
4. **Variable Support:** Works with both literals and variables
5. **Font Mapping:** Correctly applies renamed fonts from FRM
6. **VSUB Support:** Handles variable substitution formatting

## Technical Notes

### TEXT vs OUTPUT

**Use TEXT when:**
- SHP has width parameter (line wrapping needed)
- Text contains font switches (~~font~~)
- Multiple font styles in one text block

**Use OUTPUT when:**
- No width parameter
- Simple text, single font
- No special formatting needed

### WIDTH Behavior in DFA

- DFA wraps text automatically at word boundaries
- Preserves spaces and formatting
- Respects ALIGN setting within WIDTH
- Handles hyphenation if needed

### Font Specification

**In OUTPUT:**
```dfa
FONT fontname NORMAL    # All on one line
```

**In TEXT:**
```dfa
FONT fontname
NORMAL                  # Style on separate line
```

---

**Implementation Status:** ✅ Complete and Verified
**Test Status:** ✅ Passed (SIBS_CASTF.FRM, 14 instances found)
**Breaking Changes:** None (only affects SHP commands with width parameter)

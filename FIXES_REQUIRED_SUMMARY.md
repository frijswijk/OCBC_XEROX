# Xerox DBM to DFA Converter - Critical Fixes Required

**Date:** 2026-01-16
**Priority:** URGENT - Production blocker

---

## Executive Summary

After Luca's expert review of the Credit Card Statement conversion (CASIO.DBM → CASIO.dfa), **18 critical issues** were identified that prevent the generated DFA from working in Papyrus DocExec. These issues fall into 6 major categories requiring significant parser rewrites.

---

## Critical Issue Categories

### 1. ⚠️ DRAWBOX → BOX Conversion Completely Broken

**VIPP Pattern:**
```vipp
00    VAR.Y5    0.1    05.8    FBLACK    DRAWB
192.9 VAR.Y5    0.1    05.8    FBLACK    DRAWB
```

**My Wrong DFA:**
```dfa
BOX X VAR MM Y Y5 MM WIDTH 0.1 MM HEIGHT 05.8 MM;
```

**Luca's Correct DFA:**
```dfa
LINEH = MM(6);

OUTLINE
    POSITION 8 MM (40 MM-$MR_TOP+&CORSEGMENT)
    DIRECTION ACROSS;

    BOX
        POSITION 0 (LINEH)
        WIDTH 192.9 MM
        HEIGHT (LINEH)
        COLOR BLACK
        THICKNESS 0 TYPE SOLID
        SHADE 100;

    OUTPUT VAR_ARRAY1F1
        FONT ARIAL08 NORMAL
        POSITION (12 MM-$MR_LEFT) (SAME);
ENDIO;

OUTLINE
    POSITION SAME NEXT
    DIRECTION ACROSS;

    BOX
        POSITION SAME NEXT
        WIDTH 130 MM
        HEIGHT (LINEH)
        THICKNESS LIGHT TYPE SOLID;
    BOX
        POSITION CURRENT SAME
        WIDTH (59.9 MM+3 MM)
        HEIGHT (LINEH)
        THICKNESS LIGHT TYPE SOLID;
    OUTPUT VAR_ARRAY2F1
        FONT ARIAL08 NORMAL
        POSITION (12 MM-$MR_LEFT) (SAME);
ENDIO;
```

**Problems:**
1. Invalid syntax: `X VAR MM Y Y5 MM`
2. Variables (VAR, Y5) not defined and used directly as literal text
3. Missing proper BOX structure with POSITION keyword
4. Not using OUTLINE blocks for positioning
5. Not using relative positioning (SAME, NEXT, CURRENT)
6. Missing COLOR, SHADE, THICKNESS attributes
7. Not creating separate OUTLINE blocks for each table row

**Root Cause:** VIPP uses absolute positioning with stack-based PostScript syntax. DFA uses structured relative positioning with keywords. The parser is trying to do literal translation instead of semantic conversion.

**Fix Strategy:**
1. Parse DRAWB commands to extract X, Y, WIDTH, HEIGHT, COLOR
2. Detect when Y uses variables (VAR.Y5) - indicates dynamic positioning
3. Generate BOX within OUTLINE blocks using relative positioning
4. Use LINEH variable for consistent row height
5. Use POSITION SAME NEXT for sequential rows
6. Use POSITION CURRENT SAME for adjacent boxes on same row

---

### 2. ⚠️ Variable Output as Strings

**VIPP Pattern:**
```vipp
180 MOVEHR ($$VAR_SCCL.) VSUB SHr
190 MOVEH  ($$VAR_SCCD.) VSUB SH
```

**My Wrong DFA:**
```dfa
OUTPUT 'VAR_SCCL'
    FONT FK NORMAL
    POSITION (SAME) (NEXT)
    ALIGN RIGHT NOPAD;
OUTPUT 'VAR_SCCD'
    FONT FK NORMAL
    POSITION (190.0 MM-$MR_LEFT) (SAME);
```

**Luca's Correct DFA:**
```dfa
OUTPUT VAR_SCCL
    FONT FK NORMAL
    POSITION 173 MM SAME
    ALIGN RIGHT NOPAD;
OUTPUT VAR_SCCD
    FONT FK NORMAL
    POSITION (190 MM-$MR_LEFT) SAME;
```

**Problems:**
1. Variable names wrapped in quotes → literal string output
2. Wrong positions: `(SAME) (NEXT)` vs absolute `173 MM SAME`

**Root Cause:** VIPP's `($$VAR.) VSUB SH` parser is incorrectly quoting the variable name

**Fix:** Detect `$$VAR` pattern, extract variable name, output WITHOUT quotes

---

### 3. ⚠️ Broken IF/THEN/ELSE Structure

**VIPP Pattern:**
```vipp
IF CPCOUNT 1 eq
    { SKIPPAGE
     /VAR_pctot ++
    }
    ELSE
    {
      /VAR_COUNTPAGE ++
      /VAR_brkcnt ++
    } ENDIF
```

**My Wrong DFA:**
```dfa
IF CPCOUNT == 1; THEN;
    VAR_pctot = 0;
ENDIF;
ELSE;  /* <-- ORPHAN ELSE */
    VAR_COUNTTD = 0;
    VARdoc = VARdoc + 1;
ENDIF;
```

**Luca's Correct DFA:**
```dfa
IF ISTRUE(CPCOUNT==1);
THEN;
    VAR_PCTOT = 0;
ELSE;
    VAR_COUNTTD = 0;
    VARDOC = VARDOC+1;
ENDIF;
```

**Problems:**
1. ENDIF inserted before ELSE, breaking the structure
2. Missing ISTRUE() wrapper
3. Variable name case inconsistent (pctot vs PCTOT)

**Root Cause:** Parser treating IF/THEN and ELSE as separate statements instead of single IF/THEN/ELSE block

**Fix:** Parse complete IF{...}ELSE{...}ENDIF block as one unit before generating DFA

---

### 4. ⚠️ Missing Variable Initialization ($_BEFOREDOC)

**VIPP Pattern:**
```vipp
/VAR.Y1  05  SETVAR % Dynamic Horizontal Line
/VAR.Y2  00  SETVAR % Dynamic Vertical Line
/VAR.Y3  -02 SETVAR % Dynamic Shaded Boxes
/VAR.Y5  00  SETVAR % Dynamic Vertical Line for YA
```

**My DFA:** Missing entirely

**Luca's Correct DFA:**
```dfa
DOCFORMAT $_BEFOREDOC;
    P = 0;
    PP = 0;
    VAR_COUNTTD = 0;
    /*(Un)declared variables uncorrect values for BOXes*/
    VAR = MM(40);
    Y5 = MM(40);
    Y3 = MM(40);
```

**Root Cause:** Not generating $_BEFOREDOC section with variable initialization

**Fix:**
1. Parse SETVAR commands in BEGINPAGE section
2. Generate $_BEFOREDOC with all variable initializations
3. Convert VIPP variable names (VAR.Y5 → Y5)
4. Use MM() function for dimension conversions

---

### 5. ⚠️ Missing LOGICALPAGE 2

**Luca's DFA has:**
```dfa
LOGICALPAGE 1
    SIDE FRONT
    ...
    PRINTFOOTER
        P = P+1;
        IF P<1; THEN;
            USE FORMAT CASIOF EXTERNAL;
        ELSE;
            USE FORMAT CASIOS EXTERNAL;
        ENDIF;
    PRINTEND;

LOGICALPAGE 2  /* <-- MISSING */
    SIDE FRONT
    ...
    PRINTFOOTER
        P = P+1;
        IF P<1; THEN;
            USE FORMAT CASIOF EXTERNAL;
        ELSE;
            USE FORMAT CASIOS EXTERNAL;
        ENDIF;
    PRINTEND;
```

**My DFA:** Only has LOGICALPAGE 1

**Root Cause:** Not detecting/generating multiple logical pages from VIPP

**Fix:** Analyze VIPP code for page structure, generate multiple LOGICALPAGE definitions

---

### 6. ⚠️ Minor but Critical Syntax Errors

**Issue A: Assignment Order Reversed**
- Wrong: `0 = VAR_COUNTYA;`
- Correct: `VAR_COUNTYA = 0;`
- Root Cause: Reverse Polish notation conversion error

**Issue B: Font Naming**
- Wrong: `FONT ARIAL8 NORMAL`
- Correct: `FONT ARIAL08 NORMAL`
- Root Cause: Not preserving leading zeros in font aliases

**Issue C: Missing COLOR Attributes**
- Many OUTPUT commands missing `COLOR W`, `COLOR B`, etc.
- Root Cause: Not extracting color from VIPP OUTPUT commands

**Issue D: Missing Spacing**
- Wrong: `POSITION (RIGHT-11 MM)286 MM`
- Correct: `POSITION (RIGHT-11 MM) 286 MM`
- Root Cause: Tokenization issue

**Issue E: Font Height Precision**
- Wrong: `HEIGHT 12.0`
- Correct: `HEIGHT 11.8`
- Root Cause: Rounding error in font size parsing

**Issue F: SEGMENT Syntax**
- Wrong: `SEGMENT YSAB POSITION 8.0 MM (40 MM-$MR_TOP+&CORSEGMENT);`
- Correct:
  ```dfa
  SEGMENT YSAB
      POSITION 8 MM (40 MM-$MR_TOP+&CORSEGMENT);
  ```
- Root Cause: Not adding newline before POSITION

---

## Files Requiring Modification

### xerox_jdt_dfa.py

**Methods to Fix:**

1. `_convert_drawbox_to_box()` - **COMPLETE REWRITE REQUIRED**
   - Current: Generates invalid `BOX X VAR MM Y Y5 MM...` syntax
   - New: Generate proper BOX with POSITION, WIDTH, HEIGHT, COLOR, THICKNESS, SHADE
   - Strategy:
     - Parse DRAWB parameters: X, Y, WIDTH, HEIGHT, COLOR
     - Detect if Y uses variable (VAR.Y5) → use relative positioning
     - Create OUTLINE blocks for table rows
     - Use LINEH = MM(6) for consistent heights
     - Generate BOX with proper structure

2. `_convert_output_command()` - **FIX VARIABLE QUOTING**
   - Current: Wraps variable names in quotes: `'VAR_SCCL'`
   - New: Detect `$$VAR` pattern, extract variable name, NO quotes
   - Strategy:
     - Check if text contains `$$` prefix
     - Extract variable name (strip `$$` and trailing `.`)
     - Output without quotes

3. `_parse_if_block()` - **FIX IF/THEN/ELSE PARSING**
   - Current: Treats IF and ELSE as separate statements
   - New: Parse complete IF{...}ELSE{...}ENDIF as single block
   - Strategy:
     - Find matching braces for IF
     - Find ELSE within IF block
     - Find ENDIF
     - Generate complete IF/THEN/ELSE/ENDIF structure
     - Add ISTRUE() wrapper for conditions

4. `_generate_dbm_beforedoc()` - **NEW METHOD**
   - Create $_BEFOREDOC section
   - Initialize P = 0, PP = 0
   - Extract SETVAR commands from BEGINPAGE
   - Generate variable initializations
   - Convert VAR.Y5 → Y5
   - Use MM() for dimension variables

5. `_generate_logical_pages()` - **ENHANCE**
   - Currently generates single LOGICALPAGE
   - New: Detect need for multiple pages
   - Generate LOGICALPAGE 1 and LOGICALPAGE 2

6. `_fix_font_alias()` - **NEW METHOD**
   - Preserve leading zeros: ARIAL8 → ARIAL08
   - Check font definitions for actual name

7. `_fix_assignment_order()` - **NEW METHOD**
   - Detect reverse assignments: `0 = VAR`
   - Swap to correct order: `VAR = 0`

8. `_extract_output_color()` - **ENHANCE**
   - Parse VIPP output commands for color
   - Add COLOR attribute to OUTPUT

9. `_use_text_for_long_strings()` - **NEW METHOD**
   - Detect OUTPUT with strings > 100 chars
   - Convert to TEXT BASELINE with WIDTH

10. `_fix_table_positions()` - **ENHANCE**
    - For table columns, use absolute positions with SAME
    - Right-aligned columns: specific MM position
    - Left-aligned columns: relative position

---

## Testing Strategy

### Phase 1: Unit Tests
1. Test DRAWBOX → BOX conversion with sample patterns
2. Test variable output (with/without quotes)
3. Test IF/THEN/ELSE parsing
4. Test $_BEFOREDOC generation
5. Test font name preservation

### Phase 2: Integration Test
1. Convert CASIO.DBM to DFA
2. Compare with Luca's corrected version
3. Check all 14 DOCFORMAT sections generated
4. Verify BOX syntax in DF_Y0
5. Verify variables output without quotes
6. Verify IF/THEN/ELSE structure intact
7. Verify $_BEFOREDOC present

### Phase 3: Papyrus Test
1. Load generated DFA into Papyrus DocExec
2. Process with sample data
3. Verify 5 pages output (not just 1)
4. Compare PDF output with expected

---

## Implementation Priority

### Must Fix (P0) - Blocks All Output
1. ✅ BOX command conversion - COMPLETE REWRITE
2. ✅ Variable quoting in OUTPUT
3. ✅ IF/THEN/ELSE structure
4. ✅ $_BEFOREDOC generation
5. ✅ Missing DOCFORMAT sections

### Should Fix (P1) - Wrong Output
6. ✅ LOGICALPAGE 2
7. ✅ Font naming (ARIAL08)
8. ✅ Assignment order
9. ✅ Missing COLOR attributes
10. ✅ TEXT vs OUTPUT for long strings

### Nice to Fix (P2) - Minor Issues
11. ✅ Spacing in POSITION
12. ✅ Font height precision
13. ✅ SEGMENT syntax newlines
14. ✅ Table position alignment

---

## Estimated Effort

- **BOX Conversion Rewrite:** 4-6 hours (complex logic)
- **Variable Quoting Fix:** 1 hour (straightforward)
- **IF/THEN/ELSE Fix:** 2-3 hours (parser logic)
- **$_BEFOREDOC Generation:** 2 hours (new method)
- **Other Fixes:** 2-3 hours (various small fixes)

**Total:** 11-15 hours of focused development

---

## Success Criteria

1. ✅ CASIO.DBM converts to DFA without syntax errors
2. ✅ Generated DFA loads in Papyrus DocExec without errors
3. ✅ All 5 pages of document output correctly
4. ✅ All DOCFORMAT sections present (no "not found" errors)
5. ✅ No AFP object errors (segments converted to BOX)
6. ✅ Variables output as values, not literal strings
7. ✅ BOX commands have valid syntax
8. ✅ IF/THEN/ELSE structures intact
9. ✅ Output PDF matches expected layout

---

## Next Action

Begin implementation starting with P0 fixes in priority order:
1. Rewrite `_convert_drawbox_to_box()` method
2. Fix variable quoting in `_convert_output_command()`
3. Fix IF/THEN/ELSE in `_parse_if_block()`
4. Add `_generate_dbm_beforedoc()` method
5. Test with CASIO.DBM

**Ready to proceed with implementation.**

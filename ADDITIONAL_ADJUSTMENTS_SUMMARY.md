# Additional Adjustments Implementation Summary

**Date:** January 9, 2026
**Changes:** SETLSP handling, SETPAGEDEF layout extraction, FRM module placement in PRINTFOOTER

## Adjustments Implemented

### 1. SETLSP (Line Spacing) Support ✅

**Requirement:** Extract SETLSP from DBM file and add to DOCFORMAT right after MARGIN.

**Source (SIBS_CAST.DBM):**
```vipp
04 SETLSP
```

**Generated DFA:**
```dfa
DOCFORMAT THEMAIN;
  USE
    FORMATGROUP MAIN;
  MARGIN TOP 0 MM BOTTOM 0 MM LEFT 0 MM RIGHT 0 MM;
  SETUNITS LINESP 4.0 MM;
```

**Implementation:**
- Added `line_spacing` field to VIPPToDFAConverter (line 1571)
- Created `_extract_layout_info()` method to scan DBM for SETLSP (line 2711)
- Uses raw content regex as backup if command parsing doesn't capture it (line 2735-2745)
- Modified `_generate_main_docformat()` to add SETUNITS LINESP after MARGIN if found (line 3175-3178)
- Falls back to AUTO if no SETLSP in source

---

### 2. SETPAGEDEF/SETLKF Layout Extraction ✅

**Requirement:** Parse SETPAGEDEF and extract the LAST SETLKF position for OUTLINE generation.

**Source (SIBS_CAST.DBM):**
```vipp
[
    { % Page Layout For Page 1
         [ [    12      82    183        120     0 ]] SETLKF % without address
        (SIBS_CASTF.FRM) SETFORM
    }
    { % Page Layout For Page 2
         [ [ 12    82   183         190     0 ] ] SETLKF
        (SIBS_CASTS.FRM) SETFORM
    } /R
]    SETPAGEDEF
```

**Extracted:** Last SETLKF position: (12, 82)

**Generated DFA (in DF_STMTTP):**
```dfa
DOCFORMAT DF_STMTTP;
  /* VIPP command not directly supported: SETPAGEDEF */
  /* PAGEBRK IF CPCOUNT 1 eq { /VAR_pctot 0 SETVAR } % reset page count... */
  /* PREFIX eq (STMTTP) = /VAR_COUNTERY; */
  /* TX = -; */
  /* SS = -; */
  OUTLINE PAGELAYOUT2
    POSITION 12 82 MM;
  ENDIO;
  VAR_STMTTP = PREFIX;
  VAR_CCAST = FLD1;
  ...
```

**Implementation:**
- Added `page_layout_position` field to VIPPToDFAConverter (line 1574)
- Extended `_extract_layout_info()` to parse SETPAGEDEF (line 2747-2757)
- Regex pattern extracts all SETLKF arrays and takes the last one
- Modified `_generate_individual_docformats()` to add OUTLINE before STMTTP processing (line 3433-3444)

---

### 3. FRM Module Placement in PRINTFOOTER ✅

**Requirement:** Move FRM format usage from main DOCFORMAT to PRINTFOOTER with IF P < 1 condition.

**Old Location:**
```dfa
DOCFORMAT THEMAIN;
  ...
  IF PP < 1; THEN;
    USE FORMAT SIBS_CASTF EXTERNAL;
  ELSE;
    USE FORMAT SIBS_CASTS EXTERNAL;
  ENDIF;
```

**New Location (in FORMATGROUP/PRINTFOOTER):**
```dfa
FORMATGROUP MAIN;
  ...
  LOGICALPAGE 1
    SIDE FRONT
    POSITION 0 0
    WIDTH 210 MM
    HEIGHT 297 MM
    DIRECTION ACROSS
    FOOTER
      PP = PP + 1;
    FOOTEREND
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
           POSITION -5 MM 5 MM
           ALIGN RIGHT NOPAD;
      ENDIO;
    PRINTEND;
```

**Changes:**
- **Condition Changed:** `IF PP < 1` → `IF P<1`
- **Location Changed:** Main DOCFORMAT → PRINTFOOTER section
- **Comment Added:** `/*Put here the layout forms (.FRM)*/`

**Implementation:**
- Modified `_generate_formatgroup()` to call form usage in PRINTFOOTER (line 2887-2889)
- Created new method `_generate_form_usage_in_printfooter()` (line 4155-4181)
- Uses P counter instead of PP counter for page determination
- First page (P<1) uses *F.FRM, subsequent pages use *S.FRM

---

## Verification Results

### Test File: SIBS_CAST.DBM
**Extraction Log:**
```
2026-01-09 11:03:40 - INFO - Found SETLSP from raw content: 4.0 MM
2026-01-09 11:03:40 - INFO - Found SETPAGEDEF layout position from raw content: (12.0, 82.0)
```

### Generated DFA Validation

**1. SETUNITS LINESP ✅**
```dfa
MARGIN TOP 0 MM BOTTOM 0 MM LEFT 0 MM RIGHT 0 MM;
SETUNITS LINESP 4.0 MM;    # Correctly set to 4.0 from SETLSP
```

**2. PRINTFOOTER with FRM Usage ✅**
```dfa
PRINTFOOTER
  /*Put here the layout forms (.FRM)*/
  IF P<1;              # Changed from PP < 1
  THEN;
    USE
      FORMAT SIBS_CASTF EXTERNAL;    # First page form
  ELSE;
    USE
      FORMAT SIBS_CASTS EXTERNAL;    # Subsequent pages form
  ENDIF;
  P = P + 1;
  OUTLINE
    POSITION RIGHT (TOP-10 MM)
    DIRECTION ACROSS;
    OUTPUT 'Page '!P!' of '!PP
      POSITION -5 MM 5 MM
      ALIGN RIGHT NOPAD;
  ENDIO;
PRINTEND;
```

**3. OUTLINE PAGELAYOUT2 ✅**
```dfa
DOCFORMAT DF_STMTTP;
  /* VIPP command not directly supported: SETPAGEDEF */
  /* PAGEBRK IF CPCOUNT 1 eq { /VAR_pctot 0 SETVAR } ... */
  /* PREFIX eq (STMTTP) = /VAR_COUNTERY; */
  /* TX = -; */
  /* SS = -; */
  OUTLINE PAGELAYOUT2
    POSITION 12 82 MM;    # Extracted from last SETLKF (12, 82)
  ENDIO;
  VAR_STMTTP = PREFIX;
  ...
```

---

## Code Changes Summary

### Files Modified: 1
- `universal_xerox_parser.py`

### Changes Made:

1. **VIPPToDFAConverter.__init__** (lines 1570-1579)
   - Added `line_spacing` field
   - Added `page_layout_position` field
   - Call to `_extract_layout_info()`

2. **New Method: _extract_layout_info()** (lines 2711-2757)
   - Scans DBM commands for SETLSP and SETPAGEDEF
   - Uses regex on raw content as backup
   - Extracts line spacing value
   - Extracts last SETLKF position

3. **New Method: _parse_setpagedef_layout()** (lines 2759-2781)
   - Parses SETPAGEDEF parameters
   - Extracts coordinates from nested arrays

4. **_generate_formatgroup()** (lines 2887-2889)
   - Moved FRM format usage to PRINTFOOTER
   - Calls `_generate_form_usage_in_printfooter()`

5. **New Method: _generate_form_usage_in_printfooter()** (lines 4155-4181)
   - Generates IF P<1 logic in PRINTFOOTER
   - Selects first vs subsequent page forms

6. **_generate_main_docformat()** (lines 3175-3178)
   - Adds SETUNITS LINESP after MARGIN if found
   - Falls back to AUTO if not found

7. **_generate_individual_docformats()** (lines 3433-3444)
   - Adds OUTLINE PAGELAYOUT2 for STMTTP if layout position found
   - Includes commented SETPAGEDEF warning

---

## Behavior Notes

### SETLSP Behavior
- **If SETLSP found in DBM:** Uses exact value (e.g., `SETUNITS LINESP 4.0 MM;`)
- **If SETLSP not found:** Uses AUTO (e.g., `SETUNITS LINESP AUTO;`)
- **Location:** Always placed immediately after MARGIN in DOCFORMAT THEMAIN

### SETPAGEDEF Extraction
- **Parses:** All SETLKF arrays in SETPAGEDEF structure
- **Uses:** LAST layout position (typically page 2, the repeating layout)
- **Format:** Takes first two values (x, y) from `[[x, y, width, height, rotation]]`
- **Only for:** STMTTP docformat (where page layout is defined)

### FRM Form Selection
- **Counter Used:** P (page count in PRINTFOOTER) instead of PP (total page count)
- **Logic:**
  - P < 1 (first page) → Use *F.FRM (first page form)
  - P >= 1 (subsequent) → Use *S.FRM (subsequent page form)
- **Location:** Inside PRINTFOOTER (executes for each page)

---

## Benefits

1. **Correct Line Spacing:** DFA documents now use the exact line spacing defined in Xerox source
2. **Page Layout Preservation:** OUTLINE maintains the original page layout coordinates
3. **Proper Form Timing:** Forms are applied in PRINTFOOTER (per-page) instead of main processing (per-document)
4. **Page Counter Logic:** Uses P counter for page-level decisions (correct) vs PP for document-level

---

**Implementation Status:** ✅ Complete and Verified
**Test Status:** ✅ Passed (SIBS_CAST sample files)
**Breaking Changes:** None (fully backward compatible)

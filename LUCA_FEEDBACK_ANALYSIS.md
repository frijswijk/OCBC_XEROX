# Luca's Feedback Analysis - DFA Corrections Required

## Critical Issues Identified

### 1. Data Reading Issues

#### Issue 1.1: CHANNEL-CODE must be NO
**Problem:** Generated `CHANNEL-CODE ANSI NOBREAKREPEAT`
**Fix:** Must be `CHANNEL-CODE NO`
**Reason:** Header is not in CHANNEL mode

```dfa
/* WRONG */
CHANNEL-CODE ANSI NOBREAKREPEAT

/* CORRECT */
CHANNEL-CODE NO
```

#### Issue 1.2: Use Arrays, Not Single Scalars
**Problem:** Generated single variables `CC` and `CONTENT`
**Fix:** Must use arrays `CC[C]` and `CONTENT[C]`
**Reason:** Single scalar loses all lines except the last

```dfa
/* WRONG */
CC = SUBSTR(LINE1, 1, 1, '');
CONTENT = SUBSTR(LINE1, 2, LENGTH(LINE1)-1, '');

/* CORRECT */
CC[C] = LEFT(LINE1, 1, '');
CONTENT[C] = SUBSTR(LINE1, 2, LENGTH(LINE1)-1, '');
```

#### Issue 1.3: Counter C Required
**Problem:** No counter for array indexing
**Fix:** Add `C = C + 1;` in ELSE block
**Reason:** Need to track array position

```dfa
/* CORRECT */
ELSE;
    N = 0;
    C = C + 1;  /* Increment array counter */
    CC[C] = LEFT(LINE1, 1, '');
    CONTENT[C] = SUBSTR(LINE1, 2, LENGTH(LINE1)-1, '');
```

#### Issue 1.4: N=0 Placement is Opposite
**Problem:** `N = 0` in THEN block (page break)
**Fix:** `N = 0` in ELSE block (normal line)
**Reason:** Logic was inverted

```dfa
/* WRONG */
IF LINE1=='1' OR $EOF; THEN;
    N = 0;  /* Reset to continue */

/* CORRECT */
IF LINE1=='1' OR $EOF; THEN;
    ENDGROUP;
    ENDDOCUMENT;
ELSE;
    N = 0;  /* Reset to continue processing */
```

#### Issue 1.5: Missing Header Reading
**Problem:** No header reading in $_BEFOREFIRSTDOC
**Fix:** Add FOR loop to read header lines

```dfa
DOCFORMAT $_BEFOREFIRSTDOC;
    PP = 0;
    VAR_DT1 = 0;
    VAR_DT2 = 0;
    VAR_INIT = 0;

    /* READ HEADER LINES */
    FOR I REPEAT 1;
        RECORD DATAHEADER REPEAT 1;
            VARIABLE LINE1 SCALAR NOSPACE START 1;
        ENDIO;
        IF LINE1=='1'; THEN;
        ELSE;
            I = 0;
        ENDIF;
    ENDFOR;
```

### 2. Logical Issues

#### Issue 2.1: Missing ENDGROUP
**Problem:** No ENDGROUP before ENDDOCUMENT
**Fix:** Add ENDGROUP to separate documents

```dfa
/* CORRECT */
IF LINE1=='1' OR $EOF; THEN;
    ENDGROUP;      /* Separate documents */
    ENDDOCUMENT;
```

#### Issue 2.2: Nested IFs Structure
**Problem:** Deep nested IFs are hard to maintain
**Note:** Luca says this is bad but kept the structure for now
**Future:** Consider switch-case or lookup table approach

### 3. Output Issues

#### Issue 3.1: Font Definitions
**Problem:** Missing standard fonts (NCR, F7, F6, FA, F2)
**Fix:** Add mappings to actual TTF fonts

```dfa
/* Additional standard fonts needed */
FONT NCR NOTDEF AS 'Times New Roman' DBCS ROTATION 0 HEIGHT 8.0;
FONT F7 NOTDEF AS 'Times New Roman' DBCS ROTATION 0 HEIGHT 8.0;
FONT F6 NOTDEF AS 'Arial' DBCS ROTATION 0 HEIGHT 8.0;
FONT FA NOTDEF AS 'Arial Bold' DBCS ROTATION 0 HEIGHT 9.0;
FONT F2 NOTDEF AS 'Arial' DBCS ROTATION 0 HEIGHT 8.0;
```

#### Issue 3.2: Color Names
**Problem:** Generated `BLACK`, should be `B`
**Fix:** Use short color names

```dfa
/* WRONG */
DEFINE BLACK COLOR RGB RVAL 0 GVAL 0 BVAL 0;
DEFINE WHITE COLOR RGB RVAL 100 GVAL 100 BVAL 100;
DEFINE RED COLOR RGB RVAL 100 GVAL 0 BVAL 0;

/* CORRECT */
DEFINE B COLOR RGB RVAL 0 GVAL 0 BVAL 0;
DEFINE WHITE COLOR RGB RVAL 100 GVAL 100 BVAL 100;
DEFINE R COLOR RGB RVAL 100 GVAL 0 BVAL 0;
```

#### Issue 3.3: OUTPUT Must Reference Array
**Problem:** OUTPUT CONTENT (single variable)
**Fix:** OUTPUT CONTENT[C] (array element)

```dfa
/* WRONG */
OUTPUT CONTENT
    FONT NCR NORMAL

/* CORRECT */
OUTPUT CONTENT[C]
    FONT NCR NORMAL
```

#### Issue 3.4: Color Reference
**Problem:** Using `COLOR BLACK`
**Fix:** Using `COLOR B`

```dfa
/* CORRECT */
OUTPUT CONTENT[C]
    FONT NCR NORMAL
    POSITION (SAME) (NEXT)
    COLOR B;  /* Not BLACK */
```

### 4. Variable Initialization

**Add to $_BEFOREFIRSTDOC:**
```dfa
PP = 0;     /* Page counter */
VAR_DT1 = 0;
VAR_DT2 = 0;
VAR_INIT = 0;
C = 0;      /* Array counter - MUST INITIALIZE */
```

## Implementation Checklist

- [ ] Change CHANNEL-CODE to NO
- [ ] Convert CC and CONTENT to arrays with [C] indexing
- [ ] Add C counter initialization and increment
- [ ] Move N=0 to ELSE block (opposite)
- [ ] Add ENDGROUP before ENDDOCUMENT
- [ ] Add header reading FOR loop in $_BEFOREFIRSTDOC
- [ ] Change color names: BLACK→B, RED→R
- [ ] Add standard fonts: NCR, F7, F6, FA, F2 with TTF mappings
- [ ] Change OUTPUT to use CONTENT[C]
- [ ] Initialize C=0 in $_BEFOREFIRSTDOC
- [ ] Use LEFT() for carriage control extraction
- [ ] Change COLOR BLACK to COLOR B in outputs

## Python Code Changes Required

### In `_generate_jdt_header()`:
- Change `CHANNEL-CODE ANSI NOBREAKREPEAT` to `CHANNEL-CODE NO`

### In `_generate_jdt_colors()`:
- Change color names to B, WHITE, R

### In `_generate_jdt_fonts()`:
- Add standard font mappings (NCR, F7, F6, FA, F2)

### In `_generate_jdt_docformat_main()`:
- Use arrays: CC[C], CONTENT[C]
- Add C counter increment
- Move N=0 to ELSE block
- Add ENDGROUP before ENDDOCUMENT
- Change OUTPUT to CONTENT[C]
- Use LEFT() for carriage control
- Change COLOR BLACK to COLOR B

### In `_generate_jdt_condition_formats()`:
- Change OUTPUT to use CONTENT[C]
- Change COLOR to use B instead of BLACK

### New method `_generate_beforefirstdoc()`:
- Add header reading FOR I loop
- Initialize C=0, PP=0, VAR_DT1, VAR_DT2, VAR_INIT

## Font Mapping Strategy

For generic handling across all JDT files:

```python
# Standard default fonts to add to every JDT conversion
STANDARD_FONTS = {
    'NCR': ('Times New Roman', 8.0),
    'F7': ('Times New Roman', 8.0),
    'F6': ('Arial', 8.0),
    'FA': ('Arial Bold', 9.0),
    'F2': ('Arial', 8.0),
}
```

## Testing After Fixes

1. Convert merstmtd.jdt again
2. Compare with corrected MERSTMTD.DFA
3. Verify:
   - CHANNEL-CODE NO present
   - Arrays used throughout
   - ENDGROUP present
   - Header reading loop present
   - Color names correct
   - Standard fonts present
   - C counter incremented

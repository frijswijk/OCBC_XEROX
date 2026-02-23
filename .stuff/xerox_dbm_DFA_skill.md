# Xerox DBM to DFA Conversion Skill

**Version:** 1.0
**Date:** 2026-01-30
**Purpose:** Expert knowledge for converting Xerox FreeFlow DBM files to Papyrus DFA format

---

## Skill Overview

This skill provides comprehensive knowledge for converting Xerox FreeFlow Designer files (DBM/FRM) to Papyrus DocDEF (DFA) format, based on extensive feedback from LucaB and production conversion experience.

---

## Core Conversion Principles

### 1. PREFIX Case Structure

**Xerox Pattern:**
```vipp
CASE PREFIX
{
    (prefix1) { /* subroutine logic */ }
    (prefix2) { /* subroutine logic */ }
}
ENDCASE
```

**DFA Equivalent:**
```dfa
/* Main document loop routes to DOCFORMATs based on PREFIX */
USE FORMAT REFERENCE('DF_'!PREFIX);

DOCFORMAT DF_prefix1;
    /* converted logic */

DOCFORMAT DF_prefix2;
    /* converted logic */
```

### 2. When to Generate DOCFORMAT

**Generate DOCFORMAT if case has:**
- OUTPUT commands (SH, NL, MOVEH, DRAWB, SCALL)
- Page layout commands (SETFORM, SETPAGEDEF, SETLKF)
- Data manipulation (GETINTV, SUBSTR with purpose)
- Page management logic (PAGEBRK + IF)
- Counter operations (++ or --)

**Do NOT generate if:**
- Only `/VAR_XX PREFIX SETVAR` (empty marker)
- All OUTPUT commands commented out
- No meaningful logic

**Exception:** Always create stub for undefined prefixes:
```dfa
DOCFORMAT DF_XX;
    /* XX Prefix not found */
```

---

## Command Translation Patterns

### OUTPUT vs TEXT Decision Logic

#### Use OUTPUT for:
- Simple single-font strings
- Single variable output
- Short text (< 50 chars)

```dfa
OUTPUT 'Simple text' FONT F5 POSITION 10 MM 20 MM;
OUTPUT VAR_AMOUNT FONT FK POSITION 180 MM SAME ALIGN RIGHT NOPAD;
```

#### Use TEXT BASELINE for:
- Long strings (> 50 chars)
- Font style changes mid-string
- Multiple lines with ALIGN JUSTIFY
- Text blocks with width constraint

```dfa
TEXT
    POSITION SAME SAME BASELINE
    WIDTH 193 MM
    FONT F3
    ALIGN JUSTIFY
    'Long text that wraps across multiple lines and needs '
    'proper justification and line breaking';
```

#### Font Style Changes in TEXT

**Xerox:**
```vipp
(**F5NOTE / **FCNOTA:) SH
```

**DFA:**
```dfa
TEXT
    POSITION SAME SAME BASELINE
    FONT F5 BOLD ALIGN JUSTIFY
    'NOTE / ' ITALIC
    'NOTA:';
```

Or:
```dfa
TEXT
    POSITION SAME SAME BASELINE
    FONT F5 ALIGN JUSTIFY
    'NOTE / ' FONT FC
    'NOTA:';
```

### Variable vs String Detection

**Critical Rule:** Only quote literal strings, NOT variable names

**Wrong:**
```dfa
OUTPUT 'VAR_SCCL'  ← Outputs literal "VAR_SCCL"
```

**Correct:**
```dfa
OUTPUT VAR_SCCL  ← Outputs variable value
```

**Detection Pattern:**
```python
if token.startswith('VAR_') or token in known_variables:
    # It's a variable - no quotes
    return f"OUTPUT {token}"
else:
    # It's a literal - add quotes and escape
    return f"OUTPUT '{escape_quotes(token)}'"
```

### Quote Escaping

**Xerox:**
```vipp
(Payments Accepted 'Without Prejudice') SH
```

**DFA:**
```dfa
OUTPUT 'Payments Accepted ''Without Prejudice''';  ← Double the single quote
```

### Positioning Logic

#### Rule 1: Only use NEXT when Xerox has NL

**Xerox with NL:**
```vipp
-06 NL
(Text) SH
```

**DFA:**
```dfa
OUTPUT '' POSITION SAME (SAME+6 MM);  ← Or SAME+6 MM for negative NL
OUTPUT 'Text' POSITION SAME (NEXT);  ← NL means go to next line
```

#### Rule 2: Use explicit positions for MOVEH

**Xerox:**
```vipp
12 MOVEH
(Current Credit Limit Utilised) SH
180 MOVEHR ($$VAR_SCCL.) SHr
```

**DFA:**
```dfa
OUTPUT 'Current Credit Limit Utilised'
    FONT FK NORMAL
    POSITION (12 MM-$MR_LEFT) (SAME);  ← Explicit X position
OUTPUT VAR_SCCL
    FONT FK NORMAL
    POSITION 180 MM SAME  ← Explicit X position
    ALIGN RIGHT NOPAD;
```

#### Rule 3: Use LASTMAX+6MM after TEXT commands

**After TEXT (not OUTPUT):**
```dfa
TEXT
    POSITION SAME SAME BASELINE
    FONT F3 ALIGN JUSTIFY
    'Long paragraph...';

OUTPUT 'Next section'
    FONT F5
    POSITION SAME (LASTMAX+6 MM);  ← Not SAME+6MM or NEXT
```

### Numeric Formatting

**Xerox:**
```vipp
183 MOVEHR VAR_LSB (@@@,@@@,@@@,@@#.##) FORMAT SHr
```

**DFA:**
```dfa
OUTPUT NUMPICTURE(VAR_LSB,'#,##0.00')
    FONT FK
    POSITION 183 MM SAME
    ALIGN RIGHT NOPAD;
```

**Format String Conversion:**
| Xerox Format | DFA NUMPICTURE |
|--------------|----------------|
| `@@@,@@@,@@#.##` | `'#,##0.00'` |
| `@@@,@@#.##` | `'#,##0.00'` |
| `@@#` | `'#,##0'` |
| `#,###.##` | `'#,##0.00'` |

**Format Character Mapping:**
| Xerox | Meaning | DFA |
|-------|---------|-----|
| `@` | Leading zero becomes space | `#` (optional digit) |
| `#` | Digit | `0` (required digit) or `#` |
| `,` | Thousands separator | `,` |
| `.` | Decimal point | `.` |

### IF/THEN/ELSE/ENDIF Structure

**Critical:** Must properly pair ELSE with IF, use ISTRUE()

**Xerox:**
```vipp
IF CPCOUNT 1 eq
{ /VAR_pctot 0 SETVAR }
ELSE
{ /VAR_COUNTTD 0 SETVAR } ENDIF
```

**Wrong DFA:**
```dfa
IF CPCOUNT == 1; THEN;
    VAR_pctot = 0;
ENDIF;        ← Too early!
ELSE;         ← Orphan!
    VAR_COUNTTD = 0;
ENDIF;
```

**Correct DFA:**
```dfa
IF ISTRUE(CPCOUNT==1);
THEN;
    VAR_PCTOT = 0;
ELSE;
    VAR_COUNTTD = 0;
    VARDOC = VARDOC+1;
ENDIF;
```

**Implementation:** Parser must lookahead for ELSE before closing IF block

### Variables with Trailing Spaces

**Xerox:**
```vipp
IF VAR_PDD (IMMEDIATE) eq
```

**DFA:**
```dfa
IF NOSPACE(VAR_PDD)=='IMMEDIATE';
THEN;
    /* logic */
ENDIF;
```

**When to use NOSPACE():**
- String comparisons
- Variables that may have trailing spaces from data
- Especially in IF conditions

### Box/Table Positioning

**Xerox Segment:**
```vipp
/CSBX {
    00 00 193 13.5 MED DRAWB        % Top shaded box
    00 00 0.001 50.5 XDRK DRAWB     % Left vertical line
    57 -13.5 0.001 36.7 XDRK DRAWB  % Column divider
    193 00 0.001 50.5 XDRK DRAWB    % Right vertical line
    00 00 193 0.001 XDRK DRAWB      % Top horizontal line
    00 -13.5 193 0.001 XDRK DRAWB   % Middle horizontal line
    00 -50.5 193 0.001 XDRK DRAWB   % Bottom horizontal line
} XGFRESDEF
```

**DFA Conversion:**
```dfa
/* Set position anchors */
POSY = $SL_CURRY;
POSX = $SL_CURRX;

/* Top shaded box */
BOX
    POSITION (POSX+0 MM) (POSY+0 MM)
    WIDTH 193 MM
    HEIGHT 13.5 MM
    COLOR LMED
    THICKNESS 0 TYPE SOLID SHADE 100;

/* Left vertical line */
BOX
    POSITION (POSX+0 MM) (POSY+0 MM)
    WIDTH 0.1 MM
    HEIGHT 50.5 MM
    COLOR XDRK
    THICKNESS 0 TYPE SOLID SHADE 100;

/* Column divider - NOTE Y-coordinate inverted! */
BOX
    POSITION (POSX+57 MM) (POSY+13.5 MM)  ← Was -13.5, now +13.5
    WIDTH 0.1 MM
    HEIGHT 36.7 MM
    COLOR XDRK
    THICKNESS 0 TYPE SOLID SHADE 100;

/* Bottom horizontal line - Y inverted */
BOX
    POSITION (POSX+0 MM) (POSY+50.5 MM)  ← Was -50.5, now +50.5
    WIDTH 193 MM
    HEIGHT 0.1 MM
    COLOR XDRK
    THICKNESS LIGHT TYPE SOLID SHADE 100;
```

**Key Rules:**
1. Set `POSX = $SL_CURRX; POSY = $SL_CURRY;` to anchor position
2. All box positions relative to POSX/POSY
3. **Invert Y coordinates:** Negative in Xerox becomes positive in DFA
4. Width 0.001 → 0.1 MM (convert to reasonable DFA value)
5. For filled boxes: `THICKNESS 0 SHADE 100`
6. For lines: `THICKNESS LIGHT` or `THICKNESS 1 PELS`

### DRAWB Parameters

**Xerox Format:**
```
X Y Width Height Color DRAWB
```

**Conversion:**
```
X → POSX+X MM
Y → POSY+ABS(Y) MM  (flip sign if negative)
Width → WIDTH ... MM
Height → HEIGHT ... MM
Color → COLOR ...
```

**Thickness Mapping:**
| Xerox Width | DFA THICKNESS |
|-------------|---------------|
| 0.001 | LIGHT |
| 0.01 | LIGHT |
| 0.1 | MEDIUM |
| > 1 | HEAVY or numeric |

### SCALL (Subroutine Call)

**Xerox:**
```vipp
(NOTE) SCALL

/NOTE {
    F5
    (Important Notice) SH
    NL
}
```

**DFA Options:**

**Option 1: Inline the content**
```dfa
/* NOTE subroutine inlined */
OUTPUT 'Important Notice'
    FONT F5
    POSITION SAME SAME;
OUTPUT '' POSITION SAME NEXT;
```

**Option 2: Convert to SEGMENT** (if complex)
```dfa
/* NOTE subroutine as SEGMENT */
SEGMENT NOTE;
    OUTPUT 'Important Notice'
        FONT F5
        POSITION SAME SAME;
    OUTPUT '' POSITION SAME NEXT;
ENDSEG;

/* Call it */
USE SEGMENT NOTE;
```

### Image Calling (ICALL)

**Xerox:**
```vipp
(SCISSORS.JPG) 0.06 0 ICALL
```

**DFA:**
```dfa
CREATEOBJECT IOBDLL(IOBDEFS)
    POSITION SAME SAME
    PARAMETERS
        ('FILENAME'='SCISSORS')  ← Extension removed
        ('OBJECTTYPE'='1')
        ('OTHERTYPES'='JPG')
        ('XOBJECTAREASIZE'='6')  ← 0.06 * 100 = 6
        ('OBJECTMAPPING'='2');
```

**Scale Conversion:** Multiply Xerox scale by 100
- 0.06 → 6
- 0.10 → 10
- 1.00 → 100

---

## Color Definitions

### Standard Colors to Define

```dfa
/* Black and White */
COLOR FBLACK AS BLACK;
COLOR B AS BLACK;
COLOR W AS WHITE;

/* Grays */
COLOR LMED AS RGB 217 217 217;  /* Light Medium Gray */
COLOR MED AS RGB 217 217 217;   /* Medium Gray (same as LMED) */
COLOR XDRK AS RGB 166 166 166;  /* Extra Dark Gray */
```

**Common Issue:** LMED used in DRAWB but not defined - always include it!

---

## Variable Initialization

### Extract from Xerox Initialization Block

**Xerox Pattern:**
```vipp
/VARINI true /INI SETVAR
IF VARINI
{
    /* Page setup */
    MM SETUNIT
    ORITL
    PORT
    04 SETLSP
    210 297 SETPAGESIZE

    /* Run once */
    /VARINI false SETVAR

    /* Variable initialization */
    /VAR_MOC 0 /INI SETVAR
    /VAR_I1 0 /INI SETVAR
    /VAR_COUNTPAGE 0 /INI SETVAR
    /* ... many more ... */
}
ENDIF
```

**DFA Conversion:**

**1. Extract to $_BEFOREFIRSTDOC:**
```dfa
DOCFORMAT $_BEFOREFIRSTDOC;
    /* Data input setup */
    &SEP = '|';
    FOR I REPEAT 1;
        RECORD DATAHEADER REPEAT 1;
            VARIABLE LINE1 SCALAR NOSPACE START 1;
        ENDIO;
        FLD = EXTRACTALL(LINE1, &SEP, 1);
    ENDFOR;
```

**2. Initialize variables:**
```dfa
DOCFORMAT $_BEFOREDOC;
    P = 0;
    PP = 0;

    /* From /INI SETVAR in Xerox */
    VAR_MOC = 0;
    VAR_I1 = 0;
    VAR_COUNTPAGE = 0;
    VAR_COUNTTD = 0;

    /* BOX positioning variables */
    VAR = MM(40);
    Y3 = MM(40);
    Y5 = MM(40);
```

**Pattern Recognition:**
```python
# Extract all /VAR_XXX number /INI SETVAR
pattern = r'/(\w+)\s+(\S+)\s+/INI\s+SETVAR'
# Convert to: VAR_XXX = value;
```

---

## FormatGroup and FRM Usage

### Correct Pattern for Multiple FRMs

**Wrong (Current):**
```dfa
LOGICALPAGE 1
    /* ... */
    PRINTFOOTER
        /* Directly call forms - WRONG! */
    PRINTEND;
```

**Correct (LucaB's Pattern):**
```dfa
FORMATGROUP MAIN;
    SHEET WIDTH 210 MM HEIGHT 297 MM;
    LAYER 1;

    LOGICALPAGE 1
        SIDE FRONT
        POSITION 0 0
        WIDTH 210 MM HEIGHT 297 MM
        DIRECTION ACROSS
        FOOTER
            PP = PP+1;
        FOOTEREND
        PRINTFOOTER
            P = P+1;  ← Increment page-within-document counter

            /* Conditional form usage */
            IF P==1; THEN;
                USE FORMAT CASIOS EXTERNAL;
            ENDIF;
            IF P==2; THEN;
                USE FORMAT CASIOF EXTERNAL;
            ENDIF;
            IF P==3; THEN;
                USE FORMAT CASIO_TNC EXTERNAL;
            ENDIF;
            IF P==4; THEN;
                USE FORMAT CASIOF3 EXTERNAL;
            ENDIF;
            IF P==5; THEN;
                USE FORMAT CASIOB EXTERNAL;
            ENDIF;

            /* Page number in footer */
            OUTLINE
                POSITION RIGHT (0 MM)
                DIRECTION ACROSS;
                OUTPUT 'Page '!P!' of '!PP
                    FONT F5_1
                    POSITION (RIGHT-11 MM) 286 MM
                    ALIGN RIGHT NOPAD;
            ENDIO;
        PRINTEND;
```

**Key Elements:**
- `P` counter tracks page within document
- `PP` counter tracks total pages across all documents
- Each page type gets its own form via `IF P==N`
- Forms loaded with `USE FORMAT name EXTERNAL;`

---

## Page Break Control

### Xerox Manual Page Break

**Xerox:**
```vipp
IF FRLEFT 60 lt
{
    PAGEBRK
    NEWFRONT
    (CASIOF.FRM) SETFORM
}
ENDIF
```

**DFA Option 1 (Explicit):**
```dfa
IF $SL_MAXY>$LP_HEIGHT-MM(60);
THEN;
    USE LP NEXT;
ENDIF;
```

**DFA Option 2 (Automatic):**
Let DFA handle automatic page breaks - don't convert FRLEFT checks at all

**Recommendation:** Use automatic page breaks unless specific control needed

---

## Common Pitfalls and Solutions

### Pitfall 1: JUSTIFY in OUTPUT

**Wrong:**
```dfa
OUTPUT 'text' ALIGN JUSTIFY NOPAD;  ← OUTPUT doesn't support JUSTIFY!
```

**Correct:**
```dfa
TEXT
    POSITION SAME SAME BASELINE
    ALIGN JUSTIFY
    'text';
```

### Pitfall 2: NEXT Overuse

**Wrong:**
```dfa
OUTPUT 'Line 1' POSITION SAME NEXT;
OUTPUT 'Line 2' POSITION SAME NEXT;  ← No NL in Xerox!
OUTPUT 'Line 3' POSITION SAME NEXT;
```

**Correct:**
```dfa
OUTPUT 'Line 1' POSITION 10 MM 20 MM;
OUTPUT 'Line 2' POSITION 10 MM SAME;  ← Same line
OUTPUT 'Line 3' POSITION 10 MM SAME;
```

### Pitfall 3: Missing Y-Coordinate Inversion

**Wrong:**
```dfa
BOX POSITION (POSX+0 MM) (POSY-13.5 MM)  ← Negative Y!
```

**Correct:**
```dfa
BOX POSITION (POSX+0 MM) (POSY+13.5 MM)  ← Inverted to positive
```

### Pitfall 4: Variable Name as String

**Wrong:**
```dfa
OUTPUT 'VAR_AMOUNT'  ← Literal string
```

**Correct:**
```dfa
OUTPUT VAR_AMOUNT  ← Variable value
```

### Pitfall 5: Filtering Valid Cases

**Wrong:**
Don't filter Y1, Y2, T1, D1 just because they seem simple - check if they're referenced elsewhere

**Correct:**
Review LucaB's feedback - if he says "retrieve and convert it", don't filter it!

---

## Quality Checklist

Before finalizing conversion, verify:

- [ ] No orphan ELSE statements
- [ ] Variables output as values, not strings
- [ ] TEXT BASELINE used for complex strings
- [ ] OUTPUT used only for simple strings
- [ ] NEXT only where Xerox has NL
- [ ] All colors defined (especially LMED)
- [ ] Numeric formatting uses NUMPICTURE
- [ ] Box positions use POSX/POSY anchors
- [ ] Y coordinates inverted (negative → positive)
- [ ] Quotes escaped in strings (' → '')
- [ ] NOSPACE() used for string comparisons
- [ ] IF conditions wrapped in ISTRUE()
- [ ] FRM forms called with P counter pattern
- [ ] All /INI SETVAR variables initialized
- [ ] LOGICALPAGE 2 exists for duplex
- [ ] No JUSTIFY in OUTPUT commands

---

## References

- **LucaB's Email:** "Casio - OCBC.pdf" (25 pages of detailed corrections)
- **Working Example:** SIBS_CAST.DBM (95% correct conversion)
- **Target Example:** CASIO.DBM (8 DOCFORMATs, 800-900 lines)
- **Previous Analysis:** LUCA_CASIO_CORRECTIONS_ANALYSIS.md
- **Fixes Implemented:** FIXES_IMPLEMENTED_SUMMARY.md
- **Comparison:** SIBS_VS_CASIO_COMPARISON.md

---

## Skill Usage

Invoke this skill when:
- Converting Xerox DBM/FRM files to DFA
- Debugging DFA conversion issues
- Reviewing converter output quality
- Implementing converter improvements
- Answering questions about Xerox → DFA patterns

This skill encapsulates production-validated knowledge from multiple conversion iterations and extensive expert feedback.

# Xerox VIPP to Papyrus DFA Conversion Guide

**Version:** 3.0
**Date:** January 9, 2026
**Author:** Claude Code
**Converter:** universal_xerox_parser.py

---

## Table of Contents

1. [Overview](#1-overview)
2. [Getting Started](#2-getting-started)
3. [Architecture Comparison](#3-architecture-comparison)
4. [DFA Document Structure](#4-dfa-document-structure)
5. [Command Conversion Reference](#5-command-conversion-reference)
6. [Font System](#6-font-system)
7. [Color System](#7-color-system)
8. [Page Layout System](#8-page-layout-system)
9. [Variable System](#9-variable-system)
10. [OUTPUT vs TEXT Commands](#10-output-vs-text-commands)
11. [Operators](#11-operators)
12. [Resource Handling](#12-resource-handling)
13. [Complete Conversion Examples](#13-complete-conversion-examples)
14. [Recent Updates](#14-recent-updates)
15. [Quick Reference Card](#15-quick-reference-card)

---

## 1. Overview

### 1.1 What is VIPP?

VIPP (Variable data Intelligent PostScript Printware) is Xerox's proprietary language for variable data printing. It extends PostScript with high-level constructs for:

- Data-driven document composition
- Reusable form templates
- Dynamic text and image placement
- Multi-page document handling

### 1.2 What is DFA (DocDEF)?

Papyrus DocDEF (DFA) is ISIS Papyrus's document definition language for:

- Enterprise document composition
- High-volume output management
- Multi-channel delivery (print, PDF, email)
- Template-based document generation

### 1.3 Key Differences

| Aspect | VIPP | DFA |
|--------|------|-----|
| **Syntax** | PostScript-based (reverse Polish notation) | Procedural/declarative |
| **Comments** | `%` for line, `/* */` for block | `/* */` for block |
| **Variables** | `/VAR_name value SETVAR` | `VAR_name = value;` |
| **Strings** | `(text)` parentheses | `'text'` single quotes |
| **Operators** | `eq`, `ne`, `lt`, `gt` | `==`, `<>`, `<`, `>` |

---

## 2. Getting Started

### 2.1 Installation

The universal Xerox to DFA converter is a Python script that requires Python 3.6 or higher.

**Requirements:**
- Python 3.6+
- No external dependencies

### 2.2 Usage

**Basic Usage:**
```bash
python universal_xerox_parser.py <input_directory>
```

**Example:**
```bash
python universal_xerox_parser.py "SamplePDF\SIBS_CAST - codes"
```

**What it does:**
1. Scans the input directory for VIPP files (.DBM, .FRM)
2. Parses VIPP syntax (PostScript/RPN)
3. Converts to DFA format
4. Generates output files in `output/` directory

### 2.3 Input Files

The converter expects:
- **DBM files** (.DBM): Database module containing data processing logic
- **FRM files** (.FRM): Form templates containing layout/design

**Example directory structure:**
```
SamplePDF/SIBS_CAST - codes/
├── SIBS_CAST.DBM          # Main processing logic
├── SIBS_CASTF.FRM         # First page form template
└── SIBS_CASTS.FRM         # Subsequent pages form template
```

### 2.4 Output Files

The converter generates:
- **Main DFA** (e.g., `SIBS_CAST.dfa`): Converted DBM with RECORD structure and SELECT/CASE logic
- **Form DFAs** (e.g., `SIBS_CASTF.dfa`, `SIBS_CASTS.dfa`): Converted FRM files with DOCFORMAT sections

**Output directory structure:**
```
output/
├── SIBS_CAST.dfa          # Main document definition
├── SIBS_CASTF.dfa         # First page form
└── SIBS_CASTS.dfa         # Subsequent pages form
```

### 2.5 Common Conversion Workflow

1. **Prepare Input**: Place VIPP .DBM and .FRM files in a directory
2. **Run Converter**: `python universal_xerox_parser.py <directory>`
3. **Review Output**: Check generated .dfa files in `output/` directory
4. **Test in Papyrus**: Load main .dfa file into Papyrus platform
5. **Validate**: Run test data through the converted document definition

---

## 3. Architecture Comparison

### 3.1 VIPP Document Structure

```
+---------------------------------------------------------+
|  DBM File (Database Module)                             |
|  -------------------------------------------------------+
|  - Variable declarations                                |
|  - Font/Color definitions                               |
|  - CASE PREFIX processing blocks                        |
|  - Page layout definitions (SETLKF, SETPAGEDEF)        |
|  - References FRM files via SETFORM                     |
+---------------------------------------------------------+
              |
              v
+---------------------------------------------------------+
|  FRM File (Form Template)                               |
|  -------------------------------------------------------+
|  - Static page elements                                 |
|  - Logo placements                                      |
|  - Header/footer layouts                                |
|  - Conditional branding                                 |
+---------------------------------------------------------+
```

### 3.2 DFA Document Structure

```
+---------------------------------------------------------+
|  DFA File (Document Definition)                         |
|  -------------------------------------------------------+
|  - DOCDEF header                                        |
|  - APPLICATION-INPUT-FORMAT                             |
|  - APPLICATION-OUTPUT-FORMAT                            |
|  - FORMATGROUP (page layout)                            |
|  - FONT definitions                                     |
|  - COLOR definitions (DEFINE)                           |
|  - DOCFORMAT sections                                   |
|  - RECORD structure (input parsing)                     |
|  - SELECT/CASE processing                               |
|  - ENDDOCDEF footer                                     |
+---------------------------------------------------------+
```

---

## 4. DFA Document Structure

### 4.1 Complete DFA Template

```dfa
/* Header Comments */
/* Generated by: Universal Xerox to Papyrus DFA Converter */
/* Date: YYYY-MM-DD */

DOCDEF DOCUMENTNAME;

/* Input Format - MANDATORY */
APPLICATION-INPUT-FORMAT
    CODE 1200
    RECORD-FORMAT VARPC
    RECORD-DELIMITER X'0D0A'
    RECORD-LENGTH 1024
    CHANNEL-CODE ANSI NOBREAKREPEAT
    TABLE-REF-CODE NO
    DECIMAL-SEPARATOR '.'
    CACHELIMIT 100;

/* Output Format */
APPLICATION-OUTPUT-FORMAT
    CODE 1200
    AFPLRECL 8192
    PTXUNIT 1440
    FDFINCLUDE YES
    TLE YES
    ACIFINDEX NO;

/* PDF Output */
DEFINEPDFOUTPUT PDFOUT;

/* Page Layout - FORMATGROUP */
FORMATGROUP MAIN;
    SHEET
        WIDTH 210 MM
        HEIGHT 297 MM;
    LAYER 1;
    LOGICALPAGE 1
        SIDE FRONT
        POSITION 0 0
        WIDTH 210 MM
        HEIGHT 297 MM
        DIRECTION ACROSS
        /* FOOTER counts total pages (called once at end of document) */
        FOOTER
            PP = PP + 1;
        FOOTEREND
        /* PRINTFOOTER outputs page numbers (called for each page in buffer) */
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
        PRINTEND;

/* Font Definitions */
FONT ARIAL10 NOTDEF AS 'Arial' BOLD NOTDEF AS 'Arial Bold'
    ITALIC NOTDEF AS 'Arial Italic'
    BOLDITALIC NOTDEF AS 'Arial Bold Italic'
    DBCS ROTATION 0 HEIGHT 10.0;

/* Color Definitions */
DEFINE R COLOR RGB RVAL 100 GVAL 0 BVAL 0;
DEFINE B COLOR RGB RVAL 0 GVAL 0 BVAL 0;
DEFINE FONT_BLACK COLOR RGB RVAL 0 GVAL 0 BVAL 0;
DEFINE FONT_GRAY COLOR RGB RVAL 38 GVAL 38.8 BVAL 40;

/* Main Document Format */
DOCFORMAT THEMAIN;
    USE
        FORMATGROUP MAIN;
    SETUNITS LINESP AUTO;
    MARGIN TOP 20 MM BOTTOM 20 MM LEFT 15 MM RIGHT 15 MM;

/* Record Structure */
RECORD INPUTREC
    REPEAT 1;
    VARIABLE PREFIX NOSPACE START * LENGTH 10;
    VARIABLE FLD1 NOSPACE START * LENGTH 50;
    VARIABLE FLD2 NOSPACE START * LENGTH 50;
ENDIO;

/* Processing Logic */
SELECT PREFIX;
CASE 'HEADER';
    /* processing */
ENDSELECT;

/* Initialization - called once before first document */
DOCFORMAT $_BEFOREFIRSTDOC;
    P = 0;     /* Page counter for PRINTFOOTER */
    PP = 0;    /* Total page counter for FOOTER */

/* Per-document initialization - called before each new document */
DOCFORMAT $_BEFOREDOC;
    P = 0;     /* Reset page counter */
    PP = 0;    /* Reset total pages */

/* END OF DOCDEF FILE */
ENDDOCDEF;
```

---

## 5. Command Conversion Reference

### 5.1 Text Output Commands

| VIPP Command | DFA Equivalent | Description |
|--------------|----------------|-------------|
| `(text) SH` | `OUTPUT 'text' FONT name NORMAL;` | Show text |
| `(text) SHL` | `OUTPUT 'text' FONT name NORMAL ALIGN LEFT;` | Left-aligned |
| `(text) SHR` | `OUTPUT 'text' FONT name NORMAL ALIGN RIGHT;` | Right-aligned |
| `(text) SHC` | `OUTPUT 'text' FONT name NORMAL ALIGN CENTER;` | Centered |
| `var width align SHP` | `TEXT ... WIDTH width MM ...;` | Show variable with width/alignment |

**VIPP Example:**
```postscript
F4
38 MOVEH
(Balance B/F) SH
193 MOVEH
VAR_CLSB SHr
```

**DFA Equivalent:**
```dfa
OUTPUT 'Balance B/F'
    FONT F4 NORMAL
    POSITION (38.0 MM-$MR_LEFT) (45.0 MM-$MR_TOP);
OUTPUT VAR_CLSB
    FONT F4 NORMAL
    POSITION (193.0 MM-$MR_LEFT) (SAME)
    ALIGN RIGHT NOPAD;
```

### 5.2 Positioning Commands

| VIPP Command | DFA Equivalent | Description |
|--------------|----------------|-------------|
| `x y MOVETO` | `POSITION (x MM-$MR_LEFT) (y MM-$MR_TOP)` | Absolute positioning |
| `x MOVEH` | `POSITION (x MM-$MR_LEFT) (SAME)` | Horizontal move |
| `NL` | `OUTPUT '' POSITION (SAME) (NEXT);` | New line (advance down) |
| `-n NL` | `OUTPUT '' POSITION (SAME) (SAME-n MM);` | Move up n millimeters |
| `n SETLSP` | `SETUNITS LINESP n MM;` | Set line spacing |

**Important:**
- All positions use margin-relative coordinates: `(x MM-$MR_LEFT)` and `(y MM-$MR_TOP)`
- After NL without explicit vertical position, next OUTPUT uses `(NEXT)` for vertical position

**Negative NL Example:**
```postscript
F5
-04 NL
38 MOVEH (No. of Withdrawals) VSUB SH
```

**DFA Equivalent:**
```dfa
OUTPUT ''
    FONT F5 NORMAL
    POSITION (SAME) (SAME-4.0 MM);
OUTPUT 'No. of Withdrawals'
    FONT F5 NORMAL
    POSITION (38.0 MM-$MR_LEFT) (NEXT)
    ALIGN LEFT NOPAD;
```

### 5.3 Drawing Commands

| VIPP Command | DFA Equivalent | Description |
|--------------|----------------|-------------|
| `x y w h style DRAWB` (h < 1mm) | `RULE POSITION x MM y MM LENGTH w MM DIRECTION ACROSS;` | Horizontal line |
| `x y w h style DRAWB` (w < 1mm) | `RULE POSITION x MM y MM LENGTH h MM DIRECTION DOWN;` | Vertical line |
| `x y w h style DRAWB` (w,h > 1mm) | `BOX POSITION x MM y MM WIDTH w MM HEIGHT h MM;` | Rectangle |
| `CLIP ... ENDCLIP` | *Not supported* | Use MARGIN or TEXT WIDTH instead |

**DFA RULE Example (horizontal line):**
```dfa
RULE
    POSITION (12 MM-$MR_LEFT) (17 MM-$MR_TOP)
    DIRECTION ACROSS
    COLOR R
    LENGTH 187 MM
    THICKNESS 0.2 MM TYPE SOLID;
```

**DFA BOX Example:**
```dfa
BOX
    POSITION (11 MM-$MR_LEFT) (204 MM-$MR_TOP)
    WIDTH 188 MM
    HEIGHT 47 MM
    THICKNESS MEDIUM TYPE SOLID;
```

### 5.4 Control Flow Commands

| VIPP Command | DFA Equivalent |
|--------------|----------------|
| `condition IF { body } ENDIF` | `IF condition; THEN; body ENDIF;` |
| `condition IF { true } ELSE { false } ENDIF` | `IF condition; THEN; true ELSE; false ENDIF;` |
| `FOR var n REPEAT { body }` | `FOR var REPEAT n; body ENDFOR;` |

**VIPP Example:**
```postscript
VAR_CCAST (CCAST) eq IF {
    NL
    38 MOVEH
    (OCBC Bank) SH
} ENDIF
```

**DFA Equivalent:**
```dfa
IF VAR_CCAST == 'CCAST'; THEN;
    OUTPUT ''
        FONT F7 NORMAL
        POSITION (SAME) (NEXT);
    OUTPUT 'OCBC Bank'
        FONT F7 NORMAL
        POSITION (38.0 MM-$MR_LEFT) (SAME);
ENDIF;
```

**DFA Operators:**
- `==` equals
- `<>` not equals
- `<`, `>`, `<=`, `>=` comparison operators

---

## 6. Font System

### 6.1 VIPP Font Definition

```postscript
% Define font aliases
/F1  /ARIAL      10  INDEXFONT
/F2  /ARIALB     08  INDEXFONT
/F3  /ARIALO     07  INDEXFONT
/F4  /ARIALBO    08  INDEXFONT
```

### 6.2 DFA Font Definition (Correct Syntax)

**IMPORTANT:** DFA fonts must use the `NOTDEF AS` syntax with all style variants:

```dfa
FONT ARIAL10 NOTDEF AS 'Arial' BOLD NOTDEF AS 'Arial Bold'
    ITALIC NOTDEF AS 'Arial Italic'
    BOLDITALIC NOTDEF AS 'Arial Bold Italic'
    DBCS ROTATION 0 HEIGHT 10.0;

FONT ARIALB08 NOTDEF AS 'Arial Bold' BOLD NOTDEF AS 'Arial Bold'
    ITALIC NOTDEF AS 'Arial Bold Italic'
    BOLDITALIC NOTDEF AS 'Arial Bold Italic'
    DBCS ROTATION 0 HEIGHT 8.0;
```

### 6.3 Font Name Mapping

| VIPP Font | DFA Font Family |
|-----------|-----------------|
| `ARIAL` | `Arial` |
| `ARIALB` | `Arial Bold` |
| `ARIALO` | `Arial Italic` |
| `ARIALBO` | `Arial Bold Italic` |
| `COURIER` | `Courier New` |
| `COURIERB` | `Courier New Bold` |
| `HELVETICA` | `Helvetica` |
| `TIMES` | `Times New Roman` |

### 6.4 Font Conflict Resolution

When FRM files define fonts with aliases that conflict with DBM fonts, the converter automatically renames FRM fonts:

**Example:**
```
F2 in DBM: ARIAL 7pt
F2 in FRM: ARIAL 6pt
→ FRM font renamed to F2_1
```

### 6.5 Using Fonts in OUTPUT

Fonts are specified inline with OUTPUT commands:

```dfa
OUTPUT 'Customer Name'
    FONT ARIAL10 NORMAL
    POSITION LEFT NEXT;

OUTPUT 'Important Notice'
    FONT ARIALB10 NORMAL
    POSITION LEFT NEXT;
```

**IMPORTANT:** Always use `NORMAL` as the style. Font weight/style is baked into the font definition, not applied at OUTPUT time.

---

## 7. Color System

### 7.1 VIPP Color Commands

**Single-Letter Color Identifiers:**
```postscript
R    % Red
B    % Black
W    % White
G    % Green
C    % Cyan
M    % Magenta
Y    % Yellow
K    % Black (CMYK)
```

**Usage in VIPP:**
```postscript
R                              % Set color to red
NL
(https://www.ocbc.com.my) SHR  % Output text in red
B                              % Set color back to black
```

### 7.2 DFA Color Definition (Correct Syntax)

**IMPORTANT:** DFA colors use the `DEFINE` command with RGB values as percentages (0-100):

```dfa
/* Standard Color Definitions */
DEFINE R COLOR RGB RVAL 100 GVAL 0 BVAL 0;
DEFINE B COLOR RGB RVAL 0 GVAL 0 BVAL 0;
DEFINE W COLOR RGB RVAL 100 GVAL 100 BVAL 100;
DEFINE G COLOR RGB RVAL 0 GVAL 100 BVAL 0;
DEFINE C COLOR RGB RVAL 0 GVAL 100 BVAL 100;
DEFINE M COLOR RGB RVAL 100 GVAL 0 BVAL 100;
DEFINE Y COLOR RGB RVAL 100 GVAL 100 BVAL 0;
DEFINE K COLOR RGB RVAL 0 GVAL 0 BVAL 0;

/* Custom Colors */
DEFINE FONT_BLACK COLOR RGB RVAL 0 GVAL 0 BVAL 0;
DEFINE FONT_GRAY COLOR RGB RVAL 38 GVAL 38.8 BVAL 40;
DEFINE LIGHT_CYAN COLOR RGB RVAL 81.2 GVAL 93.3 BVAL 98.8;
```

### 7.3 Color Tracking and Output

The converter tracks color state throughout FRM conversion:

**VIPP:**
```postscript
R
NL
(https://www.ocbc.com.my) SHR
B
NL
(Back to black) SH
```

**DFA:**
```dfa
OUTPUT ''
    FONT F2 NORMAL
    POSITION (SAME) (NEXT);
OUTPUT 'https://www.ocbc.com.my'
    FONT F2_1 NORMAL
    POSITION (SAME) (NEXT)
    COLOR R
    ALIGN RIGHT NOPAD;
OUTPUT ''
    FONT F2 NORMAL
    POSITION (SAME) (NEXT);
OUTPUT 'Back to black'
    FONT F2 NORMAL
    POSITION (SAME) (NEXT)
    COLOR B;
```

**Color Persistence:**
- Color state persists across multiple OUTPUT commands
- Color changes only when a new color command is encountered
- Each OUTPUT includes `COLOR <identifier>` if a color is active

### 7.4 Using Colors in BOX and RULE

```dfa
BOX
    POSITION (11 MM-$MR_LEFT) (204 MM-$MR_TOP)
    WIDTH 188 MM
    HEIGHT 47 MM
    COLOR R
    THICKNESS MEDIUM TYPE SOLID;

RULE
    POSITION (12 MM-$MR_LEFT) (17 MM-$MR_TOP)
    DIRECTION ACROSS
    COLOR R
    LENGTH 187 MM
    THICKNESS 0.2 MM TYPE SOLID;
```

---

## 8. Page Layout System

### 8.1 VIPP Page Layout (SETLKF/SETPAGEDEF)

```postscript
% Define linked frame
[ [ 12 82 183 120 0 ] ] SETLKF

% Define page definitions array
[
    { [ [ 12 82 183 120 0 ] ] SETLKF
      (FIRST_PAGE.FRM) SETFORM }
    { [ [ 12 82 183 190 0 ] ] SETLKF
      (CONT_PAGE.FRM) SETFORM } /R
] SETPAGEDEF
```

### 8.2 DFA Page Layout (FORMATGROUP)

**IMPORTANT:** DFA uses FORMATGROUP for page layout:

```dfa
/* Page Layout - FORMATGROUP */
FORMATGROUP MAIN;
    SHEET
        WIDTH 210 MM
        HEIGHT 297 MM;
    LAYER 1;
    LOGICALPAGE 1
        SIDE FRONT
        POSITION 0 0
        WIDTH 210 MM
        HEIGHT 297 MM
        DIRECTION ACROSS
        /* FOOTER counts total pages (called once at end of document) */
        FOOTER
            PP = PP + 1;
        FOOTEREND
        /* PRINTFOOTER outputs page numbers (called for each page in buffer) */
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
        PRINTEND;
```

### 8.3 Using FORMATGROUP in DOCFORMAT

```dfa
DOCFORMAT THEMAIN;
    USE
        FORMATGROUP MAIN;
    SETUNITS LINESP AUTO;
    MARGIN TOP 20 MM BOTTOM 20 MM LEFT 15 MM RIGHT 15 MM;

    /* Document content here */
```

### 8.4 Using External Formats (FRM Files)

Each VIPP FRM file is converted to a separate DFA file with its own DOCFORMAT. To reference an external format from the main document, use the `USE FORMAT` command with the `EXTERNAL` keyword:

**In PRINTFOOTER (for page-by-page form selection):**
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

**FRM DFA file structure (SIBS_CASTF.dfa):**
```dfa
/* FRM DFA File: SamplePDF\SIBS_CAST - codes\SIBS_CASTF.FRM */
/* Generated by Universal Xerox FreeFlow to Papyrus DocDEF Converter */

OUTLINE;
SETUNITS LINESP 02 MM;
IF VAR_CCAST == 'CCAST'; THEN;
    SEGMENT OCBC
        POSITION (10.7 MM-$MR_LEFT) (0 MM-$MR_TOP);
    OUTPUT 'OCBC Bank (Malaysia) Berhad 199401009721 (295400-W)'
        FONT F7_1 NORMAL
        POSITION (131.3 MM-$MR_LEFT) (4.0 MM-$MR_TOP)
        ALIGN LEFT NOPAD;
    /* More form elements... */
ENDIF;
ENDIO;
```

---

## 9. Variable System

### 9.1 Variable Declaration

**VIPP:**
```postscript
/VAR_NAME  value  SETVAR
/VAR_NAME  value  /INI  SETVAR    % Initialize once
```

**DFA (Direct Assignment):**
```dfa
VAR_NAME = value;
VAR_NAME = 'text value';
VAR_NAME = 0;
```

**IMPORTANT:** DFA uses direct assignment syntax `var = value;` NOT `ASSIGN var = value;`

### 9.2 Variable from Input Records

**DFA RECORD Structure:**
```dfa
RECORD INPUTREC
    REPEAT 1;
    VARIABLE PREFIX NOSPACE START * LENGTH 10;
    VARIABLE ACCOUNT_NUMBER NOSPACE START * LENGTH 20;
    VARIABLE CUSTOMER_NAME NOSPACE START * LENGTH 40;
    VARIABLE AMOUNT_DUE NOSPACE START * LENGTH 10 NUMBER;
ENDIO;
```

### 9.3 Variable Substitution (VSUB)

**VIPP:**
```postscript
(Statement Date: $$VAR_SED.) VSUB SHL
```

**DFA:**
```dfa
OUTPUT 'Statement Date: '!VAR_SED
    FONT ARIAL10 NORMAL
    POSITION LEFT NEXT
    ALIGN LEFT NOPAD;
```

Or using concatenation:
```dfa
OUTPUT 'Page '!P!' of '!PP
    FONT ARIAL10 NORMAL
    POSITION RIGHT SAME
    ALIGN RIGHT NOPAD;
```

### 9.4 System Variables

| VIPP Variable | DFA Equivalent | Description |
|---------------|----------------|-------------|
| `CPCOUNT` | `_DOCPAGE` | Current page in document |
| `_PAGE` | `P` | Page counter (custom) |
| `_MAXPAGE` | `PP` | Total pages (custom) |
| `FRLEFT` | `$SL_CURRY` | Current Y position |
| `PREFIX` | `PREFIX` | Current record prefix |

---

## 10. OUTPUT vs TEXT Commands

### 10.1 When to Use OUTPUT

Use `OUTPUT` for simple, single-line text with uniform formatting:

```dfa
OUTPUT 'Simple text here'
    FONT ARIAL10 NORMAL
    POSITION (LEFT-$MR_LEFT) (NEXT);

OUTPUT CUSTOMER_NAME
    FONT ARIAL10 NORMAL
    POSITION (50.0 MM-$MR_LEFT) (100.0 MM-$MR_TOP);

OUTPUT 'Amount: $'!AMOUNT
    FONT ARIAL10 NORMAL
    POSITION (RIGHT-$MR_LEFT) (SAME)
    ALIGN RIGHT NOPAD;
```

### 10.2 When to Use TEXT

Use `TEXT` for complex formatting:
- Multiple fonts/styles within one block
- Font switching (~~FA, ~~FB markers in VIPP)
- Variable substitution with font changes
- Width constraints (line wrapping)
- Bold/Italic inline changes

**IMPORTANT:** TEXT command syntax differs from OUTPUT:
- **NO ALIGN directives** in TEXT commands
- Variables use **parentheses**: `(VAR_NAME)` not `! VAR_NAME`
- **NO concatenation operator** `!` in TEXT commands
- Each font change is specified inline
- **WIDTH parameter** enables automatic line wrapping

**VIPP Example with Font Switches:**
```postscript
12 70 MOVETO
(~~FAAccount Branch / ~~FBCawangan Akaun ~~FA: $$VAR_BRC.) VSUB 0 SHP
```

**DFA Equivalent:**
```dfa
TEXT
    POSITION (12.0 MM-$MR_LEFT) (70.0 MM-$MR_TOP)
    FONT FA_1
    NORMAL
    'Account Branch / '
    FONT FB_1
    NORMAL
    'Cawangan Akaun    '
    FONT FA_1
    NORMAL
    ': ' (VAR_BRC)
    ;
```

**TEXT with WIDTH (Line Wrapping):**
```dfa
TEXT
    POSITION (18.0 MM-$MR_LEFT) (32.0 MM-$MR_TOP)
    WIDTH 180.0 MM
    ALIGN LEFT
    FONT FE_1
    NORMAL
    (VAR_ABC)
    ;
```

**Multiple Variables in TEXT:**
```dfa
TEXT
    POSITION (12.0 MM-$MR_LEFT) (70.0 MM-$MR_TOP)
    FONT FA_1 NORMAL
    'Account Branch / '
    FONT FB_1 NORMAL
    'Cawangan Akaun    '
    FONT FA_1 NORMAL
    ': ' (VAR_BRC)
    ;
```

### 10.3 OUTPUT with OUTLINE

For grouped positioned content, use OUTLINE:

```dfa
OUTLINE
    POSITION (20.0 MM-$MR_LEFT) (30.0 MM-$MR_TOP)
    DIRECTION ACROSS;

    OUTPUT 'Customer Information'
        FONT ARIAL12 BOLD
        POSITION (SAME) (SAME);
    OUTPUT CUSTOMER_NAME
        FONT ARIAL10 NORMAL
        POSITION (SAME) (NEXT+2 MM);
    OUTPUT ADDRESS
        FONT ARIAL10 NORMAL
        POSITION (SAME) (NEXT);
ENDIO;
```

---

## 11. Operators

### 11.1 Comparison Operators

| VIPP | DFA | Description |
|------|-----|-------------|
| `eq` | `==` | Equal |
| `ne` | `<>` | Not equal |
| `lt` | `<` | Less than |
| `gt` | `>` | Greater than |
| `le` | `<=` | Less than or equal |
| `ge` | `>=` | Greater than or equal |

**VIPP Example:**
```postscript
VAR_AMOUNT 1000 gt IF
{ ... } ENDIF
```

**DFA Equivalent:**
```dfa
IF VAR_AMOUNT > 1000; THEN;
    ...
ENDIF;
```

### 11.2 Arithmetic Operators

| VIPP | DFA | Description |
|------|-----|-------------|
| `ADD` | `+` | Addition |
| `-` | `-` | Subtraction |
| `*` | `*` | Multiplication |
| `/` | `/` | Division |
| `++` | `VAR = VAR + 1;` | Increment |
| `--` | `VAR = VAR - 1;` | Decrement |

**DFA Example:**
```dfa
TOTAL = SUBTOTAL + TAX;
COUNTER = COUNTER + 1;
AVERAGE = TOTAL / COUNT;
VARdoc = VARdoc + 1;
```

### 11.3 String Concatenation

**DFA uses `!` for concatenation:**
```dfa
FULLNAME = FIRSTNAME!' '!LASTNAME;
OUTPUT 'Dear '!TITLE!' '!LASTNAME
    FONT ARIAL10 NORMAL
    POSITION (LEFT-$MR_LEFT) (NEXT);
```

### 11.4 Substring Extraction (SUBSTR)

**VIPP (GETINTV):**
```postscript
% Extract substring: /result source start length GETINTV SETVAR
/VARMdate  VAR_BLD 0 2 GETINTV SETVAR
/VARMmonth VAR_BLD 2 3 GETINTV SETVAR
/VARMyear  VAR_BLD 5 4 GETINTV SETVAR
```

**DFA (SUBSTR):**
```dfa
/* SUBSTR(source, start, length, pad) */
/* start is 0-based, pad fills if length exceeds available */
VARMdate  = SUBSTR(VAR_BLD, 0, 2, '');
VARMmonth = SUBSTR(VAR_BLD, 2, 3, '');
VARMyear  = SUBSTR(VAR_BLD, 5, 4, '');
```

---

## 12. Resource Handling

### 12.1 Images

**VIPP:**
```postscript
10.7 0 MOVETO (OCBC_MSG.jpg) CACHE [185 44] 0 222 SCALL
```

**DFA:**
```dfa
CREATEOBJECT IOBDLL(IOBDEFS)
    POSITION (11 MM-$MR_LEFT) (204 MM-$MR_TOP)
    PARAMETERS
        ('FILENAME'='OCBC_MSG')
        ('OBJECTTYPE'='1')
        ('OTHERTYPES'='JPG')
        ('XOBJECTAREASIZE'='185')
        ('YOBJECTAREASIZE'='44')
        ('OBJECTMAPPING'='2');
```

### 12.2 Segments

**VIPP:**
```postscript
/TXNB { ... } XGFRESDEF
TXNB SCALL
```

**DFA:**
```dfa
SEGMENT TXNB
    POSITION (12.0 MM-$MR_LEFT) (75.5 MM-$MR_TOP);
    /* Segment content */
ENDIO;
```

---

## 13. Complete Conversion Examples

### 13.1 Transaction Line Conversion

**VIPP:**
```postscript
(CCASTX)
{
    /VAR_CCASTX     PREFIX  SETVAR
    /VAR_CTXD       FLD1    SETVAR
    /VAR_CTDS       FLD3    SETVAR
    /VAR_CBAL       FLD8    SETVAR

    F4
    NL
    14 MOVEH
    VAR_CTXD SH
    38 MOVEH
    VAR_CTDS SH
    193 MOVEH
    VAR_CBAL SHr
}
```

**DFA:**
```dfa
CASE 'CCASTX';
    VAR_CCASTX = PREFIX;
    VAR_CTXD = FLD1;
    VAR_CTDS = FLD3;
    VAR_CBAL = FLD8;

    OUTPUT ''
        FONT F4 NORMAL
        POSITION (SAME) (NEXT);
    OUTPUT VAR_CTXD
        FONT F4 NORMAL
        POSITION (14.0 MM-$MR_LEFT) (SAME);
    OUTPUT VAR_CTDS
        FONT F4 NORMAL
        POSITION (38.0 MM-$MR_LEFT) (SAME);
    OUTPUT VAR_CBAL
        FONT F4 NORMAL
        POSITION (193.0 MM-$MR_LEFT) (SAME)
        ALIGN RIGHT NOPAD;
```

### 13.2 Complete SELECT/CASE Block with Form Usage

**DFA:**
```dfa
/* Process record based on PREFIX */
SELECT PREFIX;

CASE 'STMTTP';
    VAR_STMTTP = PREFIX;
    VAR_TYP = FLD1;
    VAR_BLR = FLD2;

    IF VAR_TYP == 'C'; THEN;
        VAR_CCAST = VAR_TYP!'CAST';
    ELSE;
        VAR_ICAST = VAR_TYP!'CAST';
    ENDIF;

    /* Form usage based on page counter */
    IF P < 1; THEN;
        USE FORMAT SIBS_CASTF EXTERNAL;
    ELSE;
        USE FORMAT SIBS_CASTS EXTERNAL;
    ENDIF;

CASE 'HEADER';
    VAR_HEADER = PREFIX;
    VAR_ABC = FLD1;
    VAR_CN1 = FLD2;

    OUTPUT VAR_ABC
        FONT ARIAL12 BOLD
        POSITION (20.0 MM-$MR_LEFT) (50.0 MM-$MR_TOP);

CASE 'CCASTX';
    VAR_CCASTX = PREFIX;
    VAR_CTXD = FLD1;
    VAR_CTDS = FLD3;

    OUTPUT VAR_CTXD
        FONT F4 NORMAL
        POSITION (14.0 MM-$MR_LEFT) (NEXT);

ENDSELECT;
```

---

## 14. Recent Updates

### 14.1 Version 3.0 (January 9, 2026)

#### Color Support Implementation

**Added:** Comprehensive color command support for VIPP color identifiers (R, B, W, G, C, M, Y, K)

**Changes:**
1. **Color Command Parsing**: Single-letter color identifiers are now recognized and converted to SETCOLOR commands
2. **Color State Tracking**: Current color is tracked throughout FRM conversion pipeline
3. **COLOR Output**: OUTPUT commands now include `COLOR <identifier>` directive when a color is active
4. **Color Persistence**: Color state persists across multiple OUTPUT commands until changed

**Example:**
```vipp
R
NL
(https://www.ocbc.com.my) SHR
```

Converts to:
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

#### PRINTFOOTER Enhancement

**Changed:** Page number output format in PRINTFOOTER

**Old format:**
```dfa
OUTPUT 'Page '!P!' of '!PP
    POSITION -5 MM 5 MM
    ALIGN RIGHT NOPAD;
```

**New format:**
```dfa
OUTPUT 'Page '!P!' of '!PP
    FONT F5_1
    POSITION (RIGHT-11 MM) 297 MM
    ALIGN RIGHT NOPAD;
```

**Benefits:**
- Consistent font usage (F5_1)
- Absolute positioning for reliable placement
- Proper margin-relative coordinates

#### IF/ELSE/ENDIF Structure Fixes

**Fixed:** Isolated ENDIF statements appearing after block IF structures

**Problem:** When VIPP used `} ENDIF` pattern, converter was generating duplicate ENDIF statements

**Solution:** Added conditional_depth tracking to distinguish between:
- **Block IF** (with braces): `IF condition { body } ENDIF` → Auto-generates ENDIF, skip standalone ENDIF
- **Flat IF** (without braces): `IF condition body ENDIF` → Process standalone ENDIF normally

**Example:**
```vipp
VAR_CCAST (CCAST) eq IF {
    (OCBC Bank) SH
} ENDIF
```

Now correctly converts to:
```dfa
IF VAR_CCAST == 'CCAST'; THEN;
    OUTPUT 'OCBC Bank'
        FONT F7 NORMAL
        POSITION (38.0 MM-$MR_LEFT) (SAME);
ENDIF;
```

Without duplicate ENDIF at the end.

#### ELSE Block Content Parsing

**Fixed:** ELSE blocks were appearing empty in output

**Problem:** ELSE block content wasn't being captured in prefix syntax (`ELSE { body }`)

**Solution:**
1. Added lookahead logic to capture blocks following ELSE in prefix syntax
2. Modified ELSE conversion to recursively process children
3. Added increment/decrement operator support (`++`, `--`)

**Example:**
```vipp
IF CPCOUNT == 1; THEN;
    VAR_pctot = 0;
ELSE;
    VARdoc = VARdoc + 1;
    /* GETITEM not supported */
ENDIF;
```

Now correctly generates:
```dfa
IF CPCOUNT == 1; THEN;
    VAR_pctot = 0;
ELSE;
    VARdoc = VARdoc + 1;
    /* GETITEM not supported */
    /* SETPAGENUMBER not supported */
ENDIF;
```

### 14.2 Version 2.1 (January 8, 2026)

#### TEXT Command Formatting Fix

**Fixed:** TEXT commands were incorrectly including ALIGN directives and using OUTPUT-style variable concatenation

**Changes:**
- Removed ALIGN directives from TEXT commands (ALIGN only applies to OUTPUT)
- Variables now use parentheses format: `': ' (VAR_BRC)` instead of `: ' ! VAR_BRC`
- No concatenation operator `!` in TEXT commands
- Skip empty string literals (`'''`) in TEXT output
- Support multiple variables in single TEXT segment

#### SHP Command with WIDTH Parameter

**Added:** Support for SHP commands with width parameter for line wrapping

**VIPP:**
```postscript
VAR_ABC  180    0    SHP
```

**DFA:**
```dfa
TEXT
    POSITION (18.0 MM-$MR_LEFT) (32.0 MM-$MR_TOP)
    WIDTH 180.0 MM
    ALIGN LEFT
    FONT FE_1
    NORMAL
    (VAR_ABC)
    ;
```

**Benefits:**
- Automatic line wrapping at specified width
- Proper text flow for long content
- Correct alignment within width constraints

#### Negative NL Command Support

**Added:** Support for negative NL commands for upward positioning

**VIPP:**
```postscript
-04 NL
```

**DFA:**
```dfa
OUTPUT ''
    FONT F5 NORMAL
    POSITION (SAME) (SAME-4.0 MM);
```

**How it works:**
- Negative NL values (e.g., `-04`) move up by the specified amount
- Converted to `SAME-N MM` position format
- Enables precise vertical positioning adjustments

#### Form Usage Relocation

**Changed:** Form selection code moved to PRINTFOOTER for proper page-by-page form application

**Old location:** End of main DOCFORMAT
**New location:** Inside PRINTFOOTER (before page counter increment)

**Condition change:** `IF PP == 1` → `IF P < 1` for first page detection

**Benefits:**
- Forms applied correctly for each page
- First page vs. continuation page logic works properly
- Proper integration with page counter system

### 14.3 Code Quality Improvements

#### Font Conflict Resolution

**Automatic Renaming:** When FRM fonts conflict with DBM fonts, converter automatically renames FRM fonts with numeric suffixes

**Example:**
```
F2 in DBM: ARIAL 7pt
F2 in SIBS_CASTF.FRM: ARIAL 6pt
F2 in SIBS_CASTS.FRM: ARIAL 6pt

Renamed to:
F2_1 in SIBS_CASTF.FRM
F2_2 in SIBS_CASTS.FRM
```

#### Margin-Relative Positioning

**All positions use margin-relative coordinates:**
- X positions: `(x MM-$MR_LEFT)`
- Y positions: `(y MM-$MR_TOP)`

**Benefits:**
- Consistent positioning across different page layouts
- Easy adjustment via MARGIN settings
- Proper handling of printable areas

#### APPLICATION Format Code

**Changed:** CODE from 1252 to 1200

**Reason:**
- CODE 1200 is the standard for Unicode support in Papyrus
- Ensures proper character encoding for international text
- Better compatibility with modern systems

---

## 15. Quick Reference Card

### Document Structure
```
DOCDEF name;
APPLICATION-INPUT-FORMAT CODE 1200 ... ;
APPLICATION-OUTPUT-FORMAT CODE 1200 ... ;
DEFINEPDFOUTPUT name;
FORMATGROUP name; ... LOGICALPAGE ...;
FONT name NOTDEF AS 'family' ... HEIGHT size;
DEFINE name COLOR RGB RVAL r GVAL g BVAL b;
DOCFORMAT THEMAIN; ...
RECORD name REPEAT n; VARIABLE ... ENDIO;
SELECT var; CASE 'value'; ... ENDSELECT;
DOCFORMAT $_BEFOREFIRSTDOC; ...
ENDDOCDEF;
```

### Commands Quick Reference

| VIPP | DFA |
|------|-----|
| `x y MOVETO` | `POSITION (x MM-$MR_LEFT) (y MM-$MR_TOP)` |
| `(text) SH` | `OUTPUT 'text' FONT name NORMAL;` |
| `(text) SHR` | `OUTPUT 'text' ... ALIGN RIGHT NOPAD;` |
| `var w align SHP` | `TEXT ... WIDTH w MM ... (var);` |
| `NL` | `OUTPUT '' POSITION (SAME) (NEXT);` |
| `-n NL` | `OUTPUT '' POSITION (SAME) (SAME-n MM);` |
| `n SETLSP` | `SETUNITS LINESP n MM;` |
| `x y w h DRAWB` | `RULE/BOX POSITION x y ...;` |
| `R` (color) | `COLOR R` (in OUTPUT) |
| `/VAR val SETVAR` | `VAR = val;` |
| `/VAR ++` | `VAR = VAR + 1;` |
| `IF cond { } ENDIF` | `IF cond; THEN; ... ENDIF;` |

### Operators

| VIPP | DFA |
|------|-----|
| `eq` | `==` |
| `ne` | `<>` |
| `lt` | `<` |
| `gt` | `>` |
| `le` | `<=` |
| `ge` | `>=` |

### Common Patterns

**Variable Assignment:**
```dfa
VAR_NAME = FLD1;
VAR_COUNT = VAR_COUNT + 1;
VAR_TEXT = 'Hello '!VAR_NAME;
```

**Conditional Output:**
```dfa
IF VAR_AMOUNT > 1000; THEN;
    OUTPUT 'High Value'
        FONT ARIALB10 NORMAL
        POSITION (LEFT-$MR_LEFT) (NEXT);
ENDIF;
```

**Record Processing:**
```dfa
SELECT PREFIX;
CASE 'HEADER';
    VAR_NAME = FLD1;
    OUTPUT VAR_NAME FONT ARIAL12 BOLD;
CASE 'DETAIL';
    OUTPUT FLD1 FONT ARIAL10 NORMAL;
ENDSELECT;
```

---

## Appendix A: Troubleshooting

### A.1 Common Issues

**Issue:** Missing OUTPUT in generated DFA
**Cause:** VIPP command not recognized or missing parameters
**Solution:** Check VIPP syntax, ensure all parameters are provided

**Issue:** Wrong font in OUTPUT
**Cause:** Font conflict between DBM and FRM
**Solution:** Converter automatically renames conflicting fonts with _1, _2 suffixes

**Issue:** Incorrect positioning
**Cause:** Missing MOVETO/MOVEH before output command
**Solution:** Ensure all position changes are explicit in VIPP source

**Issue:** Empty TEXT command
**Cause:** VSUB with empty variable or font switch issues
**Solution:** Check variable values and font switch syntax

### A.2 Validation Checklist

- [ ] All VIPP files (.DBM, .FRM) are in input directory
- [ ] Font definitions are consistent across files
- [ ] Color definitions are complete
- [ ] RECORD structure matches input data format
- [ ] SELECT/CASE blocks cover all PREFIX values
- [ ] FORMATGROUP matches page size requirements
- [ ] External FRM formats are referenced correctly
- [ ] Page counters (P, PP) are initialized in $_BEFOREDOC

### A.3 Performance Tips

1. **Minimize TEXT commands**: Use OUTPUT when possible for better performance
2. **Consolidate font switches**: Group content with same font together
3. **Use OUTLINE for grouped content**: Reduces redundant position calculations
4. **Cache variable values**: Don't recalculate same value multiple times
5. **Optimize RECORD structure**: Only parse fields that are actually used

---

## Appendix B: File Locations

### B.1 Converter Script
- **File:** `universal_xerox_parser.py`
- **Location:** Project root directory
- **Purpose:** Main conversion script

### B.2 Input Files
- **Location:** User-specified directory (command-line argument)
- **File types:** .DBM, .FRM
- **Example:** `SamplePDF\SIBS_CAST - codes\`

### B.3 Output Files
- **Location:** `output/` directory (created automatically)
- **File types:** .dfa
- **Naming:** Same as input files with .dfa extension

### B.4 Documentation
- **This file:** `XEROX2DFA.MD` - Comprehensive conversion guide
- **Fix summaries:** `*_FIX_SUMMARY.md` - Detailed implementation notes
- **Example outputs:** `output_test_fixed/` - Verified test outputs

---

## Appendix C: Support and Resources

### C.1 Getting Help

**Questions about the converter:**
- Check this documentation first
- Review fix summary documents for specific issues
- Examine example output files in `output_test_fixed/`

**Questions about DFA syntax:**
- Papyrus DocDEF documentation
- Reference implementations in `output/` directory

### C.2 Reporting Issues

If you encounter conversion errors:
1. Note the VIPP input that causes the error
2. Check the generated DFA output
3. Review error messages from converter
4. Document expected vs. actual output
5. Check if similar patterns work in example files

### C.3 Contributing

Improvements and fixes are welcome:
- Document new conversion patterns
- Add support for additional VIPP commands
- Improve error handling and validation
- Enhance output formatting

---

**End of Documentation**

*This document covers universal Xerox VIPP to Papyrus DFA conversion*
*For specific implementation details, see the fix summary documents*
*For code-level documentation, see comments in universal_xerox_parser.py*

*Document version 3.0 - Updated January 9, 2026*
*Based on SIBS_CAST reference implementation and all production fixes*

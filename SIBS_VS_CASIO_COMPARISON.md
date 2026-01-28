# SIBS_CAST vs CASIO Comparison Analysis

**Date:** 2026-01-19
**Purpose:** Understand why SIBS_CAST.DBM converts correctly but CASIO.DBM generates too many empty DOCFORMATs

---

## Executive Summary

| Metric | SIBS_CAST (Works) | CASIO (Broken) | Issue |
|--------|-------------------|----------------|-------|
| **PREFIX cases in DBM** | 11 cases | 26 cases | CASIO has more |
| **Generated DOCFORMATs** | 14 | 26 | CASIO generates all |
| **Should Generate** | 14 (all meaningful) | 8 (only meaningful) | **18 extra in CASIO!** |
| **Empty DOCFORMATs** | 0 | 21 | CASIO has many empty |
| **Total DFA Lines** | 893 | 2,291 | CASIO is 2.5x larger |

**Root Cause:** The converter generates a DOCFORMAT for EVERY PREFIX case in the DBM, regardless of whether that case has actual OUTPUT commands. SIBS_CAST happens to have OUTPUT commands in all PREFIX cases, but CASIO has many PREFIX cases that only do variable assignments.

---

## Detailed Analysis

### 1. SIBS_CAST.DBM Structure (ALL Cases Have Output)

**PREFIX Cases:**
```
STMTTP - Page layout + form selection (SETFORM) + variable assignments
HEADER - Variable assignments (simple, but used)
MKTMSG - Variable assignments + date formatting
TRXHDR - Variable assignment (marker)
CCASTB - OUTPUT: "Balance B/F" + amounts (F4, NL, MOVEH, SH, SHr)
ICASTB - OUTPUT: "Balance B/F" + amounts (F4, NL, MOVEH, SH, SHr)
CCASTX - OUTPUT: Transaction details (dates, descriptions, amounts)
ICASTX - OUTPUT: Transaction details (dates, descriptions, amounts)
CCASTS - OUTPUT: Transaction summary (withdrawals, deposits)
ICASTS - OUTPUT: Transaction summary (withdrawals, deposits)
1      - Page break marker + page count logic
```

**Pattern:** Every PREFIX case either:
1. Sets up page layout (SETFORM, SETPAGEDEF) - essential
2. Has OUTPUT commands (NL, MOVEH, SH, SHr) - generates visible content
3. Has complex logic (IF/THEN, calculations) - affects behavior

**None are "empty"** - they all contribute something meaningful.

---

### 2. CASIO.DBM Structure (Many Cases Are Empty)

**PREFIX Cases with OUTPUT Commands (Keep These):**
```bash
MR  - Page break + counters + PAGEBRK logic ✓
A0  - Variable assignments (address fields) ✓
YA  - Array management + counters ✓
Y0  - Year-end summary with OUTPUT commands ✓
Y1  - Payment info with OUTPUT commands ✓
```

**PREFIX Cases with ONLY Variable Assignments (Should Remove):**
```bash
Y2  - ONLY: VAR_Y2 = PREFIX ✗ (EMPTY!)
T1  - ONLY: VAR_T1 = PREFIX ✗ (EMPTY!)
D1  - Variable assignments + COMMENTED OUT outputs ✗ (EMPTY!)
T2  - ONLY: VAR_T2 = PREFIX + comment ✗ (EMPTY!)
```

**PREFIX Cases with OUTPUT But In FRM Files (Luca Removed):**
```bash
B0  - Account summary box + text (in CASIOF.FRM instead) ✗
C0  - Available credit (in CASIOF.FRM instead) ✗
M0  - Contest message box (in CASIOF.FRM instead) ✗
M1  - Dunning message (in CASIOF.FRM instead) ✗
D0  - Summary account (in CASIOF.FRM instead) ✗
M2  - Note message (in CASIOF.FRM instead) ✗
E0  - Monthly transaction (in CASIOS.FRM instead) ✗
E1  - Balance last month (in CASIOS.FRM instead) ✗
E2  - Transaction details (in CASIOS.FRM instead) ✗
E3  - New balance (in CASIOS.FRM instead) ✗
M3  - Dunning message (in CASIOS.FRM instead) ✗
I1  - IPP Summary (in FRM instead) ✗
S1  - OCBC Summary (in FRM instead) ✗
R1  - Robinson Summary (in FRM instead) ✗
V1  - Travel Card Summary (in FRM instead) ✗
M4  - Statement messages (in FRM instead) ✗
1   - Page break (handled differently) ✗
```

**Total to Remove:** 21 DOCFORMATs

---

## 3. Code Pattern Examples

### Example 1: Empty DOCFORMAT (Y2)

**CASIO.DBM (line 1085-1089):**
```vipp
(Y2)
{
    /VAR_Y2  PREFIX  SETVAR
}
```

**Generated DFA (WRONG):**
```dfa
DOCFORMAT DF_Y2;
        VAR_Y2 = PREFIX;
```

**Should Be:** NOT GENERATED AT ALL

---

### Example 2: Commented Output DOCFORMAT (D1)

**CASIO.DBM (line 1545-1573):**
```vipp
(D1)  % Card Summary Total
{
    /VAR_D1    PREFIX  SETVAR
    /VAR_TCB   FLD1    SETVAR
    /VAR_TMP   FLD2    SETVAR

    % All these are commented out:
    %F5
    %84 266.5 MOVETO
    %(Total) SH
    %VAR_TCB  (@@@,@@@,@@@,@@#.##) FORMAT SHr
}
```

**Generated DFA (WRONG):**
```dfa
DOCFORMAT DF_D1;
        VAR_D1 = PREFIX;
        VAR_TCB = FLD1;
        VAR_TMP = FLD2;
```

**Should Be:** NOT GENERATED (only variable assignments, no active output)

---

### Example 3: FRM-Handled Output (B0)

**CASIO.DBM (line 1091-1134):**
```vipp
(B0)  % Credit Card Account Summary
{
    /VAR_B0   PREFIX  SETVAR
    /VAR_DC1  FLD1    SETVAR
    % ... many field assignments ...

    F5
    03 SETLSP
    04 NL
    150 MOVEHR
    (Your Credit Card Account Summary (RM)) SHc
    % ... more output commands ...
}
```

**Generated DFA (WRONG - generates full DOCFORMAT):**
```dfa
DOCFORMAT DF_B0;
        VAR_B0 = PREFIX;
        VAR_DC1 = FLD1;
        /* ... */
        OUTLINE
            POSITION LEFT NEXT
            DIRECTION ACROSS;
            /* ... outputs ... */
        ENDIO;
```

**Luca's Decision:** NOT GENERATED - this content is handled in CASIOF.FRM file instead

**Why:** CASIO uses a different architecture where:
- DBM file only handles main document flow (MR, A0, YA, Y0, Y1)
- FRM files handle all the detailed layouts (B0, C0, M0, etc.)

---

## 4. Key Differences in Architecture

### SIBS_CAST Architecture
```
DBM File (SIBS_CAST.DBM):
├── Page setup (STMTTP)
├── Header data (HEADER, MKTMSG)
└── Transaction output (CCASTB, ICASTB, CCASTX, ICASTX, CCASTS, ICASTS)
    └── Direct OUTPUT commands in DBM

FRM Files (SIBS_CASTF.FRM, SIBS_CASTS.FRM):
└── Static layout only (logos, borders, page headers)
```

**Pattern:** DBM drives the dynamic content output

---

### CASIO Architecture
```
DBM File (CASIO.DBM):
├── Page setup (MR)
├── Header data (A0, YA)
└── Year-end summary (Y0, Y1)
    └── Only these have OUTPUT commands in DBM

FRM Files (CASIOF.FRM, CASIOS.FRM):
├── Static layout (logos, borders)
└── Dynamic sections (B0, C0, M0, E0, E1, E2, etc.)
    └── Handled via SEGMENT references in FRM
```

**Pattern:** FRM files handle most dynamic content via SEGMENT positioning

---

## 5. Detection Logic Required

To filter empty DOCFORMATs, we need to detect:

### A. Truly Empty Cases (No Output Logic)
```vipp
(PREFIX)
{
    /VAR_XX  PREFIX  SETVAR  % ONLY variable assignment
}
```

**Detection:**
- Has no OUTPUT commands (NL, SH, SHr, SHc, MOVEH, MOVETO, etc.)
- Has no OUTLINE/BOX/RULE/TEXT generation
- Has no SETFORM/SETPAGEDEF
- Only has variable assignments

**Action:** DO NOT GENERATE DOCFORMAT

---

### B. Variable-Only Cases (Just Assignments)
```vipp
(PREFIX)
{
    /VAR_XX  PREFIX  SETVAR
    /VAR_YY  FLD1    SETVAR
    /VAR_ZZ  FLD2    SETVAR
}
```

**Detection:**
- Multiple variable assignments
- No OUTPUT commands
- No conditional logic (IF/THEN)
- No calculations beyond simple GETINTV

**Action:** DO NOT GENERATE DOCFORMAT (variables will be available globally anyway)

---

### C. Commented Output Cases (Dead Code)
```vipp
(PREFIX)
{
    /VAR_XX  PREFIX  SETVAR
    %NL              % All output commented
    %(Text) SH       % All output commented
}
```

**Detection:**
- Lines starting with % are comments
- All OUTPUT commands are commented

**Action:** Treat as variable-only case - DO NOT GENERATE DOCFORMAT

---

### D. FRM-Handled Cases (Output in FRM File)
```vipp
(PREFIX)
{
    /VAR_XX  PREFIX  SETVAR
    NL
    (Text) SH
}
```

**Detection:** This is HARD - requires cross-referencing FRM files

**Workaround for now:** If the corresponding FRM file has SEGMENT commands with matching names, assume FRM handles it

**Action:** For CASIO specifically, Luca's corrections show which ones to keep:
- Keep: MR, A0, YA, Y0, Y1
- Remove: B0, C0, M0, M1, D0, D1, M2, E0, E1, E2, E3, M3, T2, I1, S1, R1, V1, M4, 1

---

## 6. Fix Strategy

### Approach 1: Simple Heuristic (Implement This First)

**Rule:** Only generate DOCFORMAT if the PREFIX case has:
1. At least one uncommented OUTPUT command (NL, SH, SHr, MOVEH, etc.), OR
2. SETFORM/SETPAGEDEF commands, OR
3. Complex logic (nested IF/THEN, calculations, loops)

**Implementation:**
```python
def should_generate_docformat(prefix_block: str) -> bool:
    """Check if PREFIX case has meaningful content."""

    # Remove comments
    lines = prefix_block.split('\n')
    uncommented_lines = [l for l in lines if not l.strip().startswith('%')]
    content = '\n'.join(uncommented_lines)

    # Check for output commands
    output_commands = ['NL', 'SH', 'SHr', 'SHc', 'MOVEH', 'MOVETO',
                       'SETFORM', 'SETPAGEDEF', 'DRAWB', 'SCALL']
    has_output = any(cmd in content for cmd in output_commands)

    # Check for complex logic
    has_logic = 'IF' in content and 'THEN' in content

    # Check for calculations (beyond simple SETVAR)
    has_calc = '++' in content or 'GETINTV' in content or 'VSUB' in content

    # Only generate if has output OR (has logic AND has calc)
    return has_output or (has_logic and has_calc)
```

---

### Approach 2: Whitelist for CASIO (Fallback)

If heuristic doesn't work perfectly, use Luca's corrections as a whitelist:

```python
CASIO_KEEP_PREFIXES = {'MR', 'A0', 'YA', 'Y0', 'Y1'}

def should_generate_docformat_casio(prefix: str) -> bool:
    """For CASIO specifically, only generate whitelisted prefixes."""
    return prefix in CASIO_KEEP_PREFIXES
```

---

## 7. Testing Plan

### Test 1: SIBS_CAST (Regression Test)
```bash
python universal_xerox_parser.py "SAMPLES/SIBS_CAST/SIBS_CAST - codes/SIBS_CAST.DBM" --single_file -o output/sibs_test
```

**Expected:**
- 14 DOCFORMATs (same as before)
- 893 lines (same as before)
- All DOCFORMATs have content

**Verification:** `diff output/sibs_baseline/SIBS_CAST.dfa output/sibs_test/SIBS_CAST.dfa`

---

### Test 2: CASIO (Fix Validation)
```bash
python universal_xerox_parser.py "SAMPLES/CreditCard Statement/CASIO - codes/CASIO.DBM" --single_file -o output/casio_fixed
```

**Expected:**
- 8 DOCFORMATs (matching Luca's: THEMAIN, DF_MR, DF_A0, DF_YA, DF_Y0, DF_Y1, $_BEFOREFIRSTDOC, $_BEFOREDOC)
- ~800-900 lines (not 2,291)
- No empty DOCFORMATs

**Verification:** Compare DOCFORMAT list with Luca's version

---

## 8. Additional Issues Found

### Issue 1: Orphan ELSE in DF_MR

**Current Generated Code (line 258-263):**
```dfa
DOCFORMAT DF_MR;
        IF CPCOUNT == 1; THEN;
            VAR_pctot = 0;
        ENDIF;
    ELSE;              ← ORPHAN ELSE!
        VAR_COUNTTD = 0;
        VARdoc = VARdoc + 1;
ENDIF;
```

**Problem:** ELSE appears after ENDIF - syntax error

**Root Cause:** Parser doesn't track IF/ENDIF nesting correctly

---

### Issue 2: Wrong BOX Syntax

**Current Generated Code (line 367-368):**
```dfa
BOX X VAR MM Y Y5 MM WIDTH 0.1 MM HEIGHT 05.8 MM;
BOX X VAR MM Y Y5 MM WIDTH 0.1 MM HEIGHT 05.8 MM;
```

**Problem:**
- `X VAR MM Y Y5 MM` is not valid DFA syntax
- Should be `POSITION (VAR) (Y5)`

**Should Be:**
```dfa
BOX
    POSITION (VAR) (Y5)
    WIDTH 0.1 MM
    HEIGHT 05.8 MM
    THICKNESS LIGHT TYPE SOLID;
```

---

### Issue 3: Missing LOGICALPAGE 2

**Current:** Only LOGICALPAGE 1 generated

**Should Have:** Both LOGICALPAGE 1 and LOGICALPAGE 2 for duplex printing

---

### Issue 4: Missing $_BEFOREDOC Initialization

**Current $_BEFOREDOC:**
```dfa
DOCFORMAT $_BEFOREDOC;
    P = 0;
    PP = 0;
```

**Should Have:**
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

---

## 9. Implementation Priority

### P1 - Critical (Do First)
1. ✅ Filter empty DOCFORMATs using heuristic
2. ✅ Fix orphan ELSE / IF-ENDIF pairing
3. ✅ Add $_BEFOREDOC initialization (VAR, Y3, Y5)

### P2 - High (Do Next)
4. ✅ Fix BOX command syntax
5. ✅ Add LOGICALPAGE 2 support
6. ✅ Add ISTRUE() wrapper to IF conditions

### P3 - Polish (If Time)
7. Consistent spacing (space before semicolon)
8. Variable name casing (uppercase)

---

## 10. Root Cause Summary

The converter was designed with SIBS_CAST-like files in mind, where every PREFIX case has OUTPUT commands. It blindly generates a DOCFORMAT for each PREFIX without checking if that PREFIX actually produces output.

CASIO has a different architecture where:
- Only 5 PREFIX cases (MR, A0, YA, Y0, Y1) generate output in DBM
- The other 21 PREFIX cases are:
  - Empty markers (Y2, T1, T2)
  - Variable holders (D1, B0, C0, etc.)
  - FRM-handled sections (E0, E1, E2, I1, S1, R1, V1, M4)

**Fix:** Add content detection logic before generating DOCFORMAT.

---

## Files to Modify

1. **universal_xerox_parser.py**
   - `_parse_dbm_case_statement()` - add should_generate check
   - `_generate_docformat_section()` - skip if empty
   - `_generate_if_command()` - fix ELSE pairing, add ISTRUE()
   - `_generate_box_command()` - fix syntax
   - `_generate_formatgroup()` - add LOGICALPAGE 2
   - `_generate_beforedoc()` - add VAR, Y3, Y5 initialization

---

## Success Criteria

✅ SIBS_CAST still works (regression test passes)
✅ CASIO generates only 8 DOCFORMATs (not 26)
✅ CASIO DFA is ~800-900 lines (not 2,291)
✅ No orphan ELSE errors
✅ BOX commands have proper syntax
✅ LOGICALPAGE 2 exists
✅ $_BEFOREDOC has VAR, Y3, Y5 initialization

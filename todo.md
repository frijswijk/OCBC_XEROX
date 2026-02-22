# CASIO Conversion — Open Issues for Human Specialist

## Issue 1: SETFORM Cursor Offset Causes Data/FRM Overlap

### Problem
The generated CASIO PDF shows data content overlapping with FRM form elements on every page. The data is rendered at the wrong Y-position — approximately **27mm too high** on the page.

### Root Cause Analysis
In Xerox VIPP, the `SETFORM` command appears to move the cursor to a **data-writing origin** — an offset position within the form where data output should begin. The DFA converter does not account for this offset.

### Evidence

**Xerox DBM source** (`CASIO.DBM` lines 505-518, Y0 PREFIX case):
```vipp
MM SETUNIT           /* Units = millimeters */
ORITL                /* Origin Top Left — resets cursor to page top-left */
PORT                 /* Portrait orientation */
03 SETLSP            /* Line spacing = 3mm */
(CASIOS.FRM) SETFORM /* Load form — THIS LIKELY SETS A CURSOR OFFSET */
/VAR_Y0 ++
FI                   /* Font: ArialBold 13pt */
W                    /* Color: WHITE */
42.19 NL             /* Advance cursor DOWN 42.19mm FROM CURRENT POSITION */
80 MOVEH             /* Move X to 80mm */
($VAR_SAAF.  (RM)) VSUB SH   /* Output "2025 (RM)" in WHITE */
```

**Xerox FRM source** (`CASIOS.FRM` lines 72-77):
```vipp
08 50 MOVETO (YRSB) SCALL     /* Black box rendered at Y=64mm (50 + abs(-14) from DRAWB) */
12 69.5 MOVETO W FH (Summary of Account Activity for) SH  /* White text at Y=69.5mm */
```

**Key observation:** In the reference PDF, the data text "2025 (RM)" appears on the SAME LINE as the FRM text "Summary of Account Activity for" at Y≈69.5mm. This means the data's 42.19mm NL advance must start from an offset position:
- **Expected:** SETFORM offset (~27.31mm) + 42.19mm NL = 69.5mm → matches FRM text at Y=69.5mm
- **Actual (converter):** 0mm (page origin) + 42.19mm NL = 42.19mm → 27mm too high

### Generated DFA (`CASIO.dfa` lines 496-506, DF_Y0):
```dfa
OUTLINE
    POSITION LEFT NEXT
    DIRECTION ACROSS;

    OUTPUT ''
        FONT FI NORMAL
        POSITION (SAME) (SAME+42.19 MM);   /* ← 42.19mm from OUTLINE origin */
    OUTPUT ''
        FONT FI NORMAL
        POSITION (80.0 MM-$MR_LEFT) (SAME);
    OUTPUT VAR_SAAF!' '!'(RM)'
```

The OUTLINE starts at `POSITION LEFT NEXT` which is relative to the cursor position from the previous DOCFORMAT. The 42.19mm NL offset is applied from this cursor position, but WITHOUT the SETFORM origin offset it lands 27mm too high.

### Question for Specialist
1. **How does SETFORM affect the cursor position in Xerox VIPP?** Does it set a Y-offset where subsequent data output begins? If so, how is this offset determined — is it stored in the FRM file itself, or is it implicit?
2. **What is the correct DFA equivalent for SETFORM's cursor positioning?** Should the OUTLINE that renders data use an explicit Y-offset matching the FRM's data area origin?
3. **Is there a standard DFA pattern for rendering form overlays (FRM) independently from data?** Currently the converter renders FRM in PRINTFOOTER and data in the formatting pass — is this the correct approach, or should both be in the same pass?

### Additional Context
- The converter currently renders FRM layouts via `USE FORMAT REFERENCE(VAR_CURFORM) EXTERNAL;` in PRINTFOOTER
- `ORITL` (Origin Top Left) is treated as a comment in the converter (line 7184 of universal_xerox_parser.py) — it should likely reset position state
- The ~27.31mm offset is consistent: FRM text Y (69.5) - data NL offset (42.19) = 27.31mm
- The data text "2025 (RM)" is rendered in WHITE — it's intentionally invisible on white background and only visible inside the FRM's black header box
- This offset issue affects ALL pages, not just page 1 — every SETFORM call in the DBM establishes a new cursor offset

### Files Referenced
- **Xerox source:** `SAMPLES/CreditCard Statement/CASIO - codes/CASIO.DBM` (lines 505-518)
- **FRM source:** `SAMPLES/CreditCard Statement/CASIO - codes/CASIOS.FRM` (lines 72-77)
- **Generated DFA:** `C:\ISIS\samples_pdd\OCBC\CASIO\docdef\CASIO.dfa` (lines 496-506)
- **Reference PDF:** `C:\ISIS\samples_pdd\OCBC\CASIO\reference\BKCSTMA - OUTPUT_data.pdf`
- **Generated PDF:** `C:\ISIS\samples_pdd\OCBC\CASIO\afpds\CASIO.pdf`
- **Converter:** `universal_xerox_parser.py` (NL handling ~line 2294, ORITL ~line 7184)

---

## Issue 2: FRM Z-Order — Form Renders ON TOP of Data (PRINTFOOTER Problem)

### Problem
In the generated PDF, FRM form elements (logo, boxes, headers, rules) render **ON TOP** of data content, hiding the data text. In the reference PDF, FRM elements are the **background** and data text appears on top of them (e.g., white text visible inside black header boxes).

### How It Works in Xerox VIPP
In VIPP, the rendering order is:
1. `SETFORM (CASIOS.FRM)` — loads and renders the form (background)
2. Data commands (`NL`, `MOVEH`, `SH`) — render on top of the form

The form is always behind the data because it renders first.

### How It Currently Works in DFA (Wrong)
The converter uses two rendering passes:
1. **Formatting pass** — Data DOCFORMATs render text/variables via OUTLINE blocks
2. **Print pass (PRINTFOOTER)** — FRM is rendered via `USE FORMAT REFERENCE(FRM_PAGE[P]) EXTERNAL;`

PRINTFOOTER runs AFTER the formatting pass, so FRM content renders **ON TOP** of data. This is the opposite of what VIPP does.

### Current DFA Structure (CASIO.dfa lines 36-67)
```dfa
FORMATGROUP MAIN;
    SHEET WIDTH 210 MM HEIGHT 297 MM;
    LAYER 1;
    LOGICALPAGE 1
        SIDE FRONT
        POSITION 0 0
        WIDTH 210 MM
        HEIGHT 297 MM
        DIRECTION ACROSS
        FOOTER
            PP = PP + 1;
            FRM_PAGE[PP] = VAR_CURFORM;
        FOOTEREND
        PRINTFOOTER
            P = P + 1;
            /* FRM renders here — ON TOP of data */
            IF ISTRUE(NOSPACE(FRM_PAGE[P])<>'');
            THEN;
                USE FORMAT REFERENCE(FRM_PAGE[P]) EXTERNAL;
            ENDIF;
            /* Page numbering */
            OUTLINE
                POSITION RIGHT (0 MM)
                DIRECTION ACROSS;
                OUTPUT 'Page '!P!' of '!PP
                    FONT F5_1
                    POSITION (RIGHT-11 MM)286 MM
                    ALIGN RIGHT NOPAD;
            ENDIO;
        PRINTEND;
```

### FRM File Structure (e.g., CASIOF.dfa)
Each FRM DFA file is an OUTLINE block with absolute positions:
```dfa
OUTLINE
    POSITION LEFT TOP
    DIRECTION ACROSS;

    /* Static content: logo, boxes, headers, rules */
    CREATEOBJECT IOBDLL(IOBDEFS) ...;           /* OCBC logo */
    OUTPUT 'OCBC Bank (Malaysia) Berhad ...'     /* Bank name */
        FONT F1_3 NORMAL
        POSITION (131.3 MM-$MR_LEFT) (4.0 MM-$MR_TOP) ...;
    BOX POSITION (117.0 MM-$MR_LEFT) (28.0 MM-$MR_TOP)
        WIDTH 84.0 MM HEIGHT 8.0 MM
        COLOR LMED
        THICKNESS 0 TYPE SOLID SHADE 100;        /* ← Opaque filled box */
    /* ... more boxes, rules, text at absolute positions ... */

    /* Conditional content */
    IF NOSPACE(VAR_PDD) == 'IMMEDIATE'; THEN;
        OUTPUT '"WITHOUT PREJUDICE"' ...;
    ENDIF;
ENDIO;
```

Key: The FRM has **opaque filled boxes** (`SHADE 100`) that completely cover any data underneath when rendered on top.

### Why Moving FRM to Formatting Pass Doesn't Work
I tried rendering FRM before data in the formatting pass (`USE FORMAT CASIOF EXTERNAL;` before the data OUTLINE). The problem:

1. FRM's OUTLINE with `POSITION LEFT TOP` renders content from Y=0 to Y≈290mm
2. After FRM's ENDIO, the **main-level cursor advances to ~290mm** (bottom of page)
3. The data OUTLINE opens at `POSITION LEFT NEXT` → NEXT after 290mm → off the page
4. DFA's main-level cursor **never goes backwards** — there's no way to reset it to Y=25mm after FRM rendering

### Why FRM Needs PRINTFOOTER (Current Design Reasons)
1. FRM must render **once per physical page** — PRINTFOOTER runs exactly once per printed page
2. Multi-FRM documents (CASIO has 7 FRMs cycling across pages) need per-page FRM selection via `FRM_PAGE[P]` array
3. Page numbering (`Page P of PP`) needs the final page count which is only available in PRINTFOOTER

### What The Expert Needs to Answer

**Primary question:** What is the correct DFA pattern to render FRM form overlays as a **background** behind data content?

**Specific approaches to evaluate:**

1. **LAYER mechanism:** Can two LAYERs be used to separate FRM (LAYER 1, background) from data (LAYER 2, foreground)? If so, how does data routing between layers work? Does each LAYER need its own LOGICALPAGE?

2. **OVERLAY on LOGICALPAGE:** Can the FRM be rendered as a dynamic OVERLAY? The challenge: FRM names vary per page (`CASIOS`, `CASIOF`, `CASIO_TNC`, `CASIOF3`, `CASIOB`) and FRM files contain conditional logic (`IF VAR_PDD == 'IMMEDIATE'`).

3. **Cursor save/restore:** Is there a DFA command to save and restore the main-level cursor position? After rendering FRM (which advances cursor to ~290mm), can the cursor be reset to Y=25mm for data output?

4. **OUTLINE that doesn't advance cursor:** Is there an OUTLINE variant or parameter that renders content at absolute positions WITHOUT advancing the parent-level cursor after ENDIO?

5. **Different approach entirely:** Should the FRM content NOT be in separate .dfa files called via `USE FORMAT EXTERNAL`? Should the form elements (boxes, rules, logos) be embedded directly in each data DOCFORMAT, before the data output?

### CASIO Page Flow (for context)
The document has 5 pages, each with a different FRM:
| Page | FRM File | Set By | Content |
|------|----------|--------|---------|
| 1 | CASIOS | DF_Y0 (line 505) | Account summary |
| 2 | CASIOF | Line 1141 (after USE LP NEXT) | Statement details |
| 3 | CASIO_TNC | DF_M2 (line 1631) | Terms & conditions |
| 4 | CASIOF3 | DF_E0 (line 1654) | Transaction table |
| 5 | CASIOB | DF_T2 (line 1984) | Reward points |

VAR_CURFORM is set in the formatting pass. FRM_PAGE[PP] snapshots it in FOOTER per page. PRINTFOOTER uses FRM_PAGE[P] to render the correct FRM per printed page.

### Files Referenced
- **Generated DFA:** `C:\ISIS\samples_pdd\OCBC\CASIO\docdef\CASIO.dfa` (FORMATGROUP lines 36-67)
- **FRM DFA files:** `C:\ISIS\samples_pdd\OCBC\CASIO\docdef\CASIOF.dfa`, `CASIOS.dfa`, etc.
- **Reference PDF:** `C:\ISIS\samples_pdd\OCBC\CASIO\reference\BKCSTMA - OUTPUT_data.pdf`
- **Generated PDF:** `C:\ISIS\samples_pdd\OCBC\CASIO\afpds\CASIO.pdf`
- **Converter:** `universal_xerox_parser.py` (LOGICALPAGE generation ~line 4280, SETFORM handling ~line 5672)

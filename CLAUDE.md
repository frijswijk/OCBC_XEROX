# OCBC Xerox-to-DFA Converter — Project Guide

## What This Project Does

Converts Xerox FreeFlow VIPP documents (DBM/FRM/JDT formats) into ISIS Papyrus DFA format
for OCBC Bank. The converters are Python scripts that read Xerox source files and generate
`.dfa` files. The generated `.dfa` files are **never hand-edited** — all fixes go into the
Python converters.

## Core Rule: Fix the Converter, Not the DFA

When a generated DFA file has a bug, **always trace the bug back to the Python converter
that produced it** and fix it there. Re-run the converter to regenerate the DFA. Direct
edits to `.dfa` files are throwaway work — they will be overwritten on the next conversion.

Update the skill xerox-dfa when new insights or bugs are being fixed and not this claude.md file.

## Converters (Source of Truth)

| File | Handles | Description |
|------|---------|-------------|
| `universal_xerox_parser.py` | DBM + FRM | Database Mode: pipe-delimited records, PREFIX routing |
| `xerox_jdt_dfa.py` | JDT | Line Mode: SETRCD conditions, RPE arrays, fixed-width records |
| `command_mappings.py` | Shared | VIPP-to-DFA command mapping dictionaries |

## Running the Converters

```bash
# DBM/FRM conversion
python universal_xerox_parser.py <input_directory>

# JDT conversion (single file)
python xerox_jdt_dfa.py <file.jdt> --single_file -o <output_directory>
```

Generated DFA files go to `C:\ISIS\samples_pdd\OCBC\<PROJECT>\docdef\`.

## Workflow for Fixing Bugs

1. Identify the bug in the generated `.dfa` file (compare with Xerox source and reference PDF)
2. Trace which part of the converter produced the wrong output
3. Fix the converter (`xerox_jdt_dfa.py` for JDT bugs, `universal_xerox_parser.py` for DBM/FRM bugs)
4. Re-run the converter to regenerate the DFA
5. Re-render the PDF in ISIS Papyrus DocEXEC and compare against the reference PDF

## Project Structure

```
OCBC_XEROX/
├── universal_xerox_parser.py   # DBM/FRM converter
├── xerox_jdt_dfa.py            # JDT converter
├── command_mappings.py         # Shared VIPP→DFA mappings
├── CLAUDE.md                   # This file
├── SAMPLES/
│   └── <PROJECT>/
│       ├── <PROJECT>P1 - output.pdf   # Reference PDF (target)
│       ├── <PROJECT>P1 - raw data.txt # Sample input data
│       └── <PROJECT> - codes/         # Xerox source files (.jdt, .frm, .dbm)
└── memory/
    └── MEMORY.md               # Cross-session project memory
```

Generated output (ISIS Papyrus):
```
C:\ISIS\samples_pdd\OCBC\<PROJECT>\
├── docdef\       # Generated .dfa files (do not hand-edit)
└── afpds\        # Rendered AFP/PDF output
```

## Key Bug Classes in the JDT Converter (xerox_jdt_dfa.py)

### SETRCD String Padding
VIPP `SETRCD` format: `/name startpos length /eq (STRING) SETRCD`
When `length > len(STRING)`, VIPP pads the comparison string with trailing spaces.
The DFA converter **must** pad the match string to `length` characters.

**Wrong:** `SUBSTR(CONTENT[C],2,6,'')=='DCDO'`  (6 chars vs 4-char string → never matches)
**Correct:** `SUBSTR(CONTENT[C],2,6,'')=='DCDO  '` (both 6 chars)

### FROMLINE-to-CONTENT Index Mapping
In JDT, each input record gets a CONTENT[N] slot. CC=`+` (overprint) and CC=`0`
(double-space) lines cause physical line numbers to diverge from CONTENT indices.
FROMLINE N in the JDT RPE does NOT necessarily map to CONTENT[N] in DFA.
Always trace the actual accumulation order from the raw data.

### RPE Array Format
JDT RPE entries: `[align justify X DX Y DY START LEN FONT COLOR]`
- Position: `(UNIH*(X+DX))`, `(UNIH*(Y+DY))`  (MTOP is NOT added separately)
- Text: `SUBSTR(CONTENT[LIN], START, LEN, '')`

## Skills Available

- `dfa-coding` — ISIS Papyrus DFA language reference
- `xerox-dfa` — Xerox VIPP to DFA conversion patterns and rules

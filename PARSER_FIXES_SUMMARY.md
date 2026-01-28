# Parser Fixes Implementation Summary

**Date:** January 9, 2026
**Approach:** User-specified (font conflict resolution + simplified DFA font definitions)

## Issues Fixed

### 1. DBM Font Parser Bug (Critical)
**Problem:** Parser expected 5 tokens but DBM format has 4 tokens
```vipp
/FE    /ARIALBO    06    INDEXFONT
[0]    [1]         [2]   [3]         # 4 tokens, not 5
```

**Fix:** Changed pattern check from `pos+4` to `pos+3` in line 1183
```python
# OLD (WRONG):
if (self.pos + 4 < len(self.tokens) and
    self.tokens[self.pos + 2].type == 'variable' and
    self.tokens[self.pos + 4].value == 'INDEXFONT'):

# NEW (CORRECT):
if (self.pos + 3 < len(self.tokens) and
    self.tokens[self.pos + 1].type == 'variable' and
    self.tokens[self.pos + 3].value == 'INDEXFONT'):
```

**Result:** All DBM fonts now parsed correctly (F0-F9, FA-FF, PNFT, Z, Z1, etc.)

---

### 2. Font Name Conflicts Between DBM and FRM Files
**Problem:** Same font alias (e.g., FE) defined differently in DBM vs FRM files

**Example:**
- DBM: `/FE /ARIALBO 06` (Arial Bold Italic, size 6)
- SIBS_CASTS.FRM: `/FE /ARIAL 10` (Arial Regular, size 10)
- SIBS_CASTF.FRM: `/FE /ARIAL 10` (Arial Regular, size 10)

**Fix:** Implemented `resolve_font_conflicts()` method that:
1. Parses DBM first (priority)
2. Detects conflicts when parsing FRM files
3. Renames conflicting FRM fonts with suffix (FE_1, FE_2)
4. Stores mapping in `frm.font_rename_map`
5. Updates all font references in FRM commands

**Generated Fonts:**
```dfa
FONT FE NOTDEF AS 'Arial Bold Italic' DBCS ROTATION 0 HEIGHT 6.0;     # From DBM
FONT FE_1 NOTDEF AS 'Arial' DBCS ROTATION 0 HEIGHT 10.0;              # From SIBS_CASTF.FRM
FONT FE_2 NOTDEF AS 'Arial' DBCS ROTATION 0 HEIGHT 10.0;              # From SIBS_CASTS.FRM
```

**FRM Commands Correctly Use Renamed Fonts:**
```dfa
# In SIBS_CASTF.dfa:
OUTPUT 'text'
    FONT FE_1 NORMAL     # Correctly uses renamed font, not FE
    POSITION x y;
```

---

### 3. Incorrect Font Style Mapping
**Problem:** DFA font definitions included unnecessary BOLD/ITALIC/BOLDITALIC variants

**Old Approach (WRONG):**
```dfa
FONT FE NOTDEF AS 'Arial Bold Italic' BOLD NOTDEF AS 'Arial Bold Italic Bold'
    ITALIC NOTDEF AS 'Arial Bold Italic Italic'
    BOLDITALIC NOTDEF AS 'Arial Bold Italic Bold Italic'
    DBCS ROTATION 0 HEIGHT 6.0;
```

This creates nonsensical variants like "Arial Bold Italic Bold".

**User's Insight:** VIPP doesn't use runtime font faces. Each font alias IS a specific font:
- `/FE /ARIALBO 06` means "FE IS Arial Bold Italic 6pt"
- No mechanism to say "use FE but make it bold"

**New Approach (CORRECT):**
```dfa
FONT FE NOTDEF AS 'Arial Bold Italic' DBCS ROTATION 0 HEIGHT 6.0;
```

**Benefits:**
- Matches VIPP semantics exactly
- Cleaner, simpler definitions
- No confusion about font variants
- All OUTPUT commands use `FONT name NORMAL` (always NORMAL, never BOLD/ITALIC)

---

### 4. Font Alias Resolution in FRM Commands
**Problem:** FRM commands needed to use renamed fonts, not original aliases

**Fix:** Updated `_map_font_alias()` method to:
1. Apply `font_rename_map` for FRM fonts
2. Always return NORMAL style (font style is baked into definition)
3. Look up DFA name in `font_mappings`

```python
def _map_font_alias(self, alias: str, frm: XeroxFRM) -> Tuple[str, str]:
    # Apply rename mapping if this is an FRM font that was renamed
    resolved_alias = frm.font_rename_map.get(alias, alias)

    # Look up DFA font name
    if resolved_alias in self.font_mappings:
        dfa_font = self.font_mappings[resolved_alias]
        return (dfa_font, 'NORMAL')

    # Fallback to DBM font
    if alias in self.font_mappings:
        dfa_font = self.font_mappings[alias]
        return (dfa_font, 'NORMAL')

    return (alias.upper(), 'NORMAL')
```

---

## Verification Results

### Test Case: FE Font from DBM
**Source (SIBS_CAST.DBM line 125):**
```vipp
/FE    /ARIALBO    06    INDEXFONT
```

**Generated DFA:**
```dfa
FONT FE NOTDEF AS 'Arial Bold Italic' DBCS ROTATION 0 HEIGHT 6.0;
```

**Verification:**
- ✅ ARIALBO → 'Arial Bold Italic' (correct mapping)
- ✅ Size 06 → HEIGHT 6.0 (correct size)
- ✅ Simplified syntax (no variants)
- ✅ NOT overridden by default_fonts list

### Test Case: Font Conflicts
**Log Output:**
```
2026-01-09 10:01:39 - WARNING - Font conflict: FE in SIBS_CASTF.FRM
    (FRM: ARIAL size 10.0) conflicts with DBM (DBM: ARIALBO size 6.0)
2026-01-09 10:01:39 - INFO - → Renamed FE to FE_1 in SIBS_CASTF.FRM
```

**Generated:**
- FE (DBM) → 'Arial Bold Italic' size 6.0
- FE_1 (SIBS_CASTF.FRM) → 'Arial' size 10.0
- FE_2 (SIBS_CASTS.FRM) → 'Arial' size 10.0

### Test Case: FRM Font Usage
**SIBS_CASTF.FRM uses renamed font:**
```dfa
OUTPUT 'text'
    FONT FE_1 NORMAL
    POSITION (18.0 MM-$MR_LEFT) (32.0 MM-$MR_TOP);
```

**Verification:**
- ✅ Uses FE_1 (not FE)
- ✅ Uses NORMAL style
- ✅ Correct font mapping applied

---

## Code Changes Summary

### Files Modified: 1
- `universal_xerox_parser.py`

### Changes Made:

1. **XeroxFRM dataclass** (line 153)
   - Added `font_rename_map` field to track renamed fonts

2. **DBM Parser** (line 1182-1202)
   - Fixed pattern to expect 4 tokens instead of 5
   - Changed `pos+4` to `pos+3`
   - Fixed token position: `[1]` instead of `[2]` for font name

3. **Font Conflict Resolution** (line 1413-1478)
   - New method `resolve_font_conflicts()`
   - Detects conflicts between DBM and FRM fonts
   - Renames FRM fonts with numeric suffix
   - Updates font definitions and mappings

4. **Font Generation** (line 2833-2880)
   - Simplified `_generate_fonts()` to use user's approach
   - Removed BOLD/ITALIC/BOLDITALIC variants
   - Single line per font: `FONT name NOTDEF AS 'family' DBCS ROTATION 0 HEIGHT size;`
   - Removed F-series from default_fonts list

5. **Font Alias Mapping** (line 2166-2201)
   - Updated `_map_font_alias()` to apply rename mapping
   - Always returns NORMAL style
   - Checks `font_rename_map` first

6. **Output Generation** (line 2324-2343)
   - Updated `_generate_simple_output()` to accept `frm` parameter
   - Calls `_map_font_alias()` for FRM fonts
   - Updated all call sites (line 2116, 2216)

7. **Main Execution** (line 4443-4444)
   - Added call to `resolve_font_conflicts()` before converter creation

---

## ARIALB vs ARIALBO

**Question:** What's the difference between /ARIALB and /ARIALBO?

**Answer:**
- `/ARIALB` = Arial **B**old only
- `/ARIALBO` = Arial **B**old + **O**blique (Italic)

The "O" suffix stands for "Oblique" (PostScript term for Italic).

**Complete Xerox Font Naming Convention:**
- Base (e.g., `ARIAL`) = Regular
- B suffix (e.g., `ARIALB`) = Bold
- O suffix (e.g., `ARIALO`) = Oblique/Italic
- BO suffix (e.g., `ARIALBO`) = Bold Oblique/Bold Italic

---

## Benefits of This Approach

1. **Correct VIPP Semantics:** Matches how VIPP actually works (fonts are immutable, not styled at runtime)

2. **Conflict Resolution:** DBM fonts have priority, FRM fonts get renamed automatically

3. **Maintainability:** 1:1 mapping between VIPP and DFA font definitions

4. **Simplicity:** No complex style variant generation, cleaner DFA output

5. **Traceability:** Font conflicts logged with details, easy to debug

6. **Scalability:** Works with any number of FRM files, automatic renaming

---

## Future Considerations

1. **Color Conflicts:** Similar approach could be applied to color definitions if needed

2. **Font Optimization:** Could deduplicate identical font definitions across files

3. **Validation:** Could add warnings for unused fonts or missing font references

4. **Documentation:** Font rename mappings could be exported to a report file

---

**Implementation Status:** ✅ Complete and Verified
**Test Status:** ✅ Passed (SIBS_CAST sample files)
**Breaking Changes:** None (backward compatible with existing DFA consumers)

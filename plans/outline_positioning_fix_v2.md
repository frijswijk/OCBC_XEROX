# Corrected Plan: DBM OUTLINE Anchoring V2 (CASIO / UT00060 / SIBS_CAST)

## Summary
Implement a feature-flagged, narrow DBM-only fix that anchors OUTLINE opening from runtime positioning state (MOVETO/MOVEH), not from coarse case-level heuristics.

## Scope
- In scope: `universal_xerox_parser.py` DBM case conversion path.
- Out of scope: FRM conversion logic, SHROW flattening, cross-DOCFORMAT carry.

## Public Interface / Config
- Add env flag (default OFF): `XEROX_DBM_OUTLINE_ANCHOR_V2=1`
  - `0`/unset: existing behavior unchanged.
  - `1`: enable V2 runtime anchor algorithm.

## Implementation

### 1) OUTLINE anchor precedence at open
In `_convert_case_commands`, when opening OUTLINE:
1. `x_was_explicitly_set && y_was_explicitly_set` => `POSITION (x MM-$MR_LEFT) (y MM-$MR_TOP)`
2. `x_was_explicitly_set && !y_was_explicitly_set` => `POSITION (x MM-$MR_LEFT) SAME`
3. Else => `POSITION LEFT SAME`

### 2) Mid-OUTLINE MOVETO close/reopen
In `_convert_case_commands` MOVETO handler:
- If flag ON and `outline_opened_here`, close current OUTLINE (`ENDIO;`) before storing new MOVETO coordinates.
- Keep ownership guard to avoid closing inherited parent outlines.

### 3) Nested IF propagation
Add optional `anchor_context` parameter:
- `_convert_case_commands(..., anchor_context="root")`
- `_convert_if_command(..., anchor_context="root")`
- Pass `anchor_context="nested"` for IF/ELSE child conversions.

### 4) Preserve existing text behavior
Do not change AUTOSPACE conversion behavior or empty `OUTPUT ''` safeguard.

### 5) Diagnostics
When flag ON, emit one-line comments on OUTLINE open:
- `/* OUTLINE_ANCHOR_V2: ABS_XY */`
- `/* OUTLINE_ANCHOR_V2: ABS_X_SAME_Y */`
- `/* OUTLINE_ANCHOR_V2: LEFT_SAME_FALLBACK */`

## Files
- `universal_xerox_parser.py`
- `plans/outline_positioning_fix_v2.md`

## Acceptance Criteria

### SIBS_CAST
- DocEXEC errors remain 0.
- No positioning regression in key sections.

### UT00060
- Anchors equivalent to:
  - `(10.7 MM-$MR_LEFT) (16.2 MM-$MR_TOP)`
  - `(131.3 MM-$MR_LEFT) (4 MM-$MR_TOP)`
- MOVETO-separated groups render as distinct OUTLINE blocks.

### CASIO
- PPDE7128W `Text coordinate < 0` count decreases vs baseline.
- IF-heavy sections avoid repeated LEFT NEXT resets.

## Verification
1. Baseline capture for CASIO, UT00060, SIBS_CAST.
2. Re-run with `XEROX_DBM_OUTLINE_ANCHOR_V2=1`.
3. Compare DocEXEC logs and OUTLINE blocks.
4. Visual page-1 check against references.
5. Record findings in `lessons.md` and `converter.log`.

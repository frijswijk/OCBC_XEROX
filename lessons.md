# Lessons Learned

## 2026-02-23 - Root-cause analysis before code changes

### 1) Wrong output set can be analyzed by mistake (project/output mismatch)
- `C:\ISIS\samples_pdd\OCBC\SIBSTST\docdef\SIBS_CAST.dfa` was generated from `SAMPLES\SIBS_CAST\SIBS_CAST - codes\SIBS_CAST.DBM`, not from `SAMPLES\CreditCard Statement\CASIO - codes\CASIO.DBM`.
- CreditCard/CASIO conversions are currently in `C:\ISIS\samples_pdd\OCBC\CCSTST\docdef\` (and also `CASOTST` from an earlier run).
- Action lesson: always validate the generated DFA source header (`/* Source: ... */`) before doing PDF gap analysis.

### 2) CASIO (CreditCard Statement) shows semantic layout drift from relative-flow handling
- `CCSTST_docexec.log` reports `PPDE7128W Text coordinate < 0` (e.g. CASIO lines ~1374/1380 and CASIOF3 line 10 context).
- Generated CASIO contains many negative relative jumps like `POSITION (SAME) (SAME-17.0 MM);`.
- Source DBM has case sections that start with negative NL (example around C0: `-17 NL`) assuming cursor continuity.
- Converter currently emits each PREFIX case in separate `DOCFORMAT`/`OUTLINE POSITION LEFT NEXT`, which can reset/shift baseline and make relative negatives unstable.
- Action lesson: for relative DBM flows, preserve anchor continuity or normalize to absolute coordinates before emitting `SAME-...` movements.

### 3) SHROW/BEGINTABLE is flattened, losing table semantics
- UT00060 source uses many `BEGINTABLE` + `SHROW` constructs.
- Parser logic combines row cells into a single SHP/TEXT-like line (no retained column widths/fixheight/margins/text-att fidelity).
- This is implemented in `universal_xerox_parser.py` (SHROW handling around the parser stack block that combines cell texts).
- Action lesson: for high-fidelity outputs, convert SHROW into structured DFA table/column output (or equivalent positioned multi-column rows), not merged plain text rows.

### 4) Unsupported VIPP commands are silently downgraded
- CASIO generated DFA contains stubs for unsupported commands like `GETITEM`, `SETPAGENUMBER`, and `BOOKMARK`.
- Even without DFA compile errors, this can remove functional behavior from the final PDF.
- Action lesson: track unsupported-command occurrences per project and rank by visual/business impact before iterative fixes.

### 5) Why SIBS_CAST can be ~95% while CASIO/UT00060 need more work
- SIBS_CAST structure is simpler for converter assumptions (less dependence on complex relative-flow/table constructs).
- CASIO and UT00060 use denser control/layout patterns:
  - deeper relative NL/MOVEH flow dependencies,
  - table abstractions (`SHROW`),
  - more branch-heavy logic and unsupported legacy commands.
- Action lesson: quality variance is expected with the same converter when source VIPP idioms differ; prioritize fixes by pattern-class, not by project name alone.

### 6) Xerox manual confirms concrete semantics for blocked commands
- Reference used: `Xerox_VIPP_Language_Reference_Manual_en-us.pdf` (text extracted to `tmp_vipp_ref.txt`).
- Confirmed command semantics:
  - `GETITEM`: assigns a set of values from a table (defined via `SETVAR`) to field names using an index (`VAR_itemtable index GETITEM`).
  - `BOOKMARK`: creates interactive PDF bookmark with text + optional hierarchy/style metadata.
  - `SETPAGENUMBER`: sets page-number format/position/rotation for subsequent pages.
  - `BEGINTABLE`/`SHROW`/`ENDTABLE`: true table model with per-cell width, margins, text attributes, align, fills/strokes, fixed height.
- Converter gap identified:
  - `universal_xerox_parser.py` currently forces `BOOKMARK`, `SETPAGENUMBER`, and `GETITEM` into unsupported stubs in the main DBM conversion path (even though helper conversion functions exist).
  - `SHROW` is currently flattened (cells merged into one text line), which loses table semantics.
- Action lesson: unblock command handling in the main conversion loop before adding new mapping logic; otherwise helper methods are dead code and output fidelity will not improve.

### 7) Implemented: BOOKMARK and SETPAGENUMBER pipeline unblocked (first slice)
- `BOOKMARK` is now emitted as DFA `GROUPINDEX` entries (PDF bookmark path) instead of unsupported stubs.
- `SETPAGENUMBER` is no longer dropped; it now maps into generated PRINTFOOTER page-number settings and emits an audit comment where encountered.
- `APPLICATION-OUTPUT-FORMAT` now includes `TLECPID YES` in addition to `TLE YES` to improve bookmark/index text encoding.
- Validation from regenerated outputs:
  - `CCSTST\\docdef\\CASIO.dfa` now has `GROUPINDEX BOOKMARK = ...` and no unsupported `BOOKMARK`/`SETPAGENUMBER` stubs.
  - `UTTST\\docdef\\UT00060.dfa` now has `GROUPINDEX BOOKMARK = ...` and `TLECPID YES`.
 - Follow-up correction:
   - Direct use of `$$VAR_pctot.` from VIPP page-number format in PRINTFOOTER caused scope warnings.
   - Mapping now normalizes known total-page token variants (`VAR_pctot`) to DFA `PP` in footer expressions.

### 8) Implemented: GETITEM/ADD table path (CASIO) and discovered DOCFORMAT filtering side-effect
- CASIO uses a VIPP table idiom for page totals:
  - `/VARtab [[/VAR_pctot]] SETVAR`
  - `{ /VARtab [[VAR_pctot]] ADD }`
  - `VARtab VARdoc GETITEM`
- Root-cause found:
  - `GETITEM` metadata extraction from parsed `SETVAR` was incomplete for bracket payloads, so converter fell back to unsupported/no-op behavior.
  - PREFIX `1` DOCFORMAT was incorrectly filtered as "empty", which removed the `ADD` side-effect that populates the table.
- Fixes implemented in `universal_xerox_parser.py`:
  - Added raw-DBM extraction for `[[...]] SETVAR` table headers.
  - Added `ADD` and `GETITEM` handling in both main case loop and IF/ELSE command block path.
  - Updated DOCFORMAT significance check to inspect nested commands; now page-management commands inside nested blocks keep the DOCFORMAT.
- Validation:
  - `CASIO.dfa` now contains `DOCFORMAT DF_1` with converted table `ADD`.
  - `CASIO.dfa` now emits converted `GETITEM` logic instead of unsupported stubs.

### 9) Remaining warning after GETITEM support
- DocEXEC still reports one warning in CASIO:
  - `PPDE7101W Variable 'VARTAB_ROWS' used without declaration` during later record processing.
- Observations:
  - The variable is initialized in `$_BEFOREFIRSTDOC`, but DocEXEC still flags later use.
  - `VAR_pctot` is now effectively dead for output (page footer uses `PP`), so this warning currently does not block PDF generation.
- Action lesson:
  - For robust DFA compatibility, avoid relying on implicit dynamic declaration semantics for table-surrogate variables; prefer explicit declaration patterns or remove dead table paths when no longer consumed by output.

### 10) Follow-up fix: removed dead total-page table semantics from emitted DFA flow
- The remaining `PPDE7101W Variable 'VARTAB_ROWS' used without declaration` in CASIO was tied to legacy `VAR_pctot` table lookup (`ADD` + `GETITEM`) that no longer drives output because page numbering now uses DFA `PP`.
- Implemented converter-side special handling:
  - Skip emitting `ADD` for single-column total-page tables (`VAR_pctot` aliases).
  - Skip emitting corresponding `GETITEM` reads for the same aliases.
- Result after regeneration/run:
  - `PPDE7101W` for `VARTAB_ROWS` is gone.
  - CASIO still returns `RC:4` only due existing `Text coordinate < 0` warnings (layout drift issue, separate root cause).

### 11) Layout drift mitigation implemented for large negative NL moves
- Root cause in CASIO DBM: first-row vertical jumps like `-17 NL` were emitted as `POSITION (SAME) (SAME-17.0 MM)` immediately after `OUTLINE POSITION LEFT NEXT`, causing coordinate underflow.
- Implemented converter safeguard in `_convert_case_commands`:
  - large negative NL moves (`>= 10`) are clamped to `NEXT`,
  - emitted with trace comment `/* Large negative NL clamped to NEXT for stable positioning */`.
- Result:
  - CASIO main-file underflow warnings were reduced; remaining warnings are now concentrated in FRM (`CASIOF3/10`) only.

### 12) SHROW spacing fidelity improved (width-aware text composition)
- Previous behavior flattened SHROW cells with single-space joins, which lost visible table-column structure.
- Parser enhancement:
  - SHROW extraction now captures `/Width` (and `/CellWdth` fallback),
  - combined SHROW text inserts width-proportional spaces between cells.
- Result:
  - generated UT00060 rows now preserve stronger visual separation (e.g., `Fund Name                 : ...`),
  - DocEXEC still completes cleanly (`UTTST` RC 0).

### 13) FRM include anchor must be page-top when rendered from PRINTFOOTER
- FRM backgrounds are rendered through `USE FORMAT REFERENCE(FRM_PAGE[P]) EXTERNAL;` inside `PRINTFOOTER`.
- Using FRM include wrapper `OUTLINE POSITION LEFT NEXT` made execution context-sensitive and triggered page-object overflow warnings in CASIO (`CASIOS/10`) on selected records/pages.
- Converter fix:
  - in FRM include mode (`as_include=True`), anchor with `POSITION LEFT TOP`.
- Result:
  - CASIO `PPDE7242W (CASIOS/10)` warnings were eliminated in current runs.
  - Remaining CASIO warning is `PPDE7128W (CASIOF3/10) Text coordinate < 0` on RN 28/48.

### 14) MOVEHR minus-sign behavior is not safely generalizable yet
- Attempted parser/converter change to preserve unary minus for `MOVEHR` and treat `MOVEHR` as relative produced severe regressions:
  - negative X cascades in `CASIOF3.dfa`,
  - `PPDE7178E Coordinate overflow` in CASIO main (`CASIO/1194`), RC 12.
- Reverted this change fully after verification.
- Action lesson:
  - do not globally reinterpret `MOVEHR` semantics without command-level proofs from Xerox examples and per-project regression tests.

### 15) CASIOF3 overlap root cause: unary minus leakage + wrong MOVEHR base in FRM
- In `CASIOF3.FRM`, header cells use patterns like `-69 MOVEHR`, `-49.5 MOVEHR`, `15 MOVEHR`, `95 MOVEHR`.
- Two coupled issues caused overlap and `CASIOF3/10` negative-coordinate warnings:
  - parser dropped unary `-` for `MOVEHR`, leaving stray minus tokens that then polluted subsequent `NL` sign parsing,
  - FRM converter interpreted `MOVEHR` as plain absolute X, yielding negative absolute positions (`-69 MM`, `-49.5 MM`).
- Converter fix now in FRM paths:
  - preserve unary minus token for `MOVEH/MOVEHR` parameter extraction in parser,
  - for FRM only, treat `MOVEHR` as offset from anchor X (last absolute `MOVETO`/`MOVEH`), not from cumulative current X.
- Result in generated `CASIOF3.dfa`:
  - header positions became stable: `19.0`, `38.5`, `103.0`, `183.0` (instead of negative values),
  - prior `PPDE7128W (CASIOF3/10)` warnings no longer appeared in the latest run; only PDF file-lock error remained when writing `CASIO.pdf`.

### 16) CASIO Y0 drift root cause: dotted unslashed identifiers (`VAR.Y5`) leak RPN stack values
- In `CASIO.DBM` Y0 rows, DRAWB uses unslashed dotted tokens (`VAR.Y5`) in patterns like:
  - `00 VAR.Y5 0.1 05.8 FBLACK DRAWB`
  - `192.9 VAR.Y5 0.1 05.8 FBLACK DRAWB`
- The lexer accepts dots for Xerox identifiers starting with `/` (`/VAR.Y5`) but not for plain identifiers (`VAR.Y5`).
- Effect:
  - parser splits `VAR.Y5` into separate tokens (`VAR`, `Y5`),
  - DRAWB pops 5 operands but leaves numeric residue (`00`, `192.9`) on stack,
  - subsequent `NL` consumes leftover numeric as spacing, producing wrong DFA such as `POSITION (SAME) (SAME+192.9 MM)`.
- Visual impact:
  - intended border DRAWB lines are not rendered correctly,
  - cursor flow is corrupted, causing block misalignment/overlap in page 1.
- Action lesson:
  - support dot in `_handle_identifier` for non-slashed identifiers and harden optional-parameter commands (like `NL`) against unrelated stack residue.

### 17) Implemented fix: dotted identifier + NL stack-guard removed YA spacing corruption
- Converter updates in `universal_xerox_parser.py`:
  - `_handle_identifier` now includes `.` so plain `VAR.Y5` parses as one identifier.
  - `NL` optional parameter extraction now requires explicit numeric token immediately before `NL`.
- Effect in CASIO:
  - removed accidental `OUTPUT '' POSITION (SAME) (SAME+192.9 MM)` jumps,
  - stabilized vertical flow in YA rows and prevented cascading overlap.

### 18) Implemented fix: DRAWB accepts variable coordinates in DBM flow
- `_convert_box_command_dfa` now supports variable x/y coordinates (not only numeric).
- Dynamic coordinates are emitted as expressions like `(VARY5-$MR_TOP)`.
- Important:
  - do not append `MM` unit token directly to variable expressions in DFA position math; use expression arithmetic with margins instead.
  - numeric coords may keep `MM` literals.

### 19) CASIO-specific refinement: variable Y in inline DRAWB should follow cursor (`SAME`)
- In CASIO Y0, lines like `00 VAR.Y5 0.1 05.8 FBLACK DRAWB` and `192.9 VAR.Y5 ...` are row separators tied to current text flow.
- `VAR.Y5` is initialized/reset to `0` and never incremented in CASIO DBM, so it behaves as a zero-offset placeholder.
- Mapping variable Y to absolute margin coordinates (`VARY5-$MR_TOP`) places lines near page top and breaks layout.
- Converter refinement in `_convert_box_command_dfa`:
  - numeric Y: keep absolute behavior (`abs(y) MM-$MR_TOP`)
  - variable Y: map to `SAME` (relative to current cursor line)
- Result: YA vertical separators align with row flow and no longer jump to top-of-page coordinates.

### 20) XGFRESDEF SCALL anchor in DBM must follow accumulated NL flow
- Root cause for YSAB misplacement: in DBM conversion, `current_y` stayed at its initial default and was not updated by `NL`.
- Effect: inlined XGFRESDEF comments showed origins like `(8.0, 40)` regardless of prior flow, causing table/grid blocks to jump upward.
- Fix:
  - track active `SETLSP` and update `current_y` on each `NL` in `_convert_case_commands`,
  - SCALL inlined draw blocks now receive a realistic flow-origin Y (e.g. `93.19` in CASIO Y0).
- Additional visibility fix:
  - clamp RULE thickness below `0.05` to `0.1 MM` in `_convert_frm_rule` so converted grid lines are visible in PDF.

### 21) Generalized DBM inline SCALL rule: flow-relative Y for all XGFRESDEF blocks
- Issue: applying absolute Y placement to inlined XGFRESDEF (`SCALL`) creates repeated drift in multiple sections (`YSAB`, `YPIB`, etc.), especially after conditional variable rows.
- Converter enhancement:
  - `_inline_xgfresdef_drawbs(..., flow_relative_y=True)` for DBM `SCALL` path,
  - emits positions like `POSITION (x MM-$MR_LEFT) (SAME+/-offset)` for inlined DRAWB commands.
- Result:
  - same fix automatically applies to all inline drawing subroutines in DBM flow, not only YSAB.

### 22) Stable Xerox-like SCALL behavior: save/anchor/restore cursor
- Best-fit mapping for DBM inline XGFRESDEF SCALL:
  - save `YPOS = $SL_CURRY; XPOS = $SL_CURRX;`
  - if a prior MOVEH/MOVETO set X/Y explicitly, override anchors from converter-known values (`XPOS = MM(<x>)`, optional `YPOS = MM(<y>)`)
  - emit inlined DRAWB using anchor expressions (`POSITION (XPOS+dx MM) (YPOS+dy MM)`)
  - restore cursor after segment with:
    - `OUTPUT '' FONT <current> NORMAL POSITION (XPOS) (YPOS);`
- This prevents inlined BOX/RULE output from drifting the text flow while preserving Xerox segment-origin semantics.

### 23) Minimum line/box thinness normalized to 0.01 MM
- For converted DRAWB geometry and RULE thickness, tiny values (0 / 0.0001 / 0.001) are normalized to `0.01 MM`.
- This aligns with Xerox intent for hairlines while remaining visible and stable in PDF rendering.

### 24) Vertical thin BOX (0.1 MM width) should emit RULE UP
- Converter rule added in both FRM DRAWB and DBM BOX conversion paths:
  - if `WIDTH == 0.1 MM` and `HEIGHT > WIDTH`, emit `RULE` instead of `BOX`.
  - start position uses the lower endpoint (`y + height`) and `DIRECTION UP`.
  - emitted stroke is forced to `THICKNESS 0.1 MM TYPE SOLID`.
- This avoids fragile box rendering for vertical separators and aligns better with expected line behavior in Papyrus PDF output.

### 25) ORITL requires inverted relative Y offsets for inlined SCALL drawing
- In XGFRESDEF/SCALL inline conversion, relative Y offsets are now sign-flipped when DBM uses `ORITL`.
- Rule applied: `-6 -> +6`, `+6 -> -6` for anchored Y expressions (`YPOS...`).
- Detection:
  - primary: parsed DBM command `ORITL`
  - fallback: raw-content search for `ORITL`
- This aligns DFA inline segment placement with Xerox top-left origin behavior.

### 26) FRM SCALL inlining must also use XPOS/YPOS save-restore anchors
- XGFRESDEF inlining inside FRM conversion now mirrors DBM behavior:
  - save cursor: `YPOS = $SL_CURRY; XPOS = $SL_CURRX;`
  - apply explicit MOVETO state when present: `XPOS = MM(x)`, `YPOS = MM(y)`
  - inline DRAWB relative to `XPOS/YPOS`
  - restore flow cursor with `OUTPUT '' ... POSITION (XPOS) (YPOS);`
- Prevents SCALL segment drawing from drifting FRM text flow and keeps placement consistent across modules.

### 27) DBM VAR.Yx lines should bind to current cursor before vertical RULE UP
- For DBM DRAWB patterns like `x VAR.Y5 0.1 5.8 FBLACK DRAWB`, converter now emits:
  - `VAR_Y5 = $SL_CURRY;`
  - `RULE POSITION (...) (VAR_Y5+5.8 MM) DIRECTION UP ...`
- This preserves Xerox dynamic Y anchor intent for YA/summary vertical separators and avoids drifting from `SAME` semantics.

### 28) VIPP `/VAR.Yx 0 ADD` is a flow-Y anchor, not arithmetic
- Converter ADD handling now maps `/VAR.Yx 0 ADD` to:
  - `VARYx = $SL_CURRY;`
- This avoids generating no-op `VARYx = VARYx + 0;` and matches Xerox usage where VAR.Yx acts as a dynamic Y baseline before DRAWB blocks.

### 29) DBM standalone FI/FK and W/B tokens must update style state
- In DBM case conversion, standalone font/color aliases are now treated as stateful style commands:
  - font aliases (`FI`, `FK`, etc.) update `current_font`
  - color aliases (`W`, `B`, etc.) update `current_color`
- `_convert_output_command_dfa` now emits `COLOR <current_color>` for OUTPUT commands, ensuring VIPP shortcut color switches are preserved consistently.

### 30) Propagate style state into nested IF/ELSE blocks
- DBM conversion now propagates both `current_font` and `current_color` when entering `_convert_if_command` children.
- This prevents losing shortcut style commands (`FI/FK`, `W/B`) inside IF/ELSE content, which previously caused intermittent missing color/font output.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xerox_annotator.py
==================
Second version of xerox_beautifier.py.

Like the beautifier it removes commented-out code and normalises indentation,
but it ALSO appends a natural-language comment after every active VIPP
instruction so that non-Xerox experts can read the code.

Usage
-----
    py -3 xerox_annotator.py <source_dir> --output <target_dir>

    <source_dir>  : folder containing .dbm / .frm / .jdt files
    <target_dir>  : folder where annotated files are written

Output example
--------------
    /F1  /ARIAL  06  INDEXFONT       % Register font alias "F1" → Arial at 6pt
    12 31 MOVETO                     % Move cursor to position (12, 31) mm
    (Private & Confidential) SH      % Print "Private & Confidential" (left-aligned) at current position
    /IF_CND1  2  7  /eq  (Period:) SETRCD  % Define IF_CND1: chars 2–8 == "Period:"
"""

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import the cleanup pipeline from the sibling beautifier script
# ---------------------------------------------------------------------------
try:
    from xerox_beautifier import beautify_vipp, VIPP_EXTENSIONS
except ImportError as _imp_err:
    print(
        f"ERROR: Cannot import xerox_beautifier.py — make sure it is in the same\n"
        f"       directory as xerox_annotator.py.  ({_imp_err})",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

# Xerox internal typeface names → human-readable names
_FONT_NAMES: dict[str, str] = {
    "NTMR":        "Times Roman",
    "NTMB":        "Times Bold",
    "NTMI":        "Times Italic",
    "NTMBI":       "Times Bold Italic",
    "NHE":         "Helvetica",
    "NHEB":        "Helvetica Bold",
    "NHEI":        "Helvetica Italic",
    "NHEN":        "Helvetica Narrow",
    "NHENB":       "Helvetica Narrow Bold",
    "NHEBO":       "Helvetica Bold Oblique",
    "NCR":         "Courier",
    "NCRB":        "Courier Bold",
    "NCRI":        "Courier Italic",
    "ARIAL":       "Arial",
    "ARIALB":      "Arial Bold",
    "ARIALI":      "Arial Italic",
    "ARIALO":      "Arial Italic",
    "ARIALBO":     "Arial Bold Italic",
    "SBT":         "Symbol",
    "SYMBOL":      "Symbol",
    # Windows / Type-1 names used in some jobs
    "Helvetica":        "Helvetica",
    "Helvetica-Bold":   "Helvetica Bold",
    "Helvetica-Oblique":"Helvetica Italic",
}

# SETRCD comparison operators
_CMP_OPS: dict[str, str] = {
    "/eq":  "==",
    "/ne":  "!=",
    "/gt":  ">",
    "/lt":  "<",
    "/ge":  ">=",
    "/le":  "<=",
}

# SH-family alignment labels
_ALIGN: dict[str, str] = {
    "SH":  "left",
    "SHL": "left",
    "SHR": "right",
    "SHr": "right",
    "SHC": "center",
}

# DRAWB styles — determines whether the box is filled or border-only
_FILL_STYLES = {
    "S1", "S2", "R_S1", "R_S2",
    "FBLACK", "FWHITE", "FRED", "FBLUE", "FGREEN", "FGREY", "FGRAY",
}
_LINE_STYLES = {"LMED", "LTHN", "LTHK", "XLTR"}


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def _tokenize(line: str) -> list[str]:
    """
    Split one VIPP source line into tokens.

    Handles:
      (string literals with spaces)
      [array / compound condition literals]
      /name  tokens
      numbers and keyword tokens
    Stops at % (comment marker).
    """
    tokens: list[str] = []
    i, n = 0, len(line)

    while i < n:
        c = line[i]

        if c in (" ", "\t"):
            i += 1

        elif c == "%":
            break  # rest is a comment

        elif c == "(":
            # String literal: scan to matching closing paren (depth-aware)
            depth, j = 1, i + 1
            while j < n and depth > 0:
                if line[j] == "(":
                    depth += 1
                elif line[j] == ")":
                    depth -= 1
                j += 1
            tokens.append(line[i:j])
            i = j

        elif c == "[":
            # Array literal: scan to matching ] — stop at % (PostScript comment)
            depth, j = 1, i + 1
            while j < n and depth > 0:
                if line[j] == "%":
                    break  # % always starts a comment, even inside [...]
                elif line[j] == "[":
                    depth += 1
                elif line[j] == "]":
                    depth -= 1
                j += 1
            tokens.append(line[i:j])
            i = j

        elif c in ("{", "}"):
            tokens.append(c)
            i += 1

        else:
            # Regular token: read until whitespace or special char
            j = i
            while j < n and line[j] not in (" ", "\t", "(", "[", "{", "}", "%"):
                j += 1
            tok = line[i:j]
            if tok:
                tokens.append(tok)
            i = j

    return tokens


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _unquote(tok: str) -> str:
    """Return the content of a (string) token without the parentheses."""
    if tok.startswith("(") and tok.endswith(")"):
        return tok[1:-1]
    return tok


def _strip_slash(tok: str) -> str:
    """Remove a leading / from a /name token."""
    return tok.lstrip("/")


def _is_number(tok: str) -> bool:
    try:
        float(tok)
        return True
    except (ValueError, TypeError):
        return False


def _is_string(tok: str) -> bool:
    return tok.startswith("(") and tok.endswith(")")


def _is_var(tok: str) -> bool:
    u = tok.upper()
    return u.startswith("VAR_") or u.startswith("FLD") or tok == "PREFIX"


def _label(tok: str) -> str:
    """Human-readable label for a string / variable / other token."""
    if _is_string(tok):
        content = _unquote(tok)
        if not content.strip():
            return "(spaces)"
        if len(content) > 32:
            return f'"{content[:29]}..."'
        return f'"{content}"'
    if _is_var(tok):
        return f"variable {tok}"
    return tok


def _expand_font(name: str) -> str:
    key = name.lstrip("/")
    return _FONT_NAMES.get(key, key)


# ---------------------------------------------------------------------------
# Individual command description functions
# ---------------------------------------------------------------------------
# Convention:
#   args  = list of tokens that appear BEFORE the command on this line
#   full  = the full token list for the line
#   cmd   = the command token string (as it appears in source)
# Each function returns a short English string (≤ 70 chars).
# ---------------------------------------------------------------------------

def _desc_port(args, full, cmd):
    return "Set page orientation to Portrait"

def _desc_land(args, full, cmd):
    return "Set page orientation to Landscape"

def _desc_xgf(args, full, cmd):
    return "Initialize Xerox Generic Format processing"

def _desc_oritl(args, full, cmd):
    return "Set coordinate origin to top-left of page"

def _desc_pagebrk(args, full, cmd):
    return "Force a page break — start a new page"

def _desc_newframe(args, full, cmd):
    return "Overflow to the next frame / page"

def _desc_skippage(args, full, cmd):
    return "Suppress output and skip this page"

def _desc_beginpage(args, full, cmd):
    return "Begin page-level output block"

def _desc_endpage(args, full, cmd):
    return "End page-level output block"

def _desc_endif(args, full, cmd):
    return "End of IF / ELSE conditional"

def _desc_endfor(args, full, cmd):
    return "End of FOR loop"

def _desc_endcase(args, full, cmd):
    return "End of CASE switch statement"

def _desc_open_brace(args, full, cmd):
    if args and args[0].upper() == "ELSE":
        return "End previous block; begin else branch"
    if args:
        first_up = args[0].upper()
        if first_up in _PREFIX_DISPATCH:
            return f"End block; then {_PREFIX_DISPATCH[first_up](args[1:], full, args[0]).lower()}"
    return "Begin block"

def _desc_close_brace(args, full, cmd):
    if args and args[0].upper() == "ELSE":
        return "End block; then else branch"
    if args:
        first_up = args[0].upper()
        if first_up in _PREFIX_DISPATCH:
            inner = _PREFIX_DISPATCH[first_up](args[1:], full, args[0]).lower()
            return f"End block; then {inner}"
    return "End block"

def _desc_if(args, full, cmd):
    if not args:
        return "If condition is true"
    cond = args[0]
    # Inline comparison: IF var value eq/ne/gt/lt {
    if len(args) >= 3:
        op_tok = args[2].lower()
        op_map = {"eq": "==", "ne": "!=", "gt": ">", "lt": "<", "ge": ">=", "le": "<="}
        if op_tok in op_map:
            return f"If {cond} {op_map[op_tok]} {_label(args[1])}"
    return f"If condition {cond} is true"

def _desc_else(args, full, cmd):
    return "Otherwise (else branch)"

def _desc_for(args, full, cmd):
    n = args[0] if args else "?"
    return f"Repeat the following block {n} times"

def _desc_case(args, full, cmd):
    var = args[0] if args else "?"
    return f"Branch based on value of {var}"

def _desc_fromline(args, full, cmd):
    n = args[0] if args else "?"
    return f"Define RPE output starting from input record line {n}"

def _desc_beginrpe(args, full, cmd):
    n = args[0] if args else "?"
    return f"Begin RPE section ({n} records per page)"

def _desc_nl(args, full, cmd):
    # May be: NL alone  or  n NL
    n = args[-1] if args and _is_number(args[-1]) else None
    if n and n != "1":
        return f"Advance {n} lines"
    return "Advance to the next line"

def _desc_moveto(args, full, cmd):
    nums = [t for t in args if _is_number(t)]
    if len(nums) >= 2:
        return f"Move cursor to position ({nums[-2]}, {nums[-1]}) mm"
    return "Move cursor to specified position"

def _desc_moveh(args, full, cmd):
    x = args[-1] if args and _is_number(args[-1]) else "?"
    return f"Move cursor horizontally to column {x}"

def _desc_movehr(args, full, cmd):
    n = args[-1] if args and _is_number(args[-1]) else "?"
    return f"Move cursor right by {n} units"

def _desc_sh(args, full, cmd):
    """Handle SH / SHL / SHR / SHr / SHC."""
    align = _ALIGN.get(cmd.upper(), "left")

    # Find the text/variable argument (last string or VAR_ token in args)
    text_tok = None
    text_idx = -1
    for j in range(len(args) - 1, -1, -1):
        t = args[j]
        if _is_string(t) or _is_var(t):
            text_tok = t
            text_idx = j
            break

    lbl = _label(text_tok) if text_tok else "text"

    # Find (x, y): numbers after text_tok take priority (pattern: text x y CMD)
    x_tok = y_tok = None
    if text_idx >= 0:
        after = args[text_idx + 1:]
        nums_after = [t for t in after if _is_number(t)]
        if len(nums_after) >= 2:
            x_tok, y_tok = nums_after[-2], nums_after[-1]
        else:
            # Fallback: look for MOVETO before text_tok
            before = args[:text_idx]
            moveto_idx = next(
                (k for k, t in enumerate(before) if t.upper() == "MOVETO"), None
            )
            if moveto_idx is not None:
                nums_before = [t for t in before[:moveto_idx] if _is_number(t)]
                if len(nums_before) >= 2:
                    x_tok, y_tok = nums_before[-2], nums_before[-1]

    if x_tok and y_tok:
        return f"Print {lbl} ({align}-aligned) at ({x_tok}, {y_tok})"
    return f"Print {lbl} ({align}-aligned) at current position"

def _desc_shp(args, full, cmd):
    """Handle SHP (show with explicit column width)."""
    text_tok = None
    width = None
    for j in range(len(args) - 1, -1, -1):
        t = args[j]
        if _is_string(t) or _is_var(t):
            text_tok = t
            after = args[j + 1:]
            nums_after = [x for x in after if _is_number(x)]
            if nums_after:
                width = nums_after[0]  # first number after text = column width
            break

    lbl = _label(text_tok) if text_tok else "text"
    w_part = f" in a {width}-unit wide column" if width else " in fixed-width column"
    return f"Print {lbl}{w_part}"

def _desc_drawb(args, full, cmd):
    """Handle DRAWB (draw box)."""
    style_kind = ""
    nums = []
    for t in args:
        tu = t.upper()
        if _is_number(t):
            nums.append(t)
        elif tu in {s.upper() for s in _FILL_STYLES}:
            style_kind = "filled "
        elif tu in {s.upper() for s in _LINE_STYLES}:
            style_kind = "border-only "

    if len(nums) >= 4:
        x, y, w, h = nums[-4], nums[-3], nums[-2], nums[-1]
        return f"Draw {style_kind}box at ({x}, {y}), size {w} × {h}"
    return f"Draw {style_kind}box"

def _desc_drawl(args, full, cmd):
    nums = [t for t in args if _is_number(t)]
    if len(nums) >= 4:
        x1, y1, x2, y2 = nums[-4], nums[-3], nums[-2], nums[-1]
        return f"Draw line from ({x1}, {y1}) to ({x2}, {y2})"
    return "Draw a line"

def _desc_indexfont(args, full, cmd):
    if len(args) >= 3:
        alias = _strip_slash(args[-3])
        face  = _expand_font(args[-2])
        size  = args[-1]
        return f'Register font alias "{alias}" → {face} at {size}pt'
    if len(args) >= 2:
        alias = _strip_slash(args[-2])
        face  = _expand_font(args[-1])
        return f'Register font alias "{alias}" → {face}'
    return "Register a named font alias"

def _desc_indexcolor(args, full, cmd):
    if len(args) >= 2:
        alias = _strip_slash(args[-2])
        color = args[-1]
        return f'Register color alias "{alias}" = {color}'
    return "Register a named color alias"

def _desc_indexbat(args, full, cmd):
    attr_map = {
        "/undl": "underline", "/bold": "bold", "/ital": "italic",
        "null": "none (reset)",
    }
    if len(args) >= 2:
        alias = _strip_slash(args[-2])
        attr  = attr_map.get(args[-1].lower(), _strip_slash(args[-1]))
        return f'Register text-attribute alias "{alias}" = {attr}'
    return "Register a named text attribute alias"

def _desc_indexsst(args, full, cmd):
    attr_map = {"/sup": "superscript", "/sub": "subscript", "null": "none (reset)"}
    if len(args) >= 2:
        alias = _strip_slash(args[-2])
        attr  = attr_map.get(args[-1].lower(), _strip_slash(args[-1]))
        return f'Register sub/superscript alias "{alias}" = {attr}'
    return "Register a sub/superscript attribute alias"

def _desc_indexpif(args, full, cmd):
    if args:
        alias = _strip_slash(args[0])
        return f'Register interactive/hyperlink alias "{alias}"'
    return "Register an interactive feature alias (hyperlink / URL)"

def _desc_setfont(args, full, cmd):
    if len(args) >= 2:
        face = _expand_font(args[-2])
        size = args[-1]
        return f"Set default font to {face} at {size}pt"
    if args:
        face = _expand_font(args[-1])
        return f"Set default font to {face}"
    return "Apply previously-set default font"

def _desc_setftsw(args, full, cmd):
    if len(args) >= 1:
        chars = _unquote(args[-2]) if len(args) >= 2 else _unquote(args[-1])
        return f'Set font-switch marker to "{chars}" (triggers inline font change)'
    return "Set font-switch control character"

def _desc_setunit(args, full, cmd):
    unit_map = {
        "MM": "millimetres", "INCH": "inches", "CM": "centimetres",
        "POINT": "points",   "UNIH": "UNIH units",
    }
    unit = args[-1].upper() if args else "?"
    return f"Set measurement unit to {unit_map.get(unit, unit)}"

def _desc_setlsp(args, full, cmd):
    n = args[-1] if args and _is_number(args[-1]) else "?"
    return f"Set line spacing to {n} units"

def _desc_setmargin(args, full, cmd):
    nums = [t for t in args if _is_number(t)]
    if len(nums) >= 4:
        t, b, l, r = nums[-4], nums[-3], nums[-2], nums[-1]
        return f"Set page margins — top:{t}  bottom:{b}  left:{l}  right:{r}"
    return "Apply page margin settings (top / bottom / left / right from preceding lines)"

def _desc_setgrid(args, full, cmd):
    nums = [t for t in args if _is_number(t)]
    if len(nums) >= 2:
        cpl, lpp = nums[-2], nums[-1]
        return f"Set grid: {cpl} characters/line, {lpp} lines/page"
    return "Set character grid (characters-per-line, lines-per-page)"

def _desc_setmaxform(args, full, cmd):
    n = args[-1] if args and _is_number(args[-1]) else "?"
    return f"Allow up to {n} overlay forms to be loaded simultaneously"

def _desc_setform(args, full, cmd):
    strings = [t for t in args if _is_string(t)]
    name    = _unquote(strings[-1]) if strings else "?"
    cached  = any(t.upper() == "CACHE" for t in args)
    return f'{"Load and cache" if cached else "Load"} overlay form "{name}"'

def _desc_setpcc(args, full, cmd):
    enc_map = {"ANSI": "ANSI/Windows Latin-1", "EBCDIC": "EBCDIC", "ASCII": "ASCII"}
    enc = _strip_slash(args[-1]) if args else "?"
    return f"Set page character encoding to {enc_map.get(enc.upper(), enc)}"

def _desc_setvfu(args, full, cmd):
    return "Define vertical forms unit (VFU) channel-skip rules"

def _desc_setparams(args, full, cmd):
    return "Configure numeric formatting (decimal point, separators, sign characters)"

def _desc_setlkf(args, full, cmd):
    return "Define linked-frame (multi-page chain) layout"

def _desc_setpagedef(args, full, cmd):
    if args:
        name = _unquote(args[-1]) if _is_string(args[-1]) else _strip_slash(args[-1])
        return f'Apply page definition "{name}"'
    return "Apply page definition"

def _desc_setvar(args, full, cmd):
    """Handle SETVAR — find the /name token robustly even in complex one-liners."""
    if not args:
        return "Set a variable"

    # Locate the last /name token that is not /INI
    name_idx = -1
    for j in range(len(args) - 1, -1, -1):
        t = args[j]
        if t.startswith("/") and t.upper() not in ("/INI", "/SETVAR"):
            name_idx = j
            break

    if name_idx < 0:
        return "Set a variable"

    name = _strip_slash(args[name_idx])
    ini  = any(a.upper() == "/INI" for a in args)

    val_tok = None
    if name_idx + 1 < len(args):
        v = args[name_idx + 1]
        if v.upper() not in ("/INI", "/SETVAR", "SETVAR", "VSUB"):
            val_tok = v

    if val_tok is not None:
        val_lbl = _unquote(val_tok) if _is_string(val_tok) else val_tok
        # Truncate long template strings
        if len(val_lbl) > 35:
            val_lbl = val_lbl[:32] + "..."
        if ini:
            return f'Initialize variable {name} = "{val_lbl}" (first run only)'
        return f'Set variable {name} = "{val_lbl}"'

    if ini:
        return f"Initialize variable {name} (first run only)"
    return f"Set variable {name}"

def _desc_vsub(args, full, cmd):
    return "Expand [=VARIABLE=] placeholders inside the preceding string"

def _desc_setrcd(args, full, cmd):
    """Define a SETRCD condition."""
    if not args:
        return "Define a record-match condition"

    cnd_name = _strip_slash(args[0])

    # Compound condition:  /name [cnd1 cnd2 /or|/and] SETRCD
    if len(args) >= 2 and args[1].startswith("["):
        inner = args[1].strip("[]").split()
        if "/or" in inner:
            parts = " OR ".join(t for t in inner if not t.startswith("/"))
            return f"Define {cnd_name} = {parts}"
        if "/and" in inner:
            parts = " AND ".join(t for t in inner if not t.startswith("/"))
            return f"Define {cnd_name} = {parts}"
        return f"Define condition {cnd_name} as compound expression"

    # Simple positional condition:  /name pos len /op (string) SETRCD
    if len(args) >= 4:
        pos    = args[1]
        length = args[2]
        op_tok = args[3].lower()

        if op_tok == "/hold":
            match_str = _unquote(args[4]) if len(args) >= 5 else "?"
            return (
                f'Define {cnd_name}: carry-forward flag if any line contains "{match_str}"'
            )

        op_label = _CMP_OPS.get(op_tok, op_tok)
        if len(args) >= 5:
            match_str = _unquote(args[4])
            try:
                end_pos = int(pos) + int(length) - 1
                pos_desc = f"chars {pos}–{end_pos}"
            except ValueError:
                pos_desc = f"pos {pos}, len {length}"
            return f'Define {cnd_name}: {pos_desc} {op_label} "{match_str}"'

        return f"Define {cnd_name}: check pos {pos}, length {length}"

    return f"Define condition {cnd_name}"

def _desc_setpcd(args, full, cmd):
    """Define a SETPCD page-control condition."""
    if not args:
        return "Define a page-control condition"
    name = _strip_slash(args[0])
    # SETPCD format: /name startline numlines pos len /op (string) SETPCD
    if len(args) >= 7:
        match_str = _unquote(args[6]) if _is_string(args[6]) else args[6]
        return f'Define page condition {name}: scan lines {args[1]}–{args[2]}, pos {args[3]}/{args[4]} == "{match_str}"'
    return f"Define page condition {name}"

def _desc_scall(args, full, cmd):
    strings = [t for t in args if _is_string(t)]
    name    = _unquote(strings[-1]) if strings else "?"
    nums    = [t for t in args if _is_number(t)]
    scale   = None
    if nums:
        # Scale is a small float (0 < x ≤ 10)
        try:
            sv = float(nums[0])
            if 0 < sv <= 10:
                scale = f"{sv * 100:.0f}%"
        except ValueError:
            pass
    suffix = f" scaled to {scale}" if scale else ""
    return f'Insert segment / image "{name}"{suffix}'

def _desc_icall(args, full, cmd):
    strings = [t for t in args if _is_string(t)]
    name    = _unquote(strings[-1]) if strings else "?"
    nums    = [t for t in args if _is_number(t)]
    scale   = None
    if nums:
        try:
            sv = float(nums[0])
            if 0 < sv <= 10:
                scale = f"{sv * 100:.0f}%"
        except ValueError:
            pass
    suffix = f" scaled to {scale}" if scale else ""
    return f'Insert image "{name}"{suffix}'

def _desc_xgfresdef(args, full, cmd):
    name = _strip_slash(args[0]) if args else "?"
    return f'Define reusable drawing element "{name}"'

def _desc_getfield(args, full, cmd):
    # /VAR line_num pos length GETFIELD
    if len(args) >= 4:
        var    = _strip_slash(args[0])
        line_n = args[1]
        pos    = args[2]
        length = args[3]
        return f"Read {length} chars from pos {pos} of input line {line_n} → {var}"
    return "Extract a field from an input record into a variable"

def _desc_getintv(args, full, cmd):
    if len(args) >= 3:
        pos    = args[-2]
        length = args[-1]
        return f"Extract substring: position {pos}, length {length}"
    return "Extract a substring (interval) from a string"

def _desc_getitem(args, full, cmd):
    return "Get an item by index from an array"

def _desc_bookmark(args, full, cmd):
    strings = [t for t in args if _is_string(t)]
    if strings:
        raw = _unquote(strings[-1])
        lbl = raw[:30] + ("..." if len(raw) > 30 else "")
        return f'Create PDF bookmark "{lbl}"'
    return "Create a PDF bookmark at the current position"

def _desc_setpagenumber(args, full, cmd):
    return "Configure page numbering"

def _desc_cache(args, full, cmd):
    return "Pre-load the resource into cache"

def _desc_mm_unit(args, full, cmd):
    return "Set measurement unit to millimetres"


# ---------------------------------------------------------------------------
# Dispatch tables
# ---------------------------------------------------------------------------
# _PREFIX_DISPATCH  : command is recognised as the FIRST token on the line
# _SUFFIX_DISPATCH  : command is recognised scanning RIGHT-TO-LEFT

_PREFIX_DISPATCH: dict[str, callable] = {
    "PORT":      _desc_port,
    "LAND":      _desc_land,
    "XGF":       _desc_xgf,
    "ORITL":     _desc_oritl,
    "PAGEBRK":   _desc_pagebrk,
    "NEWFRAME":  _desc_newframe,
    "SKIPPAGE":  _desc_skippage,
    "BEGINPAGE": _desc_beginpage,
    "ENDPAGE":   _desc_endpage,
    "ENDIF":     _desc_endif,
    "ENDFOR":    _desc_endfor,
    "ENDCASE":   _desc_endcase,
    "IF":        _desc_if,
    "ELSE":      _desc_else,
    "FOR":       _desc_for,
    "CASE":      _desc_case,
    "FROMLINE":  _desc_fromline,
    "BEGINRPE":  _desc_beginrpe,
    "{":         _desc_open_brace,
    "}":         _desc_close_brace,
}

_SUFFIX_DISPATCH: dict[str, callable] = {
    "SH":            _desc_sh,
    "SHL":           _desc_sh,
    "SHR":           _desc_sh,
    "SHr":           _desc_sh,
    "SHC":           _desc_sh,
    "SHP":           _desc_shp,
    "MOVETO":        _desc_moveto,
    "MOVEH":         _desc_moveh,
    "MOVEHR":        _desc_movehr,
    "NL":            _desc_nl,
    "DRAWB":         _desc_drawb,
    "DRAWL":         _desc_drawl,
    "INDEXFONT":     _desc_indexfont,
    "INDEXCOLOR":    _desc_indexcolor,
    "INDEXBAT":      _desc_indexbat,
    "INDEXSST":      _desc_indexsst,
    "INDEXPIF":      _desc_indexpif,
    "SETFONT":       _desc_setfont,
    "SETFTSW":       _desc_setftsw,
    "SETUNIT":       _desc_setunit,
    "SETLSP":        _desc_setlsp,
    "SETMARGIN":     _desc_setmargin,
    "SETGRID":       _desc_setgrid,
    "SETMAXFORM":    _desc_setmaxform,
    "SETFORM":       _desc_setform,
    "SETPCC":        _desc_setpcc,
    "SETVFU":        _desc_setvfu,
    "SETPARAMS":     _desc_setparams,
    "SETLKF":        _desc_setlkf,
    "SETPAGEDEF":    _desc_setpagedef,
    "SETVAR":        _desc_setvar,
    "VSUB":          _desc_vsub,
    "SETRCD":        _desc_setrcd,
    "SETPCD":        _desc_setpcd,
    "SCALL":         _desc_scall,
    "ICALL":         _desc_icall,
    "XGFRESDEF":     _desc_xgfresdef,
    "GETFIELD":      _desc_getfield,
    "GETINTV":       _desc_getintv,
    "GETITEM":       _desc_getitem,
    "BOOKMARK":      _desc_bookmark,
    "SETPAGENUMBER": _desc_setpagenumber,
    "CACHE":         _desc_cache,
    "MM":            _desc_mm_unit,
}


# ---------------------------------------------------------------------------
# RPE array annotation
# ---------------------------------------------------------------------------

def _annotate_rpe_array(tok: str) -> str:
    """
    Annotate a JDT RPE array token of the form:
        [align justify X DX Y DY START LEN FONT COLOR]
    or with an embedded literal string instead of START/LEN:
        [align justify X DX Y DY 0 (LITERAL TEXT) FONT COLOR]
    """
    inner = tok[1:-1].strip()

    # Check for an embedded string literal
    str_match = re.search(r"\(([^)]+)\)", inner)
    if str_match:
        literal = str_match.group(1)
        if len(literal) > 25:
            literal = literal[:22] + "..."
        suffix_parts = inner[str_match.end():].split()
        font = _strip_slash(suffix_parts[-2]) if len(suffix_parts) >= 2 else ""
        color = suffix_parts[-1] if suffix_parts else ""
        font_part = f", font {font}" if font else ""
        return f'RPE: print literal "{literal}"{font_part}, {color}'

    # Standard numeric entry
    parts = inner.split()
    if len(parts) >= 10:
        align_map = {"0": "left", "1": "right", "2": "center"}
        align  = align_map.get(parts[0], parts[0])
        x, dx  = parts[2], parts[3]
        y, dy  = parts[4], parts[5]
        start  = parts[6]
        length = parts[7]
        font   = _strip_slash(parts[8])
        color  = parts[9]
        try:
            s     = int(start)
            l     = int(length)
            x_str = str(int(x) + int(dx)) if dx != "0" else str(int(x))
            y_str = str(int(y) + int(dy)) if dy != "0" else str(int(y))
            end   = s + l - 1
            return (
                f"RPE: chars {s}–{end}, {align}-aligned "
                f"at ({x_str},{y_str}), font {font}, {color}"
            )
        except ValueError:
            pass

    # Minimal fallback
    tail = inner.rsplit(None, 2)
    if len(tail) >= 3:
        font  = _strip_slash(tail[-2]) if tail[-2].startswith("/") else ""
        color = tail[-1]
        return f"RPE output entry, font {font}, {color}"
    return "RPE output entry"


# ---------------------------------------------------------------------------
# Main per-line annotation function
# ---------------------------------------------------------------------------

def _annotate_line(stripped: str) -> str:
    """
    Return a short English description of a single VIPP source line.
    Returns '' if the line is a comment, blank, or unrecognised.
    """
    if not stripped or stripped.startswith("%"):
        return ""

    tokens = _tokenize(stripped)
    if not tokens:
        return ""

    # --- RPE array entry: entire line is a [...] token ---
    if len(tokens) == 1 and tokens[0].startswith("["):
        return _annotate_rpe_array(tokens[0])

    # --- Prefix dispatch: first token is the command ---
    first_up = tokens[0].upper()
    if first_up in _PREFIX_DISPATCH:
        return _PREFIX_DISPATCH[first_up](tokens[1:], tokens, tokens[0])

    # Handle } which may have trailing tokens like } ELSE { or } BEGINPAGE
    if tokens[0] == "}":
        return _desc_close_brace(tokens[1:], tokens, "}")

    # --- Suffix dispatch: scan right-to-left for the command ---
    for i in range(len(tokens) - 1, -1, -1):
        tok_up = tokens[i].upper()
        if tok_up in _SUFFIX_DISPATCH:
            return _SUFFIX_DISPATCH[tok_up](tokens[:i], tokens, tokens[i])

    # --- Standalone font-alias invocation: F1, F7, FA, F12, PNFT … ---
    if len(tokens) == 1:
        t = tokens[0]
        # Short uppercase token that looks like a font alias
        if re.match(r"^[A-Z][A-Z0-9]{0,5}$", t):
            return f'Switch active font to "{t}"'

    return ""


# ---------------------------------------------------------------------------
# Annotation pass (runs on top of beautified output)
# ---------------------------------------------------------------------------

# Column at which inline % comments begin (padded with spaces if needed)
_COMMENT_COL = 52


def _has_inline_comment(line: str) -> bool:
    """
    Return True if an active code line already carries an inline % comment.
    e.g.  'PORT   % PORT - Portrait orientation'

    In PostScript/VIPP, % ALWAYS starts a comment — even inside [...] arrays.
    Only text inside (...) parenthesised strings is protected.
    """
    in_string = False
    for ch in line:
        if ch == "(" and not in_string:
            in_string = True
        elif ch == ")" and in_string:
            in_string = False
        elif ch == "%" and not in_string:
            return True
    return False


def annotate_vipp(source_text: str) -> str:
    """
    Beautify a VIPP source file and add natural-language inline comments.

    Processing steps:
      1. Apply xerox_beautifier.beautify_vipp() to strip commented-out code
         and normalise indentation.
      2. Walk each line of the cleaned output; for every active code line
         that does NOT already carry an inline comment, append a % comment
         with an English description of what the instruction does.
         Lines that already have an inline comment are left untouched —
         their existing comment is already informative.
    """
    cleaned = beautify_vipp(source_text)

    out_lines: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()

        # Leave blanks and pure comment lines untouched
        if not stripped or stripped.startswith("%"):
            out_lines.append(line)
            continue

        # If the line already has an inline comment, keep it as-is
        if _has_inline_comment(line):
            out_lines.append(line)
            continue

        annotation = _annotate_line(stripped)
        if annotation:
            padded = line.rstrip()
            # Align the comment to _COMMENT_COL, or add at least 2 spaces
            gap = max(_COMMENT_COL - len(padded), 2)
            out_lines.append(f"{padded}{' ' * gap}% {annotation}")
        else:
            out_lines.append(line)

    return "\n".join(out_lines) + "\n"


# ---------------------------------------------------------------------------
# File and directory processing
# ---------------------------------------------------------------------------

def process_file(src_path: Path, dest_path: Path) -> dict:
    """Annotate a single VIPP source file and write it to dest_path."""
    try:
        text = src_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"  ERROR: Cannot read {src_path}: {exc}", file=sys.stderr)
        return {"error": str(exc)}

    annotated = annotate_vipp(text)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(annotated, encoding="utf-8")

    return {
        "original_lines":  len(text.splitlines()),
        "annotated_lines": len(annotated.splitlines()),
    }


def process_directory(source_dir: Path, target_dir: Path) -> int:
    """
    Find all VIPP source files in source_dir and write annotated versions
    into target_dir, preserving the relative directory structure.
    Returns 0 on success, 1 if no files found.
    """
    source_dir = source_dir.resolve()
    target_dir = target_dir.resolve()

    vipp_files: list[Path] = []
    for ext in VIPP_EXTENSIONS:
        vipp_files.extend(source_dir.rglob(f"*{ext}"))
        vipp_files.extend(source_dir.rglob(f"*{ext.upper()}"))

    # Deduplicate (case-insensitive on Windows)
    seen: set[str] = set()
    unique: list[Path] = []
    for f in sorted(vipp_files):
        key = str(f).lower()
        if key not in seen:
            seen.add(key)
            unique.append(f)

    if not unique:
        print(f"No VIPP files (.dbm/.frm/.jdt) found in: {source_dir}")
        return 1

    print(f"Found {len(unique)} VIPP file(s) in: {source_dir}")
    print(f"Output directory: {target_dir}")
    print()
    target_dir.mkdir(parents=True, exist_ok=True)

    for src_path in unique:
        rel       = src_path.relative_to(source_dir)
        dest_path = target_dir / rel
        print(f"  {rel.name:<40s}", end="")
        stats = process_file(src_path, dest_path)
        if "error" in stats:
            print(f"  ERROR: {stats['error']}")
        else:
            orig = stats["original_lines"]
            ann  = stats["annotated_lines"]
            print(f"  {orig:>5d} -> {ann:>5d} lines")

    print()
    print("Done.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="xerox_annotator",
        description=(
            "Beautify + annotate Xerox FreeFlow VIPP source files (DBM/FRM/JDT).\n"
            "Removes commented-out dead code, normalises indentation, and adds\n"
            "a natural-language comment after every active instruction so that\n"
            "non-Xerox experts can read and understand the code."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "source",
        metavar="SOURCE",
        help="Source directory containing VIPP files (.dbm/.frm/.jdt)",
    )
    p.add_argument(
        "--output", "-o",
        required=True,
        metavar="PATH",
        help="Output directory for annotated files",
    )
    return p


def main() -> int:
    args = _build_parser().parse_args()
    src = Path(args.source)
    tgt = Path(args.output)

    if not src.is_dir():
        print(f"ERROR: Source directory not found: {src}", file=sys.stderr)
        return 1

    return process_directory(src, tgt)


if __name__ == "__main__":
    sys.exit(main())

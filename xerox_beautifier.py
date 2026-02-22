#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xerox_beautifier.py
===================
Beautifies Xerox FreeFlow VIPP source files (DBM, FRM, JDT) by:

1. Removing commented-out code while preserving meaningful comments
2. Normalizing indentation (tabs -> spaces, consistent nesting)
3. Removing trailing whitespace and excess blank lines

Comment Classification
----------------------
- KEEP ALWAYS: %! and %% header lines (PostScript DSC headers)
- KEEP: Section comments like "% Define Font Indexing" that precede active code
- REMOVE: Commented-out code lines (e.g. "%  08 12 193 268 S1 DRAWB")
- REMOVE: Comment-only headers that are followed only by more commented-out code

The key heuristic: a comment line is "commented-out code" if stripping the
leading % reveals something that looks like VIPP code (MOVETO, SH, DRAWB, etc.)
or numeric coordinates.  A comment is a "section header" if it's short, uses
title-case words, and is followed (within a few lines) by active code.

Usage
-----
    py -3 xerox_beautifier.py <source_dir> --output <target_dir>

    <source_dir>  : folder containing .dbm/.frm/.jdt files
    <target_dir>  : folder where beautified files are written
"""

import argparse
import os
import re
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# VIPP code detection patterns
# ---------------------------------------------------------------------------

# Commands that indicate a line is VIPP code (not a human comment)
VIPP_CODE_COMMANDS = {
    # Text output
    'SH', 'SHL', 'SHR', 'SHr', 'SHC', 'SHP',
    # Positioning
    'MOVETO', 'MOVEH', 'MOVEHR', 'NL',
    # Drawing
    'DRAWB', 'DRAWL', 'SCALL', 'ICALL',
    # Variables
    'SETVAR', 'VSUB',
    # Control flow
    'ENDIF', 'ENDFOR', 'ENDCASE',
    # Layout
    'SETFORM', 'SETLKF', 'SETPAGEDEF', 'SETFTSW',
    'SETLSP', 'SETUNIT', 'SETMARGIN', 'SETGRID',
    'SETMAXFORM', 'SETPCC', 'SETVFU', 'SETFONT',
    'SETPAGENUMBER',
    # Font/color indexing
    'INDEXFONT', 'INDEXCOLOR', 'INDEXBAT',
    # Page control
    'PAGEBRK', 'NEWFRAME', 'SKIPPAGE', 'BEGINPAGE', 'ENDPAGE',
    # Image / clip
    'CLIP', 'ENDCLIP',
    # Other
    'XGFRESDEF', 'SETRCD', 'BOOKMARK',
    'GETINTV', 'FORMAT', 'GETITEM',
    # Operators
    'SETPARAMS', 'EXTRACTALL',
}

# Regex to detect lines that look like commented-out code
# Matches: %<optional_spaces><number> or %<optional_spaces>( or %<optional_spaces>/
_RE_COMMENTED_CODE_COORD = re.compile(
    r'^%\s*\d+\.?\d*\s+\d+'  # e.g. %12 14 MOVETO or %08 12 193 268
)
_RE_COMMENTED_CODE_PAREN = re.compile(
    r'^%\s*\('  # e.g. %(OCBC-LOGO.TIF) 0.16 0 ICALL
)
_RE_COMMENTED_CODE_SLASH = re.compile(
    r'^%\s*/\w+'  # e.g. %/IF_CND36 ... SETRCD
)
_RE_COMMENTED_CODE_VAR = re.compile(
    r'^%\s*(?:VAR_|FLD\d|PREFIX|CPCOUNT)'  # e.g. %VAR_HMD  180  0  SHP
)
_RE_COMMENTED_CODE_COMMAND = re.compile(
    r'^%\s*(?:' + '|'.join(re.escape(c) for c in [
        'DUPLEX', 'PAGEBRK', 'NL', 'NEWFRAME', 'SKIPPAGE',
        'ELSE', 'ENDIF', 'ENDFOR', 'IF ', 'FOR ',
    ]) + ')',
    re.IGNORECASE,
)

# DSC header lines that are always preserved
_RE_DSC_HEADER = re.compile(r'^%[!%]')

# Separator lines: % followed by mostly dashes, equals, or underscores
_RE_SEPARATOR = re.compile(r'^%\s*[-=_]{4,}\s*$')


def _is_commented_out_code(line: str) -> bool:
    """
    Determine if a %-commented line is actually commented-out VIPP code
    rather than a human-readable comment.
    """
    stripped = line.strip()
    if not stripped.startswith('%'):
        return False

    # DSC headers are never "commented-out code"
    if _RE_DSC_HEADER.match(stripped):
        return False

    # Separator lines (% ----) are formatting, not code
    if _RE_SEPARATOR.match(stripped):
        return False

    # Check the content after the %
    content = stripped.lstrip('%').strip()
    if not content:
        return False  # bare % is just a blank comment

    # Coordinate patterns: %12 14 MOVETO, %08 12 193 268 S1 DRAWB
    if _RE_COMMENTED_CODE_COORD.match(stripped):
        return True

    # Parenthesized string calls: %(OCBC-LOGO.TIF) 0.16 0 ICALL
    if _RE_COMMENTED_CODE_PAREN.match(stripped):
        return True

    # Variable/name definitions: %/IF_CND36 ... SETRCD
    if _RE_COMMENTED_CODE_SLASH.match(stripped):
        return True

    # Variable references: %VAR_HMD 180 0 SHP
    if _RE_COMMENTED_CODE_VAR.match(stripped):
        return True

    # Known command keywords at start
    if _RE_COMMENTED_CODE_COMMAND.match(stripped):
        return True

    # Check if line contains a VIPP command keyword
    tokens = content.split()
    for token in tokens:
        clean = token.strip('(){}[].,;:')
        if clean.upper() in VIPP_CODE_COMMANDS:
            return True

    # Lines with "ori" prefix (original/old version markers)
    if content.startswith('ori'):
        return True

    # Single letter/token lines that look like font switches: %B, %R, %F6
    if re.match(r'^[A-Z]\d?$', content) or re.match(r'^F\d+$', content):
        return True

    return False


def _is_section_comment(line: str) -> bool:
    """
    Determine if a comment line is a meaningful section header/description.
    These are short, human-readable, and typically use title-case.

    Examples that should return True:
        % Define Font Indexing
        % HEADER
        % Insert Company Logo
        % Process PREFIX (CASE starts here)
        % change request 29.06.2015 by Lian

    Examples that should return False:
        %  08 12 193 268 S1 DRAWB
        %(OCBC-LOGO.TIF) CACHE 0.14 0 SCALL
    """
    stripped = line.strip()
    if not stripped.startswith('%'):
        return False
    if _RE_DSC_HEADER.match(stripped):
        return True  # DSC headers are always meaningful

    content = stripped.lstrip('%').strip()
    if not content:
        return False

    # If it looks like code, it's not a section comment
    if _is_commented_out_code(line):
        return False

    return True


def _is_active_code(line: str) -> bool:
    """Return True if the line is active (non-comment, non-blank) VIPP code."""
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith('%'):
        return False
    return True


# ---------------------------------------------------------------------------
# Indentation / nesting tracking
# ---------------------------------------------------------------------------

# Tokens that increase nesting level
_INDENT_OPEN = {'{', 'IF', 'CASE'}
# Tokens that decrease nesting level
_INDENT_CLOSE = {'}', 'ENDIF', 'ENDCASE', 'ENDFOR'}
# Tokens that temporarily reduce indent (like ELSE between IF/ENDIF)
_INDENT_DEDENT_THEN_INDENT = {'ELSE'}

INDENT_UNIT = '    '  # 4 spaces


def _compute_indent_level(line: str, current_level: int) -> tuple[int, int]:
    """
    Given a line and the current indentation level, return:
    (indent_for_this_line, indent_for_next_line)

    This is a simplified approach that tracks { } and IF/ENDIF nesting.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith('%'):
        return current_level, current_level

    # Count openers and closers in the line
    tokens = stripped.split()

    # Check for close-before-open patterns
    starts_with_close = False
    if tokens:
        first = tokens[0].strip('()')
        if first in _INDENT_CLOSE or first in _INDENT_DEDENT_THEN_INDENT:
            starts_with_close = True

    # Also check if line starts with } (common in VIPP)
    if stripped.startswith('}') or stripped.startswith('ELSE') or stripped.startswith('ENDIF') or stripped.startswith('ENDCASE') or stripped.startswith('ENDFOR'):
        starts_with_close = True

    # Indent for this line: if it starts with a closer, dedent first
    this_level = max(0, current_level - 1) if starts_with_close else current_level

    # Count net brace changes for next line
    open_count = stripped.count('{')
    close_count = stripped.count('}')

    # Also count IF/ENDIF keywords (but only standalone, not inside strings)
    # Simple approach: just use braces for nesting since VIPP uses { }
    next_level = current_level + open_count - close_count

    # Special: if line has ELSE, we already dedented for this line,
    # but next line should be indented again
    if 'ELSE' in tokens and '{' not in stripped:
        next_level = this_level + 1

    next_level = max(0, next_level)

    return this_level, next_level


# ---------------------------------------------------------------------------
# Main beautifier logic
# ---------------------------------------------------------------------------

def beautify_vipp(source_text: str) -> str:
    """
    Beautify a VIPP source file:
    1. Remove commented-out code
    2. Keep meaningful comments (section headers, DSC headers)
    3. Remove orphan section comments (comments only followed by more comments)
    4. Normalize indentation
    5. Clean up excess blank lines
    """
    lines = source_text.splitlines()

    # ---------------------------------------------------------------
    # Pass 1: Classify each line
    # ---------------------------------------------------------------
    # Classification: 'active', 'comment_code', 'comment_section',
    #                 'dsc_header', 'separator', 'blank'
    classified: list[tuple[str, str]] = []  # (line, classification)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            classified.append((line, 'blank'))
        elif _RE_DSC_HEADER.match(stripped):
            classified.append((line, 'dsc_header'))
        elif _RE_SEPARATOR.match(stripped):
            classified.append((line, 'separator'))
        elif stripped.startswith('%'):
            if _is_commented_out_code(line):
                classified.append((line, 'comment_code'))
            else:
                classified.append((line, 'comment_section'))
        else:
            classified.append((line, 'active'))

    # ---------------------------------------------------------------
    # Pass 2: Determine which section comments to keep
    # A section comment is kept only if it is followed (within a
    # reasonable window) by active code, not just by more comments
    # or commented-out code.
    # ---------------------------------------------------------------
    n = len(classified)
    keep = [False] * n

    for i in range(n):
        _line, cls = classified[i]
        if cls == 'active':
            keep[i] = True
        elif cls == 'dsc_header':
            keep[i] = True
        elif cls == 'blank':
            keep[i] = True  # blanks are kept initially, cleaned up later
        elif cls == 'separator':
            # Keep separators only if they are near active code
            # Look forward for active code within 3 lines
            has_active_nearby = False
            for j in range(i + 1, min(i + 4, n)):
                if classified[j][1] == 'active':
                    has_active_nearby = True
                    break
            # Also look backward
            if not has_active_nearby:
                for j in range(max(0, i - 2), i):
                    if classified[j][1] == 'active':
                        has_active_nearby = True
                        break
            keep[i] = has_active_nearby
        elif cls == 'comment_section':
            # Orphan detection: conceptually remove comment_code lines,
            # then check what the next non-blank line is. A section
            # comment is kept only if the next meaningful line is active
            # code or a DSC header. If it's another section comment,
            # this one is an orphan (its code was all commented-out).
            has_active_after = False
            for j in range(i + 1, n):
                jcls = classified[j][1]
                if jcls in ('blank', 'comment_code', 'separator'):
                    continue  # skip blanks, removed code, separators
                elif jcls in ('active', 'dsc_header'):
                    has_active_after = True
                    break
                else:
                    # Next meaningful line is another section comment
                    break
            keep[i] = has_active_after
        elif cls == 'comment_code':
            keep[i] = False  # always remove commented-out code

    # ---------------------------------------------------------------
    # Pass 3: Build the output with proper indentation
    # ---------------------------------------------------------------
    output_lines: list[str] = []
    indent_level = 0

    for i in range(n):
        if not keep[i]:
            continue

        line, cls = classified[i]
        stripped = line.strip()

        if cls == 'blank':
            output_lines.append('')
            continue

        if cls in ('dsc_header',):
            # DSC headers: no indentation, preserve as-is
            output_lines.append(stripped)
            indent_level_for_line = 0
            # Don't change indent level for headers
            continue

        if cls == 'separator':
            # Separators get current indentation
            output_lines.append(INDENT_UNIT * indent_level + stripped)
            continue

        if cls == 'comment_section':
            # Section comments get current indentation
            output_lines.append(INDENT_UNIT * indent_level + stripped)
            continue

        # Active code: compute indentation
        this_level, next_level = _compute_indent_level(stripped, indent_level)
        output_lines.append(INDENT_UNIT * this_level + stripped)
        indent_level = next_level

    # ---------------------------------------------------------------
    # Pass 4: Clean up excess blank lines (max 1 consecutive)
    # ---------------------------------------------------------------
    cleaned: list[str] = []
    prev_blank = False
    for line in output_lines:
        is_blank = line.strip() == ''
        if is_blank:
            if prev_blank:
                continue  # skip consecutive blanks
            prev_blank = True
        else:
            prev_blank = False
        cleaned.append(line)

    # Remove leading/trailing blank lines
    while cleaned and cleaned[0].strip() == '':
        cleaned.pop(0)
    while cleaned and cleaned[-1].strip() == '':
        cleaned.pop()

    return '\n'.join(cleaned) + '\n'


# ---------------------------------------------------------------------------
# File processing
# ---------------------------------------------------------------------------

VIPP_EXTENSIONS = {'.dbm', '.frm', '.jdt'}


def process_file(src_path: Path, dest_path: Path) -> dict:
    """
    Beautify a single VIPP source file.
    Returns a stats dict with line counts.
    """
    try:
        text = src_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        print(f"  ERROR: Cannot read {src_path}: {e}", file=sys.stderr)
        return {'error': str(e)}

    original_lines = len(text.splitlines())
    beautified = beautify_vipp(text)
    beautified_lines = len(beautified.splitlines())

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(beautified, encoding='utf-8')

    return {
        'original_lines': original_lines,
        'beautified_lines': beautified_lines,
        'removed_lines': original_lines - beautified_lines,
    }


def process_directory(source_dir: Path, target_dir: Path) -> int:
    """
    Find all VIPP source files in source_dir and beautify them into target_dir.
    Returns 0 on success.
    """
    source_dir = source_dir.resolve()
    target_dir = target_dir.resolve()

    # Find all VIPP files recursively
    vipp_files = []
    for ext in VIPP_EXTENSIONS:
        vipp_files.extend(source_dir.rglob(f'*{ext}'))
        vipp_files.extend(source_dir.rglob(f'*{ext.upper()}'))

    # Deduplicate (case-insensitive on Windows)
    seen: set[str] = set()
    unique_files: list[Path] = []
    for f in sorted(vipp_files):
        key = str(f).lower()
        if key not in seen:
            seen.add(key)
            unique_files.append(f)

    if not unique_files:
        print(f"No VIPP source files (.dbm/.frm/.jdt) found in: {source_dir}")
        return 1

    print(f"Found {len(unique_files)} VIPP source file(s) in: {source_dir}")
    print(f"Output directory: {target_dir}")
    print()

    target_dir.mkdir(parents=True, exist_ok=True)

    total_original = 0
    total_beautified = 0

    for src_path in unique_files:
        # Preserve relative path structure
        rel = src_path.relative_to(source_dir)
        dest_path = target_dir / rel

        print(f"  {rel.name:<30s}", end='')
        stats = process_file(src_path, dest_path)

        if 'error' in stats:
            print(f"  ERROR: {stats['error']}")
        else:
            orig = stats['original_lines']
            beaut = stats['beautified_lines']
            removed = stats['removed_lines']
            pct = (removed / orig * 100) if orig > 0 else 0
            print(f"  {orig:>5d} -> {beaut:>5d} lines  ({removed:>4d} removed, {pct:.0f}%)")
            total_original += orig
            total_beautified += beaut

    total_removed = total_original - total_beautified
    pct = (total_removed / total_original * 100) if total_original > 0 else 0
    print()
    print(f"  {'TOTAL':<30s}  {total_original:>5d} -> {total_beautified:>5d} lines  ({total_removed:>4d} removed, {pct:.0f}%)")
    print()
    print("Done.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='xerox_beautifier',
        description=(
            'Beautify Xerox FreeFlow VIPP source files (DBM/FRM/JDT).\n'
            'Removes commented-out code, normalizes indentation, and\n'
            'preserves meaningful section comments and DSC headers.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'source',
        metavar='SOURCE',
        help='Source directory containing VIPP files (.dbm/.frm/.jdt)',
    )
    parser.add_argument(
        '--output', '-o',
        required=True,
        metavar='PATH',
        help='Output directory for beautified files',
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source_dir = Path(args.source)
    target_dir = Path(args.output)

    if not source_dir.is_dir():
        print(f"ERROR: Source directory not found: {source_dir}", file=sys.stderr)
        return 1

    return process_directory(source_dir, target_dir)


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_xerox_to_papyrus.py
===========================
Automates the migration of a Xerox FreeFlow project into a properly structured
Papyrus Designer project folder.

Workflow
--------
1. Parse the source Xerox folder (locate codes subfolder, data files, reference PDF).
2. Run the appropriate converter (universal_xerox_parser.py for DBM+FRM projects,
   xerox_jdt_dfa.py for JDT-based projects) to produce .dfa output file(s).
3. Create the full Papyrus Designer project folder structure (mirroring XeroxV1).
4. Copy generated DFA files, data files, resource files, and reference PDF into
   the correct sub-folders.
5. Generate three configuration files with all paths correctly substituted:
      <project_name>.prj   — project file (points to DFA + ppde.prf)
      DEFAULT.LBP          — library profile (resource paths)
      ppde.prf             — DocEXEC environment profile

Usage
-----
    py -3 migrate_xerox_to_papyrus.py \\
        --source  "C:\\...\\SIBS_CAST" \\
        --output  "C:\\ISIS\\samples_pdd\\MyProject" \\
        --project-name MyProject

Optional:
    --codes-subfolder "SIBS_CAST - codes"   (auto-detected when omitted)
    --converter  universal | jdt            (auto-detected when omitted)
    --verbose                               (show converter stdout/stderr)
"""

import argparse
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Ghostscript integration — PS→PDF and EPS→JPG conversion
# ---------------------------------------------------------------------------

# Candidate Ghostscript executables tried in order.
_GS_CANDIDATES = [
    r"C:\Program Files\gs\gs*\bin\gswin64c.exe",
    r"C:\Program Files (x86)\gs\gs*\bin\gswin32c.exe",
    "gswin64c",
    "gswin32c",
    "gs",
]


def _find_ghostscript() -> "str | None":
    """Return the first usable Ghostscript executable, or None if not found."""
    import glob as _glob
    for candidate in _GS_CANDIDATES:
        if "*" in candidate:
            for match in sorted(_glob.glob(candidate), reverse=True):
                p = Path(match)
                if p.exists():
                    return str(p)
        else:
            try:
                r = subprocess.run(
                    [candidate, "--version"],
                    capture_output=True, text=True, timeout=10,
                )
                if r.returncode == 0:
                    return candidate
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue
    return None


def _gs_convert(
    gs_cmd: str,
    device: str,
    extra_args: "list[str]",
    input_path: Path,
    output_path: Path,
) -> bool:
    """Run Ghostscript conversion. Returns True on success."""
    cmd = [
        gs_cmd,
        "-dNOPAUSE", "-dBATCH", "-dSAFER",
        f"-sDEVICE={device}",
        f"-sOutputFile={output_path}",
    ] + extra_args + [str(input_path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return r.returncode == 0 and output_path.exists()
    except (subprocess.TimeoutExpired, OSError):
        return False


# ---------------------------------------------------------------------------
# Constants — sub-folder names that make up a Papyrus Designer project
# ---------------------------------------------------------------------------

# These folder names are taken directly from the XeroxV1 reference project.
# Each entry is (folder_name, description_for_report).
PROJECT_FOLDERS = [
    ("docdef",    "DFA source files and .prj project file"),
    ("userisis",  "Profile files (ppde.prf, DEFAULT.LBP)"),
    ("data",      "Input data files"),
    ("afpds",     "AFP / PDF output files (initially empty)"),
    ("jpeg",      "JPEG image resources"),
    ("tiff",      "TIFF image resources"),
    ("png",       "PNG image resources"),
    ("pseg",      "Page segments (240 / 300 / 600 dpi)"),
    ("ttf",       "TrueType font files"),
    ("fonts240",  "AFP bitmap fonts at 240 dpi"),
    ("fonts300",  "AFP bitmap fonts at 300 dpi"),
    ("fonts600",  "AFP bitmap fonts at 600 dpi"),
    ("fontsoln",  "Outline fonts"),
    ("ovl240",    "AFP overlays at 240 dpi"),
    ("ovl300",    "AFP overlays at 300 dpi"),
    ("ovl600",    "AFP overlays at 600 dpi"),
    ("fdf_pdf",   "FDF / PDF form resources"),
    ("object",    "ICC colour profile objects"),
    ("pdf",       "PDF object resources"),
    ("imported",  "XSD / imported schema files"),
    ("reference", "Original source PDF for visual comparison"),
]

# Folders that contain shared resources and may live in a central location
# when --resources-dir is supplied.  All other folders always go under the
# project root (docdef, userisis, data, afpds, reference, imported).
SHARED_RESOURCE_FOLDERS = {
    "ttf", "jpeg", "tiff", "png", "pseg",
    "fonts240", "fonts300", "fonts600", "fontsoln",
    "ovl240", "ovl300", "ovl600",
    "fdf_pdf", "object", "pdf",
}

# Windows font directories.
# System-wide fonts (requires admin to install):
WINDOWS_FONTS_DIR = Path("C:/Windows/Fonts")
# Per-user fonts (Windows 10/11 — no admin needed, used when fonts are
# installed via Settings > Fonts > "Install for me only"):
WINDOWS_USER_FONTS_DIR = Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts"

# Mapping from the font face name used in DFA  FONT ... AS '<face>'
# to the standard Windows TTF filename(s) for that face.
# Keys are lower-cased; values are lists of candidate filenames.
FONT_FACE_TO_TTF: dict[str, list[str]] = {
    # Arial family
    "arial":                     ["arial.ttf"],
    "arial bold":                ["arialbd.ttf"],
    "arial italic":              ["ariali.ttf"],
    "arial bold italic":         ["arialbi.ttf"],
    "arial narrow":              ["ARIALN.TTF"],
    "arial narrow bold":         ["ARIALNB.TTF"],
    "arial narrow italic":       ["ARIALNI.TTF"],
    "arial narrow bold italic":  ["ARIALNBI.TTF"],
    # Courier New family
    "courier new":               ["cour.ttf"],
    "courier new bold":          ["courbd.ttf"],
    "courier new italic":        ["couri.ttf"],
    "courier new bold italic":   ["courbi.ttf"],
    # Times New Roman
    "times new roman":           ["times.ttf"],
    "times new roman bold":      ["timesbd.ttf"],
    "times new roman italic":    ["timesi.ttf"],
    "times new roman bold italic": ["timesbi.ttf"],
    # Verdana
    "verdana":                   ["verdana.ttf"],
    "verdana bold":              ["verdanab.ttf"],
    "verdana italic":            ["verdanai.ttf"],
    "verdana bold italic":       ["verdanaz.ttf"],
    # Tahoma
    "tahoma":                    ["tahoma.ttf"],
    "tahoma bold":               ["tahomabd.ttf"],
    # Calibri
    "calibri":                   ["calibri.ttf"],
    "calibri bold":              ["calibrib.ttf"],
    "calibri italic":            ["calibrii.ttf"],
    "calibri bold italic":       ["calibriz.ttf"],
    # Trebuchet MS
    "trebuchet ms":              ["trebuc.ttf"],
    "trebuchet ms bold":         ["trebucbd.ttf"],
    "trebuchet ms italic":       ["trebucit.ttf"],
    "trebuchet ms bold italic":  ["trebucbi.ttf"],
    # Georgia
    "georgia":                   ["georgia.ttf"],
    "georgia bold":              ["georgiab.ttf"],
    "georgia italic":            ["georgiai.ttf"],
    "georgia bold italic":       ["georgiaz.ttf"],
    # Lucida
    "lucida console":            ["lucon.ttf"],
    "lucida sans unicode":       ["l_10646.ttf"],
    # Palatino Linotype
    "palatino linotype":         ["pala.ttf"],
    "palatino linotype bold":    ["palab.ttf"],
    "palatino linotype italic":  ["palai.ttf"],
    "palatino linotype bold italic": ["palabi.ttf"],
    # Misc
    "symbol":                    ["symbol.ttf"],
    "wingdings":                 ["wingding.ttf"],
    "comic sans ms":             ["comic.ttf"],
    "comic sans ms bold":        ["comicbd.ttf"],
    "impact":                    ["impact.ttf"],
    # Helvetica family — used by Xerox printer-resident aliases NHE/NHEB/NHEBO.
    # Helvetica is not a standard Windows system font but may be present when
    # Adobe Acrobat / Creative Suite is installed, or shipped with the project.
    # Candidates are tried in order: project-supplied → Adobe install → fallback.
    # Helvetica is a commercial font — not in standard Windows Fonts.
    # Candidates tried in order: project-supplied → Adobe install → Arial fallback.
    # Arial ships with every Windows installation and is metrically very close
    # to Helvetica, so it is used as a guaranteed last-resort substitute.
    "helvetica": [
        "helvetica.ttf",               # project-supplied (e.g. FIN886 codes folder)
        "Helvetica.ttf",               # Adobe Acrobat / Creative Suite install
        "HelveticaNeue.ttf",           # Helvetica Neue variant
        "HelveticaNeueLTStd-Roman.ttf",
        "Helvetica-Regular.ttf",
        "arial.ttf",                   # Windows fallback (metrically equivalent)
    ],
    "helvetica bold": [
        "helvetica-bold.ttf",          # project-supplied
        "helveticab.ttf",
        "Helvetica-Bold.ttf",          # Adobe install
        "HelveticaNeue-Bold.ttf",
        "HelveticaNeueLTStd-Bold.ttf",
        "arialbd.ttf",                 # Windows fallback
    ],
    "helvetica bold italic": [
        "helveticabo.ttf",             # project-supplied
        "Helvetica-BoldOblique.ttf",   # Adobe naming
        "HelveticaNeue-BoldItalic.ttf",
        "arialbi.ttf",                 # Windows fallback
    ],
    # Stone Sans Bold — Xerox proprietary printer-resident font (alias SBT).
    # No standard TTF substitute is known; place the font file manually in \ttf\.
    # Listed here so the migrate report names it explicitly rather than
    # emitting the generic "no known TTF mapping" warning.
    "stone sans bold":           ["stonesansbd.ttf", "stoneb.ttf"],
}

# Extensions that belong in each resource sub-folder.
# Used when copying files from the Xerox codes subfolder.
RESOURCE_FOLDER_MAP = {
    ".jpg":  "jpeg",
    ".jpeg": "jpeg",
    ".tif":  "tiff",
    ".tiff": "tiff",
    ".png":  "png",
    ".eps":  "pseg",   # EPS segments placed here for page-segment use
    ".240":  "pseg",
    ".300":  "pseg",
    ".600":  "pseg",
    ".ttf":  "ttf",
    ".otf":  "ttf",
    ".pdf":  "fdf_pdf",
    ".fdf":  "fdf_pdf",
    ".icc":  "object",
    ".icm":  "object",
}

# Extensions considered data / input files (stay in \data)
DATA_EXTENSIONS = {".txt", ".dat", ".csv", ".tsv", ".xml", ".json"}

# Extensions considered Xerox source code — we do NOT copy these into the
# Papyrus project; they are only inputs to the converter.
XEROX_SOURCE_EXTENSIONS = {".dbm", ".frm", ".jdt", ".max", ".vippvar"}

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

class MigrationReport:
    """Accumulates and prints a structured summary of what the migrator did."""

    def __init__(self, project_name: str, output_root: Path):
        self.project_name = project_name
        self.output_root  = output_root
        self._sections: list[tuple[str, list[str]]] = []
        self._current_section: str = ""
        self._current_items:  list[str] = []
        self._warnings: list[str] = []

    def section(self, title: str) -> None:
        """Start a new named section in the report."""
        if self._current_section:
            self._sections.append((self._current_section, list(self._current_items)))
            self._current_items.clear()
        self._current_section = title

    def item(self, msg: str) -> None:
        self._current_items.append(msg)

    def warn(self, msg: str) -> None:
        self._warnings.append(msg)
        print(f"  [WARN] {msg}", flush=True)

    def _flush(self) -> None:
        if self._current_section:
            self._sections.append((self._current_section, list(self._current_items)))
            self._current_items.clear()
            self._current_section = ""

    def print_summary(self) -> None:
        self._flush()
        width = 70
        print()
        print("=" * width)
        print(f"  Migration Report — {self.project_name}")
        print(f"  Output: {self.output_root}")
        print(f"  Date  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * width)
        for title, items in self._sections:
            print(f"\n  {title}")
            print(f"  {'-' * (len(title) + 2)}")
            if items:
                for item in items:
                    print(f"    {item}")
            else:
                print("    (nothing)")
        if self._warnings:
            print(f"\n  WARNINGS ({len(self._warnings)})")
            print(f"  ----------")
            for w in self._warnings:
                print(f"    {w}")
        print()
        print("=" * width)
        print()


def _find_python() -> str:
    """Return a usable Python interpreter command string."""
    # Prefer 'py -3' launcher (Windows), fall back to 'python3' / 'python'.
    for cmd in ("py -3", "python3", "python"):
        try:
            result = subprocess.run(
                cmd.split() + ["--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    raise RuntimeError(
        "No Python interpreter found. "
        "Ensure 'py', 'python3', or 'python' is on PATH."
    )


def _run_converter(
    python_cmd: str,
    script_path: Path,
    input_path: Path,
    output_dir: Path,
    extra_args: list[str],
    verbose: bool,
) -> subprocess.CompletedProcess:
    """
    Invoke a converter script as a subprocess.

    Parameters
    ----------
    python_cmd  : interpreter command string (e.g. 'py -3')
    script_path : absolute path to the .py converter script
    input_path  : path passed as the positional 'input_path' argument
    output_dir  : directory where the converter should write DFA files
    extra_args  : any additional CLI flags for the converter
    verbose     : if True, stream converter output to stdout

    Returns
    -------
    CompletedProcess instance (caller checks returncode)
    """
    cmd = python_cmd.split() + [
        str(script_path),
        str(input_path),
        "--output_dir", str(output_dir),
    ] + extra_args

    print(f"  Running: {' '.join(cmd)}", flush=True)

    if verbose:
        result = subprocess.run(cmd, text=True)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            # Always print INFO-level lines even in non-verbose mode
            for line in result.stdout.splitlines():
                if "INFO" in line or "ERROR" in line or "WARNING" in line:
                    print(f"    {line}", flush=True)
        if result.returncode != 0 and result.stderr.strip():
            print(result.stderr[-2000:], flush=True)

    return result


# ---------------------------------------------------------------------------
# Source-folder analysis
# ---------------------------------------------------------------------------

def find_codes_subfolder(source_dir: Path, hint: str | None) -> Path | None:
    """
    Locate the subfolder that contains the Xerox source code files
    (DBM, FRM, JDT, resource files).

    Strategy
    --------
    1. If --codes-subfolder was supplied, use it directly.
    2. Else look for any direct child folder whose name contains 'code'
       (case-insensitive) and that contains at least one .dbm/.frm/.jdt file.
    3. Else fall back to the source_dir itself if it contains such files.
    """
    if hint:
        candidate = source_dir / hint
        if candidate.is_dir():
            return candidate
        # Maybe the hint is an absolute path
        candidate = Path(hint)
        if candidate.is_dir():
            return candidate
        return None

    xerox_exts = {".dbm", ".frm", ".jdt"}

    # Search immediate children
    for child in source_dir.iterdir():
        if child.is_dir() and "code" in child.name.lower():
            has_xerox = any(
                f.suffix.lower() in xerox_exts for f in child.iterdir() if f.is_file()
            )
            if has_xerox:
                return child

    # Wider search: any child that contains DBM/FRM/JDT
    for child in source_dir.iterdir():
        if child.is_dir():
            has_xerox = any(
                f.suffix.lower() in xerox_exts for f in child.iterdir() if f.is_file()
            )
            if has_xerox:
                return child

    # Last resort: look in source_dir itself
    has_xerox = any(
        f.suffix.lower() in xerox_exts for f in source_dir.iterdir() if f.is_file()
    )
    if has_xerox:
        return source_dir

    return None


def find_data_files(source_dir: Path) -> list[Path]:
    """
    Return data files found directly in source_dir (not in subfolders).
    These are the input data files for DocEXEC.
    """
    return [
        f for f in source_dir.iterdir()
        if f.is_file() and f.suffix.lower() in DATA_EXTENSIONS
    ]


def find_reference_pdf(source_dir: Path) -> Path | None:
    """
    Return the first PDF in source_dir that looks like a reference / output sample.
    We prefer files whose name contains 'output' or 'reference'; otherwise the
    first PDF found.
    """
    pdfs = [
        f for f in source_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".pdf"
    ]
    for p in pdfs:
        if any(kw in p.name.lower() for kw in ("output", "reference", "sample", "ref")):
            return p
    return pdfs[0] if pdfs else None


def detect_converter(codes_dir: Path) -> str:
    """
    Decide which converter to use based on files present in the codes folder.
    Returns 'universal' (DBM+FRM) or 'jdt'.
    """
    files = list(codes_dir.iterdir())
    exts = {f.suffix.lower() for f in files if f.is_file()}
    if ".jdt" in exts and ".dbm" not in exts:
        return "jdt"
    return "universal"


def find_dbm_file(codes_dir: Path) -> Path | None:
    """Return the first .DBM file in the codes directory."""
    for f in codes_dir.iterdir():
        if f.is_file() and f.suffix.lower() == ".dbm":
            return f
    return None


# ---------------------------------------------------------------------------
# Font discovery helpers
# ---------------------------------------------------------------------------

# Regex that matches:  FONT <id> NOTDEF AS '<face name>' ...
_FONT_RE = re.compile(
    r"""FONT\s+\S+\s+NOTDEF\s+AS\s+'([^']+)'""",
    re.IGNORECASE,
)


def extract_font_faces_from_dfa(dfa_paths: list[Path]) -> set[str]:
    """
    Parse one or more DFA files and return the set of unique font face names
    referenced in FONT ... NOTDEF AS '<face>' declarations.

    Example DFA line:
        FONT ARIAL06 NOTDEF AS 'Arial' DBCS ROTATION 0 HEIGHT 6.0;
    Returns: {'Arial', 'Arial Bold', 'Courier New', ...}
    """
    faces: set[str] = set()
    for dfa_path in dfa_paths:
        try:
            text = dfa_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in _FONT_RE.finditer(text):
            faces.add(match.group(1).strip())
    return faces


def resolve_ttf_files(
    face_names: set[str],
    search_dirs: list[Path],
) -> tuple[dict[str, Path], list[str]]:
    """
    For each font face name, locate the corresponding TTF file.

    Parameters
    ----------
    face_names  : set of face names extracted from DFA files
    search_dirs : directories to search, tried in order

    Returns
    -------
    found   : {face_name: Path}  — face names that were resolved to a file
    missing : [face_name]        — face names for which no file was found
    """
    found:   dict[str, Path] = {}
    missing: list[str] = []

    for face in sorted(face_names):
        candidates = FONT_FACE_TO_TTF.get(face.lower(), [])
        if not candidates:
            missing.append(face)
            continue

        resolved: Path | None = None
        for search_dir in search_dirs:
            if not search_dir.is_dir():
                continue  # skip dirs that don't exist yet (e.g. empty \ttf\)
            for candidate in candidates:
                probe = search_dir / candidate
                if probe.exists():
                    resolved = probe
                    break
                # Try case-insensitive match (important on Windows/Linux)
                try:
                    for existing in search_dir.iterdir():
                        if existing.name.lower() == candidate.lower():
                            resolved = existing
                            break
                except OSError:
                    pass  # permission error or race — skip this dir
                if resolved:
                    break
            if resolved:
                break

        if resolved:
            found[face] = resolved
        else:
            missing.append(face)

    return found, missing


# ---------------------------------------------------------------------------
# Configuration file generators
# ---------------------------------------------------------------------------

def generate_prj(
    project_name: str,
    project_root: Path,
    dfa_filename: str,
    data_filename: str | None,
) -> str:
    """
    Generate the content of <project_name>.prj.

    The .prj file is the entry point for Papyrus Designer / DocEXEC.
    It specifies:
      JOBNAME    — label shown in the Designer UI
      DEPROF     — path to the ppde.prf environment profile
      DOCDEF     — path to the main DFA file
      LINEDATA   — path to the input data file
      OUTPUT     — path where AFP/PDF output will be written
      HSTSAVE    — history save path (empty = disabled)
      STICKERFILENAME — sticker index path (empty = disabled)
    """
    docdef_path    = project_root / "docdef" / dfa_filename
    deprof_path    = project_root / "userisis" / "ppde.prf"
    output_path    = project_root / "afpds" / f"{project_name}.afp"
    sticker_path   = project_root / "afpds" / "afpds"

    # If we know the data file, point to it; otherwise leave blank so the
    # user can fill it in.
    if data_filename:
        linedata_path = str(project_root / "data" / data_filename)
    else:
        linedata_path = str(project_root / "data" / "")

    lines = [
        f' JOBNAME="{project_name}"',
        f' DEPROF="{deprof_path}"',
        f' DOCDEF="{docdef_path}"',
        f' LINEDATA="{linedata_path}"',
        f' OUTPUT="{output_path}"',
        f' HSTSAVE=""',
        f' STICKERFILENAME="{sticker_path}"',
        "",
    ]
    return "\r\n".join(lines)


def generate_lbp(project_root: Path, resource_root: Path | None = None) -> str:
    """
    Generate the content of DEFAULT.LBP (library profile).

    The LBP tells DocEXEC where to search for each category of resource.
    Path tokens use the syntax:   CATEGORY="<path><EXT>"
    where <EXT> is the file extension filter inside angle brackets.

    Resource categories and their default sub-folder names are taken from
    the XeroxV1 reference project and the Day 1 training guide.

    Parameters
    ----------
    project_root  : root of the Papyrus project (docdef, userisis, data, etc.)
    resource_root : root for shared resource folders (ttf, jpeg, tiff, …).
                    When None (default), shared resources are under project_root.
    """
    p = project_root           # shorthand for project-only folders
    r = resource_root or project_root  # shorthand for shared resource folders

    # Helpers to build path entries.
    # Shared resource folders use `r`; project-only folders use `p`.
    def res(category: str, *folder_ext_pairs: tuple[str, str]) -> str:
        """LBP entry for a shared resource folder (may be in resource_root)."""
        paths = ",".join(
            f'"{r / folder}<{ext}>"' for folder, ext in folder_ext_pairs
        )
        return f" {category}={paths}"

    lines = [
        res("FON",    ("fonts240", "FON"), ("fontsoln", "fon")),
        res("CHS",    ("fonts240", "CHS"), ("fontsoln", "chs")),
        res("CDP",    ("fonts240", "CDP")),
        res("PSG",    ("pseg",     "240")),
        res("OVL",    ("ovl240",   "OVL")),
        res("FDF",    ("fdf_pdf",  "BIN")),
        res("PDF",    ("fdf_pdf",  "PDF")),
        res("TIF",    ("tiff",     "tif")),
        res("FON300", ("fonts300", "FON")),
        res("CHS300", ("fonts300", "CHS")),
        res("PSG300", ("pseg",     "300")),
        res("OVL300", ("ovl300",   "OVL")),
        res("FON600", ("fonts600", "FON")),
        res("CHS600", ("fonts600", "CHS")),
        res("PSG600", ("pseg",     "600")),
        res("OVL600", ("ovl600",   "OVL")),
        res("JPG",    ("jpeg",     "JPG")),
        res("PDFOBJ", ("pdf",      "pdf")),
        res("CMR",    ("object",   "icc")),
        res("PNG",    ("png",      "PNG")),
        # TTF: project resource folder first, then Windows system fonts
        f' TTF="{r / "ttf"}<ttf>,$SystemFont$"',
        "",
    ]
    return "\r\n".join(lines)


def generate_prf(
    project_name: str,
    project_root: Path,
    dfa_filename: str,
) -> str:
    """
    Generate the content of ppde.prf (DocEXEC environment profile).

    This is the most complex configuration file. It defines:
      - Group 1 : input/output directory paths
      - Group 2 : internal file locations (DFA, IMP, IDF, HTML libraries)
      - Group 2A: library profile reference (LBP)
      - Group 3 : DocEXEC parameters (trace, AFP type, etc.)
      - Group 4 : AFP output settings (resolution, record length, etc.)
      - Group 5 : default fonts
      - Group 6 : code pages

    The template is derived from XeroxV1/userisis/ppde.prf, with all hard-coded
    paths replaced by paths relative to project_root.

    Note: many settings (window positions, last-opened files, etc.) are
    Designer UI state that is irrelevant for a fresh project — they are
    omitted or blanked here and will be written by the Designer on first open.
    """
    p      = project_root
    lbp    = p / "userisis" / "DEFAULT.LBP"
    docdef = p / "docdef" / dfa_filename

    # Lines are grouped with inline comments for readability, matching the
    # structure described in the Day 1 training guide (pages 6–8).
    lines = [
        "* Group 1: input/output directories",
        f'DOCDEF=""',
        f'INPUT=""',
        f'HISTORY=""',
        f'HISTORYMODE=""',
        f'OUTPUT=""',
        f'LOG=""',
        f'CODEPAGES=""',
        f'RESNAME=""',
        f'NDXNAME=""',
        "",
        "* Group 2: internal file locations",
        f'DDEFLIB="{p / "docdef"}<DFA>"',
        f'DDFILIB="{p / "docdef"}<DFA>,{p / "docdef"}<INC>"',
        f'IDFTLIB="{p / "docdef"}<IMP>"',
        f'HTMLLIB="{p / "docdef"}"',
        f'IDFDLIB="{p / "docdef"}<IDF>"',
        "",
        "* Group 2A: Library Profile for resources",
        f'LIBPROF="{lbp}"',
        "",
        "* Group 2B: font profile (ini files — largely obsolete but kept for compatibility)",
        f'TFONPROF="textfon.ini"',
        f'CFONPROF="charfon.ini"',
        "",
        "* Group 3: DocEXEC parameters",
        f'TRACE="No"',
        f'WARNING="Y"',
        f'MAX_WARNING="-1"',
        f'MAX_ERROR="-1"',
        f'AFPIMPORTLIB=""',
        f'OUTPUTSYNTAX="No"',
        f'RENAMETARGET="No"',
        f'OUTPUTDEFINEPATH=""',
        f'LISTOUTPATH=""',
        "",
        "* Group 4: AFP Output definition",
        f'AFPTYPE="Pc"',
        f'AFPLRECL="8200"',
        f'SOURCERES="240"',
        f'TARGETRES="240"',
        f'PTXUNIT="240"',
        f'INTRES="1440"',
        f'FDFINCLUDE="No"',
        f'TIMESTAMP="No"',
        f'OBJCOUNT="No"',
        f'CPID="No"',
        f'TLECPID="No"',
        f'MDRGENERATE="No"',
        f'RESGROUP=""',
        f'TLE="No"',
        f'ACIFINDEX="No"',
        "",
        "* Group 5: Default Fonts",
        f'DEFFNT1="gt0a"',
        f'DEFFNT2="gt0a"',
        "",
        "* Group 6: Codepages",
        f'CODEOWN=""',
        f'CODESRC="1202"',
        f'CODEINP="437"',
        f'CODEIDF="273"',
        f'CODEFNT="273"',
        f'CODEMIX="-1"',
        "",
        "* Group 7: Spelling and Hyphenation",
        f'HYPHENATIONENGINE="Proximity"',
        f'SPELLCHECKENGINE="Proximity"',
        f'HYPHENLIB=""',
        f'HUNHYPHENLIB=""',
        f'USERDEFHYPHEN="No"',
        f'USEVERIFIEDHYPHENATION="No"',
        f'SPELLCHECKERPROF="pclsc.cfg"',
        f'HUNSPELLCHECKERPROF="hunspell.cfg"',
        f'SPELLLIB=""',
        f'HUNSPELLLIB=""',
        f'SPELLCHECKCOMPOUNDWORDS="Yes"',
        "",
        "* Compatibility and miscellaneous switches",
        f'S1PREFIX="Yes"',
        f'O1PREFIX="Yes"',
        f'CIPHERSTORE=""',
        f'PASSWORDVAULT=""',
        f'TXTDESCFNT="No"',
        f'GENERATESPACES="No"',
        f'SOSI="Yes"',
        f'CLEANCACHE=""',
        f'REPRESMSG="no"',
        f'DFACACHEMODE="Yes"',
        f'FORCEPDF="No"',
        f'FORCEWORD="No"',
        f'IDFCOMMENT=""',
        f'WRITERESOURCEGUIDS="No"',
        f'WRITERESOURCENAMES="No"',
        f'GRAMLANG="brt"',
        f'STICKERFILE=""',
        f'USESTICKERFILE="No"',
        f'STICKERGENERATE="Yes"',
        f'IGNORESTICKEROUTPUTDEFINITION="No"',
        f'PROMPTANNOTATION="No"',
        f'FLUSHOUTPUTPERPAGE="Yes"',
        f'DOUBLETEXTPOSITION="Yes"',
        f'IMAGECELL="Yes"',
        f'NEWLINEBREAKING="Yes"',
        f'GENERATETAGS="Yes"',
        f'TAGGEDAFPMODE="0"',
        f'V780_COMP_FIELDBREAK="Yes"',
        f'V791_COMP_TEXTDIVTAG="Yes"',
        f'SYSTEMATTRIBUTEDOLLAR="Yes"',
        f'ISISTEST_NOP="Yes"',
        f'UTF8INVARPROMPT="Yes"',
        f'TESTMODE="Outline"',
        f'TESTAREA=""',
        f'TESTPAGES="Random"',
        f'LANGUAGE="ENG"',
        "",
        "* Papyrus Designer paths (written by Designer on first open — pre-populated)",
        f'DOCJPATH="{p / "docdef"}\\"',
        f'DOCDPATH="{p / "docdef"}\\"',
        f'LINDPATH="{p / "data"}\\"',
        f'OUTPPATH="{p / "afpds"}\\"',
        f'CPTSPATH="C:\\Isis\\Cpts\\"',
        f'PPFAPATH="C:\\Isis\\fdf_pdf\\"',
        f'INCLPATH="C:\\Isis\\docdef<Inc>"',
        f'LIBRPROF="C:\\Isis\\userisis\\Default.Lbp"',
        f'DEPROF=""',
        "",
        "* XSD / imported schema library",
        f'XSDLIB="{p / "imported"}"',
        "",
    ]
    return "\r\n".join(lines)


# Path to the Papyrus DocEXEC executable — matches the reference bat file.
PDEW_EXE = r"C:\ISIS\samples_pdd\pdew6710\pdew6.exe"
ISIS_COMMON = r"C:\ISIS\samples_pdd\isiscomm"


def generate_docexec_bat(
    project_name: str,
    project_root: Path,
    prj_filename: str,
) -> str:
    """
    Generate a .bat file that runs Papyrus DocEXEC for this project.

    The script mirrors the environment setup in the reference
    'docexec - editor.bat', but:
      - CDs to the project's own userisis folder (not the shared one)
      - Points the .prj and log file at locations inside the project
      - Has no 'pause' at the end (suitable for automated use)

    The log is written to:
        <project_root>\\docdef\\<project_name>_docexec.log

    so the migration tool can pick it up automatically when --run-docexec
    is supplied.
    """
    prj_path = project_root / "docdef" / prj_filename
    log_path = project_root / "docdef" / f"{project_name}_docexec.log"
    userisis_dir = project_root / "userisis"

    lines = [
        "@echo off",
        f"set ISIS_COMMON={ISIS_COMMON}",
        r"set Path=%ISIS_COMMON%\w3\lib;%PATH%",
        "set ISIS_KEY_MODE=-",
        "set ISIS_OMS_DOMAIN=ATPRIMIPAS",
        "set ISIS_OMS_PORT=32003",
        "set ISIS_PCS_LOGMODE=M,S7,T3,OF,G0,C",
        "",
        f'CD /d "{userisis_dir}"',
        f'"{PDEW_EXE}" "{prj_path}" /FORCEPDF="YES" >"{log_path}" 2<&1',
        "",
    ]
    return "\r\n".join(lines)


# ---------------------------------------------------------------------------
# Main migration logic
# ---------------------------------------------------------------------------

def migrate(args: argparse.Namespace) -> int:
    """
    Execute the full migration pipeline.

    Returns 0 on success, non-zero on failure.
    """
    report = MigrationReport(args.project_name, Path(args.output))

    # ------------------------------------------------------------------
    # Step 1 — Validate inputs
    # ------------------------------------------------------------------
    report.section("Step 1: Input validation")

    source_dir = Path(args.source).resolve()
    output_root = Path(args.output).resolve()
    project_name = args.project_name

    if not source_dir.is_dir():
        print(f"ERROR: Source directory does not exist: {source_dir}", file=sys.stderr)
        return 1
    report.item(f"Source dir : {source_dir}")

    if output_root.exists() and any(output_root.iterdir()):
        if not args.force:
            print(
                f"ERROR: Output directory already exists and is not empty: {output_root}\n"
                f"       Use --force to overwrite.",
                file=sys.stderr,
            )
            return 1
        report.item(f"Output dir : {output_root}  [OVERWRITE — --force supplied]")
    else:
        report.item(f"Output dir : {output_root}  [will be created]")

    # Determine where shared resource folders live.
    # When --resources-dir is supplied, shared folders (ttf, jpeg, tiff, …)
    # are created there and DEFAULT.LBP will point to them.
    # Otherwise everything lives under the project root.
    if args.resources_dir:
        resource_root = Path(args.resources_dir).resolve()
        resource_root.mkdir(parents=True, exist_ok=True)
        report.item(f"Resources  : {resource_root}  [central shared location]")
    else:
        resource_root = output_root
        report.item(f"Resources  : (inside project folder)")

    # ------------------------------------------------------------------
    # Step 2 — Locate source components
    # ------------------------------------------------------------------
    report.section("Step 2: Source folder analysis")

    codes_dir = find_codes_subfolder(source_dir, args.codes_subfolder)
    if codes_dir is None:
        print(
            f"ERROR: Could not find a codes subfolder containing Xerox source files.\n"
            f"       Use --codes-subfolder to specify the folder name explicitly.",
            file=sys.stderr,
        )
        return 1
    report.item(f"Codes subfolder : {codes_dir.name}  ({codes_dir})")

    data_files = find_data_files(source_dir)
    if not data_files:
        report.warn("No data files found in the source directory root.")
    else:
        for df in data_files:
            report.item(f"Data file       : {df.name}")

    reference_pdf = find_reference_pdf(source_dir)
    if reference_pdf:
        report.item(f"Reference PDF   : {reference_pdf.name}")
    else:
        report.warn("No reference PDF found in source directory.")

    # Determine converter
    if args.converter:
        converter_choice = args.converter.lower()
    else:
        converter_choice = detect_converter(codes_dir)
    report.item(f"Converter       : {converter_choice}")

    # Resolve converter script path
    script_dir = Path(__file__).parent.resolve()
    if converter_choice == "jdt":
        converter_script = script_dir / "xerox_jdt_dfa.py"
    else:
        converter_script = script_dir / "universal_xerox_parser.py"

    if not converter_script.exists():
        print(
            f"ERROR: Converter script not found: {converter_script}",
            file=sys.stderr,
        )
        return 1
    report.item(f"Script path     : {converter_script}")

    # ------------------------------------------------------------------
    # Step 3 — Run the converter into a temporary staging directory
    # ------------------------------------------------------------------
    report.section("Step 3: DFA conversion")

    # Use a staging directory inside the output folder so that any partial
    # output is isolated from the final project layout.
    staging_dir = output_root / "_converter_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    python_cmd = _find_python()
    report.item(f"Python interpreter : {python_cmd}")

    # For --single_file mode we pass the DBM file; for directory mode we pass
    # the codes directory.  Using --single_file is preferred because it ensures
    # the converter picks up all FRM files in the same folder automatically.
    dbm_file = find_dbm_file(codes_dir)

    if dbm_file:
        # Single-file mode: point directly at the DBM
        conv_result = _run_converter(
            python_cmd       = python_cmd,
            script_path      = converter_script,
            input_path       = dbm_file,
            output_dir       = staging_dir,
            extra_args       = ["--single_file"],
            verbose          = args.verbose,
        )
        report.item(f"Converter input  : {dbm_file.name}  (single-file mode)")
    else:
        # Directory mode: pass the whole codes folder
        conv_result = _run_converter(
            python_cmd       = python_cmd,
            script_path      = converter_script,
            input_path       = codes_dir,
            output_dir       = staging_dir,
            extra_args       = [],
            verbose          = args.verbose,
        )
        report.item(f"Converter input  : {codes_dir}  (directory mode)")

    if conv_result.returncode != 0:
        print(
            f"ERROR: Converter exited with code {conv_result.returncode}.\n"
            f"       Run with --verbose for full output.",
            file=sys.stderr,
        )
        # Do not abort — partial DFA output may still be usable; we continue
        # with whatever was produced and warn the user.
        report.warn(
            f"Converter returned exit code {conv_result.returncode}. "
            "DFA output may be incomplete."
        )
    else:
        report.item("Converter completed successfully.")

    # Collect DFA files produced by the converter.
    # Deduplicate by lower-case name so Windows case-insensitive globbing
    # does not yield the same file twice (*.dfa and *.DFA).
    _seen: set[str] = set()
    dfa_files_produced: list[Path] = []
    for _dfa in sorted(staging_dir.glob("*.dfa")) + sorted(staging_dir.glob("*.DFA")):
        if _dfa.name.lower() not in _seen:
            _seen.add(_dfa.name.lower())
            dfa_files_produced.append(_dfa)
    if not dfa_files_produced:
        print(
            "ERROR: Converter produced no .dfa files in the staging directory.",
            file=sys.stderr,
        )
        return 1

    for dfa in dfa_files_produced:
        report.item(f"DFA produced     : {dfa.name}")

    # Identify the 'main' DFA (from the DBM, not an FRM).  Heuristic: the
    # file whose stem matches the DBM stem, or the shortest stem (usually the
    # DBM-derived one).
    if dbm_file:
        dbm_stem = dbm_file.stem.upper()
        main_dfa = next(
            (d for d in dfa_files_produced if d.stem.upper() == dbm_stem),
            dfa_files_produced[0]
        )
    else:
        # Fallback: pick the one without an 'F' suffix pattern
        non_frm = [d for d in dfa_files_produced if not d.stem.upper().endswith("F")]
        main_dfa = non_frm[0] if non_frm else dfa_files_produced[0]

    report.item(f"Main DFA         : {main_dfa.name}")

    # ------------------------------------------------------------------
    # Step 4 — Create the Papyrus Designer project folder structure
    # ------------------------------------------------------------------
    report.section("Step 4: Project folder structure")

    output_root.mkdir(parents=True, exist_ok=True)
    for folder_name, desc in PROJECT_FOLDERS:
        # Shared resource folders go to resource_root; everything else to output_root.
        folder_root = resource_root if folder_name in SHARED_RESOURCE_FOLDERS else output_root
        folder_path = folder_root / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        location = f"[{resource_root}]" if folder_root is not output_root else ""
        report.item(f"Created  \\{folder_name}\\  — {desc}  {location}".rstrip())

    # ------------------------------------------------------------------
    # Step 5 — Copy DFA files into \docdef\
    # ------------------------------------------------------------------
    report.section("Step 5: Copy DFA files")

    docdef_dir = output_root / "docdef"
    for dfa in dfa_files_produced:
        dest = docdef_dir / dfa.name
        shutil.copy2(dfa, dest)
        report.item(f"Copied {dfa.name}  ->  \\docdef\\{dfa.name}")

    # Clean up staging directory
    shutil.rmtree(staging_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Step 6 — Copy data files into \data\
    # ------------------------------------------------------------------
    report.section("Step 6: Copy data files")

    data_dir = output_root / "data"
    copied_data: list[str] = []
    for df in data_files:
        dest = data_dir / df.name
        shutil.copy2(df, dest)
        report.item(f"Copied {df.name}  ->  \\data\\{df.name}")
        copied_data.append(df.name)

    # The data file to reference in the .prj is the first one found, or None.
    prj_data_file = data_files[0].name if data_files else None

    # ------------------------------------------------------------------
    # Step 7 — Copy resource files from the codes subfolder
    # ------------------------------------------------------------------
    report.section("Step 7: Copy resource files")

    skip_extensions = XEROX_SOURCE_EXTENSIONS | {".db", ".bak", ".tmp", ".ps"}

    for resource_file in codes_dir.iterdir():
        if not resource_file.is_file():
            continue
        ext = resource_file.suffix.lower()
        if ext in skip_extensions:
            continue
        if ext == ".pdf":
            # PDFs in the codes folder are typically form resources, not data
            target_subfolder = "fdf_pdf"
        else:
            target_subfolder = RESOURCE_FOLDER_MAP.get(ext)

        if target_subfolder:
            # Shared resource folders may live in resource_root
            folder_root = resource_root if target_subfolder in SHARED_RESOURCE_FOLDERS else output_root
            dest = folder_root / target_subfolder / resource_file.name
            shutil.copy2(resource_file, dest)
            report.item(
                f"Copied {resource_file.name}  ->  \\{target_subfolder}\\{resource_file.name}"
            )
        else:
            report.warn(
                f"Unknown resource type '{resource_file.name}' (ext={ext}) — not copied. "
                f"Place manually into the appropriate sub-folder."
            )

    # ------------------------------------------------------------------
    # Step 7b — Convert PS→PDF and EPS→JPG using Ghostscript
    # ------------------------------------------------------------------
    report.section("Step 7b: Convert PS/EPS resources")

    gs_cmd = _find_ghostscript()
    if gs_cmd:
        report.item(f"Ghostscript: {gs_cmd}")
        pdf_out_dir  = output_root / "pdf"
        jpeg_out_dir = resource_root / "jpeg"

        for resource_file in sorted(codes_dir.iterdir()):
            if not resource_file.is_file():
                continue
            ext = resource_file.suffix.lower()

            if ext == ".ps":
                dest = pdf_out_dir / (resource_file.stem + ".pdf")
                ok = _gs_convert(
                    gs_cmd, "pdfwrite", [], resource_file, dest
                )
                if ok:
                    report.item(
                        f"Converted {resource_file.name}  ->  \\pdf\\{dest.name}"
                    )
                else:
                    report.warn(
                        f"PS→PDF conversion failed for {resource_file.name}  "
                        "(place {resource_file.stem}.pdf manually in \\pdf\\)"
                    )

            elif ext == ".eps":
                dest = jpeg_out_dir / (resource_file.stem + ".jpg")
                ok = _gs_convert(
                    gs_cmd, "jpeg",
                    ["-r150", "-dJPEGQ=90"],
                    resource_file, dest,
                )
                if ok:
                    report.item(
                        f"Converted {resource_file.name}  ->  \\jpeg\\{dest.name}"
                    )
                else:
                    report.warn(
                        f"EPS→JPG conversion failed for {resource_file.name}  "
                        f"(place {resource_file.stem}.jpg manually in \\jpeg\\)"
                    )
    else:
        report.warn(
            "Ghostscript not found — PS and EPS files not converted. "
            "Install from https://www.ghostscript.com (gswin64c) and re-run, "
            "or manually convert: .ps→.pdf into \\pdf\\ and .eps→.jpg into \\jpeg\\"
        )

    # ------------------------------------------------------------------
    # Step 8 — Copy reference PDF into \reference\
    # ------------------------------------------------------------------
    report.section("Step 8: Copy reference PDF")

    if reference_pdf:
        dest = output_root / "reference" / reference_pdf.name
        shutil.copy2(reference_pdf, dest)
        report.item(f"Copied {reference_pdf.name}  ->  \\reference\\{reference_pdf.name}")
    else:
        report.item("No reference PDF to copy.")

    # ------------------------------------------------------------------
    # Step 9 — Discover and copy TTF fonts referenced in the DFA files
    # ------------------------------------------------------------------
    report.section("Step 9: Copy TrueType fonts")

    # Collect all DFA files now in \docdef\
    dfa_in_docdef = list((output_root / "docdef").glob("*.dfa"))
    font_faces = extract_font_faces_from_dfa(dfa_in_docdef)
    report.item(f"Font faces referenced in DFA : {len(font_faces)}")
    for face in sorted(font_faces):
        report.item(f"  '{face}'")

    # Build the list of directories to search for TTF files.
    # Search order:
    #   (1) user-supplied --fonts-source-dir
    #   (2) codes subfolder (project-shipped TTFs, e.g. helvetica.ttf in FIN886)
    #   (3) project \ttf\ folder (already populated by step 7 resource copy)
    #   (4) converter's own directory + fonts/ subdirectory (drop TTFs here)
    #   (5) Windows system fonts  (Arial is used as Helvetica fallback)
    font_search_dirs: list[Path] = []
    if args.fonts_source_dir:
        fsd = Path(args.fonts_source_dir).resolve()
        if fsd.is_dir():
            font_search_dirs.append(fsd)
        else:
            report.warn(f"--fonts-source-dir not found: {fsd}")
    # Project-shipped fonts: codes subfolder and the already-populated \ttf\ dir
    font_search_dirs.append(codes_dir)
    font_search_dirs.append(resource_root / "ttf")
    # Converter directory: place any TTF substitutes (e.g. helvetica.ttf) here
    _script_dir = Path(__file__).parent.resolve()
    font_search_dirs.append(_script_dir)
    font_search_dirs.append(_script_dir / "fonts")
    if WINDOWS_USER_FONTS_DIR.is_dir():
        font_search_dirs.append(WINDOWS_USER_FONTS_DIR)
    if WINDOWS_FONTS_DIR.is_dir():
        font_search_dirs.append(WINDOWS_FONTS_DIR)

    ttf_dest_dir = resource_root / "ttf"
    found_ttf, missing_ttf = resolve_ttf_files(font_faces, font_search_dirs)

    for face, src_path in sorted(found_ttf.items()):
        dest = ttf_dest_dir / src_path.name
        if not dest.exists():
            shutil.copy2(src_path, dest)
            report.item(f"Copied {src_path.name}  ('{face}')  ->  \\ttf\\{src_path.name}")
        else:
            report.item(f"Skipped {src_path.name}  ('{face}')  — already exists in \\ttf\\")

    for face in missing_ttf:
        if face.upper() not in FONT_FACE_TO_TTF and face.lower() not in FONT_FACE_TO_TTF:
            report.warn(
                f"Font face '{face}' has no known TTF mapping — "
                f"place the font file manually in \\ttf\\"
            )
        else:
            report.warn(
                f"Font file for '{face}' not found in search path(s) — "
                f"place it manually in \\ttf\\"
            )

    # ------------------------------------------------------------------
    # Step 10 — Generate configuration files
    # ------------------------------------------------------------------
    report.section("Step 10: Generate configuration files")

    # 10a. .prj file
    prj_content = generate_prj(
        project_name  = project_name,
        project_root  = output_root,
        dfa_filename  = main_dfa.name,
        data_filename = prj_data_file,
    )
    prj_path = docdef_dir / f"{project_name}.prj"
    prj_path.write_text(prj_content, encoding="utf-8")
    report.item(f"Generated  \\docdef\\{prj_path.name}")

    # 10b. DEFAULT.LBP
    lbp_content = generate_lbp(project_root=output_root, resource_root=resource_root)
    lbp_path = output_root / "userisis" / "DEFAULT.LBP"
    lbp_path.write_text(lbp_content, encoding="utf-8")
    report.item(f"Generated  \\userisis\\DEFAULT.LBP")

    # 10c. ppde.prf
    prf_content = generate_prf(
        project_name  = project_name,
        project_root  = output_root,
        dfa_filename  = main_dfa.name,
    )
    prf_path = output_root / "userisis" / "ppde.prf"
    prf_path.write_text(prf_content, encoding="utf-8")
    report.item(f"Generated  \\userisis\\ppde.prf")

    # ------------------------------------------------------------------
    # Step 11 — Generate DocEXEC run script (.bat)
    # ------------------------------------------------------------------
    report.section("Step 11: Generate DocEXEC run script")

    bat_content = generate_docexec_bat(
        project_name  = project_name,
        project_root  = output_root,
        prj_filename  = prj_path.name,
    )
    bat_path = output_root / f"run_docexec_{project_name}.bat"
    bat_path.write_text(bat_content, encoding="ascii")
    log_path = output_root / "docdef" / f"{project_name}_docexec.log"
    report.item(f"Generated  {bat_path.name}")
    report.item(f"DocEXEC log will be written to  \\docdef\\{log_path.name}")

    # ------------------------------------------------------------------
    # Step 12 — Optionally run DocEXEC and check the log
    # ------------------------------------------------------------------
    if args.run_docexec:
        report.section("Step 12: Run DocEXEC")

        print(f"  Running DocEXEC — this may take a moment ...", flush=True)
        try:
            de_result = subprocess.run(
                ["cmd.exe", "/c", str(bat_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            report.warn("DocEXEC timed out after 300 seconds.")
            de_result = None

        if de_result is not None:
            rc = de_result.returncode
            report.item(f"DocEXEC exit code : {rc}")

        # Read and scan the log file
        if log_path.exists():
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            log_lines = log_text.splitlines()
            report.item(f"Log file          : {log_path}  ({len(log_lines)} lines)")

            # Categorise lines by the severity character at the end of the
            # message code (3rd whitespace-delimited token, e.g. AFPR0135E).
            # E = Error, W = Warning, S/F = Severe/Fatal, I = Info.
            def _log_sev(line: str) -> str:
                parts = line.split(None, 3)
                if len(parts) >= 3:
                    ch = parts[2][-1]
                    if ch.isalpha() and ch.isupper():
                        return ch
                return ""

            error_lines   = [l for l in log_lines if _log_sev(l) == "E"]
            warning_lines = [l for l in log_lines if _log_sev(l) == "W"]
            severe_lines  = [l for l in log_lines if _log_sev(l) in ("S", "F")]

            # Print errors immediately to the console (not deferred to report)
            if severe_lines or error_lines:
                print(f"\n  --- DocEXEC errors ({len(severe_lines + error_lines)}) ---", flush=True)
                for line in severe_lines + error_lines:
                    print(f"  {line.strip()}", flush=True)
                print(flush=True)
            else:
                print("  No errors in DocEXEC log.", flush=True)

            # Summary counts go into the report
            if severe_lines:
                report.item(f"SEVERE/FATAL      : {len(severe_lines)} line(s)")
            report.item(f"Errors            : {len(error_lines)}")
            report.item(f"Warnings          : {len(warning_lines)}")
            if not error_lines and not severe_lines:
                report.item("No errors detected in log.")

            # Check whether an output file was produced
            output_afp = output_root / "afpds" / f"{project_name}.afp"
            output_pdf = output_root / "afpds" / f"{project_name}.pdf"
            if output_afp.exists():
                report.item(f"Output produced   : \\afpds\\{output_afp.name}  ({output_afp.stat().st_size:,} bytes)")
            elif output_pdf.exists():
                report.item(f"Output produced   : \\afpds\\{output_pdf.name}  ({output_pdf.stat().st_size:,} bytes)")
            else:
                report.warn("No AFP/PDF output file found in \\afpds\\ after DocEXEC run.")
        else:
            report.warn(f"Log file not found after DocEXEC run: {log_path}")

    # ------------------------------------------------------------------
    # Done — print report
    # ------------------------------------------------------------------
    report.print_summary()

    print("Migration complete.")
    print(f"Open the project in Papyrus Designer with:")
    print(f"   {prj_path}")
    print()
    print(f"Run DocEXEC with:")
    print(f"   {bat_path}")
    if not args.run_docexec:
        print(f"   (or re-run this tool with --run-docexec to execute it automatically)")
    print()

    return 0


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrate_xerox_to_papyrus",
        description=textwrap.dedent("""\
            Migrate a Xerox FreeFlow project folder into a structured
            Papyrus Designer project, running the DFA converter and
            generating all required configuration files automatically.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Example
            -------
            py -3 migrate_xerox_to_papyrus.py \\
                --source  "C:\\Users\\freddievr\\claude-projects\\OCBC_XEROX\\SAMPLES\\SIBS_CAST" \\
                --output  "C:\\ISIS\\samples_pdd\\SIBS_CAST_Migrated" \\
                --project-name SIBS_CAST

            The converter scripts (universal_xerox_parser.py / xerox_jdt_dfa.py)
            must be in the same directory as this script.
        """),
    )

    parser.add_argument(
        "--source", "-s",
        required=True,
        metavar="PATH",
        help=(
            "Path to the Xerox FreeFlow source project folder. "
            "This is the folder that contains the codes subfolder "
            "and the input data file(s)."
        ),
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        metavar="PATH",
        help=(
            "Path where the new Papyrus Designer project should be created. "
            "The folder will be created if it does not exist."
        ),
    )
    parser.add_argument(
        "--project-name", "-n",
        required=True,
        dest="project_name",
        metavar="NAME",
        help=(
            "Name for the new Papyrus project. Used as the JOBNAME in the "
            ".prj file and as the base name of the .prj file itself. "
            "Should not contain spaces or special characters."
        ),
    )
    parser.add_argument(
        "--codes-subfolder",
        dest="codes_subfolder",
        default=None,
        metavar="NAME",
        help=(
            "Name of the subfolder inside --source that contains the Xerox "
            "source files (DBM, FRM, JDT, images). "
            "If omitted, the tool tries to detect it automatically by looking "
            "for a subfolder containing Xerox source files."
        ),
    )
    parser.add_argument(
        "--converter",
        choices=["universal", "jdt"],
        default=None,
        help=(
            "Which converter script to use: 'universal' (for DBM+FRM projects) "
            "or 'jdt' (for JDT-based projects). "
            "Default: auto-detected from the source files present."
        ),
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite the output directory if it already exists and is not empty.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Stream converter stdout/stderr to the console in real time.",
    )
    parser.add_argument(
        "--resources-dir",
        dest="resources_dir",
        default=None,
        metavar="PATH",
        help=(
            "Optional path to a central shared resources folder. "
            "When supplied, shared resource sub-folders (ttf, jpeg, tiff, png, pseg, "
            "ovl*, fonts*, fdf_pdf, pdf, object) are created and populated there "
            "instead of inside the project folder. "
            "DEFAULT.LBP is updated to point to this central location. "
            "Useful when multiple migrated projects share the same font/image library."
        ),
    )
    parser.add_argument(
        "--fonts-source-dir",
        dest="fonts_source_dir",
        default=None,
        metavar="PATH",
        help=(
            "Additional directory to search for TTF font files before falling back "
            "to C:\\Windows\\Fonts. Use this if the project requires custom or "
            "vendor-supplied fonts that are not part of the Windows system fonts."
        ),
    )
    parser.add_argument(
        "--run-docexec",
        dest="run_docexec",
        action="store_true",
        help=(
            "After migration, automatically execute Papyrus DocEXEC via the "
            "generated .bat file, capture its output to "
            "<project>\\docdef\\<name>_docexec.log, and report any errors found."
        ),
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args   = parser.parse_args()
    return migrate(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Xerox FreeFlow to Papyrus DocDEF Converter

This tool converts Xerox FreeFlow Designer files (DBM and FRM) to Papyrus DocDEF (DFA) format
based on the VIPP Language Reference Manual.

Created by: Claude 3.7 Sonnet
Date: April 28, 2025
"""

import os
import re
import sys
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union, Any
import argparse
import json
from datetime import datetime
import traceback

# Import command mappings
from command_mappings import (
    VIPP_TO_DFA_COMMANDS,
    VIPP_TO_DFA_ALIGNMENT,
    VIPP_TO_DFA_FONTS,
    VIPP_TO_DFA_COLORS,
    VIPP_BOX_PARAMS,
    VIPP_SPECIAL_COMMANDS,
    VIPP_TO_DFA_OPERATORS,
    VIPP_TO_DFA_SYSTEM_VARS,
    VIPP_TO_DFA_FUNCTIONS,
    translate_vipp_command,
    translate_output_command,
    translate_position_command,
    translate_box_command,
    translate_resource_command,
    translate_variable_assignment,
    translate_conditional_command,
    translate_loop_command,
    translate_case_command,
    translate_txnb_command,
    translate_params
)


# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('XeroxParser')


@dataclass
class XeroxToken:
    """Represents a token in Xerox FreeFlow code."""
    type: str  # 'keyword', 'variable', 'string', 'number', 'operator', 'delimiter', 'comment'
    value: str
    line_number: int
    column: int
    
    def __str__(self):
        return f"{self.type}({self.value})"


@dataclass
class XeroxCommand:
    """Represents a parsed Xerox command with its parameters and content."""
    name: str
    parameters: List[Any] = field(default_factory=list)
    content: str = ""
    line_number: int = 0
    column: int = 0
    indentation: int = 0
    parent: Optional['XeroxCommand'] = None
    children: List['XeroxCommand'] = field(default_factory=list)
    tokens: List[XeroxToken] = field(default_factory=list)


@dataclass
class XeroxFont:
    """Represents a font definition in Xerox FreeFlow."""
    alias: str
    name: str
    size: float = 10.0
    bold: bool = False
    italic: bool = False
    rotation: int = 0
    additional_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class XeroxColor:
    """Represents a color definition in Xerox FreeFlow."""
    alias: str
    name: str
    rgb: Optional[Tuple[int, int, int]] = None
    cmyk: Optional[Tuple[int, int, int, int]] = None


@dataclass
class XeroxVariable:
    """Represents a variable definition in Xerox FreeFlow."""
    name: str
    type: str = "string"  # string, number, array
    default_value: Any = None
    usage: Set[str] = field(default_factory=set)  # Where this variable is used
    dimensions: Optional[List[int]] = None  # For arrays


@dataclass
class XeroxProject:
    """Represents a full Xerox FreeFlow project."""
    name: str
    dbm_files: Dict[str, 'XeroxDBM'] = field(default_factory=dict)
    frm_files: Dict[str, 'XeroxFRM'] = field(default_factory=dict)
    jdt: 'XeroxJDT' = None  # JDT file (alternative to DBM)
    resources: Dict[str, str] = field(default_factory=dict)  # resource_name -> file_path


@dataclass
class XeroxDBM:
    """Represents a parsed Xerox DBM file."""
    filename: str
    title: str = ""
    creator: str = ""
    creation_date: str = ""
    variables: Dict[str, XeroxVariable] = field(default_factory=dict)
    fonts: Dict[str, XeroxFont] = field(default_factory=dict)
    colors: Dict[str, XeroxColor] = field(default_factory=dict)
    wizvar_prefixes: List[str] = field(default_factory=list)
    wizvar_fields: List[str] = field(default_factory=list)
    commands: List[XeroxCommand] = field(default_factory=list)
    case_blocks: Dict[str, List[XeroxCommand]] = field(default_factory=dict)
    raw_content: str = ""
    tokens: List[XeroxToken] = field(default_factory=list)


@dataclass
class XeroxFRM:
    """Represents a parsed Xerox FRM file."""
    filename: str
    title: str = ""
    creator: str = ""
    creation_date: str = ""
    fonts: Dict[str, XeroxFont] = field(default_factory=dict)
    colors: Dict[str, XeroxColor] = field(default_factory=dict)
    indexbat_defs: Dict[str, str] = field(default_factory=dict)
    xgfresdef_resources: Dict[str, Dict] = field(default_factory=dict)
    commands: List[XeroxCommand] = field(default_factory=list)
    raw_content: str = ""
    tokens: List[XeroxToken] = field(default_factory=list)
    font_rename_map: Dict[str, str] = field(default_factory=dict)  # Maps original font alias to renamed alias (e.g., "FE" -> "FE_1")


@dataclass
class XeroxCondition:
    """Represents a SETRCD condition in a JDT file."""
    name: str  # e.g., "IF_CND14"
    position: int  # Character position (recpos) - 0-based
    length: int  # Length to check
    operator: str  # /eq, /ne, /gt, /lt, /HOLD
    value: str  # String to compare
    is_compound: bool = False  # True if uses /and, /or
    compound_operator: str = ""  # /and or /or
    sub_conditions: List[str] = field(default_factory=list)  # For compound conditions


@dataclass
class XeroxRPEArray:
    """Represents one RPE output array in a JDT file."""
    condition_index: int = 0  # 0 = no condition, 1 = use first condition, etc.
    vertical_skip: int = 0
    x_position: int = 0
    y_skip: int = 0
    horizontal_position: int = 0
    vertical_position: int = 0
    start_position: int = 0  # Field start in data line (0-based)
    length: int = 0  # Field length
    font: str = ""
    color: str = ""
    literal_text: str = None  # If outputting literal instead of field
    special_call: str = None  # For {SCALL} resources
    condition_name: str = None  # For conditional lines like /IF_CND14
    align_right: bool = False  # For right-aligned fields


@dataclass
class XeroxJDT:
    """Represents a parsed Xerox JDT (Job Descriptor Ticket) file."""
    filename: str
    title: str = ""
    creator: str = ""
    creation_date: str = ""
    application: str = ""  # Application name from %%Application

    # Page setup
    orientation: str = "PORT"  # PORT, LAND, IPORT, ILAND
    pcc_mode: str = "ANSI"  # ANSI, EBCDIC, etc.
    vfu_settings: List = field(default_factory=list)  # VFU channel settings
    margins: Dict[str, int] = field(default_factory=dict)  # top, bottom, left, right (in points)
    grid: Dict[str, int] = field(default_factory=dict)  # cpl (chars per line), lpp (lines per page)

    # Resources
    fonts: Dict[str, XeroxFont] = field(default_factory=dict)
    colors: Dict[str, XeroxColor] = field(default_factory=dict)
    indexbat_defs: Dict[str, str] = field(default_factory=dict)  # BAT key definitions
    forms: List[str] = field(default_factory=list)  # Referenced .frm files via SETFORM
    max_forms: int = 0  # From SETMAXFORM

    # Conditionals
    conditions: Dict[str, XeroxCondition] = field(default_factory=dict)  # IF_CND1, etc.
    pcd_definitions: Dict[str, Dict] = field(default_factory=dict)  # Page Criteria Definitions

    # RPE Definition
    rpe_start_line: int = 0  # Starting line number from BEGINRPE
    rpe_lines: Dict[int, List[XeroxRPEArray]] = field(default_factory=dict)  # line# -> arrays

    # BEGINPAGE procedure
    beginpage_commands: List[XeroxCommand] = field(default_factory=list)

    # Variables
    variables: Dict[str, XeroxVariable] = field(default_factory=dict)

    # XGFResources (like in FRM)
    xgfresdef_resources: Dict[str, Dict] = field(default_factory=dict)

    # Raw content
    raw_content: str = ""
    tokens: List[XeroxToken] = field(default_factory=list)


@dataclass
class InputDataConfig:
    """Configuration for input data format - extracted from raw data."""
    delimiter: str = '|'  # Default, but will be detected from SETDBSEP
    field_names: List[str] = field(default_factory=list)  # From header or %%WIZVAR
    field_count: int = 0
    has_header_line: bool = False
    document_separator: str = '1'  # Line containing just '1'
    record_length: int = 4096  # Increased from 1024 for long CSV lines


@dataclass
class DFAGenerationConfig:
    """Runtime configuration for DFA generation."""
    use_dynamic_formats: bool = True  # USE FORMAT REFERENCE('DF_'!FLD[1])
    channel_code: str = 'NO'  # Changed from ANSI
    enable_extractall: bool = True  # Use EXTRACTALL for splitting
    enable_document_boundaries: bool = True  # Check for '1' marker


class XeroxLexer:
    """Lexical analyzer for Xerox FreeFlow code."""
    
    # Token definitions
    KEYWORDS = {
        # VIPP structure and flow control
        'XGF', 'ENDXGF', 'SETPROJECT', 'ENDJOB', 'STARTDBM', 'ENDCASE', 'BEGINDOCUMENT', 'ENDDOCUMENT',
        'CASE', 'PREFIX', 'ENDPAGE', 'BEGINPAGE', 'FSHOW', 'SETPARAMS', 'SETUNIT', 'SETFTSW',
        'SETSUB', 'SETVARS', 'SETVAR', 'SETINFO', 'IF', 'ELSE', 'ENDIF', 'FOR', 'ENDFOR',
        'WHILE', 'ENDWHILE', 'REPEAT', 'BREAK', 'CONTINUE', 'GOTO',

        # Font and color handling
        'INDEXFONT', 'INDEXCOLOR', 'INDEXBAT', 'XGFRESDEF',

        # Page and positioning
        'SETPAGESIZE', 'SETLSP', 'SETPAGENUMBER', 'SETPAGEDEF', 'SETLKF', 'SETFORM',
        'MOVETO', 'MOVEH', 'LINETO', 'NL', 'ORITL', 'PORT', 'LAND', 'SHL', 'SHR', 'SHC', 'SHP',
        'IPORT', 'ILAND',  # Inverse orientation modes

        # Resource handling
        'CACHE', 'ICALL', 'SCALL', 'DRAWB',

        # Forms specific
        'MM', 'CM', 'INCH', 'POINT',

        # JDT-specific keywords
        # Line mode operations
        'STARTLM', 'SETJDT', 'SETLMFILE', 'STARTXML', 'STARTDBM',

        # Printer control and page setup
        'SETPCC', 'SETVFU', 'SETMARGIN', 'SETGRID', 'SETMAXFORM', 'SETBUFSIZE',

        # Record and page criteria
        'SETRCD', 'SETPCD', 'GETFIELD', 'GETINTV',

        # RPE (Record Processing Entry)
        'BEGINRPE', 'ENDRPE', 'FROMLINE',

        # Variable substitution and manipulation
        'VSUB', 'GETITEM',

        # Page control
        'SKIPPAGE', 'NEWFRAME', 'PAGEBRK', 'BOOKMARK',

        # Table handling
        'BEGINTABLE', 'ENDTABLE', 'SHROW',

        # Other JDT commands
        'INDEXPIF', 'ENDCLIP', 'CLIP', 'ENDIFALL',
    }
    
    OPERATORS = {'+', '-', '*', '/', '=', '==', '!=', '<', '>', '<=', '>=', '!', '&&', '||', '++', '--'}
    
    DELIMITERS = {'(', ')', '[', ']', '{', '}', ',', ';', ':'}
    
    def __init__(self):
        self.input = ""
        self.tokens = []
        self.pos = 0
        self.line = 1
        self.col = 1
    
    def tokenize(self, input_text: str) -> List[XeroxToken]:
        """Convert the input string into a list of tokens."""
        self.input = input_text
        self.tokens = []
        self.pos = 0
        self.line = 1
        self.col = 1
        
        while self.pos < len(self.input):
            # Skip whitespace
            if self.input[self.pos].isspace():
                if self.input[self.pos] == '\n':
                    self.line += 1
                    self.col = 1
                else:
                    self.col += 1
                self.pos += 1
                continue
            
            # Handle comments
            if self.pos + 1 < len(self.input) and self.input[self.pos:self.pos+2] == '/*':
                self._handle_block_comment()
                continue
            
            if self.input[self.pos] == '%':
                self._handle_line_comment()
                continue
            
            # Handle string literals
            if self.input[self.pos] == "'":
                self._handle_string_literal("'")
                continue

            if self.input[self.pos] == '"':
                self._handle_string_literal('"')
                continue

            # Handle VIPP-style parentheses strings (text)
            if self.input[self.pos] == '(':
                self._handle_vipp_string()
                continue
            
            # Handle numbers
            if self.input[self.pos].isdigit() or (self.input[self.pos] == '.' and 
                                              self.pos + 1 < len(self.input) and 
                                              self.input[self.pos + 1].isdigit()):
                self._handle_number()
                continue
            
            # Handle identifiers and keywords
            if self.input[self.pos].isalpha() or self.input[self.pos] == '_' or self.input[self.pos] == '$':
                self._handle_identifier()
                continue
            
            # Handle Xerox-specific prefixes
            if self.input[self.pos] == '/':
                self._handle_xerox_identifier()
                continue
            
            # Handle operators
            if self.input[self.pos] in '+-*/=!<>&|':
                self._handle_operator()
                continue
            
            # Handle delimiters
            if self.input[self.pos] in self.DELIMITERS:
                token = XeroxToken(
                    type='delimiter',
                    value=self.input[self.pos],
                    line_number=self.line,
                    column=self.col
                )
                self.tokens.append(token)
                self.col += 1
                self.pos += 1
                continue
            
            # Handle unknown characters
            self.pos += 1
            self.col += 1
        
        return self.tokens
    
    def _handle_block_comment(self):
        """Handle a /* ... */ style comment."""
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        self.pos += 2  # Skip /*
        self.col += 2
        
        while self.pos < len(self.input) - 1:
            if self.input[self.pos:self.pos+2] == '*/':
                self.pos += 2
                self.col += 2
                
                # Create token for the comment
                comment_text = self.input[start_pos:self.pos]
                token = XeroxToken(
                    type='comment',
                    value=comment_text,
                    line_number=start_line,
                    column=start_col
                )
                self.tokens.append(token)
                return
            
            if self.input[self.pos] == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            
            self.pos += 1
        
        # If we get here, the comment was never closed
        logger.warning(f"Unclosed block comment starting at line {start_line}, column {start_col}")
        
        # Still create a token for the unclosed comment
        comment_text = self.input[start_pos:self.pos]
        token = XeroxToken(
            type='comment',
            value=comment_text,
            line_number=start_line,
            column=start_col
        )
        self.tokens.append(token)
    
    def _handle_line_comment(self):
        """Handle a % comment that goes to the end of the line."""
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        
        while self.pos < len(self.input) and self.input[self.pos] != '\n':
            self.pos += 1
            self.col += 1
        
        # Create token for the comment
        comment_text = self.input[start_pos:self.pos]
        token = XeroxToken(
            type='comment',
            value=comment_text,
            line_number=start_line,
            column=start_col
        )
        self.tokens.append(token)
    
    def _handle_string_literal(self, quote_char):
        """Handle a string literal."""
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        self.pos += 1  # Skip opening quote
        self.col += 1
        
        escaped = False
        
        while self.pos < len(self.input):
            if escaped:
                escaped = False
            elif self.input[self.pos] == '\\':
                escaped = True
            elif self.input[self.pos] == quote_char:
                self.pos += 1
                self.col += 1
                
                # Create token for the string including quotes
                string_text = self.input[start_pos:self.pos]
                token = XeroxToken(
                    type='string',
                    value=string_text,
                    line_number=start_line,
                    column=start_col
                )
                self.tokens.append(token)
                return
            
            if self.input[self.pos] == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            
            self.pos += 1
        
        # If we get here, the string was never closed
        logger.warning(f"Unclosed string starting at line {start_line}, column {start_col}")

        # Still create a token for the unclosed string
        string_text = self.input[start_pos:self.pos]
        token = XeroxToken(
            type='string',
            value=string_text,
            line_number=start_line,
            column=start_col
        )
        self.tokens.append(token)

    def _handle_vipp_string(self):
        """Handle a VIPP-style parentheses string (text)."""
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        self.pos += 1  # Skip opening (
        self.col += 1

        depth = 1  # Track nested parentheses

        while self.pos < len(self.input) and depth > 0:
            char = self.input[self.pos]

            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    self.pos += 1
                    self.col += 1

                    # Create token for the string including parentheses
                    string_text = self.input[start_pos:self.pos]
                    token = XeroxToken(
                        type='string',
                        value=string_text,
                        line_number=start_line,
                        column=start_col
                    )
                    self.tokens.append(token)
                    return
            elif char == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1

            self.pos += 1

        # If we get here, the string was never closed
        logger.warning(f"Unclosed VIPP string starting at line {start_line}, column {start_col}")

        # Still create a token for the unclosed string
        string_text = self.input[start_pos:self.pos]
        token = XeroxToken(
            type='string',
            value=string_text,
            line_number=start_line,
            column=start_col
        )
        self.tokens.append(token)

    def _handle_number(self):
        """Handle a numeric literal."""
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        
        # Handle base prefixes (hex, octal, etc.)
        if self.input[self.pos:self.pos+2].lower() == '0x':
            self.pos += 2
            self.col += 2
            while self.pos < len(self.input) and (self.input[self.pos].isdigit() or 
                                             self.input[self.pos].lower() in 'abcdef'):
                self.pos += 1
                self.col += 1
        else:
            # Regular decimal number
            while self.pos < len(self.input) and (self.input[self.pos].isdigit() or 
                                             self.input[self.pos] == '.'):
                self.pos += 1
                self.col += 1
        
        # Create token for the number
        number_text = self.input[start_pos:self.pos]
        token = XeroxToken(
            type='number',
            value=number_text,
            line_number=start_line,
            column=start_col
        )
        self.tokens.append(token)
    
    def _handle_identifier(self):
        """Handle an identifier or keyword."""
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        
        while self.pos < len(self.input) and (self.input[self.pos].isalnum() or 
                                         self.input[self.pos] in '_$'):
            self.pos += 1
            self.col += 1
        
        # Check if it's a keyword
        identifier = self.input[start_pos:self.pos]
        if identifier.upper() in self.KEYWORDS:
            token = XeroxToken(
                type='keyword',
                value=identifier,
                line_number=start_line,
                column=start_col
            )
        else:
            token = XeroxToken(
                type='identifier',
                value=identifier,
                line_number=start_line,
                column=start_col
            )
        
        self.tokens.append(token)
    
    def _handle_xerox_identifier(self):
        """Handle a Xerox-specific identifier that starts with /."""
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        self.pos += 1  # Skip /
        self.col += 1
        
        while self.pos < len(self.input) and (self.input[self.pos].isalnum() or 
                                         self.input[self.pos] in '_$'):
            self.pos += 1
            self.col += 1
        
        # Create token for the Xerox identifier
        identifier = self.input[start_pos:self.pos]
        token = XeroxToken(
            type='variable',
            value=identifier,
            line_number=start_line,
            column=start_col
        )
        self.tokens.append(token)
    
    def _handle_operator(self):
        """Handle an operator."""
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        
        # Check for two-character operators
        if self.pos + 1 < len(self.input):
            potential_op = self.input[self.pos:self.pos+2]
            if potential_op in self.OPERATORS:
                self.pos += 2
                self.col += 2
                
                token = XeroxToken(
                    type='operator',
                    value=potential_op,
                    line_number=start_line,
                    column=start_col
                )
                self.tokens.append(token)
                return
        
        # Single-character operator
        token = XeroxToken(
            type='operator',
            value=self.input[self.pos],
            line_number=start_line,
            column=start_col
        )
        self.tokens.append(token)
        self.pos += 1
        self.col += 1


class XeroxParser:
    """Parser for Xerox FreeFlow code."""

    # VIPP commands and their expected parameter counts (in RPN order)
    # Format: command_name: (num_params, param_types)
    # param_types: 'any' for any type, 'num' for numbers, 'str' for strings, 'var' for variables
    VIPP_COMMANDS = {
        # Output commands
        'SH': 1,      # (text) SH
        'SHL': 1,     # (text) SHL
        'SHR': 1,     # (text) SHR
        'SHr': 1,     # (text) SHr
        'SHC': 1,     # (text) SHC
        'SHP': 3,     # var width align SHP or (text) width align SHP

        # Positioning
        'MOVETO': 2,  # x y MOVETO
        'MOVEH': 1,   # x MOVEH
        'NL': 0,      # NL (optional param for spacing)

        # Variable operations
        'SETVAR': 2,  # /var value SETVAR (can have /INI in between)
        '++': 1,      # /var ++ (increment)
        '--': 1,      # /var -- (decrement)

        # Drawing
        'DRAWB': 5,   # x y w h style DRAWB

        # Resources
        'SCALL': 1,   # (name) SCALL or (name) scale SCALL
        'ICALL': 1,   # (name) ICALL
        'CACHE': 0,   # (name) CACHE [dimensions] - variable params, handled specially

        # Page layout
        'SETFORM': 1,     # (name.FRM) SETFORM
        'SETLKF': 1,      # [[...]] SETLKF
        'SETPAGEDEF': 1,  # [...] SETPAGEDEF
        'NEWFRAME': 0,    # NEWFRAME
        'PAGEBRK': 0,     # PAGEBRK
        'SKIPPAGE': 0,    # SKIPPAGE

        # Font/Color indexing
        'INDEXFONT': 3,   # /alias /font size INDEXFONT
        'INDEXCOLOR': 2,  # /alias color INDEXCOLOR
        'INDEXBAT': 2,    # /alias value INDEXBAT
        'XGFRESDEF': 2,   # /name { commands } XGFRESDEF

        # Control flow
        'IF': 0,      # Handled specially (consumes condition from stack)
        'ENDIF': 0,
        'ELSE': 0,
        'FOR': 0,
        'ENDFOR': 0,

        # Comparison operators (binary, consume 2 from stack)
        'eq': 2,
        'ne': 2,
        'lt': 2,
        'gt': 2,
        'le': 2,
        'ge': 2,

        # PDF features
        'BOOKMARK': 1,        # (text) BOOKMARK
        'SETPAGENUMBER': 5,   # (text) style x y size SETPAGENUMBER

        # Clipping
        'CLIP': 4,    # x y w h CLIP
        'ENDCLIP': 0,

        # String functions
        'GETINTV': 4,  # /result var start len GETINTV SETVAR (result variable included)
        'GETITEM': 2,  # array index GETITEM
        'VSUB': 0,     # VSUB (operates on preceding string)

        # Misc
        'SETUNIT': 0,  # MM SETUNIT
        'SETLSP': 1,   # n SETLSP
        'ORITL': 0,
        'PORT': 0,
        'LAND': 0,
        'SETFTSW': 2,  # (char) n SETFTSW
        'SETPARAMS': 1,  # [...] SETPARAMS
        'XGFRESDEF': 0,  # {...} XGFRESDEF
        'ADD': 0,      # array [...] ADD
    }

    def __init__(self):
        self.lexer = XeroxLexer()
        self.tokens = []
        self.pos = 0

    def _parse_vipp_block(self, tokens: List[XeroxToken], line_offset: int = 0) -> List[XeroxCommand]:
        """
        Parse a block of VIPP code using RPN (Reverse Polish Notation) parsing.

        VIPP uses postfix notation where commands come AFTER their parameters.
        Example: `38 MOVEH` means "move horizontal to 38"
                 `(Balance B/F) SH` means "show text 'Balance B/F'"

        Args:
            tokens: List of tokens to parse
            line_offset: Line number offset for error reporting

        Returns:
            List of XeroxCommand objects
        """
        commands = []
        stack = []  # Parameter stack for RPN parsing
        i = 0

        while i < len(tokens):
            token = tokens[i]

            # Skip comments
            if token.type == 'comment':
                i += 1
                continue

            # Handle block delimiters - push as is for later processing
            if token.value in ('{', '}', '[', ']'):
                # Collect entire block for commands that need it
                if token.value in ('{', '['):
                    block_tokens, end_idx = self._collect_block(tokens, i)
                    stack.append(('block', block_tokens))
                    i = end_idx + 1
                    continue
                else:
                    i += 1
                    continue

            # Check if this is a known VIPP command
            if token.value in self.VIPP_COMMANDS:
                cmd_name = token.value
                param_count = self.VIPP_COMMANDS[cmd_name]

                # Special handling for certain commands
                if cmd_name == 'CACHE':
                    # CACHE: (filename) CACHE [dimensions...] - variable parameters
                    # Pop filename parameter from stack
                    params = []
                    if len(stack) > 0:
                        p = stack.pop()
                        if isinstance(p, tuple) and p[0] == 'block':
                            params.append(self._tokens_to_string(p[1]))
                        else:
                            params.append(str(p))

                    # Try to look ahead in tokens to capture dimensions [width height]
                    # This is needed because stack-based parsing can't capture lookahead params
                    look_ahead_idx = i + 1
                    while look_ahead_idx < len(tokens) and look_ahead_idx < i + 10:
                        next_token = tokens[look_ahead_idx]
                        if next_token.value in self.VIPP_COMMANDS:
                            break  # Stop at next command
                        # Add lookahead tokens as parameters
                        params.append(next_token.value)
                        look_ahead_idx += 1

                    cmd = XeroxCommand(
                        name='CACHE',
                        line_number=token.line_number + line_offset,
                        column=token.column
                    )
                    cmd.parameters = params
                    commands.append(cmd)

                elif cmd_name == 'SETVAR':
                    # SETVAR: /var value [/INI] SETVAR
                    # Pop params, handling optional /INI
                    params = []
                    while len(stack) > 0 and len(params) < 3:
                        p = stack.pop()
                        if isinstance(p, tuple) and p[0] == 'block':
                            # Convert block tokens to string using our method
                            params.insert(0, self._tokens_to_string(p[1]))
                        else:
                            params.insert(0, str(p))
                    # Filter out /INI if present
                    params = [p for p in params if p != '/INI']
                    if len(params) >= 2:
                        cmd = XeroxCommand(
                            name='SETVAR',
                            line_number=token.line_number + line_offset,
                            column=token.column
                        )
                        cmd.parameters = params[:2]  # [var_name, value]
                        commands.append(cmd)

                elif cmd_name == 'IF':
                    # IF can be in two forms:
                    # 1. RPN (DBM): condition { block } IF - IF comes AFTER
                    # 2. Prefix (FRM): IF condition { block } ENDIF - IF comes FIRST

                    # Check if we have a block on stack (RPN syntax)
                    has_block_on_stack = any(isinstance(item, tuple) and item[0] == 'block' for item in stack)

                    if has_block_on_stack:
                        # RPN syntax: condition { block } IF
                        # Collect condition from stack, separating condition from block
                        condition = []
                        if_body_tokens = None

                        # Process stack items in reverse order
                        stack_items = []
                        while len(stack) > 0:
                            stack_items.insert(0, stack.pop())

                        for item in stack_items:
                            if isinstance(item, tuple) and item[0] == 'block':
                                # This is the IF body block - save for recursive parsing
                                if_body_tokens = item[1]
                            elif isinstance(item, list):
                                # This is a list of tokens - convert to string
                                condition.append(self._tokens_to_string(item))
                            else:
                                # This is part of the condition
                                condition.append(str(item))

                        cmd = XeroxCommand(
                            name='IF',
                            line_number=token.line_number + line_offset,
                            column=token.column
                        )
                        cmd.parameters = condition
                        commands.append(cmd)

                        # If there's a body block, recursively parse and store as children
                        if if_body_tokens:
                            child_commands = self._parse_vipp_block(if_body_tokens, line_offset)
                            cmd.children = child_commands
                    else:
                        # Prefix syntax: IF condition { block } ENDIF
                        # Look ahead to collect condition and block
                        condition_tokens = []
                        if_body_tokens = None
                        j = i + 1

                        # Collect tokens until we hit { (the block start)
                        while j < len(tokens) and tokens[j].value != '{':
                            if tokens[j].type != 'comment':
                                condition_tokens.append(tokens[j])
                            j += 1

                        # Parse condition tokens using mini RPN parser
                        condition = self._parse_if_condition(condition_tokens)

                        # Collect the block if present
                        if j < len(tokens) and tokens[j].value == '{':
                            if_body_tokens, block_end_idx = self._collect_block(tokens, j)
                            j = block_end_idx + 1

                            # Skip ENDIF token if present
                            if j < len(tokens) and tokens[j].value == 'ENDIF':
                                j += 1

                        # Update main loop index
                        i = j - 1  # -1 because main loop will increment

                        cmd = XeroxCommand(
                            name='IF',
                            line_number=token.line_number + line_offset,
                            column=token.column
                        )
                        cmd.parameters = [condition] if condition else []
                        commands.append(cmd)

                        # Recursively parse IF body
                        if if_body_tokens:
                            child_commands = self._parse_vipp_block(if_body_tokens, line_offset)
                            cmd.children = child_commands

                elif cmd_name in ('eq', 'ne', 'lt', 'gt', 'le', 'ge'):
                    # Comparison operators - leave in stack as part of condition
                    if len(stack) >= 2:
                        right = stack.pop()
                        left = stack.pop()
                        stack.append(f"{left} {cmd_name} {right}")
                    else:
                        stack.append(cmd_name)

                elif cmd_name == 'ELSE':
                    # ELSE can have a block in two forms:
                    # 1. RPN: { block } ELSE - block is already on stack
                    # 2. Prefix: ELSE { block } - need to look ahead

                    else_body_tokens = None

                    # First check if there's a block on stack (RPN syntax)
                    if len(stack) > 0 and isinstance(stack[-1], tuple) and stack[-1][0] == 'block':
                        # Pop the block from stack
                        block_tuple = stack.pop()
                        else_body_tokens = block_tuple[1]
                    else:
                        # Prefix syntax: look ahead for block after ELSE
                        j = i + 1
                        if j < len(tokens) and tokens[j].value == '{':
                            # Collect the block following ELSE
                            else_body_tokens, block_end_idx = self._collect_block(tokens, j)
                            i = block_end_idx  # Skip past the block

                    cmd = XeroxCommand(
                        name='ELSE',
                        line_number=token.line_number + line_offset,
                        column=token.column
                    )
                    commands.append(cmd)

                    # If there's a body block, recursively parse and store as children
                    if else_body_tokens:
                        child_commands = self._parse_vipp_block(else_body_tokens, line_offset)
                        cmd.children = child_commands

                elif cmd_name == 'VSUB':
                    # VSUB operates on the preceding string on the stack
                    # Mark the last item on stack as needing VSUB processing
                    if stack:
                        last_item = stack.pop()
                        # Wrap with VSUB marker that the output handler will recognize
                        stack.append(('VSUB', last_item))

                elif cmd_name == 'NL':
                    # NL can have optional spacing parameter
                    params = []
                    # Check if there's a number on stack
                    if len(stack) > 0:
                        # IMPORTANT: Check for minus+number FIRST before checking for direct number
                        # Check if we have a number preceded by minus operator (e.g., stack: [-, 04])
                        if len(stack) >= 2 and isinstance(stack[-1], str) and stack[-2] == '-':
                            # Last item is a number, second-to-last is minus
                            num = stack[-1]
                            if num.replace('.', '', 1).isdigit():
                                stack.pop()  # Remove the number
                                stack.pop()  # Remove the minus
                                params.append(f"-{num}")  # Combine into negative number
                        # Check for direct number (no minus)
                        elif isinstance(stack[-1], str) and (stack[-1].replace('.', '', 1).replace('-', '', 1).isdigit()):
                            params.append(stack.pop())
                    cmd = XeroxCommand(
                        name='NL',
                        line_number=token.line_number + line_offset,
                        column=token.column
                    )
                    cmd.parameters = params
                    commands.append(cmd)

                elif cmd_name in ('SETLKF', 'SETPAGEDEF', 'SETPARAMS'):
                    # These commands consume a block from stack
                    params = []
                    if len(stack) > 0:
                        p = stack.pop()
                        if isinstance(p, tuple) and p[0] == 'block':
                            params.append(self._tokens_to_string(p[1]))
                        else:
                            params.append(str(p))
                    cmd = XeroxCommand(
                        name=cmd_name,
                        line_number=token.line_number + line_offset,
                        column=token.column
                    )
                    cmd.parameters = params
                    commands.append(cmd)

                elif cmd_name == 'XGFRESDEF':
                    # XGFRESDEF: /name { commands } XGFRESDEF
                    # Pop resource name and command block
                    if len(stack) >= 2:
                        block = stack.pop()
                        name = stack.pop()

                        if isinstance(name, str) and name.startswith('/'):
                            resource_name = name.lstrip('/')

                            # Parse block if it's a tuple
                            if isinstance(block, tuple) and block[0] == 'block':
                                resource_commands = self._parse_vipp_block(block[1], line_offset)
                            else:
                                resource_commands = []

                            cmd = XeroxCommand(
                                name='XGFRESDEF',
                                line_number=token.line_number + line_offset,
                                column=token.column
                            )
                            cmd.parameters = [resource_name]
                            cmd.children = resource_commands
                            commands.append(cmd)

                elif cmd_name == 'SHP':
                    # SHP has variable parameter count depending on VSUB:
                    # - With VSUB: (text) VSUB align SHP → stack has 2 items, expands to 3 params
                    # - Without VSUB: var width align SHP → stack has 3 items, 3 params
                    params = []

                    # Check if the top of stack (after popping align) has VSUB tuple
                    # First, peek at stack to determine how many to pop
                    items_to_pop = param_count  # Default to 3

                    # Peek at second item on stack (index -2) to check for VSUB
                    if len(stack) >= 2 and isinstance(stack[-2], tuple) and stack[-2][0] == 'VSUB':
                        # VSUB case: only pop 2 items from stack
                        items_to_pop = 2

                    # Pop parameters
                    for _ in range(min(items_to_pop, len(stack))):
                        p = stack.pop()
                        if isinstance(p, tuple) and p[0] == 'block':
                            params.insert(0, self._tokens_to_string(p[1]))
                        elif isinstance(p, tuple) and p[0] == 'VSUB':
                            # VSUB-marked parameter - add both the parameter and VSUB marker
                            params.insert(0, str(p[1]))
                            params.insert(1, 'VSUB')  # Insert VSUB after the text parameter
                        else:
                            params.insert(0, str(p))

                    cmd = XeroxCommand(
                        name='SHP',
                        line_number=token.line_number + line_offset,
                        column=token.column
                    )
                    cmd.parameters = params
                    commands.append(cmd)

                else:
                    # Standard command - pop required params from stack
                    params = []
                    for _ in range(min(param_count, len(stack))):
                        p = stack.pop()
                        if isinstance(p, tuple) and p[0] == 'block':
                            params.insert(0, self._tokens_to_string(p[1]))
                        elif isinstance(p, tuple) and p[0] == 'VSUB':
                            # VSUB-marked parameter - add both the parameter and VSUB marker
                            params.insert(0, str(p[1]))
                            params.insert(1, 'VSUB')  # Insert VSUB after the text parameter
                        else:
                            params.insert(0, str(p))

                    cmd = XeroxCommand(
                        name=cmd_name,
                        line_number=token.line_number + line_offset,
                        column=token.column
                    )
                    cmd.parameters = params
                    commands.append(cmd)

            elif token.type == 'string':
                # String literal - push to stack
                stack.append(token.value)

            elif token.type == 'number':
                # Number - push to stack
                stack.append(token.value)

            elif token.type == 'variable':
                # Variable reference - push to stack
                stack.append(token.value)

            elif token.type == 'identifier':
                # Could be a font alias (F1, F2, etc.) or unknown command
                if token.value.upper() in ('MM', 'CM', 'INCH', 'POINT'):
                    # Unit specifier - push to stack
                    stack.append(token.value)
                elif len(token.value) <= 3 and token.value[0].upper() == 'F':
                    # Font alias (F1, F2, FA, FB, etc.) - create font command
                    cmd = XeroxCommand(
                        name='SETFONT',
                        line_number=token.line_number + line_offset,
                        column=token.column
                    )
                    cmd.parameters = [token.value]
                    commands.append(cmd)
                elif token.value.upper() in ('R', 'B', 'W', 'G', 'C', 'M', 'Y', 'K'):
                    # Color alias (R=Red, B=Black, W=White, etc.) - create color command
                    cmd = XeroxCommand(
                        name='SETCOLOR',
                        line_number=token.line_number + line_offset,
                        column=token.column
                    )
                    cmd.parameters = [token.value.upper()]
                    commands.append(cmd)
                elif token.value in ('FRLEFT', 'CPCOUNT', '_PAGE', 'PREFIX'):
                    # System variable - push to stack
                    stack.append(token.value)
                elif token.value.startswith('VAR_') or token.value.startswith('VAR'):
                    # User variable - push to stack
                    stack.append(token.value)
                elif token.value in ('true', 'false'):
                    # Boolean - push to stack
                    stack.append(token.value)
                elif token.value.startswith('FLD'):
                    # Field variable - push to stack
                    stack.append(token.value)
                else:
                    # Unknown identifier - push to stack
                    stack.append(token.value)

            elif token.type == 'keyword':
                # Known keyword not in VIPP_COMMANDS - push to stack
                stack.append(token.value)

            else:
                # Other token types - push to stack
                if token.value not in ('(', ')', ',', ';'):
                    stack.append(token.value)

            i += 1

        return commands

    def _collect_block(self, tokens: List[XeroxToken], start_idx: int) -> tuple:
        """
        Collect tokens within a balanced block (braces or brackets).

        Args:
            tokens: List of all tokens
            start_idx: Index of opening delimiter

        Returns:
            Tuple of (block_tokens, end_idx)
        """
        open_char = tokens[start_idx].value
        close_char = '}' if open_char == '{' else ']'
        block_tokens = []
        depth = 1
        i = start_idx + 1

        while i < len(tokens) and depth > 0:
            if tokens[i].value == open_char:
                depth += 1
            elif tokens[i].value == close_char:
                depth -= 1
                if depth == 0:
                    break
            block_tokens.append(tokens[i])
            i += 1

        return (block_tokens, i)

    def _tokens_to_string(self, tokens: List[XeroxToken]) -> str:
        """Convert a list of tokens back to a string representation."""
        if not tokens:
            return ""
        parts = []
        for t in tokens:
            if isinstance(t, XeroxToken):
                parts.append(t.value)
            else:
                parts.append(str(t))
        return ' '.join(parts)

    def _parse_if_condition(self, tokens: List[XeroxToken]) -> str:
        """
        Parse IF condition tokens (prefix syntax) using RPN evaluation.
        Example: VAR_CCAST (CCAST) eq -> VAR_CCAST == 'CCAST'
        """
        if not tokens:
            return ""

        stack = []
        for token in tokens:
            if token.value in ('eq', 'ne', 'lt', 'gt', 'le', 'ge'):
                # Comparison operator
                if len(stack) >= 2:
                    right = stack.pop()
                    left = stack.pop()
                    # Format as comparison
                    stack.append(f"{left} {token.value} {right}")
                else:
                    stack.append(token.value)
            else:
                # Push token value onto stack
                stack.append(token.value)

        # Join remaining stack items
        return ' '.join(str(item) for item in stack)

    def _collect_case_block_tokens(self, start_idx: int) -> Tuple[List[XeroxToken], int]:
        """
        Collect all tokens within a VIPP case block (between { and }).

        This method handles nested braces correctly.

        Args:
            start_idx: Index of the opening brace

        Returns:
            Tuple of (list of tokens inside the block, index of closing brace)
        """
        if start_idx >= len(self.tokens) or self.tokens[start_idx].value != '{':
            return ([], start_idx)

        block_tokens = []
        depth = 1
        i = start_idx + 1

        while i < len(self.tokens) and depth > 0:
            token = self.tokens[i]

            if token.value == '{':
                depth += 1
                block_tokens.append(token)
            elif token.value == '}':
                depth -= 1
                if depth > 0:
                    block_tokens.append(token)
            else:
                block_tokens.append(token)

            i += 1

        # i is now pointing past the closing brace, so return i-1 as the end index
        return (block_tokens, i - 1)

    def parse_file(self, filename: str) -> Union[XeroxDBM, XeroxFRM, XeroxJDT]:
        """Parse a Xerox file and return the appropriate structure."""
        try:
            logger.info(f"Parsing file: {filename}")
            with open(filename, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Determine file type
            if filename.lower().endswith('.dbm'):
                return self.parse_dbm(filename, content)
            elif filename.lower().endswith('.frm'):
                return self.parse_frm(filename, content)
            elif filename.lower().endswith('.jdt'):
                return self.parse_jdt(filename, content)
            else:
                logger.warning(f"Unknown file type: {filename}")
                # Try to guess based on content
                if 'STARTDBM' in content:
                    return self.parse_dbm(filename, content)
                elif 'BEGINRPE' in content or 'SETRCD' in content or 'STARTLM' in content:
                    return self.parse_jdt(filename, content)
                else:
                    return self.parse_frm(filename, content)

        except UnicodeDecodeError:
            # Try again with latin-1 encoding
            logger.info(f"Retrying with latin-1 encoding: {filename}")
            with open(filename, 'r', encoding='latin-1') as f:
                content = f.read()

            if filename.lower().endswith('.dbm'):
                return self.parse_dbm(filename, content)
            elif filename.lower().endswith('.frm'):
                return self.parse_frm(filename, content)
            elif filename.lower().endswith('.jdt'):
                return self.parse_jdt(filename, content)
            else:
                # Try to guess based on content
                if 'STARTDBM' in content:
                    return self.parse_dbm(filename, content)
                elif 'BEGINRPE' in content or 'SETRCD' in content or 'STARTLM' in content:
                    return self.parse_jdt(filename, content)
                else:
                    return self.parse_frm(filename, content)
    
    def parse_dbm(self, filename: str, content: str) -> XeroxDBM:
        """Parse DBM content and return a structured representation."""
        logger.info(f"Parsing as DBM: {filename}")
        dbm = XeroxDBM(filename=filename, raw_content=content)
        
        # Tokenize the content
        self.tokens = self.lexer.tokenize(content)
        dbm.tokens = self.tokens
        self.pos = 0
        
        # Extract metadata
        dbm.title, dbm.creator, dbm.creation_date = self._extract_metadata()
        
        # Extract WIZVAR fields if present
        dbm.wizvar_prefixes, dbm.wizvar_fields = self._extract_wizvar()
        
        # Parse declarations and case blocks
        self._parse_dbm_structure(dbm)
        
        return dbm
    
    def parse_frm(self, filename: str, content: str) -> XeroxFRM:
        """Parse FRM content and return a structured representation."""
        logger.info(f"Parsing as FRM: {filename}")
        frm = XeroxFRM(filename=filename, raw_content=content)
        
        # Tokenize the content
        self.tokens = self.lexer.tokenize(content)
        frm.tokens = self.tokens
        self.pos = 0
        
        # Extract metadata
        frm.title, frm.creator, frm.creation_date = self._extract_metadata()
        
        # Parse form structure
        self._parse_frm_structure(frm)
        
        return frm
    
    def _extract_metadata(self) -> Tuple[str, str, str]:
        """Extract metadata from comments at the start of the file."""
        title = ""
        creator = ""
        creation_date = ""
        
        # Look for metadata in the first few tokens
        for i, token in enumerate(self.tokens[:20]):
            if token.type == 'comment':
                if '%%Title:' in token.value:
                    title = token.value.split('%%Title:')[1].strip()
                elif '%%Creator:' in token.value:
                    creator = token.value.split('%%Creator:')[1].strip()
                elif '%%CreationDate:' in token.value:
                    creation_date = token.value.split('%%CreationDate:')[1].strip()
        
        return title, creator, creation_date
    
    def _extract_wizvar(self) -> Tuple[List[str], List[str]]:
        """Extract WIZVAR prefixes and fields from the file."""
        prefixes = []
        fields = []
        
        # Look for WIZVAR:BEGIN and WIZVAR:END sections
        in_wizvar = False
        for token in self.tokens:
            if token.type == 'comment' and '%%WIZVAR:BEGIN' in token.value:
                in_wizvar = True
                continue
            
            if token.type == 'comment' and '%%WIZVAR:END' in token.value:
                in_wizvar = False
                continue
            
            if in_wizvar and token.type == 'comment' and '%%WIZVAR' in token.value:
                # Parse the WIZVAR line
                parts = token.value.replace('%%WIZVAR', '').strip().split(',')
                for part in parts:
                    var_name = part.strip()
                    if var_name.startswith('PREFIX'):
                        prefixes.append(var_name)
                    else:
                        fields.append(var_name)
        
        return prefixes, fields

    def parse_jdt(self, filename: str, content: str) -> XeroxJDT:
        """Parse JDT (Job Descriptor Ticket) content and return a structured representation."""
        logger.info(f"Parsing as JDT: {filename}")
        jdt = XeroxJDT(filename=filename, raw_content=content)

        # Tokenize the content
        self.tokens = self.lexer.tokenize(content)
        jdt.tokens = self.tokens
        self.pos = 0

        # Extract metadata from PostScript comments
        jdt.title, jdt.creator, jdt.creation_date, jdt.application = self._extract_ps_metadata(content)

        # Parse JDT-specific sections
        self._parse_jdt_structure(jdt)

        logger.info(f"JDT parsing complete: {len(jdt.fonts)} fonts, {len(jdt.colors)} colors, " +
                   f"{len(jdt.conditions)} conditions, {len(jdt.rpe_lines)} RPE lines")

        return jdt

    def _extract_ps_metadata(self, content: str):
        """Extract metadata from PostScript comment header."""
        title = ""
        creator = ""
        creation_date = ""
        application = ""

        for line in content.split('\n'):
            if line.startswith('%%Title:'):
                title = line.replace('%%Title:', '').strip()
            elif line.startswith('%%Creator:'):
                creator = line.replace('%%Creator:', '').strip()
            elif line.startswith('%%CreationDate:'):
                creation_date = line.replace('%%CreationDate:', '').strip()
            elif line.startswith('%%Application:'):
                application = line.replace('%%Application:', '').strip()

        return title, creator, creation_date, application

    def _parse_jdt_structure(self, jdt: XeroxJDT):
        """Parse the structure of a JDT file."""
        self.pos = 0

        # Track parsing state
        in_beginpage = False
        in_beginrpe = False
        beginpage_tokens = []
        current_line = None

        # Debug: track iterations to detect infinite loops
        max_iterations = len(self.tokens) * 2
        iteration = 0

        while self.pos < len(self.tokens):
            token = self.tokens[self.pos]
            iteration += 1

            # Safety check for infinite loops
            if iteration > max_iterations:
                logger.error(f"Infinite loop detected at position {self.pos}, token: {token.value}")
                logger.error(f"Last 10 tokens: {[t.value for t in self.tokens[max(0, self.pos-10):self.pos+1]]}")
                break

            # Handle orientation
            if token.value in ['PORT', 'LAND', 'IPORT', 'ILAND']:
                jdt.orientation = token.value
                self.pos += 1
                continue

            # Handle SETPCC
            if token.type == 'operator' and token.value == '/' and self.pos + 1 < len(self.tokens):
                next_token = self.tokens[self.pos + 1]
                if next_token.value in ['ANSI', 'EBCDIC'] and self.pos + 2 < len(self.tokens):
                    if self.tokens[self.pos + 2].value == 'SETPCC':
                        jdt.pcc_mode = next_token.value
                        self.pos += 3
                        continue

            # Handle SETMARGIN
            if token.value == 'SETMARGIN':
                self._parse_setmargin(jdt)
                continue

            # Handle SETGRID
            if token.value == 'SETGRID':
                self._parse_setgrid(jdt)
                continue

            # Handle SETMAXFORM
            if token.value == 'SETMAXFORM':
                self.pos += 1
                if self.pos < len(self.tokens) and self.tokens[self.pos].type == 'number':
                    jdt.max_forms = int(float(self.tokens[self.pos].value))
                self.pos += 1
                continue

            # Handle SETFORM (form references)
            if token.value == 'SETFORM':
                self._parse_setform(jdt)
                continue

            # Handle INDEXFONT
            if token.value == 'INDEXFONT':
                self._parse_jdt_font(jdt)
                continue

            # Handle INDEXCOLOR: /alias R G B INDEXCOLOR
            if token.value == 'INDEXCOLOR':
                # Skip for now - colors will use defaults
                self.pos += 1
                continue

            # Handle INDEXBAT definitions: /U0 /UNDL INDEXBAT or /N0 null INDEXBAT
            if token.value == 'INDEXBAT':
                # Look backward for alias and name
                if self.pos >= 3:
                    alias_token = self.tokens[self.pos - 2]
                    name_token = self.tokens[self.pos - 1]

                    if alias_token.type in ['operator', 'variable'] and alias_token.value.startswith('/'):
                        alias = alias_token.value.lstrip('/')

                        # Handle both variable (/UNDL) and literal (null) values
                        if name_token.type in ['operator', 'variable'] and name_token.value.startswith('/'):
                            name = name_token.value.lstrip('/')
                        else:
                            name = name_token.value

                        jdt.indexbat_defs[alias] = name
                self.pos += 1
                continue

            # Handle SETRCD (condition definitions)
            if token.value == 'SETRCD':
                self._parse_setrcd(jdt)
                continue

            # Handle SETPCD (page criteria definitions)
            if token.value == 'SETPCD':
                self._parse_setpcd(jdt)
                continue

            # Handle SETVAR: /varname value SETVAR or /varname value /type SETVAR
            if token.value == 'SETVAR':
                # Look backward for variable name and value
                if self.pos >= 3:
                    var_token = self.tokens[self.pos - 2]
                    val_token = self.tokens[self.pos - 1]

                    if var_token.type in ['operator', 'variable'] and var_token.value.startswith('/'):
                        var_name = var_token.value.lstrip('/')
                        var_value = val_token.value if val_token.type in ['string', 'number'] else '0'

                        jdt.variables[var_name] = XeroxVariable(
                            name=var_name,
                            default_value=var_value,
                            type='string' if val_token.type == 'string' else 'number'
                        )
                self.pos += 1
                continue

            # Handle BEGINPAGE
            if token.value == 'BEGINPAGE':
                in_beginpage = True
                beginpage_tokens = []
                self.pos += 1
                continue

            # Handle BEGINRPE
            if token.value == 'BEGINRPE':
                in_beginrpe = True
                self.pos += 1
                # Get the starting line number - this is also the line number for the first FROMLINE
                if self.pos < len(self.tokens) and self.tokens[self.pos].type == 'number':
                    start_line = int(float(self.tokens[self.pos].value))
                    jdt.rpe_start_line = start_line
                    current_line = start_line  # Set current_line for the first FROMLINE
                    self.pos += 1
                continue

            # Handle ENDRPE
            if token.value == 'ENDRPE':
                in_beginrpe = False
                self.pos += 1
                continue

            # Handle line numbers in RPE section (MUST come before FROMLINE check)
            if in_beginrpe and token.type == 'number':
                current_line = int(float(token.value))
                self.pos += 1
                continue

            # Handle FROMLINE inside RPE (after line number is set)
            if in_beginrpe and token.value == 'FROMLINE':
                self._parse_fromline(jdt, current_line)
                continue

            # Handle XGFRESDEF (same as FRM) - skip for now
            if token.value == 'XGFRESDEF':
                # Skip XGFRESDEF for now
                self.pos += 1
                continue

            # Collect BEGINPAGE tokens
            if in_beginpage:
                if token.value == '}' and self.pos + 1 < len(self.tokens) and \
                   self.tokens[self.pos + 1].value == 'BEGINPAGE':
                    # End of BEGINPAGE block
                    in_beginpage = False
                    jdt.beginpage_commands = beginpage_tokens
                    self.pos += 2
                    continue
                else:
                    beginpage_tokens.append(token)

            self.pos += 1

    def _parse_setmargin(self, jdt: XeroxJDT):
        """Parse SETMARGIN command: top bottom left right SETMARGIN"""
        # self.pos is currently pointing at SETMARGIN
        # Look backward for 4 numbers: top bottom left right
        margins = []
        for i in range(4, 0, -1):
            if self.pos - i >= 0 and self.tokens[self.pos - i].type == 'number':
                margins.append(int(float(self.tokens[self.pos - i].value)))

        if len(margins) == 4:
            jdt.margins = {
                'top': margins[0],
                'bottom': margins[1],
                'left': margins[2],
                'right': margins[3]
            }

        self.pos += 1  # Move past SETMARGIN

    def _parse_setgrid(self, jdt: XeroxJDT):
        """Parse SETGRID command: cpl lpp SETGRID"""
        # self.pos is currently pointing at SETGRID
        # Look backward for the two numbers
        if self.pos >= 2:
            cpl_token = self.tokens[self.pos - 2]
            lpp_token = self.tokens[self.pos - 1]

            if cpl_token.type == 'number' and lpp_token.type == 'number':
                jdt.grid = {
                    'cpl': int(float(cpl_token.value)),
                    'lpp': int(float(lpp_token.value))
                }

        self.pos += 1  # Move past SETGRID

    def _parse_setform(self, jdt: XeroxJDT):
        """Parse SETFORM command: (formname) CACHE SETFORM or (formname) SETFORM"""
        # self.pos is currently pointing at SETFORM
        # Look backward for the form name (might have CACHE before SETFORM)
        for i in range(1, min(4, self.pos + 1)):
            if self.pos - i >= 0:
                form_token = self.tokens[self.pos - i]
                if form_token.type == 'string':
                    form_name = form_token.value
                    if form_name not in jdt.forms:
                        jdt.forms.append(form_name)
                    break

        self.pos += 1  # Move past SETFORM

    def _parse_jdt_font(self, jdt: XeroxJDT):
        """Parse JDT INDEXFONT command: /FontKey /FontName Size INDEXFONT"""
        # self.pos is currently pointing at INDEXFONT
        # Expected format: /FontKey /FontName Size INDEXFONT
        # Example: /Font1 /NTMR 7.5 INDEXFONT
        #          pos-3   pos-2  pos-1  pos

        font_key = ""
        font_name = ""
        size = 0.0

        # Check if we have at least 3 tokens before this
        if self.pos >= 3:
            # Get the three tokens before INDEXFONT
            size_token = self.tokens[self.pos - 1]
            name_token = self.tokens[self.pos - 2]
            key_token = self.tokens[self.pos - 3]

            # Extract size (should be a number)
            if size_token.type == 'number':
                try:
                    size = float(size_token.value)
                except ValueError:
                    pass

            # Extract font name (should be a variable starting with /)
            if name_token.type == 'variable' and name_token.value.startswith('/'):
                font_name = name_token.value[1:]  # Remove leading /

            # Extract font key (should be a variable starting with /)
            if key_token.type == 'variable' and key_token.value.startswith('/'):
                font_key = key_token.value[1:]  # Remove leading /

        # Create font if all parameters found
        if font_key and font_name and size > 0:
            jdt.fonts[font_key] = XeroxFont(
                alias=font_key,
                name=font_name,
                size=size
            )

        self.pos += 1  # Move past INDEXFONT

    def _parse_setrcd(self, jdt: XeroxJDT):
        """Parse SETRCD condition definition."""
        """
        Format: /CondName position length /operator (value) SETRCD
        Example: /IF_CND14 2 3 /eq (HD1) SETRCD
                 pos-6 pos-5 pos-4 pos-3 pos-2 pos-1  pos
        Or compound: /IF_CND17 [IF_CND14 IF_CND15 /and] SETRCD
        """
        # self.pos is currently pointing at SETRCD

        cond_name = ""
        position = 0
        length = 0
        operator = ""
        value = ""
        is_compound = False
        sub_conditions = []
        compound_op = ""

        # Check for compound condition by looking for [
        for i in range(max(0, self.pos - 15), self.pos):
            if self.tokens[i].type == 'delimiter' and self.tokens[i].value == '[':
                is_compound = True
                # Extract sub-conditions and operator
                j = i + 1
                while j < self.pos and self.tokens[j].value != ']':
                    if self.tokens[j].value.startswith('IF_CND') or self.tokens[j].value.startswith('BANNER'):
                        sub_conditions.append(self.tokens[j].value)
                    elif self.tokens[j].value in ['/and', '/or']:
                        compound_op = self.tokens[j].value[1:]  # Remove /
                    j += 1
                break

        # Find condition name by looking backward for /IF_CND or /BANNER
        # Token value may include '/' prefix from lexer (e.g., '/IF_CND14')
        for i in range(self.pos - 1, max(0, self.pos - 20), -1):
            val = self.tokens[i].value.lstrip('/')
            if val.startswith('IF_CND') or val.startswith('BANNER'):
                cond_name = val  # Store without '/' prefix
                break

        # If not compound, extract simple condition parameters
        if not is_compound and self.pos >= 5:
            # Simple format: /CondName position length /operator (value) SETRCD
            # Try to extract from expected positions
            if self.pos >= 1 and self.tokens[self.pos - 1].type == 'string':
                value = self.tokens[self.pos - 1].value.strip('()')

            if self.pos >= 2 and self.tokens[self.pos - 2].type == 'variable' and \
               self.tokens[self.pos - 2].value.startswith('/'):
                operator = self.tokens[self.pos - 2].value[1:]  # Remove /

            if self.pos >= 3 and self.tokens[self.pos - 3].type == 'number':
                length = int(float(self.tokens[self.pos - 3].value))

            if self.pos >= 4 and self.tokens[self.pos - 4].type == 'number':
                position = int(float(self.tokens[self.pos - 4].value))

        # Create condition
        if cond_name:
            jdt.conditions[cond_name] = XeroxCondition(
                name=cond_name,
                position=position,
                length=length,
                operator=operator,
                value=value,
                is_compound=is_compound,
                compound_operator=compound_op,
                sub_conditions=sub_conditions
            )

        self.pos += 1  # Move past SETRCD

    def _parse_setpcd(self, jdt: XeroxJDT):
        """Parse SETPCD (Page Criteria Definition)."""
        """Example: /BANNER 2 1 12 13 /eq (DATE PRINTED:) SETPCD"""
        # self.pos is currently pointing at SETPCD

        # Similar to SETRCD but for page-level criteria
        # For now, store in pcd_definitions dict
        pcd_name = ""

        for i in range(self.pos - 1, max(self.pos - 10, -1), -1):
            if i < 0:
                continue
            token = self.tokens[i]
            if token.type == 'operator' and token.value == '/' and i + 1 < len(self.tokens):
                next_token = self.tokens[i + 1]
                if next_token.value not in ['eq', 'ne', 'gt', 'lt', 'HOLD']:
                    pcd_name = next_token.value
                    break

        if pcd_name:
            jdt.pcd_definitions[pcd_name] = {'name': pcd_name}

        self.pos += 1  # Move past SETPCD

    def _parse_fromline(self, jdt: XeroxJDT, line_number: int):
        """Parse FROMLINE and its associated RPE arrays."""
        """
        Format after FROMLINE:
        [cond vskip xpos yskip hpos vpos start len /Font COLOR]
        or
        /ELSE/IF_COND
        [array]
        /ENDIFALL
        """
        logger.debug(f"Parsing FROMLINE for line {line_number} at position {self.pos}")
        self.pos += 1  # Skip FROMLINE

        if line_number is None:
            logger.debug("  Line number is None, skipping")
            return

        # Initialize array list for this line if not exists
        if line_number not in jdt.rpe_lines:
            jdt.rpe_lines[line_number] = []

        # Parse arrays and conditionals until we hit next FROMLINE or ENDRPE
        current_condition = None

        while self.pos < len(self.tokens):
            token = self.tokens[self.pos]

            # Check for end of RPE section or next FROMLINE
            if token.value in ['FROMLINE', 'ENDRPE']:
                # Don't increment - let the main loop handle this token
                break

            # Check if this is a line number followed by FROMLINE (next line marker)
            if token.type == 'number' and self.pos + 1 < len(self.tokens) and \
               self.tokens[self.pos + 1].value == 'FROMLINE':
                # This is the next line number - let main loop handle it
                break

            # Check for conditional markers
            # Lexer produces '/ELSE', '/IF_CND*', '/ENDIFALL' as single variable tokens
            token_val = token.value.lstrip('/')

            if token_val == 'ENDIFALL':
                current_condition = None
                self.pos += 1
                continue

            if token_val == 'ELSE':
                # Check if next token is /IF_CND (else-if pattern)
                if self.pos + 1 < len(self.tokens):
                    next_val = self.tokens[self.pos + 1].value.lstrip('/')
                    if next_val.startswith('IF_CND'):
                        # /ELSE/IF_CND pattern — skip ELSE, let next iteration handle IF_CND
                        self.pos += 1
                        continue
                # Plain /ELSE — default else branch
                current_condition = 'ELSE'
                self.pos += 1
                continue

            if token_val.startswith('IF_CND'):
                current_condition = token_val  # Store without '/' prefix
                self.pos += 1
                continue

            # Check for array start
            if token.type == 'delimiter' and token.value == '[':
                rpe_array = self._parse_rpe_array(current_condition)
                if rpe_array:
                    jdt.rpe_lines[line_number].append(rpe_array)
                continue

            self.pos += 1

    def _parse_rpe_array(self, condition: str = None) -> XeroxRPEArray:
        """Parse a single RPE array."""
        """
        Format: [cond vskip xpos yskip hpos vpos start len /Font COLOR]
        or: [cond vskip xpos yskip hpos vpos 0 (literal text) /Font COLOR]
        or: [{SCALL} cond xpos yskip ypos vpos 0 (ResName) /Font COLOR]
        """
        self.pos += 1  # Skip [

        elements = []
        font_name = ""
        color_name = ""
        literal_text = None
        special_call = None

        while self.pos < len(self.tokens):
            token = self.tokens[self.pos]

            if token.type == 'delimiter' and token.value == ']':
                self.pos += 1
                break

            if token.value == '{SCALL}':
                special_call = 'SCALL'
                self.pos += 1
                continue

            if token.type == 'number':
                elements.append(int(float(token.value)))
            elif token.type == 'string':
                literal_text = token.value
            elif token.type == 'operator' and token.value == '/' and \
                 self.pos + 1 < len(self.tokens):
                next_token = self.tokens[self.pos + 1]
                if next_token.value in ['Font1', 'Font2', 'Font3', 'Font4', 'Font5', 'Font6',
                                       'Font7', 'Font8', 'Font9', 'Font10', 'Font11', 'Font12',
                                       'F15', 'F16', 'F17', 'F19', 'F20', 'Font21', 'Font22',
                                       'Font23', 'Font24', 'NCR', 'NTMR', 'NHE', 'NTMI', 'NTMB',
                                       'NHEB', 'NCRB', 'NHENB', 'NHEN', 'SBT', 'NHEBO']:
                    font_name = next_token.value
                    self.pos += 1
            elif token.value in ['BLACK', 'WHITE', 'RED', 'B', 'W', 'R']:
                color_name = token.value

            self.pos += 1

        # Ensure we have enough elements
        while len(elements) < 8:
            elements.append(0)

        rpe = XeroxRPEArray(
            condition_index=elements[0] if len(elements) > 0 else 0,
            vertical_skip=elements[1] if len(elements) > 1 else 0,
            x_position=elements[2] if len(elements) > 2 else 0,
            y_skip=elements[3] if len(elements) > 3 else 0,
            horizontal_position=elements[4] if len(elements) > 4 else 0,
            vertical_position=elements[5] if len(elements) > 5 else 0,
            start_position=elements[6] if len(elements) > 6 else 0,
            length=elements[7] if len(elements) > 7 else 0,
            font=font_name,
            color=color_name,
            literal_text=literal_text,
            special_call=special_call,
            condition_name=condition
        )

        # Check if this is right-aligned (condition_index = 1)
        if rpe.condition_index == 1:
            rpe.align_right = True

        return rpe

    def _parse_dbm_structure(self, dbm: XeroxDBM):
        """Parse the structure of a DBM file."""
        # Reset position
        self.pos = 0
        
        # Flags for tracking sections
        in_case_block = False
        current_case = ""
        current_command = None
        
        while self.pos < len(self.tokens):
            token = self.tokens[self.pos]
            
            # Handle font definitions: /FE /ARIALBO 06 INDEXFONT (4 tokens)
            if (token.type == 'variable' and
                self.pos + 3 < len(self.tokens) and
                self.tokens[self.pos + 1].type == 'variable' and
                self.tokens[self.pos + 3].value == 'INDEXFONT'):

                alias = token.value
                font_name = self.tokens[self.pos + 1].value
                try:
                    size = float(self.tokens[self.pos + 2].value)
                except ValueError:
                    size = 10.0

                dbm.fonts[alias.lstrip('/')] = XeroxFont(
                    alias=alias.lstrip('/'),
                    name=font_name.lstrip('/'),
                    size=size
                )

                self.pos += 4
                continue
            
            # Handle color definitions
            if (token.type == 'variable' and 
                self.pos + 2 < len(self.tokens) and
                self.tokens[self.pos + 2].value == 'INDEXCOLOR'):
                
                alias = token.value
                color_name = self.tokens[self.pos + 1].value
                
                dbm.colors[alias.lstrip('/')] = XeroxColor(
                    alias=alias.lstrip('/'),
                    name=color_name.lstrip('/')
                )
                
                self.pos += 3
                continue
            
            # Handle variable definitions with SETVAR
            if (token.type == 'variable' and 
                self.pos + 2 < len(self.tokens) and
                self.tokens[self.pos + 2].value == 'SETVAR'):
                
                var_name = token.value
                var_value = self.tokens[self.pos + 1].value
                
                dbm.variables[var_name.lstrip('/')] = XeroxVariable(
                    name=var_name.lstrip('/'),
                    default_value=var_value
                )
                
                self.pos += 3
                continue
            
            # Handle CASE PREFIX
            if token.value == 'CASE' and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].value == 'PREFIX':
                in_case_block = True
                self.pos += 2
                continue
            
            # Handle case values - now tokenized as strings like (STMTTP)
            if in_case_block and token.type == 'string' and token.value.startswith('(') and token.value.endswith(')'):
                # Extract case value from the string token
                case_value = token.value[1:-1]  # Remove ( and )

                # Skip if this looks like a content string (has spaces or special chars)
                # Case labels are typically simple identifiers like STMTTP, HEADER, CCASTX
                if ' ' not in case_value and '.' not in case_value:
                    current_case = case_value
                    dbm.case_blocks[current_case] = []
                    self.pos += 1

                    # Now look for the opening brace of the case block
                    while self.pos < len(self.tokens) and self.tokens[self.pos].value != '{':
                        self.pos += 1

                    if self.pos < len(self.tokens) and self.tokens[self.pos].value == '{':
                        # Collect all tokens in the block
                        block_tokens, end_idx = self._collect_case_block_tokens(self.pos)

                        # Parse the VIPP commands in this block
                        commands = self._parse_vipp_block(block_tokens, token.line_number)
                        dbm.case_blocks[current_case] = commands
                        dbm.commands.extend(commands)

                        self.pos = end_idx + 1
                    continue

            # Handle empty case ({})
            if in_case_block and token.type == 'delimiter' and token.value == '{':
                if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].value == '}':
                    current_case = "{}"
                    dbm.case_blocks[current_case] = []
                    self.pos += 2
                    continue
                # Check if this is a standalone block (not after a case label)
                elif not current_case:
                    # Collect block tokens
                    block_tokens, end_idx = self._collect_case_block_tokens(self.pos)
                    # Parse but don't assign to a case
                    commands = self._parse_vipp_block(block_tokens, token.line_number)
                    dbm.commands.extend(commands)
                    self.pos = end_idx + 1
                    continue

            # Check for end of CASE block (ENDCASE)
            if in_case_block and token.value == 'ENDCASE':
                in_case_block = False
                current_case = ""
                self.pos += 1
                continue
            
            # Move to next token if none of the above matched
            self.pos += 1
    
    def _parse_frm_structure(self, frm: XeroxFRM):
        """Parse the structure of an FRM file using VIPP RPN parsing."""
        # Reset position
        self.pos = 0

        # First pass: extract font and color definitions
        while self.pos < len(self.tokens):
            token = self.tokens[self.pos]

            # Handle font definitions: /F1 /ARIALB 05 INDEXFONT
            if (token.type == 'variable' and
                self.pos + 3 < len(self.tokens) and
                self.tokens[self.pos + 1].type == 'variable' and
                self.tokens[self.pos + 3].value == 'INDEXFONT'):

                alias = token.value
                font_name = self.tokens[self.pos + 1].value
                try:
                    size = float(self.tokens[self.pos + 2].value)
                except ValueError:
                    size = 10.0

                frm.fonts[alias.lstrip('/')] = XeroxFont(
                    alias=alias.lstrip('/'),
                    name=font_name.lstrip('/'),
                    size=size
                )

                self.pos += 4
                continue

            # Handle color definitions: /B BLACK INDEXCOLOR
            if (token.type == 'variable' and
                self.pos + 2 < len(self.tokens) and
                self.tokens[self.pos + 2].value == 'INDEXCOLOR'):

                alias = token.value
                color_name = self.tokens[self.pos + 1].value

                frm.colors[alias.lstrip('/')] = XeroxColor(
                    alias=alias.lstrip('/'),
                    name=color_name.lstrip('/')
                )

                self.pos += 3
                continue

            # Handle INDEXBAT definitions: /U0 /UNDL INDEXBAT or /N0 null INDEXBAT
            if (token.type == 'variable' and
                self.pos + 2 < len(self.tokens) and
                self.tokens[self.pos + 2].value == 'INDEXBAT'):

                alias = token.value.lstrip('/')
                name_token = self.tokens[self.pos + 1]

                # Handle both variable (/UNDL) and literal (null) values
                if name_token.type == 'variable':
                    name = name_token.value.lstrip('/')
                else:
                    name = name_token.value

                frm.indexbat_defs[alias] = name

                self.pos += 3
                continue

            self.pos += 1

        # Second pass: parse commands using VIPP RPN parser
        # Find the form block content (between { and })
        # The form block typically starts with { followed by %%Begin Form comment
        form_tokens = []
        in_form = False
        brace_depth = 0
        self.pos = 0

        while self.pos < len(self.tokens):
            token = self.tokens[self.pos]

            # Check for form block start - look for { with nearby %%Begin Form
            if token.type == 'delimiter' and token.value == '{':
                # Check if this is the form block start (look for Begin Form in nearby comments)
                is_form_start = False
                for look_ahead in range(1, min(5, len(self.tokens) - self.pos)):
                    if self.tokens[self.pos + look_ahead].type == 'comment':
                        if 'Begin Form' in self.tokens[self.pos + look_ahead].value:
                            is_form_start = True
                            break
                        break  # Stop if we hit a non-Begin Form comment

                if is_form_start and not in_form:
                    in_form = True
                    brace_depth = 1
                    self.pos += 1
                    continue
                elif in_form:
                    brace_depth += 1

            # Check for form block end
            if token.type == 'delimiter' and token.value == '}':
                if in_form:
                    brace_depth -= 1
                    if brace_depth == 0:
                        in_form = False
                        break

            # Collect tokens within form block (skip comments)
            if in_form and token.type != 'comment':
                form_tokens.append(token)

            self.pos += 1

        # Parse the form tokens using the VIPP block parser
        if form_tokens:
            frm.commands = self._parse_vipp_block(form_tokens)

    def resolve_font_conflicts(self, dbm: XeroxDBM, frm_files: Dict[str, XeroxFRM]):
        """
        Detect and resolve font name conflicts between DBM and FRM files.

        Strategy:
        1. DBM fonts have priority and keep their original names
        2. FRM fonts that conflict with DBM or other FRMs get renamed with suffix (_1, _2, etc.)
        3. Store rename mapping in frm.font_rename_map for later use in command generation

        Args:
            dbm: The parsed DBM file
            frm_files: Dictionary of parsed FRM files
        """
        # Track all font names used (start with DBM fonts)
        used_font_names = set(dbm.fonts.keys())

        # Track rename counters for each base font name
        rename_counters = {}

        # Process each FRM file
        for frm_name, frm in frm_files.items():
            logger.info(f"Resolving font conflicts for FRM: {frm_name}")

            for font_alias, font_def in list(frm.fonts.items()):
                if font_alias in used_font_names:
                    # Font conflict detected
                    # Get the DBM definition for comparison
                    if font_alias in dbm.fonts:
                        dbm_font = dbm.fonts[font_alias]
                        logger.warning(
                            f"Font conflict: {font_alias} in {frm_name} "
                            f"(FRM: {font_def.name} size {font_def.size}) conflicts with "
                            f"DBM (DBM: {dbm_font.name} size {dbm_font.size})"
                        )
                    else:
                        logger.warning(
                            f"Font conflict: {font_alias} in {frm_name} conflicts with previous FRM"
                        )

                    # Generate new name with suffix
                    if font_alias not in rename_counters:
                        rename_counters[font_alias] = 1
                    else:
                        rename_counters[font_alias] += 1

                    new_alias = f"{font_alias}_{rename_counters[font_alias]}"

                    # Store the rename mapping
                    frm.font_rename_map[font_alias] = new_alias

                    # Update the font definition with new alias
                    font_def.alias = new_alias

                    # Move to new key in fonts dict
                    del frm.fonts[font_alias]
                    frm.fonts[new_alias] = font_def

                    # Add new name to used set
                    used_font_names.add(new_alias)

                    logger.info(f"  → Renamed {font_alias} to {new_alias} in {frm_name}")
                else:
                    # No conflict, add to used set
                    used_font_names.add(font_alias)
                    # Identity mapping (no rename)
                    frm.font_rename_map[font_alias] = font_alias


class VIPPToDFAConverter:
    """Converts Xerox VIPP commands to Papyrus DocDEF (DFA) code."""

    # Font style mappings from VIPP to Papyrus
    FONT_STYLE_MAPPINGS = {
        'ARIAL': 'Arial',
        'ARIALB': 'Arial Bold',
        'ARIALO': 'Arial Italic',
        'ARIALBO': 'Arial Bold Italic',
        'COURIER': 'Courier New',
        'COURIERB': 'Courier New Bold',
        'COURIERO': 'Courier New Italic',
        'COURIERBO': 'Courier New Bold Italic',
        'HELVETICA': 'Helvetica',
        'HELVE': 'Helvetica',
        'HELVEB': 'Helvetica Bold',
        'TIMES': 'Times New Roman',
        'TIMESB': 'Times New Roman Bold',
        'TIMESI': 'Times New Roman Italic',
        'TIMESBI': 'Times New Roman Bold Italic',
        'NZDB': 'NZDB',  # Special character font
    }

    # Command mappings from VIPP to DFA
    COMMAND_MAPPINGS = {
        'MOVETO': 'POSITION',
        'MOVEH': 'POSITION',
        'NL': 'NL',
        'SH': 'OUTPUT',
        'SHL': 'OUTPUT',
        'SHR': 'OUTPUT',
        'SHr': 'OUTPUT',
        'SHC': 'OUTPUT',
        'SHP': 'OUTPUT',
        'IF': 'IF',
        'ENDIF': 'ENDIF',
        'ELSE': 'ELSE',
        'FOR': 'FOR',
        'ENDFOR': 'ENDFOR',
        'DRAWB': 'BOX',
        'SCALL': 'SEGMENT',
        'ICALL': 'IMAGE',
        'CACHE': 'CACHE',
        'CLIP': 'CLIP',
        'ENDCLIP': 'ENDCLIP',
        'SETFORM': 'SETFORM',
        'SETLKF': 'SETLKF',
        'SETPAGEDEF': 'SETPAGEDEF',
        'PAGEBRK': 'PAGEBREAK',
        'NEWFRAME': 'NEWFRAME',
        'SKIPPAGE': 'SKIPPAGE',
        'BOOKMARK': 'BOOKMARK',
        'SETPAGENUMBER': 'PAGENUMBER',
        'GETINTV': 'SUBSTR',
        'GETITEM': 'GETITEM',
        'ADD': '+',
    }

    # VIPP comparison operators to DFA
    COMPARISON_OPERATORS = {
        'eq': '==',
        'ne': '<>',
        'lt': '<',
        'gt': '>',
        'le': '<=',
        'ge': '>=',
    }

    def __init__(self, dbm: Union[XeroxDBM, XeroxJDT] = None, frm_files: Dict[str, XeroxFRM] = None, jdt: XeroxJDT = None):
        """
        Initialize the converter with parsed DBM/JDT and FRM files.

        Args:
            dbm: Parsed DBM file structure (or JDT for backward compatibility)
            frm_files: Dictionary of parsed FRM files
            jdt: Parsed JDT file structure (alternative to dbm parameter)
        """
        # Support both dbm and jdt parameters
        if jdt is not None:
            self.jdt = jdt
            self.dbm = None
            self.is_jdt = True
        elif isinstance(dbm, XeroxJDT):
            self.jdt = dbm
            self.dbm = None
            self.is_jdt = True
        else:
            self.dbm = dbm
            self.jdt = None
            self.is_jdt = False

        self.frm_files = frm_files or {}
        self.output_lines = []
        self.indent_level = 0
        self.font_mappings = {}  # Maps VIPP font aliases to DFA font names
        self.font_sizes = {}  # Maps DFA font names to their sizes for position correction
        self.color_mappings = {}  # Maps VIPP color aliases to DFA color names
        self.variables = {}  # Tracks variables for VSUB handling

        # Universal converter configuration
        self.input_config = InputDataConfig()
        self.dfa_config = DFAGenerationConfig()
        self.format_registry = {}  # Maps PREFIX values to DOCFORMAT names

        # Track SETLSP (line spacing) from DBM/JDT
        self.line_spacing = None  # Will be set if SETLSP found in DBM/JDT

        # Track SETPAGEDEF layout positions for OUTLINE generation
        self.page_layout_position = None  # (x, y) from last SETLKF in SETPAGEDEF

        # Auto-detect input format from DBM or JDT
        if not self.is_jdt:
            self._detect_input_format()
            self._build_format_registry()
            self._extract_layout_info()
        else:
            # JDT uses line mode, not delimited records
            self.input_config.delimiter = None
            self.dfa_config.channel_code = self.jdt.pcc_mode if self.jdt else 'ANSI'

    def generate_dfa_code(self) -> str:
        """
        Generate DFA code from the parsed VIPP structures (DBM or JDT).

        Returns:
            Generated DFA code as a string
        """
        self.output_lines = []
        self.indent_level = 0

        # Route to JDT-specific generation if this is a JDT file
        if self.is_jdt:
            return self._generate_jdt_dfa_code()

        # Generate header
        self._generate_header()

        # Generate font definitions
        self._generate_fonts()

        # Generate color definitions
        self._generate_colors()

        # Generate main document format
        self._generate_docformat_main()

        return '\n'.join(self.output_lines)

    def _generate_jdt_dfa_code(self) -> str:
        """
        Generate DFA code specifically for JDT (Job Descriptor Ticket) files.
        JDT files use Line Mode processing instead of database mode.

        Returns:
            Generated DFA code as a string
        """
        # Generate header with LINE MODE configuration
        self._generate_jdt_header()

        # Generate font definitions
        self._generate_jdt_fonts()

        # Generate color definitions
        self._generate_jdt_colors()

        # Generate main document format with line mode processing
        self._generate_jdt_docformat_main()

        # End of document definition (no ENDDOCDEF in DFA — not a valid command)

        return '\n'.join(self.output_lines)

    def _generate_jdt_header(self):
        """Generate DFA header for JDT file with LINE MODE configuration."""
        import os
        from datetime import datetime

        # Extract base name for DOCDEF
        docdef_name = ''.join(c for c in os.path.splitext(os.path.basename(self.jdt.filename))[0] if c.isalnum())
        docdef_name = docdef_name.upper()

        self.add_line("/* Generated by Xerox JDT to Papyrus DocDEF Converter */")
        self.add_line(f"/* Source: {self.jdt.filename} */")
        self.add_line(f"/* Conversion Date: {datetime.now().strftime('%Y-%m-%d')} */")
        self.add_line("")

        if self.jdt.title:
            self.add_line(f"/* Original Title: {self.jdt.title} */")
        if self.jdt.creator:
            self.add_line(f"/* Original Creator: {self.jdt.creator} */")
        if self.jdt.creation_date:
            self.add_line(f"/* Original Date: {self.jdt.creation_date} */")
        if self.jdt.application:
            self.add_line(f"/* Application: {self.jdt.application} */")

        self.add_line("")
        self.add_line(f"DOCDEF {docdef_name};")
        self.add_line("")

        # Input format - LINE MODE
        self.add_line("/* Input format specification - LINE MODE */")
        self.add_line("APPLICATION-INPUT-FORMAT")
        self.indent()
        self.add_line("CODE 1252")
        self.add_line("RECORD-FORMAT VARPC")
        self.add_line("RECORD-DELIMITER X'0D0A'")
        self.add_line("RECORD-LENGTH 4096")

        # Channel code - must be NO because header is not in CHANNEL mode
        self.add_line("CHANNEL-CODE NO")

        self.add_line("TABLE-REF-CODE NO")
        self.add_line("DECIMAL-SEPARATOR '.'")
        self.add_line("CACHELIMIT 100;")
        self.dedent()
        self.add_line("")

        # Output format
        self.add_line("/* Output format specification */")
        self.add_line("APPLICATION-OUTPUT-FORMAT")
        self.indent()
        self.add_line("CODE 1200")
        self.add_line("AFPLRECL 8192")
        self.add_line("PTXUNIT 1440")
        self.add_line("FDFINCLUDE YES")
        self.add_line("TLE YES")
        self.add_line("ACIFINDEX NO;")
        self.dedent()
        self.add_line("")

        self.add_line("DEFINEPDFOUTPUT PDFOUT;")
        self.add_line("")

        # FORMATGROUP with page layout from SETMARGIN/SETGRID
        self.add_line("/* Page Layout - from SETMARGIN and SETGRID */")
        self.add_line("FORMATGROUP MAIN;")
        self.indent()
        self.add_line("SHEET")
        self.indent()
        self.add_line("WIDTH 210 MM")
        self.add_line("HEIGHT 297 MM;")
        self.dedent()
        self.add_line("LAYER 1;")
        self.add_line("LOGICALPAGE 1")
        self.indent()
        self.add_line("SIDE FRONT")
        self.add_line("POSITION 0 0")
        self.add_line("WIDTH 210 MM")
        self.add_line("HEIGHT 297 MM")
        self.add_line("DIRECTION ACROSS")

        # Footer with page numbering
        self.add_line("FOOTER")
        self.indent()
        self.add_line("PP = PP + 1;")
        self.dedent()
        self.add_line("FOOTEREND")

        self.add_line("PRINTFOOTER")
        self.indent()

        # Referenced forms
        if self.jdt.forms:
            for form in self.jdt.forms:
                form_name = ''.join(c for c in os.path.splitext(form)[0] if c.isalnum())
                self.add_line(f"USE FORMAT {form_name} EXTERNAL;")
                self.add_line("")

        # Page layout position from SETMARGIN
        if self.jdt.margins:
            left_mm = self.jdt.margins.get('left', 0) * 25.4 / 72  # Convert PT to MM
            top_mm = self.jdt.margins.get('top', 0) * 25.4 / 72
            self.add_line("OUTLINE PAGELAYOUT")
            self.indent()
            self.add_line(f"POSITION {left_mm:.1f} MM {top_mm:.1f} MM;")
            self.dedent()
            self.add_line("ENDIO;")

        self.dedent()
        self.add_line("PRINTEND;")
        self.dedent()
        self.dedent()
        self.add_line("")

    def _generate_jdt_fonts(self):
        """Generate font definitions from JDT file."""
        if not self.jdt.fonts:
            return

        self.add_line("/* Font Definitions - from INDEXFONT commands */")

        for font_alias, font_obj in self.jdt.fonts.items():
            # Map VIPP font names to common font names
            font_physical = self.FONT_STYLE_MAPPINGS.get(font_obj.name.upper(), font_obj.name)

            # Store mapping for later use
            self.font_mappings[font_alias] = font_alias
            self.font_sizes[font_alias] = font_obj.size

            self.add_line(f"FONT {font_alias.upper()} NOTDEF AS '{font_physical}' DBCS ROTATION 0 HEIGHT {font_obj.size};")

        # Add standard fonts for generic compatibility
        standard_fonts = {
            'NCR': ('Times New Roman', 8.0),
            'F7': ('Times New Roman', 8.0),
            'F6': ('Arial', 8.0),
            'FA': ('Arial Bold', 9.0),
            'F2': ('Arial', 8.0),
        }

        for font_alias, (font_name, height) in standard_fonts.items():
            # Only add if not already defined
            if font_alias.upper() not in [k.upper() for k in self.jdt.fonts.keys()]:
                self.add_line(f"FONT {font_alias} NOTDEF AS '{font_name}' DBCS ROTATION 0 HEIGHT {height};")
                self.font_mappings[font_alias] = font_alias
                self.font_sizes[font_alias] = height

        self.add_line("")

    def _generate_jdt_colors(self):
        """Generate color definitions from JDT file."""
        if not self.jdt.colors:
            # Add default colors with short names (B, WHITE, R)
            self.add_line("/* Color Definitions */")
            self.add_line("DEFINE B COLOR RGB RVAL 0 GVAL 0 BVAL 0;")
            self.add_line("DEFINE WHITE COLOR RGB RVAL 100 GVAL 100 BVAL 100;")
            self.add_line("DEFINE R COLOR RGB RVAL 100 GVAL 0 BVAL 0;")
            self.add_line("")
            return

        self.add_line("/* Color Definitions */")

        for color_alias, color_obj in self.jdt.colors.items():
            if color_obj.color_model == 'RGB':
                r = color_obj.red
                g = color_obj.green
                b = color_obj.blue
                self.add_line(f"DEFINE {color_alias} COLOR RGB RVAL {r} GVAL {g} BVAL {b};")

        self.add_line("")

    def _convert_xerox_position_to_dfa(self, x_xerox: int, y_xerox: int) -> Tuple[str, str]:
        """
        Convert Xerox positions (0-2440 internal resolution) to DFA expressions.

        VPF Point 1: Xerox uses internal resolution of 2440 units.
        Formula: POSITION (UNIH*#xpos) (MTOP+UNIH*#ypos)

        Args:
            x_xerox: Horizontal position in Xerox units (0-2440)
            y_xerox: Vertical position in Xerox units

        Returns:
            Tuple of (x_dfa_expr, y_dfa_expr) as strings
        """
        x_dfa = f"UNIH*#{x_xerox}"
        y_dfa = f"MTOP+UNIH*#{y_xerox}"
        return (x_dfa, y_dfa)

    def _generate_jdt_docformat_main(self):
        """Generate main DOCFORMAT for JDT with line mode processing."""
        self.add_line("/* Main document format - LINE MODE PROCESSING */")
        self.add_line("DOCFORMAT THEMAIN;")
        self.indent()

        # Set line spacing
        self.add_line("SETUNITS LINESP 4 MM;")

        # Line mode processing loop
        self.add_line("/* Line mode processing - reads one line at a time */")
        self.add_line("FOR N")
        self.indent()
        self.add_line("REPEAT 1;")
        self.add_line("RECORD INPUTREC")
        self.indent()
        self.add_line("REPEAT 1;")
        self.add_line("VARIABLE LINE1 SCALAR START 1;")
        self.dedent()
        self.add_line("ENDIO;")
        self.dedent()

        # Check for page break
        self.add_line("/* Check for page break (form feed '1') */")
        self.add_line("IF LINE1=='1' OR $EOF;")
        self.add_line("THEN;")
        self.indent()
        self.add_line("ENDGROUP;")
        self.add_line("ENDDOCUMENT;")
        self.dedent()
        self.add_line("ELSE;")
        self.indent()

        # VPF Point 3: Proper document structure - extract channel code and content
        self.add_line("/* Reset to continue processing */")
        self.add_line("N = 0;")
        self.add_line("C = C+1;")
        self.add_line("")
        self.add_line("/* Extract carriage control character and content */")
        self.add_line("CC[C] = LEFT(LINE1,1, '');")
        self.add_line("CONTENT[C] = SUBSTR(LINE1,2,LENGTH(LINE1)-1, '');")
        self.add_line("")

        self.dedent()
        self.add_line("ENDIF;")
        self.dedent()
        self.add_line("ENDFOR;")
        self.add_line("")

        # VPF Point 2: Evaluate ALL conditions after reading complete document
        if self.jdt.conditions:
            self._generate_condition_evaluation_block()

        # Generate output based on RPE arrays
        self.add_line("/* Output generation based on RPE arrays */")
        self.add_line("/* This section will output formatted content */")
        self.add_line("")

        # Generate DOCFORMAT sections for each condition
        self._generate_jdt_condition_formats()

        self.dedent()  # End THEMAIN content
        self.add_line("ENDFORMAT;")
        self.add_line("")

        # Generate default format (separate DOCFORMAT)
        self.add_line("/* Default format - output full line */")
        self.add_line("DOCFORMAT FMT_DEFAULT;")
        self.indent()
        self.add_line("OUTLINE")
        self.indent()
        self.add_line("POSITION LEFT NEXT")
        self.add_line("DIRECTION ACROSS;")
        self.add_line("")
        self.add_line("OUTPUT CONTENT[C]")
        self.indent()
        self.add_line("FONT NCR NORMAL")
        self.add_line("POSITION (SAME) (NEXT)")
        self.add_line("COLOR B;")
        self.dedent()
        self.dedent()
        self.add_line("ENDIO;")
        self.dedent()
        self.add_line("ENDFORMAT;")
        self.add_line("")

        # Initialization - CRITICAL: Read header lines first
        self.add_line("/* Initialization */")
        self.add_line("DOCFORMAT $_BEFOREFIRSTDOC;")
        self.indent()
        self.add_line("PP = 0;")
        self.add_line("/* Page counter */")
        self.add_line("VAR_DT1 = 0;")
        self.add_line("VAR_DT2 = 0;")
        self.add_line("VAR_INIT = 0;")
        self.add_line("")

        # Add UNIH unit variables for Xerox-to-DFA position conversion (VPF Point 1)
        self.add_line("/* Xerox positioning units - from SETMARGIN */")
        self.add_line("VARIABLE UNIH SCALAR DECIMAL;")
        self.add_line("UNIH = $LP_WIDTH/2440;")
        self.add_line("")

        # Extract margin values from SETMARGIN
        mtop = self.jdt.margins.get('top', 140) if self.jdt.margins else 140
        mleft = self.jdt.margins.get('left', 30) if self.jdt.margins else 30
        mright = self.jdt.margins.get('right', 100) if self.jdt.margins else 100

        self.add_line(f"VARIABLE MTOP SCALAR DECIMAL;")
        self.add_line(f"MTOP = UNIH*{mtop};")
        self.add_line(f"VARIABLE MLEFT SCALAR DECIMAL;")
        self.add_line(f"MLEFT = UNIH*{mleft};")
        self.add_line(f"VARIABLE MRIGHT SCALAR DECIMAL;")
        self.add_line(f"MRIGHT = UNIH*{mright};")
        self.add_line("")

        # Add arrays for document structure (VPF Point 3)
        self.add_line("/* Document structure arrays */")
        self.add_line("VARIABLE C SCALAR INTEGER;")
        self.add_line("VARIABLE CONTENT ARRAY 10000 VARCHAR 1024;")
        self.add_line("VARIABLE CC ARRAY 10000 VARCHAR 1;")
        self.add_line("C = 1;")
        self.add_line("CONTENT[C] = '1';")
        self.add_line("")

        # Add line tracking variables for FROMLINE output
        if self.jdt.rpe_lines:
            self.add_line("/* Line tracking variables for FROMLINE output */")
            self.add_line("VARIABLE LIN SCALAR INTEGER;")
            self.add_line("VARIABLE MEASURE SCALAR INTEGER;")
            self.add_line("VARIABLE Z SCALAR INTEGER;")
            self.add_line("VARIABLE II SCALAR INTEGER;")
            self.add_line("")

        # Add condition flags for SETRCD conditions (VPF Point 2)
        if self.jdt.conditions:
            self.add_line("/* Condition flags for SETRCD */")
            for cond_name in sorted(self.jdt.conditions.keys()):
                self.add_line(f"VARIABLE {cond_name} SCALAR INTEGER INITIAL 0;")
            self.add_line("")

        # Add header reading loop
        self.add_line("FOR I")
        self.indent()
        self.add_line("REPEAT 1;")
        self.add_line("RECORD DATAHEADER")
        self.indent()
        self.add_line("REPEAT 1;")
        self.add_line("VARIABLE LINE1 SCALAR NOSPACE START 1;")
        self.dedent()
        self.add_line("ENDIO;")
        self.dedent()

        self.add_line("/* Field (Standard) Names: FLD1, FLD2, etc. */")
        self.add_line("IF LINE1=='1';")
        self.add_line("THEN;")
        self.add_line("ELSE;")
        self.indent()
        self.add_line("I = 0;")
        self.dedent()
        self.add_line("ENDIF;")
        self.dedent()
        self.add_line("ENDFOR;")
        self.dedent()
        self.add_line("ENDFORMAT;")
        self.add_line("")

    def _generate_simple_condition_check(self, cond_name: str, cond: 'XeroxCondition'):
        """
        Generate a simple condition check for SETRCD.

        VPF Point 2: Simple conditions check SUBSTR in the FOR C loop.
        Example: IF NOSPACE(SUBSTR(CONTENT[C],1,7, ''))=='Period:'; THEN; IF_CND1=1; ENDIF;

        Position offset: VIPP positions include channel code (col 1), but CONTENT[C]
        has channel code already stripped, so subtract 1. DFA SUBSTR is 1-based,
        so minimum position is 1.
        """
        # Adjust position: subtract 1 for channel code, minimum 1 (DFA is 1-based)
        dfa_pos = max(1, cond.position - 1)

        # Build the operator mapping
        op_map = {
            'eq': '==', 'ne': '<>', 'gt': '>', 'lt': '<',
            'HOLD': '=='
        }
        dfa_op = op_map.get(cond.operator, '==')

        # Build SUBSTR expression with NOSPACE wrapper
        substr_expr = f"NOSPACE(SUBSTR(CONTENT[C],{dfa_pos},{cond.length}, ''))"

        if cond.operator == 'HOLD':
            self.add_line(f"/* {cond_name}: HOLD condition */")

        self.add_line(f"IF {substr_expr}{dfa_op}'{cond.value}';")
        self.add_line("THEN;")
        self.indent()
        self.add_line(f"{cond_name} = 1;")
        self.dedent()
        self.add_line("ENDIF;")

    def _generate_compound_condition_check(self, cond_name: str, cond: 'XeroxCondition'):
        """
        Generate compound condition check combining other conditions.

        VPF Point 2: Compound conditions use AND/OR on other condition flags.
        Example: IF ISTRUE(IF_CND1) OR ISTRUE(IF_CND2) THEN IF_CND3=1 ENDIF
        """
        if not cond.sub_conditions or len(cond.sub_conditions) < 2:
            return

        # Build condition expression
        conditions_expr = []
        for sub_cond in cond.sub_conditions:
            conditions_expr.append(f"ISTRUE({sub_cond}==1)")

        operator_str = " OR " if cond.compound_operator == "or" else " AND "
        full_expr = operator_str.join(conditions_expr)

        self.add_line(f"IF {full_expr};")
        self.add_line("THEN;")
        self.indent()
        self.add_line(f"{cond_name} = 1;")
        self.dedent()
        self.add_line("ENDIF;")

    def _generate_condition_evaluation_block(self):
        """
        Generate FOR C loop that evaluates all SETRCD conditions.

        VPF Point 2: All conditions are evaluated by looping through CONTENT array
        and checking SUBSTR matches. Compound conditions are evaluated after simple ones.
        """
        self.add_line("/* VPF Point 2: Evaluate all SETRCD conditions */")
        self.add_line("FOR C")
        self.indent()
        self.add_line("REPEAT MAXINDEX(CONTENT);")
        self.add_line("")

        # Reset all condition flags at start of each page
        self.add_line("/* Reset condition flags */")
        for cond_name in sorted(self.jdt.conditions.keys()):
            cond = self.jdt.conditions[cond_name]
            if cond.operator != 'HOLD':  # HOLD conditions preserve their value
                self.add_line(f"{cond_name} = 0;")
        self.add_line("")

        # Generate simple conditions first
        self.add_line("/* Simple condition checks */")
        for cond_name, cond in sorted(self.jdt.conditions.items()):
            if not cond.is_compound:
                self._generate_simple_condition_check(cond_name, cond)
                self.add_line("")

        # Generate compound conditions after simple ones
        self.add_line("/* Compound condition checks */")
        for cond_name, cond in sorted(self.jdt.conditions.items()):
            if cond.is_compound:
                self._generate_compound_condition_check(cond_name, cond)
                self.add_line("")

        self.dedent()
        self.add_line("ENDFOR;")
        self.add_line("")

    def _group_rpe_by_condition(self, line_num: int) -> List[Tuple[str, List]]:
        """
        Group RPE arrays by their condition_name for a given FROMLINE.

        Returns:
            List of tuples (condition_name, [rpe_arrays])
            Preserves source order: unconditional first, IF_CND* in parse order, ELSE last.
        """
        if line_num not in self.jdt.rpe_lines:
            return []

        # Use ordered dict to preserve parse order
        grouped = {}
        order = []
        for rpe in self.jdt.rpe_lines[line_num]:
            cond = rpe.condition_name if rpe.condition_name else ""
            if cond not in grouped:
                grouped[cond] = []
                order.append(cond)
            grouped[cond].append(rpe)

        # Return in order: unconditional first, IF_CND* in parse order, ELSE last
        result = []
        if "" in grouped:
            result.append(("", grouped[""]))
        for cond in order:
            if cond != "" and cond != "ELSE":
                result.append((cond, grouped[cond]))
        if "ELSE" in grouped:
            result.append(("ELSE", grouped["ELSE"]))

        return result

    def _generate_rpe_output_statement(self, rpe: 'XeroxRPEArray', use_measure: bool = False,
                                     measure_offset: int = 0):
        """
        Generate a single OUTPUT statement from RPE array.

        VPF Point 1 & 4: Uses UNIH positioning and handles field extraction.

        Args:
            rpe: RPE array to convert
            use_measure: If True, use MEASURE variable for Y position
            measure_offset: Offset to add to MEASURE
        """
        # Determine output content
        # Position offset: VIPP positions include channel code (col 1), but CONTENT
        # has channel code stripped, so subtract 1. DFA SUBSTR is 1-based, min = 1.
        if rpe.literal_text:
            # Literal text output
            content_expr = f"'{rpe.literal_text}'"
        elif rpe.special_call:
            # Special resource call (SCALL)
            self.add_line(f"/* WARNING: SCALL {rpe.literal_text} - placeholder generated */")
            content_expr = f"'[{rpe.literal_text}]'"
        else:
            # Field extraction from CONTENT array
            dfa_start = max(1, rpe.start_position - 1)
            if rpe.length > 0:
                content_expr = f"SUBSTR(CONTENT[II],{dfa_start},{rpe.length}, '')"
            else:
                content_expr = f"CONTENT[II]"

        # Generate OUTPUT statement
        self.add_line(f"OUTPUT {content_expr}")
        self.indent()

        # Font
        font_name = rpe.font if rpe.font else "NCR"
        self.add_line(f"FONT {font_name} NORMAL")

        # Position using UNIH
        x_dfa, y_dfa = self._convert_xerox_position_to_dfa(rpe.x_position, rpe.horizontal_position)

        if use_measure:
            # Use MEASURE variable for vertical position
            y_dfa = f"MTOP+UNIH*MEASURE"
            if measure_offset != 0:
                y_dfa = f"MTOP+UNIH*(MEASURE+#{measure_offset})"

        self.add_line(f"POSITION ({x_dfa}) ({y_dfa})")

        # Color — map long names to short DFA names
        color_name = rpe.color if rpe.color else "B"
        color_map = {'BLACK': 'B', 'RED': 'R', 'BLUE': 'BLUE', 'GREEN': 'GREEN'}
        color_name = color_map.get(color_name.upper(), color_name)
        self.add_line(f"COLOR {color_name};")

        self.dedent()

    def _generate_fromline_output(self, line_num: int, rpe_arrays: List['XeroxRPEArray']):
        """
        Generate output for a FROMLINE with channel code checking.

        VPF Point 4: Uses LIN and MEASURE variables for line tracking and positioning.
        Checks CC[LIN+1] for channel continuation.
        """
        if not rpe_arrays:
            return

        self.add_line(f"/* FROMLINE {line_num} output */")
        self.add_line(f"LIN = {line_num};")

        # Calculate initial MEASURE based on line number (approximate)
        # Each line is roughly 50 units apart in Xerox coordinates
        initial_measure = 320 + (line_num - 11) * 50
        self.add_line(f"MEASURE = {initial_measure};")
        self.add_line("")

        # Channel code checking loop
        self.add_line("FOR Z")
        self.indent()
        self.add_line("REPEAT 1;")
        self.add_line("")

        # Output all RPE arrays for this line
        self.add_line("II = LIN;")
        for rpe in rpe_arrays:
            self._generate_rpe_output_statement(rpe, use_measure=False, measure_offset=0)
            self.add_line("")

        # Check for line continuation via channel code
        # '-' means continuation line — keep looping; anything else stops
        self.add_line("/* Check channel code for continuation */")
        self.add_line("IF CC[LIN+1]=='-';")
        self.add_line("THEN;")
        self.indent()
        self.add_line("LIN = LIN+1;")
        self.add_line("MEASURE = MEASURE+50;")
        self.add_line("Z = 0;")
        self.dedent()
        self.add_line("ENDIF;")
        self.add_line("")

        self.dedent()
        self.add_line("ENDFOR;")
        self.add_line("")

    def _generate_nested_condition_block(self, conditions: List[Tuple[str, List]], depth: int = 0):
        """
        Generate nested IF/ELSE/ENDIF blocks for conditional RPE arrays.

        VPF Point 5: Handles IF/ELSE IF/ELSE/ENDIF chains from /ENDIFALL markers.
        Generates:
            IF cond1; THEN; ...
            ELSE; IF cond2; THEN; ...
            ELSE; (default)
            ENDIF; ENDIF;  (one per IF)
        """
        if not conditions:
            return

        if_count = 0  # Track how many IFs we open

        for i, (cond_name, arrays) in enumerate(conditions):
            if cond_name == "ELSE":
                # Default ELSE clause (should be last in list)
                self.add_line("ELSE;")
                self.indent()
                for rpe in arrays:
                    self._generate_rpe_output_statement(rpe, use_measure=True, measure_offset=0)
                    self.add_line("")
                self.dedent()
            elif i == 0:
                # First condition — plain IF
                self.add_line(f"IF ISTRUE({cond_name}==1);")
                self.add_line("THEN;")
                self.indent()
                for rpe in arrays:
                    self._generate_rpe_output_statement(rpe, use_measure=True, measure_offset=0)
                    self.add_line("")
                self.dedent()
                if_count += 1
            else:
                # Subsequent conditions — ELSE IF
                self.add_line(f"ELSE; IF ISTRUE({cond_name}==1);")
                self.add_line("THEN;")
                self.indent()
                for rpe in arrays:
                    self._generate_rpe_output_statement(rpe, use_measure=True, measure_offset=0)
                    self.add_line("")
                self.dedent()
                if_count += 1

        # Close all nested IFs — one ENDIF per IF opened
        for _ in range(if_count):
            self.add_line("ENDIF;")

    def _generate_conditional_rpe_output(self, line_num: int, conditional_groups: List[Tuple[str, List]]):
        """
        Generate conditional output for RPE arrays with nested IF/ELSE.

        VPF Point 5: Generates nested IF ISTRUE(IF_CNDxx==1) blocks based on
        condition_name from RPE arrays.
        """
        if not conditional_groups:
            return

        self.add_line(f"/* Conditional output for line {line_num} */")
        self.add_line(f"II = {line_num};")
        self.add_line("")

        # Build nested structure
        self._generate_nested_condition_block(conditional_groups, depth=0)
        self.add_line("")

    def _generate_jdt_condition_formats(self):
        """
        Generate output based on RPE arrays from FROMLINE sections.

        VPF Points 4 & 5: Uses FROMLINE data to generate OUTPUT statements with
        proper positioning, channel code checking, and conditional logic.
        """
        if not self.jdt.rpe_lines:
            self.add_line("/* No RPE arrays to process */")
            return

        self.add_line("/* RPE-based output generation */")
        self.add_line("")

        # Process each FROMLINE
        for line_num in sorted(self.jdt.rpe_lines.keys()):
            grouped = self._group_rpe_by_condition(line_num)

            if not grouped:
                continue

            # Separate unconditional and conditional RPE arrays
            unconditional = []
            conditional_groups = []

            for cond_name, arrays in grouped:
                if cond_name == "":
                    unconditional = arrays
                else:
                    conditional_groups.append((cond_name, arrays))

            # Generate unconditional output first
            if unconditional:
                self._generate_fromline_output(line_num, unconditional)

            # Generate conditional output
            if conditional_groups:
                # Handle /ELSE/IF_CND pattern from JDT
                # Need to build proper nested structure
                nested_structure = []
                for i, (cond_name, arrays) in enumerate(conditional_groups):
                    nested_structure.append((cond_name, arrays))

                # Check if last condition should be ELSE
                # (In JDT, last condition before /ENDIFALL is often the default)
                if nested_structure:
                    self._generate_conditional_rpe_output(line_num, nested_structure)

        self.add_line("")

    def generate_frm_dfa_code(self, frm: XeroxFRM, as_include: bool = False) -> str:
        """
        Generate a standalone DFA file for an FRM file.

        Each FRM becomes its own DFA file that can be referenced via USE FORMAT.

        Args:
            frm: Parsed FRM file structure
            as_include: If True, don't wrap in DOCFORMAT (for external includes)

        Returns:
            Generated DFA code as a string
        """
        self.output_lines = []
        self.indent_level = 0

        # Extract FRM name without extension
        frm_name = os.path.splitext(os.path.basename(frm.filename))[0].upper()
        frm_name = ''.join(c for c in frm_name if c.isalnum() or c == '_')

        # Generate FRM DFA header
        self.add_line(f"/* FRM DFA File: {frm.filename} */")
        self.add_line(f"/* Generated by Universal Xerox FreeFlow to Papyrus DocDEF Converter */")
        if frm.title:
            self.add_line(f"/* Original Title: {frm.title} */")
        if frm.creator:
            self.add_line(f"/* Original Creator: {frm.creator} */")
        if frm.creation_date:
            self.add_line(f"/* Original Date: {frm.creation_date} */")
        self.add_line("")

        if not as_include:
            # Generate DOCFORMAT for this FRM
            self.add_line(f"DOCFORMAT {frm_name};")
            self.indent()

            # Set margins and units
            self.add_line("MARGIN TOP 0 MM BOTTOM 0 MM LEFT 0 MM RIGHT 0 MM;")
            self.add_line("SETUNITS LINESP AUTO;")
            self.add_line("")

            # Generate OUTLINE block for FRM content
            self.add_line("OUTLINE")
            self.indent()
            self.add_line("POSITION (0 MM) (0 MM)")
            self.add_line("DIRECTION ACROSS;")
            self.add_line("")

            # Convert FRM commands to DFA
            self._convert_frm_commands(frm)

            self.dedent()
            self.add_line("ENDIO;")

            self.dedent()
            self.add_line("")
            self.add_line(f"/* END OF FRM DOCFORMAT {frm_name} */")
        else:
            # Just generate comment header for includes
            self.add_line(f"/* External Format: {frm.filename} */")
            self.add_line("")

            # Add OUTLINE wrapper for FRM commands
            self.add_line("OUTLINE ")
            self.indent()
            self.add_line("POSITION (0 MM) (0 MM)")
            self.add_line("DIRECTION ACROSS;")
            self.add_line("")            

            # Convert FRM commands
            self._convert_frm_commands(frm)

            # Close OUTLINE
            self.add_line("ENDIO;")

        return '\n'.join(self.output_lines)

    def _convert_frm_commands(self, frm: XeroxFRM):
        """
        Convert FRM commands to DFA OUTPUT and control structures.

        Args:
            frm: Parsed FRM file structure
        """
        current_x = 0.0
        current_y = 0.0
        current_font = "ARIAL08"

        # Track whether position was explicitly set (to distinguish from residual values)
        x_was_explicitly_set = False
        y_was_explicitly_set = False
        y_is_next_line = False  # Track if next OUTPUT should use NEXT (after NL)

        in_conditional = False
        conditional_depth = 0

        # Track CACHE command for SCALL processing
        last_cache_cmd = None

        # Track current color
        current_color = None

        for cmd in frm.commands:
            # Handle font changes
            if cmd.name == 'SETFONT':
                if cmd.parameters:
                    current_font = cmd.parameters[0].upper()
                continue

            # Handle color changes
            if cmd.name == 'SETCOLOR':
                if cmd.parameters:
                    current_color = cmd.parameters[0].upper()
                continue

            # Handle positioning - MOVETO
            if cmd.name == 'MOVETO':
                if len(cmd.parameters) >= 2:
                    try:
                        current_x = float(cmd.parameters[0])
                        current_y = float(cmd.parameters[1])
                        x_was_explicitly_set = True
                        y_was_explicitly_set = True
                        y_is_next_line = False  # Explicit Y position overrides NEXT
                    except ValueError:
                        pass
                continue

            # Handle horizontal move - MOVEH
            if cmd.name == 'MOVEH':
                if cmd.parameters:
                    try:
                        current_x = float(cmd.parameters[0])
                        x_was_explicitly_set = True
                        y_was_explicitly_set = False  # Y becomes implicit (use SAME)
                        y_is_next_line = False  # MOVEH resets next-line flag, Y should be SAME
                    except ValueError:
                        pass
                continue

            # Handle NL (newline) - OUTPUT '' POSITION SAME NEXT
            if cmd.name == 'NL':
                y_position = 'NEXT'

                if cmd.parameters:
                    try:
                        spacing_val = float(cmd.parameters[0])
                        if spacing_val < 0:
                            # Negative NL: move up by N mm from current position
                            # Example: -04 NL becomes SAME-4.0 MM
                            distance_up = abs(spacing_val)
                            y_position = f"SAME-{distance_up} MM"
                        else:
                            # Positive NL: move down by N mm from current position
                            # Example: 0.3 NL becomes SAME+0.3 MM
                            y_position = f"SAME+{spacing_val} MM"
                    except ValueError:
                        pass

                self.add_line("OUTPUT ''")
                self.add_line(f"    FONT {current_font} NORMAL")
                self.add_line(f"    {self._format_position('SAME', y_position)};")

                # After NL, next OUTPUT should use NEXT (advance to next line)
                y_was_explicitly_set = False
                y_is_next_line = True
                continue

            # Handle SETLSP (line spacing)
            if cmd.name == 'SETLSP':
                if cmd.parameters:
                    spacing_val = cmd.parameters[0]
                    self.add_line(f"SETUNITS LINESP {spacing_val} MM;")
                else:
                    self.add_line("SETUNITS LINESP AUTO;")
                continue

            # Handle IF conditional
            if cmd.name == 'IF':
                # Check if condition contains only definition keywords
                DEFINITION_KEYWORDS = {'INDEXBAT', 'INDEXFONT', 'INDEXCOLOR', 'SETUNIT', 'MM', 'CM', 'INCH', 'null'}
                filtered = [p for p in cmd.parameters if p in DEFINITION_KEYWORDS]

                condition = self._convert_frm_condition(cmd.parameters)

                # Add comment if definition keywords were filtered out
                if filtered and condition == "TRUE":
                    self.add_line(f"/* Original IF had definition commands: {' '.join(filtered)} */")
                    self.add_line(f"/* These are not boolean tests - IF is unconditional */")

                self.add_line(f"IF {condition}; THEN;")

                # Process children commands if present (nested block)
                if cmd.children:
                    # Recursively convert child commands with updated context
                    self._convert_frm_command_list(cmd.children, current_x, current_y, current_font, frm)
                    # Output ENDIF after processing children
                    self.add_line("ENDIF;")
                else:
                    # No children - just increment depth for flat IF structure
                    self.indent()
                    conditional_depth += 1
                    in_conditional = True
                continue

            # Handle ELSE
            if cmd.name == 'ELSE':
                self.dedent()
                self.add_line("ELSE;")
                self.indent()
                continue

            # Handle ENDIF
            if cmd.name == 'ENDIF':
                # Only process ENDIF if there's an open flat IF structure (conditional_depth > 0)
                # If conditional_depth == 0, this is a standalone ENDIF after a block IF {...},
                # which already generated its own ENDIF
                if conditional_depth > 0:
                    self.dedent()
                    self.add_line("ENDIF;")
                    conditional_depth -= 1
                    if conditional_depth == 0:
                        in_conditional = False
                continue

            # Handle output commands (SH, SHL, SHR, SHC, SHP)
            if cmd.name in ('SH', 'SHL', 'SHR', 'SHr', 'SHC', 'SHP'):
                self._convert_frm_output(cmd, current_x, current_y, current_font, frm,
                                        x_was_explicitly_set, y_was_explicitly_set, y_is_next_line,
                                        current_color)
                # After output, position becomes implicit and next output should advance to next line
                x_was_explicitly_set = False
                y_was_explicitly_set = False
                y_is_next_line = True
                continue

            # Handle XGFRESDEF resource definitions
            if cmd.name == 'XGFRESDEF':
                self._convert_xgfresdef(cmd, frm)
                continue

            # Handle line drawing - DRAWB converts to RULE in DFA
            if cmd.name == 'DRAWB':
                self._convert_frm_rule(cmd)
                continue

            # Handle resource calls - SCALL (segment/image)
            if cmd.name == 'SCALL':
                self._convert_frm_segment(cmd, current_x, current_y, frm, last_cache_cmd,
                                         x_was_explicitly_set, y_was_explicitly_set)
                last_cache_cmd = None  # Clear after use
                # Reset position tracking after SCALL
                x_was_explicitly_set = False
                y_was_explicitly_set = False
                continue

            # Handle image calls - ICALL
            if cmd.name == 'ICALL':
                self._convert_frm_image(cmd, current_x, current_y)
                continue

            # Handle CACHE (resource caching with scale)
            if cmd.name == 'CACHE':
                # Store CACHE command for next SCALL
                last_cache_cmd = cmd
                continue

            # Handle CLIP/ENDCLIP - not supported in DFA
            if cmd.name in ('CLIP', 'ENDCLIP'):
                self.add_line("/* Note: DFA does not support CLIP/ENDCLIP. */")
                self.add_line("/* Use MARGIN, SHEET/LOGICALPAGE dimensions, WIDTH on TEXT, or image size params instead */")
                continue

            # Skip comments
            if cmd.name == 'COMMENT':
                continue

    def _convert_frm_command_list(self, commands: List[XeroxCommand], start_x: float, start_y: float,
                                    start_font: str, frm: XeroxFRM):
        """
        Recursively convert a list of FRM commands (used for IF block children).

        Args:
            commands: List of commands to convert
            start_x: Starting X position
            start_y: Starting Y position
            start_font: Starting font
            frm: FRM structure for context
        """
        current_x = start_x
        current_y = start_y
        current_font = start_font

        # Track whether position was explicitly set (to distinguish from residual values)
        x_was_explicitly_set = False
        y_was_explicitly_set = False
        y_is_next_line = False  # Track if next OUTPUT should use NEXT (after NL)

        # Track CACHE command for SCALL processing
        last_cache_cmd = None

        # Track current color
        current_color = None

        self.indent()

        for cmd in commands:
            # Handle font changes
            if cmd.name == 'SETFONT':
                if cmd.parameters:
                    current_font = cmd.parameters[0].upper()
                continue

            # Handle color changes
            if cmd.name == 'SETCOLOR':
                if cmd.parameters:
                    current_color = cmd.parameters[0].upper()
                continue

            # Handle positioning - MOVETO
            if cmd.name == 'MOVETO':
                if len(cmd.parameters) >= 2:
                    try:
                        current_x = float(cmd.parameters[0])
                        current_y = float(cmd.parameters[1])
                        x_was_explicitly_set = True
                        y_was_explicitly_set = True
                        y_is_next_line = False  # Explicit Y position overrides NEXT
                    except ValueError:
                        pass
                continue

            # Handle horizontal move - MOVEH
            if cmd.name == 'MOVEH':
                if cmd.parameters:
                    try:
                        current_x = float(cmd.parameters[0])
                        x_was_explicitly_set = True
                        y_was_explicitly_set = False  # Y becomes implicit (use SAME)
                        y_is_next_line = False  # MOVEH resets next-line flag, Y should be SAME
                    except ValueError:
                        pass
                continue

            # Handle NL (newline)
            if cmd.name == 'NL':
                y_position = 'NEXT'

                if cmd.parameters:
                    try:
                        spacing_val = float(cmd.parameters[0])
                        if spacing_val < 0:
                            # Negative NL: move up by N mm from current position
                            # Example: -04 NL becomes SAME-4.0 MM
                            distance_up = abs(spacing_val)
                            y_position = f"SAME-{distance_up} MM"
                        else:
                            # Positive NL: move down by N mm from current position
                            # Example: 0.3 NL becomes SAME+0.3 MM
                            y_position = f"SAME+{spacing_val} MM"
                    except ValueError:
                        pass

                self.add_line("OUTPUT ''")
                self.add_line(f"    FONT {current_font} NORMAL")
                self.add_line(f"    {self._format_position('SAME', y_position)};")

                # After NL, next OUTPUT should use NEXT (advance to next line)
                y_was_explicitly_set = False
                y_is_next_line = True
                continue

            # Handle SETLSP (line spacing)
            if cmd.name == 'SETLSP':
                if cmd.parameters:
                    spacing_val = cmd.parameters[0]
                    self.add_line(f"SETUNITS LINESP {spacing_val} MM;")
                else:
                    self.add_line("SETUNITS LINESP AUTO;")
                continue

            # Handle output commands (SH, SHL, SHR, SHC, SHP)
            if cmd.name in ('SH', 'SHL', 'SHR', 'SHr', 'SHC', 'SHP'):
                self._convert_frm_output(cmd, current_x, current_y, current_font, frm,
                                        x_was_explicitly_set, y_was_explicitly_set, y_is_next_line,
                                        current_color)
                # After output, position becomes implicit and next output should advance to next line
                x_was_explicitly_set = False
                y_was_explicitly_set = False
                y_is_next_line = True
                continue

            # Handle SCALL (segment call)
            if cmd.name == 'SCALL':
                self._convert_frm_segment(cmd, current_x, current_y, frm, last_cache_cmd,
                                         x_was_explicitly_set, y_was_explicitly_set)
                last_cache_cmd = None  # Clear after use
                # Reset position tracking after SCALL
                x_was_explicitly_set = False
                y_was_explicitly_set = False
                continue

            # Handle ICALL (image call)
            if cmd.name == 'ICALL':
                self._convert_frm_image(cmd, current_x, current_y)
                continue

            # Handle CACHE (resource caching with scale)
            if cmd.name == 'CACHE':
                # Store CACHE command for next SCALL
                last_cache_cmd = cmd
                continue

            # Handle DRAWB (draw box/line)
            if cmd.name == 'DRAWB':
                self._convert_frm_rule(cmd)
                continue

            # Nested IF blocks
            if cmd.name == 'IF' and cmd.children:
                condition = self._convert_frm_condition(cmd.parameters)
                self.add_line(f"IF {condition}; THEN;")
                self._convert_frm_command_list(cmd.children, current_x, current_y, current_font, frm)
                self.add_line("ENDIF;")
                continue

        self.dedent()

    def _convert_frm_condition(self, params: List[str]) -> str:
        """Convert FRM IF condition to DFA format."""
        if not params:
            return "TRUE"

        # Split parameters if they're combined into a single string
        split_params = []
        for param in params:
            if ' ' in param:
                split_params.extend(param.split())
            else:
                split_params.append(param)

        # Filter out definition keywords that should not be in IF conditions
        DEFINITION_KEYWORDS = {'INDEXBAT', 'INDEXFONT', 'INDEXCOLOR', 'SETUNIT', 'MM', 'CM', 'INCH', 'null'}

        # Track what was filtered for debugging
        filtered_params = [p for p in split_params if p in DEFINITION_KEYWORDS]
        split_params = [p for p in split_params if p not in DEFINITION_KEYWORDS]

        # If no parameters remain after filtering, return TRUE
        # This means the IF was unconditional (only had definition commands)
        if not split_params:
            if filtered_params:
                # Add comment showing what was filtered out
                logger.debug(f"IF condition had only definition commands (filtered: {' '.join(filtered_params)}), converting to IF 1")
            return "1"

        # Convert operators and format
        condition_parts = []
        for param in split_params:
            if param.lower() in self.COMPARISON_OPERATORS:
                condition_parts.append(self.COMPARISON_OPERATORS[param.lower()])
            elif param.startswith('/'):
                condition_parts.append(param.lstrip('/'))
            elif param.startswith('(') and param.endswith(')'):
                condition_parts.append(f"'{param[1:-1]}'")
            else:
                condition_parts.append(param)

        return ' '.join(condition_parts)

    def _convert_frm_output(self, cmd: XeroxCommand, x: float, y: float, font: str, frm: XeroxFRM,
                           x_was_set: bool = True, y_was_set: bool = True, y_is_next: bool = False,
                           color: str = None):
        """Convert FRM output command (SH, SHL, SHR, etc.) to DFA OUTPUT or TEXT."""
        text = ""
        is_variable = False
        has_vsub = False
        vsub_alignment = None
        shp_width = None  # Width parameter for SHP

        # Extract text and parameters
        # For SHP, parameters can be: [var, width, align] or [text, width, align]
        for i, param in enumerate(cmd.parameters):
            if param == 'VSUB':
                has_vsub = True
                # Next parameter might be alignment (0=left, 1=right)
                if i + 1 < len(cmd.parameters):
                    try:
                        vsub_alignment = int(cmd.parameters[i + 1])
                    except (ValueError, IndexError):
                        pass
                continue
            elif param.startswith('(') and param.endswith(')'):
                text = param[1:-1]
            elif param.startswith('VAR_') or param.startswith('FLD'):
                text = param
                is_variable = True
            elif cmd.name == 'SHP':
                # SHP has 3 parameters: [var/text, width, align]
                if i == 0 and not text:
                    # First parameter - could be variable or text
                    if param.startswith('VAR_') or param.startswith('FLD'):
                        text = param
                        is_variable = True
                    elif param.startswith('(') and param.endswith(')'):
                        text = param[1:-1]
                    else:
                        text = param
                        is_variable = True
                elif i == 1:
                    # Second parameter is width
                    try:
                        shp_width = float(param)
                    except (ValueError, TypeError):
                        pass
                elif i == 2:
                    # Third parameter is alignment
                    try:
                        vsub_alignment = int(param)
                    except (ValueError, TypeError):
                        pass

        # Determine alignment from command type if not from VSUB
        if vsub_alignment is None:
            if cmd.name == 'SHL':
                vsub_alignment = 0  # Left
            elif cmd.name in ('SHR', 'SHr'):
                vsub_alignment = 1  # Right
            elif cmd.name == 'SHC':
                vsub_alignment = 2  # Center

        if not text:
            return

        # Check if SHP has width parameter - use TEXT command for line wrapping
        if shp_width is not None and shp_width > 0:
            # SHP with width requires TEXT command with WIDTH parameter
            if has_vsub and not is_variable:
                text = self._convert_vsub(text)
                # After VSUB conversion, if text contains ! concatenation, treat as variable
                if ' ! ' in text:
                    is_variable = True
            self._generate_text_with_width(text, x, y, font, shp_width, is_variable, vsub_alignment,
                                          x_was_set, y_was_set, y_is_next, frm)
        # Check if text contains font switches
        elif '~~' in text and not is_variable:
            # Use TEXT command for font switching
            self._generate_text_with_font_switches(text, x, y, font, frm, vsub_alignment,
                                                   x_was_set, y_was_set, y_is_next, color)
        else:
            # Use simple OUTPUT command
            if has_vsub and not is_variable:
                text = self._convert_vsub(text)
                # After VSUB conversion, if text contains ! concatenation, treat as variable
                if ' ! ' in text:
                    is_variable = True
            self._generate_simple_output(text, x, y, font, is_variable, vsub_alignment,
                                        x_was_set, y_was_set, y_is_next, frm, color)

    def _convert_font_switch_simple(self, text: str) -> str:
        """Simple font switch removal - just strip ~~XX patterns for now."""
        import re
        # Remove ~~XX font switch markers
        return re.sub(r'~~[A-Za-z0-9]{1,2}', '', text)

    def _parse_font_switches(self, text: str, default_font: str) -> List[Tuple[str, str]]:
        """
        Parse font switch patterns in text.

        Args:
            text: Text with ~~XX font switches
            default_font: Font to use when no switch specified

        Returns:
            List of (font_alias, text_segment) tuples

        Example:
            "~~FAHello ~~FBWorld ~~FAEnd" -> [('FA', 'Hello '), ('FB', 'World '), ('FA', 'End')]
        """
        import re

        # Pattern: ~~XX where XX is 1-2 alphanumeric characters
        pattern = r'~~([A-Za-z0-9]{1,2})'

        segments = []
        last_pos = 0
        current_font = default_font

        for match in re.finditer(pattern, text):
            # Add text before switch with current font
            if match.start() > last_pos:
                text_segment = text[last_pos:match.start()]
                if text_segment:
                    segments.append((current_font, text_segment))

            # Update current font
            current_font = match.group(1)
            last_pos = match.end()

        # Add remaining text
        if last_pos < len(text):
            text_segment = text[last_pos:]
            if text_segment:
                segments.append((current_font, text_segment))

        return segments

    def _map_font_alias(self, alias: str, frm: XeroxFRM) -> Tuple[str, str]:
        """
        Map VIPP font alias to DFA font name (applying rename if needed).

        Following VIPP semantics:
        - Each font alias IS a specific font with baked-in style
        - Always return NORMAL style (font style is in the definition, not applied at runtime)
        - Apply font_rename_map to get potentially renamed alias

        Args:
            alias: Font alias like 'FA', 'FB', 'F1', 'FE', etc.
            frm: The FRM structure containing font definitions and rename mapping

        Returns:
            Tuple of (dfa_font_name, style) like ('FE_1', 'NORMAL')

        Examples:
            FE (original alias, renamed to FE_1) -> ('FE_1', 'NORMAL')
            FA (no conflict) -> ('FA', 'NORMAL')
        """
        # Apply rename mapping if this is an FRM font that was renamed
        resolved_alias = frm.font_rename_map.get(alias, alias)

        # Look up the DFA font name in font_mappings
        # This handles both renamed fonts (FE_1) and original fonts
        if resolved_alias in self.font_mappings:
            dfa_font = self.font_mappings[resolved_alias]
            return (dfa_font, 'NORMAL')

        # Fallback: check if it's a DBM font
        if alias in self.font_mappings:
            dfa_font = self.font_mappings[alias]
            return (dfa_font, 'NORMAL')

        # Last resort: use alias as-is in uppercase
        return (alias.upper(), 'NORMAL')

    def _generate_text_with_font_switches(self, text: str, x, y,
                                           default_font: str, frm: XeroxFRM, alignment: int = None,
                                           x_was_set: bool = True, y_was_set: bool = True, y_is_next: bool = False,
                                           color: str = None):
        """Generate TEXT command with inline font changes."""
        # Process VSUB variables first
        text = self._convert_vsub(text)

        # Parse font switches
        segments = self._parse_font_switches(text, default_font)

        if len(segments) <= 1:
            # No switches, use simple OUTPUT
            self._generate_simple_output(text, x, y, default_font, False, alignment,
                                        x_was_set, y_was_set, y_is_next, frm, color)
            return

        # Generate TEXT command
        self.add_line("TEXT")
        self.indent()

        # Map default font for position correction
        dfa_font, _ = self._map_font_alias(default_font, frm)

        # For right-aligned text, use LEFT-$MR_LEFT as starting position and x as WIDTH
        if alignment == 1:  # Right aligned
            # Use LEFT-$MR_LEFT as x position
            x_pos = 'LEFT-$MR_LEFT'
            if y_is_next:
                y_pos = 'NEXT'
            elif y_was_set:
                y_pos = y
            else:
                y_pos = 'SAME'

            self.add_line(self._format_position(x_pos, y_pos, dfa_font))

            # Add WIDTH using the original x value
            if x_was_set and x != 'SAME':
                self.add_line(f"WIDTH {x} MM")

            # Add ALIGN RIGHT
            self.add_line("ALIGN RIGHT")
        else:
            # Left or center aligned - use standard position
            x_pos = x if x_was_set else 'SAME'
            if y_is_next:
                y_pos = 'NEXT'  # After NL, use NEXT to stay on the new line
            elif y_was_set:
                y_pos = y  # Explicit position
            else:
                y_pos = 'SAME'  # Implicit position

            # Use helper method for consistent POSITION formatting
            self.add_line(self._format_position(x_pos, y_pos, dfa_font))

        # Add font-switched segments
        for font_alias, text_seg in segments:
            # Skip empty segments (happens when text starts with font switch)
            if not text_seg or text_seg.isspace():
                continue

            # Format the text segment for TEXT command
            formatted_seg = self._format_text_segment_for_text_cmd(text_seg)

            # Skip if formatted segment is just empty quotes (''')
            if formatted_seg.strip() in ["''", "'''", '""', '"""']:
                continue

            # Map font alias to base font + style
            base_font, style = self._map_font_alias(font_alias, frm)

            self.add_line(f"FONT {base_font} {style}")
            self.add_line(formatted_seg)

        self.add_line(";")
        self.dedent()

    def _format_text_segment_for_text_cmd(self, text_seg: str) -> str:
        """
        Format a text segment for use in TEXT command.

        TEXT command syntax differs from OUTPUT:
        - Pure literal: 'text here'
        - Variable with prefix: 'prefix' (VAR)
        - Multiple variables: 'prefix' (VAR1) 'middle' (VAR2)

        Examples:
            'Account Branch / ' -> 'Account Branch / '
            ": ' ! VAR_BRC" -> ': ' (VAR_BRC)
            ": ' ! VAR_SSD ! ' TO ' ! VAR_SED" -> ': ' (VAR_SSD) ' TO ' (VAR_SED)
        """
        import re

        # Check if there are any variables at all
        if ' ! ' not in text_seg:
            # No VSUB variables - just quote the whole thing
            return f"'{text_seg}'"

        # Convert all variable references from OUTPUT format to TEXT format
        # Pattern: ' ! VAR_NAME (with optional following concatenation)
        # Step 1: Replace ' ! VAR_NAME with ' (VAR_NAME)
        result = re.sub(r"' ! ([A-Za-z_][A-Za-z0-9_]*)", r"' (\1)", text_seg)

        # Step 2: Clean up concatenation between variable and next literal
        # Pattern: ) ! ' -> ) '
        result = re.sub(r"\) ! '", r") '", result)

        # Step 3: Add leading quote if the result doesn't start with one
        # This handles cases where the segment starts with a literal before a variable
        # Example: ": ' (VAR)" should become "': ' (VAR)"
        if not result.startswith("'"):
            # Find where the first quote is
            first_quote_pos = result.find("'")
            if first_quote_pos > 0:
                # Add opening quote at the beginning
                result = "'" + result

        return result

    def _format_text_segment(self, text_seg: str) -> str:
        """
        Format a text segment for use in TEXT command (legacy method).
        Handles mixing of literal text and variable references.

        Examples:
            'Account Branch / ' -> 'Account Branch / '
            ': ' ! VAR_BRC -> : ' ! VAR_BRC  (already formatted, return as-is)
            'text' ! VAR -> text' ! VAR
        """
        import re

        # Pattern for VSUB-formatted variables: ' ! VAR
        vsub_var_pattern = r"' ! [A-Za-z_][A-Za-z0-9_]*"

        if not re.search(vsub_var_pattern, text_seg):
            # No VSUB variables - just quote the whole thing
            return f"'{text_seg}'"

        # Has VSUB variables - return as-is since VSUB already formatted it correctly
        # The format is: literal_chars' ! VAR where literal_chars are already quoted
        return text_seg

    def _generate_simple_output(self, text: str, x, y,
                               default_font: str, is_variable: bool, alignment: int = None,
                               x_was_set: bool = True, y_was_set: bool = True, y_is_next: bool = False,
                               frm: XeroxFRM = None, color: str = None):
        """Generate simple OUTPUT command with proper alignment."""
        # Generate OUTPUT
        if is_variable:
            self.add_line(f"OUTPUT {text}")
        else:
            self.add_line(f"OUTPUT '{text}'")

        self.indent()

        # Map font alias if FRM is provided (for FRM-specific output)
        if frm:
            dfa_font, style = self._map_font_alias(default_font, frm)
            self.add_line(f"FONT {dfa_font} {style}")
        else:
            # DBM output - use font directly (already in font_mappings)
            dfa_font = default_font
            self.add_line(f"FONT {default_font} NORMAL")

        # Use flags to determine position format
        x_pos = x if x_was_set else 'SAME'
        if y_is_next:
            y_pos = 'NEXT'  # After NL, use NEXT to stay on the new line
        elif y_was_set:
            y_pos = y  # Explicit position
        else:
            y_pos = 'SAME'  # Implicit position

        # Add position using helper method (handles both keywords and numeric with margin correction)
        # Pass font for vertical position correction
        self.add_line(self._format_position(x_pos, y_pos, dfa_font))

        # Add color if specified
        if color:
            self.add_line(f"COLOR {color}")

        # Add alignment if specified
        if alignment == 0:
            self.add_line("ALIGN LEFT NOPAD")
        elif alignment == 1:
            self.add_line("ALIGN RIGHT NOPAD")
        elif alignment == 2:
            self.add_line("ALIGN CENTER NOPAD")
        elif alignment == 3:
            self.add_line("ALIGN JUSTIFY NOPAD")

        self.add_line(";")
        self.dedent()

    def _generate_text_with_width(self, text: str, x, y,
                                  default_font: str, width: float, is_variable: bool, alignment: int = None,
                                  x_was_set: bool = True, y_was_set: bool = True, y_is_next: bool = False,
                                  frm: XeroxFRM = None):
        """
        Generate TEXT command with WIDTH parameter for line wrapping.

        Used for SHP commands with width parameter that require text to wrap within a column.

        Args:
            text: Text content or variable name
            x, y: Position coordinates
            default_font: Font alias to use
            width: Column width in MM for text wrapping
            is_variable: True if text is a variable reference
            alignment: 0=LEFT, 1=RIGHT, 2=CENTER, 3=LEFT (default)
            x_was_set: Whether X position was explicitly set
            y_was_set: Whether Y position was explicitly set
            y_is_next: Whether to use NEXT for Y position
            frm: FRM structure for font mapping
        """
        # Generate TEXT command
        self.add_line("TEXT")
        self.indent()

        # Determine font first (needed for position correction)
        if frm:
            dfa_font, style = self._map_font_alias(default_font, frm)
        else:
            dfa_font = default_font
            style = "NORMAL"

        # Use flags to determine position format
        x_pos = x if x_was_set else 'SAME'
        if y_is_next:
            y_pos = 'NEXT'  # After NL, use NEXT to stay on the new line
        elif y_was_set:
            y_pos = y  # Explicit position
        else:
            y_pos = 'SAME'  # Implicit position

        # Add position with font correction
        self.add_line(self._format_position(x_pos, y_pos, dfa_font))

        # Add WIDTH parameter for line wrapping
        self.add_line(f"WIDTH {width} MM")

        # Add alignment if specified
        if alignment == 0:
            self.add_line("ALIGN LEFT")
        elif alignment == 1:
            self.add_line("ALIGN RIGHT")
        elif alignment == 2:
            self.add_line("ALIGN CENTER")
        elif alignment == 3:
            self.add_line("ALIGN JUSTIFY")

        # Add font
        self.add_line(f"FONT {dfa_font}")
        self.add_line(style)

        # Add text content
        # For TEXT command, variables are in parentheses: (VAR)
        # Literals are in quotes: 'text'
        if is_variable:
            # Variable reference - use parentheses
            # Check if it's VSUB-formatted (contains ! concatenation)
            if ' ! ' in text:
                # VSUB format: 'literal' ! VAR
                # TEXT command needs this reformatted
                self.add_line(text)
            else:
                # Simple variable
                self.add_line(f"({text})")
        else:
            # Literal text - quote it
            self.add_line(f"'{text}'")

        self.add_line(";")
        self.dedent()

    def _convert_xgfresdef(self, cmd: XeroxCommand, frm: XeroxFRM):
        """
        Convert XGFRESDEF resource definition and store metadata.

        VIPP: /TXNB { 0 0 188 09 LMED DRAWB } XGFRESDEF
        DFA: Store definition, convert SCALL to BOX later
        """
        if not cmd.parameters or not cmd.children:
            return

        resource_name = cmd.parameters[0]

        # Analyze commands to determine resource type
        if cmd.children and cmd.children[0].name == 'DRAWB':
            # It's a box drawing resource
            box_cmd = cmd.children[0]
            if len(box_cmd.parameters) >= 4:
                x = box_cmd.parameters[0]
                y = box_cmd.parameters[1]
                width = box_cmd.parameters[2]
                height = box_cmd.parameters[3]
                style = box_cmd.parameters[4] if len(box_cmd.parameters) > 4 else 'R_S1'

                # Store for later SCALL conversion
                frm.xgfresdef_resources[resource_name] = {
                    'type': 'box',
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height,
                    'style': style
                }

        # Don't generate output for XGFRESDEF definitions themselves

    def _convert_frm_rule(self, cmd: XeroxCommand):
        """Convert FRM DRAWB command to DFA RULE (line) or BOX (rectangle).

        VIPP DRAWB format: x y width/length height/thickness style DRAWB

        Examples:
        - Line:  12 17 187 0.2 R_S1 DRAWB  (thickness < 1mm → RULE)
        - Box:   11 204 188 47 S2 DRAWB    (height > 1mm → BOX)

        DFA RULE syntax:
        RULE
            POSITION (x MM-$MR_LEFT) (y MM-$MR_TOP)
            DIRECTION ACROSS|DOWN
            COLOR R|G|B|F
            LENGTH length MM
            THICKNESS thickness MM TYPE SOLID|DASHED|DOTTED
        ;

        DFA BOX syntax:
        BOX
            POSITION (x MM-$MR_LEFT) (y MM-$MR_TOP)
            WIDTH width MM
            HEIGHT height MM
            THICKNESS MEDIUM TYPE SOLID
            SHADE percentage;
        ;
        """
        if len(cmd.parameters) < 4:
            return

        # Parse parameters
        x = cmd.parameters[0]
        y = cmd.parameters[1]
        param3 = cmd.parameters[2]  # width or length
        param4 = cmd.parameters[3]  # height or thickness
        style = cmd.parameters[4] if len(cmd.parameters) > 4 else "R_S1"

        # Parse color and shade from style parameter
        color = None
        line_type = "SOLID"
        shade = None

        # Check for color prefix (R=RED, G=GREEN, B=BLUE, F=BLACK)
        if style.startswith('R'):
            color = 'R'
        elif style.startswith('G'):
            color = 'G'
        elif style.startswith('B'):
            color = 'B'
        elif style.startswith('F'):
            color = 'F'
        elif style.startswith('S'):
            # Style like "S2" without color prefix defaults to BLACK
            color = 'F'

        # Parse shade suffix (S1=100%, S2=75%, S3=50%, S4=25%)
        if 'S1' in style or '_S1' in style:
            shade = 100
        elif 'S2' in style or '_S2' in style:
            shade = 75
        elif 'S3' in style or '_S3' in style:
            shade = 50
        elif 'S4' in style or '_S4' in style:
            shade = 25

        # Parse line type
        if style in ['LDSH', 'L_DSH']:
            line_type = 'DASHED'
        elif style in ['LDOT', 'L_DOT']:
            line_type = 'DOTTED'

        # Handle legacy thickness keywords
        param4_val = param4
        try:
            param4_float = float(param4)
        except ValueError:
            # Thickness is a keyword like LMED
            thickness_map = {
                'LTHN': 0.1,
                'LMED': 0.2,
                'LTHK': 0.5,
            }
            param4_float = thickness_map.get(param4, 0.2)
            param4_val = str(param4_float)

        # Determine if this is a BOX (rectangle) or RULE (line)
        # If param4 (height/thickness) > 1.0 mm, it's a BOX
        is_box = param4_float > 1.0

        if is_box:
            # Generate BOX command
            width = param3
            height = param4

            self.add_line("BOX")
            self.indent()

            # Position
            self.add_line(f"POSITION ({x} MM-$MR_LEFT) ({y} MM-$MR_TOP)")

            # Dimensions
            self.add_line(f"WIDTH {width} MM")
            self.add_line(f"HEIGHT {height} MM")

            # Thickness (border)
            self.add_line(f"THICKNESS MEDIUM TYPE {line_type};")

            self.dedent()
        else:
            # Generate RULE command (line)
            length = param3
            thickness = param4_val

            # Determine direction based on length vs thickness
            try:
                length_f = float(length)
                thickness_f = float(thickness)
                direction = 'ACROSS' if length_f >= thickness_f else 'DOWN'
            except ValueError:
                direction = 'ACROSS'

            self.add_line("RULE")
            self.indent()

            # Position
            self.add_line(f"POSITION ({x} MM-$MR_LEFT) ({y} MM-$MR_TOP)")

            # Direction
            self.add_line(f"DIRECTION {direction}")

            # Color (if specified)
            if color:
                self.add_line(f"COLOR {color}")

            # Length
            self.add_line(f"LENGTH {length} MM")

            # Thickness with type
            self.add_line(f"THICKNESS {thickness} MM TYPE {line_type}")

            self.add_line(";")
            self.dedent()

    def _convert_frm_segment(self, cmd: XeroxCommand, x: float, y: float, frm: XeroxFRM, cache_cmd: XeroxCommand = None,
                            x_was_set: bool = False, y_was_set: bool = False):
        """Convert FRM SCALL command to DFA SEGMENT or CREATEOBJECT.

        For .jpg/.tiff files with CACHE: Generate CREATEOBJECT IOBDLL
        For .eps files: Generate SEGMENT with vertical position 0 MM
        For other files: Generate standard SEGMENT command

        Args:
            cmd: SCALL command
            x: Current X position (used only if x_was_set is True)
            y: Current Y position (used only if y_was_set is True)
            frm: FRM structure
            cache_cmd: Previous CACHE command if any
            x_was_set: Whether X position was explicitly set with MOVETO
            y_was_set: Whether Y position was explicitly set with MOVETO
        """
        resource_name = ""
        filename = ""

        # Extract filename from SCALL or CACHE parameters
        # If CACHE command exists, filename is in CACHE parameters
        # Otherwise, filename is in SCALL parameters
        if cache_cmd and cache_cmd.parameters:
            for i, param in enumerate(cache_cmd.parameters):
                if param.startswith('(') and param.endswith(')'):
                    filename = param[1:-1]
                    break

        if not filename:
            # Try SCALL parameters
            for i, param in enumerate(cmd.parameters):
                if param.startswith('(') and param.endswith(')'):
                    filename = param[1:-1]
                    break

        if not filename:
            return

        # Extract file extension
        file_ext = ""
        if '.' in filename:
            file_ext = filename.split('.')[-1].lower()
            resource_name = filename.rsplit('.', 1)[0]  # Remove extension
        else:
            resource_name = filename

        # Extract CACHE dimensions if available
        cache_width = None
        cache_height = None
        if cache_cmd and cache_cmd.parameters:
            # Look for [width height] pattern in CACHE parameters
            # Can be: '[' '185' '44' ']' or '[185 44]' or '[185' '44]'
            for i, param in enumerate(cache_cmd.parameters):
                try:
                    if param == '[' and i + 3 < len(cache_cmd.parameters):
                        # Tokenized format: '[' '185' '44' ']'
                        if cache_cmd.parameters[i + 3] == ']':
                            cache_width = int(cache_cmd.parameters[i + 1])
                            cache_height = int(cache_cmd.parameters[i + 2])
                            break
                    elif param.startswith('['):
                        # Combined formats
                        if param.endswith(']') and ' ' in param:
                            # Single parameter: '[185 44]'
                            dims = param[1:-1].split()
                            cache_width = int(dims[0])
                            cache_height = int(dims[1])
                            break
                        elif i + 1 < len(cache_cmd.parameters):
                            # Split across parameters: '[185' '44]'
                            width_str = param[1:]  # Remove leading [
                            cache_width = int(width_str)
                            height_str = cache_cmd.parameters[i + 1].rstrip(']')
                            cache_height = int(height_str)
                            break
                except (ValueError, IndexError):
                    pass

        # Generate DFA based on file type
        if file_ext in ('jpg', 'jpeg', 'tif', 'tiff'):
            # Generate CREATEOBJECT IOBDLL for image files
            # CREATEOBJECT always uses POSITION (SAME) (SAME) to inherit from previous command
            # since SCALL itself has no position parameters
            other_type = 'JPG' if file_ext in ('jpg', 'jpeg') else 'TIF'

            self.add_line("CREATEOBJECT IOBDLL(IOBDEFS)")
            self.indent()
            self.add_line("POSITION (SAME) (SAME)")
            self.add_line("PARAMETERS")
            self.indent()
            self.add_line(f"('FILENAME'='{resource_name}')")
            self.add_line("('OBJECTTYPE'='1')")
            self.add_line(f"('OTHERTYPES'='{other_type}')")

            # Only include dimensions if CACHE dimensions are available
            if cache_width is not None and cache_height is not None:
                self.add_line(f"('XOBJECTAREASIZE'='{cache_width}')")
                self.add_line(f"('YOBJECTAREASIZE'='{cache_height}')")

            self.add_line("('OBJECTMAPPING'='2');")
            self.dedent()
            self.dedent()

        elif file_ext == 'eps':
            # EPS files: use SEGMENT with vertical position 0 MM
            # (Xerox measures upward, so we don't have enough info for vertical position)
            self.add_line(f"SEGMENT {resource_name}")
            self.indent()
            # For EPS, use horizontal position from MOVETO, vertical is always 0 MM with segment correction
            if x_was_set:
                self.add_line(f"POSITION ({x} MM-$MR_LEFT) (0 MM-$MR_TOP+&CORSEGMENT);")
            else:
                self.add_line("POSITION (SAME) (0 MM-$MR_TOP+&CORSEGMENT);")
            self.dedent()

        else:
            # Standard SEGMENT command for other file types (e.g., TXNB)
            # Use position based on whether it was explicitly set
            self.add_line(f"SEGMENT {resource_name}")
            self.indent()
            if not x_was_set and not y_was_set:
                self.add_line("POSITION (SAME) (SAME);")
            else:
                x_part = f"{x} MM-$MR_LEFT" if x_was_set else "SAME"
                # Add segment correction to Y position when it's numeric
                if y_was_set:
                    y_part = f"{y} MM-$MR_TOP+&CORSEGMENT"
                else:
                    y_part = "SAME"
                self.add_line(f"POSITION ({x_part}) ({y_part});")
            self.dedent()

    def _convert_frm_image(self, cmd: XeroxCommand, x: float, y: float):
        """Convert FRM ICALL command to DFA IMAGE."""
        resource_name = ""
        scale = "1.0"

        for i, param in enumerate(cmd.parameters):
            if param.startswith('(') and param.endswith(')'):
                resource_name = param[1:-1]
            elif i > 0 and param.replace('.', '', 1).isdigit():
                scale = param

        if resource_name:
            self.add_line(f"IMAGE '{resource_name}'")
            self.indent()
            self.add_line(f"POSITION ({x} MM-$MR_LEFT) ({y} MM-$MR_TOP)")
            self.add_line(f"SCALE {scale}")
            self.add_line(";")
            self.dedent()

    def add_line(self, line: str):
        """Add a line of output with proper indentation."""
        # Validate line for malformed VIPP code patterns
        if self._is_malformed_line(line):
            # Wrap malformed line in comment
            line = f"/* {line} */"

        indent = '    ' * self.indent_level
        self.output_lines.append(f"{indent}{line}")

    def _is_malformed_line(self, line: str) -> bool:
        """
        Check if a line contains malformed VIPP code that shouldn't appear in DFA.
        Returns True if the line should be commented out.
        """
        # Skip lines that are already comments
        if line.strip().startswith('/*') or line.strip().startswith('//'):
            return False

        # Skip empty lines
        if not line.strip():
            return False

        # Malformed patterns to detect:
        malformed_patterns = [
            'PAGEBRK IF',           # PAGEBRK with conditional logic
            # Note: CPCOUNT and GETITEM removed - they can appear in valid IF conditions
            '{ /',                  # VIPP braces with variables
            '} %',                  # VIPP closing brace with comment
            # Note: comparison operators removed - they're valid in IF conditions
            'SETPAGENUMBER',        # Unsupported command
            ' VSUB ',               # VIPP VSUB command
            ' SETVAR }',            # SETVAR inside braces
            '= -;',                 # Assignment with just dash
            '= =;',                 # Assignment with just equals
        ]

        # Check for malformed patterns
        for pattern in malformed_patterns:
            if pattern in line:
                return True

        # Check for assignment followed by VIPP keywords (e.g., "PREFIX eq (STMTTP) = VAR_X;")
        # Pattern: word operator word = VAR_something;
        if ' eq (' in line or ' ne (' in line or ' gt (' in line or ' lt (' in line:
            if ' = VAR_' in line or ' = FLD' in line:
                return True

        return False

    def indent(self):
        """Increase indentation level."""
        self.indent_level += 1

    def dedent(self):
        """Decrease indentation level."""
        if self.indent_level > 0:
            self.indent_level -= 1

    def _detect_input_format(self):
        """
        Detect input format from DBM metadata.
        Extracts delimiter from SETDBSEP and field names from %%WIZVAR.
        """
        config = self.input_config

        # Search for SETDBSEP in raw content to detect delimiter
        if self.dbm.raw_content:
            # Pattern: (delimiter) SETDBSEP
            setdbsep_pattern = r'\((.)\)\s+SETDBSEP'
            match = re.search(setdbsep_pattern, self.dbm.raw_content)
            if match:
                config.delimiter = match.group(1)
                logger.info(f"Detected delimiter: '{config.delimiter}'")
            else:
                logger.info(f"Using default delimiter: '{config.delimiter}'")

        # Extract field names from WIZVAR
        if self.dbm.wizvar_fields:
            # Use WIZVAR field names
            config.field_names = ['PREFIX'] + self.dbm.wizvar_fields
            config.field_count = len(config.field_names)
            logger.info(f"Found {config.field_count} fields from %%WIZVAR")
        else:
            # Use default field naming: PREFIX, FLD1, FLD2, ... FLD20
            config.field_names = ['PREFIX'] + [f'FLD{i}' for i in range(1, 21)]
            config.field_count = 21
            logger.info(f"Using default field names (no %%WIZVAR found)")

        # Check for header line - if first data line contains "PREFIX|"
        if self.dbm.raw_content:
            if 'PREFIX|' in self.dbm.raw_content:
                config.has_header_line = True
                logger.info("Data file appears to have header line")

    def _build_format_registry(self):
        """
        Build mapping of PREFIX values to DOCFORMAT names.
        Each CASE block becomes a separate DOCFORMAT.
        """
        self.format_registry = {}
        for case_value in self.dbm.case_blocks.keys():
            if case_value != "{}":
                docformat_name = f"DF_{case_value}"
                self.format_registry[case_value] = docformat_name
                logger.info(f"Registered format: {case_value} -> {docformat_name}")

    def _extract_layout_info(self):
        """
        Extract SETLSP and SETPAGEDEF/SETLKF layout information from DBM commands and raw content.

        - SETLSP: Extract line spacing value for use in DOCFORMAT
        - SETPAGEDEF: Extract last SETLKF position for OUTLINE generation
        """
        # First try to scan DBM commands
        for cmd in self.dbm.commands:
            # Extract SETLSP value (typically at start of file)
            if cmd.name == 'SETLSP' and cmd.parameters and not self.line_spacing:
                try:
                    self.line_spacing = float(cmd.parameters[0])
                    logger.info(f"Found SETLSP: {self.line_spacing} MM")
                except (ValueError, IndexError):
                    pass

            # Extract SETPAGEDEF layout information
            if cmd.name == 'SETPAGEDEF' and cmd.parameters:
                # SETPAGEDEF contains array of page layouts
                # Each layout has SETLKF with [[x, y, width, height, ?]]
                # We want the LAST layout (usually page 2, the repeating layout)
                self._parse_setpagedef_layout(cmd.parameters)

        # If not found, try to extract from raw content as backup
        if not self.line_spacing and self.dbm.raw_content:
            # Pattern: number SETLSP
            setlsp_pattern = r'(\d+(?:\.\d+)?)\s+SETLSP'
            match = re.search(setlsp_pattern, self.dbm.raw_content)
            if match:
                try:
                    self.line_spacing = float(match.group(1))
                    logger.info(f"Found SETLSP from raw content: {self.line_spacing} MM")
                except (ValueError, IndexError):
                    pass

        # Extract SETPAGEDEF from raw content as backup
        if not self.page_layout_position and self.dbm.raw_content:
            # Pattern to find SETLKF arrays before SETPAGEDEF
            # Looking for: [ [ number number number number number ] ] SETLKF
            setlkf_pattern = r'\[\s*\[\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+\d+\s*\]\s*\]'
            matches = re.findall(setlkf_pattern, self.dbm.raw_content)
            if matches:
                # Get the last match (last page layout)
                last_match = matches[-1]
                self.page_layout_position = (float(last_match[0]), float(last_match[1]))
                logger.info(f"Found SETPAGEDEF layout position from raw content: {self.page_layout_position}")

    def _parse_setpagedef_layout(self, params):
        """
        Parse SETPAGEDEF parameters to extract the last SETLKF position.

        SETPAGEDEF structure:
        [
            { [[x1, y1, w1, h1, 0]] SETLKF (form1.FRM) SETFORM }
            { [[x2, y2, w2, h2, 0]] SETLKF (form2.FRM) SETFORM } /R
        ] SETPAGEDEF

        We want the last layout's (x, y) position.
        """
        last_setlkf_position = None

        # Params is typically a list/block containing the page definitions
        for param in params:
            if isinstance(param, tuple) and param[0] == 'block':
                # This is the array block
                block_content = param[1]

                # Look for patterns like [[x, y, w, h, 0]]
                # This is a simplified parser - may need refinement
                import re
                # Pattern to match numbers in SETLKF arrays
                setlkf_pattern = r'\[\s*\[\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+\d+\s*\]\s*\]'
                matches = re.findall(setlkf_pattern, str(block_content))

                if matches:
                    # Get the last match (last page layout)
                    last_match = matches[-1]
                    last_setlkf_position = (float(last_match[0]), float(last_match[1]))
                    logger.info(f"Found SETPAGEDEF layout position: {last_setlkf_position}")

        if last_setlkf_position:
            self.page_layout_position = last_setlkf_position

    def set_input_config(self, delimiter: str = None, field_names: List[str] = None, record_length: int = None):
        """
        Allow manual override of detected input configuration.

        Args:
            delimiter: Field delimiter character
            field_names: List of field names
            record_length: Maximum record length in bytes
        """
        if delimiter:
            self.input_config.delimiter = delimiter
        if field_names:
            self.input_config.field_names = field_names
            self.input_config.field_count = len(field_names)
        if record_length:
            self.input_config.record_length = record_length

    def validate_conversion(self) -> List[str]:
        """
        Validate the conversion and return list of warnings.

        Returns:
            List of warning messages
        """
        warnings = []

        if not self.input_config.field_names:
            warnings.append("No field names detected - using defaults")

        if self.input_config.record_length < 2048:
            warnings.append("RECORD-LENGTH may be too small for complex data")

        if not self.format_registry:
            warnings.append("No format registry built - dynamic routing disabled")

        if not self.dbm.case_blocks:
            warnings.append("No CASE blocks found - document may not process data correctly")

        return warnings

    def _generate_header(self):
        """Generate the DFA file header with metadata."""
        # Extract a valid DOCDEF name (alphanumeric only)
        docdef_name = ''.join(c for c in os.path.splitext(os.path.basename(self.dbm.filename))[0] if c.isalnum())
        if not docdef_name:
            docdef_name = "CONVERTED"

        self.add_line("/* Generated by Universal Xerox FreeFlow to Papyrus DocDEF Converter */")
        self.add_line(f"/* Source: {self.dbm.filename} */")
        self.add_line(f"/* Conversion Date: {datetime.now().strftime('%Y-%m-%d')} */")
        self.add_line("")

        if self.dbm.title:
            self.add_line(f"/* Original Title: {self.dbm.title} */")
        if self.dbm.creator:
            self.add_line(f"/* Original Creator: {self.dbm.creator} */")
        if self.dbm.creation_date:
            self.add_line(f"/* Original Date: {self.dbm.creation_date} */")

        self.add_line("")
        self.add_line(f"DOCDEF {docdef_name};")
        self.add_line("")

        # Add APPLICATION-INPUT-FORMAT (mandatory in DFA)
        self.add_line("/* Input format specification */")
        self.add_line("APPLICATION-INPUT-FORMAT")
        self.indent()
        self.add_line("CODE 1252")
        self.add_line("RECORD-FORMAT VARPC")
        self.add_line("RECORD-DELIMITER X'0D0A'")
        self.add_line(f"RECORD-LENGTH {self.input_config.record_length}")
        self.add_line(f"CHANNEL-CODE {self.dfa_config.channel_code} NOBREAKREPEAT")
        self.add_line("TABLE-REF-CODE NO")
        self.add_line("DECIMAL-SEPARATOR '.'")
        self.add_line("CACHELIMIT 100;")
        self.dedent()
        self.add_line("")

        # Add APPLICATION-OUTPUT-FORMAT
        self.add_line("/* Output format specification */")
        self.add_line("APPLICATION-OUTPUT-FORMAT")
        self.indent()
        self.add_line("CODE 1200")
        self.add_line("AFPLRECL 8192")
        self.add_line("PTXUNIT 1440")
        self.add_line("FDFINCLUDE YES")
        self.add_line("TLE YES")
        self.add_line("ACIFINDEX NO;")
        self.dedent()
        self.add_line("")

        # Add PDF output definition
        self.add_line("DEFINEPDFOUTPUT PDFOUT;")
        self.add_line("")

        # Add FORMATGROUP for page layout (A4 portrait)
        self.add_line("/* Page Layout - FORMATGROUP */")
        self.add_line("FORMATGROUP MAIN;")
        self.indent()
        self.add_line("SHEET")
        self.add_line("    WIDTH 210 MM")
        self.add_line("    HEIGHT 297 MM;")
        self.add_line("LAYER 1;")
        self.add_line("LOGICALPAGE 1")
        self.add_line("    SIDE FRONT")
        self.add_line("    POSITION 0 0")
        self.add_line("    WIDTH 210 MM")
        self.add_line("    HEIGHT 297 MM")
        self.add_line("    DIRECTION ACROSS")
        # FOOTER counts total pages (called once at end of document)
        self.add_line("    FOOTER")
        self.add_line("        PP = PP + 1;")
        self.add_line("    FOOTEREND")
        # PRINTFOOTER outputs page numbers (called for each page in buffer)
        self.add_line("    PRINTFOOTER")

        # Add form usage in PRINTFOOTER (moved from main DOCFORMAT)
        self.add_line("  /*Put here the layout forms (.FRM)*/")
        self._generate_form_usage_in_printfooter()

        self.add_line("        P = P + 1;")
        self.add_line("        OUTLINE")
        self.add_line("            POSITION RIGHT (0 MM)")
        self.add_line("            DIRECTION ACROSS;")
        self.add_line("            OUTPUT 'Page '!P!' of '!PP")
        self.add_line("                FONT F5_1")
        self.add_line("                POSITION (RIGHT-11 MM)286 MM")
        self.add_line("                ALIGN RIGHT NOPAD;")
        self.add_line("        ENDIO;")
        self.add_line("    PRINTEND;")
        self.dedent()
        self.add_line("")

    def _generate_fonts(self):
        """
        Generate font definitions from DBM and FRM files.

        Following VIPP semantics:
        - Each font alias (e.g., FE) IS a specific font (e.g., Arial Bold Italic 6pt)
        - No runtime face variants (BOLD/ITALIC) needed - use NORMAL always
        - Font style is baked into the definition, not applied at OUTPUT time
        """
        self.add_line("/* Font Definitions */")

        # Collect all fonts from DBM and FRM files (FRM fonts already renamed if conflicts exist)
        all_fonts = dict(self.dbm.fonts)
        for frm in self.frm_files.values():
            all_fonts.update(frm.fonts)

        # Generate DFA font definitions and mappings
        for alias, font in sorted(all_fonts.items()):
            # Map Xerox font names to Papyrus font family names
            # ARIALBO -> 'Arial Bold Italic', ARIALB -> 'Arial Bold', etc.
            papyrus_name = self.FONT_STYLE_MAPPINGS.get(font.name.lstrip('/'), font.name.lstrip('/'))

            # Create DFA font definition
            dfa_alias = f"{alias.upper()}".replace("/", "")
            self.font_mappings[alias] = dfa_alias

            # Generate simplified DFA font definition
            # VIPP doesn't use runtime face variants, so we define the font as-is
            size = font.size if font.size else 10.0
            self.font_sizes[dfa_alias] = size  # Store size for position correction
            self.add_line(f"FONT {dfa_alias} NOTDEF AS '{papyrus_name}' DBCS ROTATION 0 HEIGHT {size};")

        # Add minimal default fonts only if not already defined
        # These are generic fallbacks, not F-series fonts which come from source files
        default_fonts = [
            ("ARIAL06", "Arial", 6.0),
            ("ARIAL08", "Arial", 8.0),
            ("ARIAL10", "Arial", 10.0),
            ("ARIAL12", "Arial", 12.0),
            ("COURIER08", "Courier New", 8.0),
            ("COURIER10", "Courier New", 10.0),
        ]

        for dfa_alias, family, size in default_fonts:
            if dfa_alias not in self.font_mappings.values():
                self.add_line(f"FONT {dfa_alias} NOTDEF AS '{family}' DBCS ROTATION 0 HEIGHT {size};")
                self.font_mappings[dfa_alias.lower()] = dfa_alias
                self.font_sizes[dfa_alias] = size  # Store size for position correction

        self.add_line("")

    def _generate_colors(self):
        """Generate color definitions from DBM and FRM files."""
        self.add_line("/* Color Definitions */")

        # Collect all colors from DBM and FRM files
        all_colors = dict(self.dbm.colors)
        for frm in self.frm_files.values():
            all_colors.update(frm.colors)

        # Standard color mappings to RGB values (percentages)
        color_rgb_map = {
            'BLACK': (0, 0, 0),
            'WHITE': (100, 100, 100),
            'RED': (100, 0, 0),
            'GREEN': (0, 100, 0),
            'BLUE': (0, 0, 100),
            'YELLOW': (100, 100, 0),
            'CYAN': (0, 100, 100),
            'MAGENTA': (100, 0, 100),
            'ORANGE': (100, 64.7, 0),
            'GRAY': (50, 50, 50),
            'LIGHTGRAY': (75, 75, 75),
            'DARKGRAY': (25, 25, 25),
        }

        # Generate DFA color definitions using DEFINE syntax
        for alias, color in sorted(all_colors.items()):
            dfa_alias = alias.upper().replace("/", "")
            color_name = color.name.upper() if hasattr(color, 'name') else str(color).upper()

            # Get RGB values or use default
            if color_name in color_rgb_map:
                r, g, b = color_rgb_map[color_name]
            else:
                r, g, b = 0, 0, 0  # Default to black

            self.color_mappings[alias] = dfa_alias
            self.add_line(f"DEFINE {dfa_alias} COLOR RGB RVAL {r} GVAL {g} BVAL {b};")

        self.add_line("")

    def _get_font_correction(self, font_name: str) -> str:
        """
        Get the position correction variable name for a given font.

        Args:
            font_name: DFA font name (e.g., 'ARIAL06', 'F1', etc.)

        Returns:
            Correction variable name (e.g., '&CORFONT6', '&CORFONT10') or empty string if no correction
        """
        if not font_name:
            return ""

        # Look up font size from our stored mappings
        size = self.font_sizes.get(font_name)
        if not size:
            # Try uppercase version
            size = self.font_sizes.get(font_name.upper())

        if not size:
            return ""

        # Map size to correction variable
        # Round to nearest supported size
        if size <= 6.5:
            return "&CORFONT6"
        elif size <= 7.5:
            return "&CORFONT7"
        elif size <= 9:
            return "&CORFONT8"
        elif size <= 11:
            return "&CORFONT10"
        else:
            return "&CORFONT12"

    def _format_position(self, x, y, font: str = None):
        """
        Format POSITION statement with proper DFA syntax.

        Handles both keyword positions (SAME, NEXT, LEFT, etc.) and numeric positions.
        All numeric positions are margin-corrected. For OUTPUT/TEXT commands, adds font-specific
        vertical position correction.

        Args:
            x: X coordinate - either a number (MM) or keyword (SAME, LEFT, RIGHT)
            y: Y coordinate - either a number (MM) or keyword (SAME, NEXT, TOP, BOTTOM)
            font: Optional DFA font name for vertical position correction

        Returns:
            Formatted POSITION string with parentheses and margin correction

        Examples:
            _format_position('SAME', 'NEXT') -> 'POSITION (SAME) (NEXT)'
            _format_position(24, 49.91) -> 'POSITION (24 MM-$MR_LEFT) (49.91 MM-$MR_TOP)'
            _format_position(24, 49.91, 'ARIAL06') -> 'POSITION (24 MM-$MR_LEFT) (49.91 MM-$MR_TOP+&CORFONT6)'
            _format_position('LEFT', 65.5) -> 'POSITION (LEFT) (65.5 MM-$MR_TOP)'
        """
        # Handle X coordinate
        if isinstance(x, str):
            x_upper = x.upper()
            # Check if it's a keyword or starts with a keyword (for expressions like LEFT-$MR_LEFT)
            if x_upper in ('SAME', 'LEFT', 'RIGHT', 'CENTER') or x_upper.startswith(('LEFT-', 'RIGHT-', 'SAME-', 'SAME+')):
                x_part = f"({x})"
            else:
                # Numeric position - use margin correction
                x_part = f"({x} MM-$MR_LEFT)"
        else:
            # Numeric position - use margin correction
            x_part = f"({x} MM-$MR_LEFT)"

        # Handle Y coordinate
        font_correction = ""
        if font:
            font_correction = self._get_font_correction(font)

        if isinstance(y, str):
            y_upper = y.upper()
            # Check if it's a keyword or starts with a keyword (for expressions like NEXT-(...))
            if y_upper in ('SAME', 'NEXT', 'TOP', 'BOTTOM') or y_upper.startswith(('NEXT-', 'NEXT+', 'SAME-', 'SAME+')):
                y_part = f"({y})"
            else:
                # Numeric position - use margin correction and font correction
                if font_correction:
                    y_part = f"({y} MM-$MR_TOP+{font_correction})"
                else:
                    y_part = f"({y} MM-$MR_TOP)"
        else:
            # Numeric position - use margin correction and font correction
            if font_correction:
                y_part = f"({y} MM-$MR_TOP+{font_correction})"
            else:
                y_part = f"({y} MM-$MR_TOP)"

        return f"POSITION {x_part} {y_part}"

    def _has_output_commands(self, commands: List[XeroxCommand]) -> bool:
        """
        Check if command list contains OUTPUT/TEXT/graphical commands.

        These commands require an OUTLINE wrapper in DFA.

        Args:
            commands: List of VIPP commands to check

        Returns:
            True if list contains any output/graphical commands, False otherwise
        """
        output_commands = {
            'SH', 'SHL', 'SHR', 'SHr', 'SHC', 'SHP',  # Text output
            'DRAWB', 'SCALL', 'ICALL',                 # Graphics
            'SETLSP', 'NL'                             # Spacing/newlines
        }
        return any(cmd.name in output_commands for cmd in commands)

    def _convert_vsub(self, text: str) -> str:
        """
        Convert VIPP VSUB variable substitution to DFA format.

        VIPP format: $$VAR_name. or $VAR_name
        DFA format: 'literal' ! VAR (no parentheses around variable)

        Args:
            text: Input text containing VSUB patterns

        Returns:
            Converted text with DFA variable references
        """
        import re

        # Pattern for $$VAR_name. (VSUB with trailing dot)
        vsub_pattern = r'\$\$([A-Za-z_][A-Za-z0-9_]*)\.'

        # Split text into parts: literals and variables
        parts = []
        last_end = 0

        for match in re.finditer(vsub_pattern, text):
            # Add literal text before this variable (if any)
            if match.start() > last_end:
                literal = text[last_end:match.start()]
                if literal:
                    parts.append(('literal', literal))

            # Add variable
            var_name = match.group(1)
            parts.append(('variable', var_name))

            last_end = match.end()

        # Add any remaining literal text after last variable
        if last_end < len(text):
            literal = text[last_end:]
            if literal:
                parts.append(('literal', literal))

        # If no variables found, return original text (will be quoted by caller)
        if not parts or all(p[0] == 'literal' for p in parts):
            return text

        # Build DFA concatenation expression
        result_parts = []
        for part_type, part_value in parts:
            if part_type == 'literal':
                # Quote literal parts
                result_parts.append(f"'{part_value}'")
            else:
                # Variable without parentheses
                result_parts.append(part_value)

        # Join with ! concatenation operator
        return ' ! '.join(result_parts)

    def _convert_font_switch(self, text: str) -> str:
        """
        Convert VIPP font switch sequences to DFA format.

        VIPP format: ~~FA (switch to font FA inline)
        DFA format: Uses FONTSWITCH or splits into multiple OUTPUT statements

        Args:
            text: Input text containing font switch sequences

        Returns:
            Converted text or indication that multiple outputs are needed
        """
        import re

        # Pattern for ~~XX font switch (where XX is font alias)
        font_switch_pattern = r'~~([A-Za-z][A-Za-z0-9]?)'

        # Find all font switches
        switches = re.findall(font_switch_pattern, text)

        if not switches:
            return text

        # Split text by font switches for DFA processing
        # DFA doesn't support inline font switching the same way
        # Return the text with font switch markers for later processing
        parts = re.split(font_switch_pattern, text)

        return parts  # Return list for special handling

    def _convert_comparison_operators(self, params: List[str]) -> List[str]:
        """
        Convert VIPP comparison operators to DFA equivalents.

        Args:
            params: List of parameters that may contain comparison operators

        Returns:
            List with converted operators
        """
        result = []
        for param in params:
            # Check if this is a comparison operator
            if param.lower() in self.COMPARISON_OPERATORS:
                result.append(self.COMPARISON_OPERATORS[param.lower()])
            else:
                result.append(param)
        return result

    def _generate_docformat_main(self):
        """Generate the main DOCFORMAT section."""
        self.add_line("/* Main document format */")
        self.add_line("DOCFORMAT THEMAIN;")
        self.indent()

        # Use the FORMATGROUP
        #self.add_line("USE")
        #self.add_line("    FORMATGROUP MAIN;")

        # Set margins
        self.add_line("MARGIN TOP 0 MM BOTTOM 0 MM LEFT 0 MM RIGHT 0 MM;")

        # Set line spacing if SETLSP was found in DBM
        if self.line_spacing is not None:
            self.add_line(f"SETUNITS LINESP {self.line_spacing} MM;")
        else:
            self.add_line("SETUNITS LINESP AUTO;")

        self.add_line("")

        # Add OUTLINE PAGELAYOUT if SETPAGEDEF was found
        # This sets the initial position for all subsequent output
        if self.page_layout_position:
            x, y = self.page_layout_position
            self.add_line("/* Page layout position from SETPAGEDEF */")
            self.add_line("OUTLINE PAGELAYOUT")
            self.indent()
            self.add_line(f"POSITION {int(x)} MM {int(y)} MM;")
            self.dedent()
            self.add_line("ENDIO;")
            self.add_line("")

        self.dedent()

        # Generate main processing loop (Luca's pattern: FOR N REPEAT 1)
        self._generate_main_loop()

        self.add_line("")

        # Generate individual DOCFORMATs for each record type
        self._generate_individual_docformats()

        # Generate initialization in $_BEFOREFIRSTDOC
        self._generate_initialization()

        # End document definition
        self.add_line("/* END OF DOCDEF FILE */")

    def _generate_main_loop(self):
        """
        Generate the main processing loop following Luca's pattern.
        Structure: FOR N REPEAT 1 -> RECORD -> IF not separator THEN extract ELSE end doc
        """
        # Begin main processing loop (FOR N REPEAT 1)
        self.add_line("/* Main processing loop - reads one record per iteration */")
        self.add_line("FOR N REPEAT 1;")
        self.indent()

        # Generate RECORD structure
        self.add_line("RECORD INPUTREC")
        self.indent()
        self.add_line("REPEAT 1;")
        self.add_line("VARIABLE LINE1 SCALAR NOSPACE START 1;")
        self.dedent()
        self.add_line("ENDIO;")
        self.add_line("")

        # Check if line is NOT document separator
        if self.dfa_config.enable_document_boundaries:
            separator = self.input_config.document_separator
            self.add_line(f"IF LINE1<>'{separator}';")
        else:
            # If no document boundaries, always process
            self.add_line("IF 1;")

        self.add_line("THEN;")
        self.indent()

        # Generate field extraction (Luca's pattern)
        self._generate_field_extraction()

        # Generate format routing
        self.add_line("/* Route to appropriate format based on PREFIX */")
        self.add_line("USE FORMAT REFERENCE('DF_'!PREFIX);")
        self.add_line("")
        self.add_line("/* Reset Field Names/Number */")
        self.add_line("D = CLEAR(FLD);")

        self.dedent()
        self.add_line("ELSE;")
        self.indent()

        # Document separator handling
        if self.dfa_config.enable_document_boundaries:
            self.add_line("/* Here the output of the document... */")
            self.add_line("ENDGROUP 'DOC';")
            self.add_line("")
            self.add_line("/* Check if next record is EOF only */")
            self.add_line("RECORD INPUTREC")
            self.indent()
            self.add_line("REPEAT 1;")
            self.add_line("VARIABLE LINE1 SCALAR NOSPACE START 1;")
            self.dedent()
            self.add_line("ENDIO;")
            self.add_line("")
            self.add_line("IF LINE1<>'%%EOF'; THEN;")
            self.indent()
            self.add_line("SKIPRECORD -1;")
            self.dedent()
            self.add_line("ENDIF;")
            self.add_line("")
            self.add_line("ENDDOCUMENT;")

        self.dedent()
        self.add_line("ENDIF;")

        # End main loop
        self.dedent()
        self.add_line("ENDFOR;")

    def _generate_field_extraction(self):
        """
        Generate field extraction code using Luca's elegant pattern.
        This replaces the old _generate_record_structure method's field handling.
        """
        # Reset counter (Luca's pattern - N=0 causes FOR N REPEAT 1 to loop infinitely)
        self.add_line("/* Reset counter to continue processing */")
        self.add_line("N = 0;")
        self.add_line("")

        # Declare separator variable
        delimiter = self.input_config.delimiter
        # Escape delimiter for DFA syntax if needed
        if delimiter == "'":
            delimiter_literal = '"\'"'
        else:
            delimiter_literal = f"'{delimiter}'"

        self.add_line("/* Delimiter for field extraction */")
        self.add_line(f"&SEP = {delimiter_literal};")
        self.add_line("")

        # Now extract fields using EXTRACTALL with &SEP
        self.add_line("/* Split line into fields using EXTRACTALL */")
        self.add_line("D = EXTRACTALL(FLD, LINE1, &SEP, '');")
        self.add_line("")

        # Extract PREFIX for routing (more readable than direct FLD[1])
        self.add_line("/* Extract PREFIX for format routing */")
        self.add_line("PREFIX = FLD[1];")
        self.add_line("")

        # Create scalar variables using dynamic references (Luca's elegant pattern)
        self.add_line("/* Create scalar variables FLD0, FLD1, FLD2... from array */")
        self.add_line("FOR I REPEAT MAXINDEX(FLD)-1;")
        self.indent()
        self.add_line("{&FIELDS[I]} = FLD[I+1];")
        self.dedent()
        self.add_line("ENDFOR;")
        self.add_line("")

    def _generate_record_structure(self):
        """
        Generate the record structure for input data parsing.
        Uses EXTRACTALL to split delimited input lines with Luca's elegant pattern.
        Creates scalar variables FLD0, FLD1, FLD2... using dynamic references.
        """
        self.add_line("/* Read entire line and split by delimiter */")
        self.add_line("RECORD INPUTREC")
        self.indent()
        self.add_line("REPEAT 1;")

        # Read entire line as single variable
        self.add_line("VARIABLE LINE1 SCALAR NOSPACE START 1;")

        self.dedent()
        self.add_line("ENDIO;")
        self.add_line("")

        # Reset counter (Luca's pattern)
        self.add_line("/* Reset counter */")
        self.add_line("N = 0;")
        self.add_line("")

        # Declare separator variable
        delimiter = self.input_config.delimiter
        # Escape delimiter for DFA syntax if needed
        if delimiter == "'":
            delimiter_literal = '"\'"'
        else:
            delimiter_literal = f"'{delimiter}'"

        self.add_line("/* Delimiter for field extraction */")
        self.add_line(f"&SEP = {delimiter_literal};")
        self.add_line("")

        # Now extract fields using EXTRACTALL with &SEP
        self.add_line("/* Split line into fields using EXTRACTALL */")
        self.add_line("D = EXTRACTALL(FLD, LINE1, &SEP, '');")
        self.add_line("")

        # Extract PREFIX for routing (more readable than direct FLD[1])
        self.add_line("/* Extract PREFIX for format routing */")
        self.add_line("PREFIX = FLD[1];")
        self.add_line("")

        # Create scalar variables using dynamic references (Luca's elegant pattern)
        self.add_line("/* Create scalar variables FLD0, FLD1, FLD2... from array */")
        self.add_line("FOR I REPEAT MAXINDEX(FLD)-1;")
        self.indent()
        self.add_line("{&FIELDS[I]} = FLD[I+1];")
        self.dedent()
        self.add_line("ENDFOR;")
        self.add_line("")
    
    def _generate_case_processing(self):
        """
        Generate dynamic format routing based on PREFIX field.
        Uses USE FORMAT REFERENCE for flexible record type handling.
        """
        if not self.dfa_config.use_dynamic_formats:
            # Fall back to static SELECT/CASE if dynamic routing disabled
            self._generate_static_case_processing()
            return

        self.add_line("/* Dynamic format routing based on record type */")

        # Check for document boundary marker
        if self.dfa_config.enable_document_boundaries:
            self.add_line(f"IF LINE1 == '{self.input_config.document_separator}'; THEN;")
            self.indent()
            self.add_line("/* Document separator - end current document */")
            self.add_line("ENDGROUP 'DOC';")
            self.add_line("ENDDOCUMENT;")
            self.dedent()
            self.add_line("ELSE;")
            self.indent()

        # Use dynamic format reference
        self.add_line("/* Route to appropriate format based on PREFIX (FLD[0]) */")
        self.add_line("USE FORMAT REFERENCE('DF_'!PREFIX);")
        self.add_line("")
        self.add_line("/* Reset Field Names/Number */")
        self.add_line("D = CLEAR(FLD);")

        if self.dfa_config.enable_document_boundaries:
            self.dedent()
            self.add_line("ENDIF;")

        self.add_line("")

    def _generate_static_case_processing(self):
        """Generate static SELECT/CASE processing structure (legacy mode)."""
        self.add_line("/* Process record based on PREFIX */")
        self.add_line("_SELECT PREFIX;")

        # Process each case block
        for case_value, commands in self.dbm.case_blocks.items():
            if case_value == "{}":
                continue

            self.add_line(f"_CASE '{case_value}';")
            self._convert_case_commands(commands)

        self.add_line("ENDSELECT;")
        self.add_line("")

    def _generate_individual_docformats(self):
        """
        Generate individual DOCFORMAT sections for each PREFIX case.
        Each record type gets its own DOCFORMAT for dynamic routing.
        """
        self.add_line("/* Individual DOCFORMAT sections for each record type */")
        self.add_line("")

        for case_value, commands in self.dbm.case_blocks.items():
            if case_value == "{}":
                continue

            docformat_name = f"DF_{case_value}"
            self.add_line(f"DOCFORMAT {docformat_name};")
            self.indent()

            # Generate case-specific processing
            self._convert_case_commands(commands)

            self.dedent()
            self.add_line("")

        self.add_line("/* END OF INDIVIDUAL DOCFORMATS */")
        self.add_line("")
    
    def _convert_case_commands(self, commands: List[XeroxCommand]):
        """Convert VIPP commands within a case block to DFA."""
        self.indent()

        # Track current position for OUTLINE generation
        current_x = 20  # Default x position in MM
        current_y = 40  # Default y position in MM
        current_font = "ARIAL8"

        # Track whether position was explicitly set (to distinguish from residual values)
        x_was_explicitly_set = False
        y_was_explicitly_set = False
        y_is_next_line = False  # Track if next OUTPUT should use NEXT (after NL)

        # Check if we need OUTLINE wrapper (for OUTPUT/TEXT/graphics commands)
        has_output = self._has_output_commands(commands)
        outline_opened = False

        for i, cmd in enumerate(commands):
            # Map command name if possible
            dfa_cmd = self.COMMAND_MAPPINGS.get(cmd.name, cmd.name)

            # Skip comments or unsupported commands
            if cmd.name.startswith('%') or dfa_cmd.startswith('/'):
                continue

            # Handle SETVAR -> direct assignment (DFA uses var = value; not ASSIGN)
            if cmd.name == 'SETVAR':
                if len(cmd.parameters) >= 2:
                    var_name = cmd.parameters[0].lstrip('/')
                    var_value = cmd.parameters[1]

                    # Fix parameter order if they're swapped (parsing artifact)
                    # If var_name is an operator, parameters are in wrong order
                    if var_name in ('++', '--', '+', '-', '*', '/'):
                        # Swap parameters: value and var_name are reversed
                        var_name, var_value = var_value.lstrip('/'), var_name
                        logger.debug(f"Swapped SETVAR parameters: {cmd.parameters} -> [{var_name}, {var_value}]")

                    # Detect malformed SETVAR patterns and comment them out
                    malformed_keywords = ['IF', 'ELSE', 'THEN',
                                         'ENDIF', 'PAGEBRK', '{', '}', '%']
                    # Note: Removed eq/ne/gt/lt/ge/le, CPCOUNT, GETITEM - can appear in valid expressions
                    is_malformed = (
                        var_value == '-' or  # Just a dash
                        var_value == '=' or  # Just an equals sign
                        any(keyword in str(cmd.parameters) for keyword in malformed_keywords) or  # Contains VIPP keywords
                        any(keyword in var_name for keyword in malformed_keywords)  # Variable name contains keywords
                    )

                    if is_malformed:
                        # Comment out the entire malformed assignment
                        assignment = f"{var_name} = {var_value};"
                        # If parameters contain complex expressions, include them too
                        if len(cmd.parameters) > 2 or any(keyword in str(cmd.parameters) for keyword in ['{', 'IF', 'PAGEBRK']):
                            # Complex malformed expression - output all parameters
                            full_expr = ' '.join(str(p) for p in cmd.parameters)
                            self.add_line(f"/* {full_expr} */")
                        else:
                            self.add_line(f"/* {assignment} */")
                        continue

                    # Handle VIPP increment/decrement operators
                    if var_value == '++':
                        # Increment: VAR = VAR + 1
                        self.add_line(f"{var_name} = {var_name} + 1;")
                    elif var_value == '--':
                        # Decrement: VAR = VAR - 1
                        self.add_line(f"{var_name} = {var_name} - 1;")
                    else:
                        # Convert to proper DFA direct assignment
                        # Strip leading slash from var_name if present
                        if var_value.startswith('/'):
                            # This means we're assigning one variable to another
                            var_value = var_value.lstrip('/')
                        elif var_value.startswith('(') and var_value.endswith(')'):
                            var_value = f"'{var_value[1:-1]}'"
                        self.add_line(f"{var_name} = {var_value};")
                continue

            # Handle SETFONT - store font for next OUTPUT
            if cmd.name == 'SETFONT':
                if cmd.parameters:
                    current_font = cmd.parameters[0].upper()
                continue

            # Open OUTLINE before first output command
            # All OUTPUT, TEXT, and graphics commands must be inside OUTLINE block
            if has_output and not outline_opened and cmd.name in ('NL', 'SH', 'SHL', 'SHR', 'SHr', 'SHC', 'SHP', 'SETLSP', 'DRAWB', 'SCALL', 'ICALL'):
                self.add_line("")
                self.add_line("OUTLINE")
                self.indent()
                self.add_line("POSITION LEFT NEXT")
                self.add_line("DIRECTION ACROSS;")
                self.add_line("")
                outline_opened = True

            # Handle NL (newline) - generate OUTPUT '' POSITION SAME NEXT
            if cmd.name == 'NL':
                y_position = 'NEXT'

                # If NL has a spacing parameter
                if cmd.parameters:
                    try:
                        spacing_val = float(cmd.parameters[0])
                        if spacing_val < 0:
                            # Negative NL: move up by N mm from current position
                            # Example: -04 NL becomes SAME-4.0 MM
                            distance_up = abs(spacing_val)
                            y_position = f"SAME-{distance_up} MM"
                        else:
                            # Positive NL: move down by N mm from current position
                            # Example: 0.3 NL becomes SAME+0.3 MM
                            y_position = f"SAME+{spacing_val} MM"
                    except ValueError:
                        pass

                # Generate the newline as OUTPUT with POSITION SAME (NEXT or SAME+/-X MM)
                self.add_line("OUTPUT ''")
                self.add_line(f"    FONT {current_font} NORMAL")
                self.add_line(f"    {self._format_position('SAME', y_position)};")

                # After NL, next OUTPUT should use NEXT (advance to next line)
                y_was_explicitly_set = False
                y_is_next_line = True
                continue

            # Handle SETLSP (line spacing) - convert to SETUNITS LINESP
            if cmd.name == 'SETLSP':
                if cmd.parameters:
                    spacing_val = cmd.parameters[0]
                    self.add_line(f"SETUNITS LINESP {spacing_val} MM;")
                else:
                    # Default to AUTO (uses font's line spacing)
                    self.add_line("SETUNITS LINESP AUTO;")
                continue

            # Handle if/else conditions
            if dfa_cmd == 'IF':
                # Convert the IF command with its children
                self._convert_if_command(cmd)

                # Note: ELSE/ENDIF will be handled as separate commands in the loop
                # They should NOT be consumed here because they might belong to this IF
                # at the current nesting level, not as lookahead from nested IFs

                continue

            if cmd.name == 'ENDIF':
                # ENDIF closes a block, so dedent before outputting
                self.dedent()
                self.add_line("ENDIF;")
                # Note: Don't re-indent here - parent will handle indentation
                continue

            if cmd.name == 'ELSE':
                # ELSE transitions from true to false block
                # Dedent from true block, output ELSE, then process else-block
                self.dedent()
                self.add_line("ELSE;")

                # If ELSE has children (else-block content), process them
                if cmd.children:
                    self._convert_case_commands(cmd.children)
                else:
                    # No children, just re-indent for potential sibling commands
                    self.indent()
                continue

            # Handle increment/decrement operators
            if cmd.name == '++':
                # /var ++ -> VAR = VAR + 1;
                if cmd.parameters:
                    var_name = cmd.parameters[0].lstrip('/')
                    self.add_line(f"{var_name} = {var_name} + 1;")
                continue

            if cmd.name == '--':
                # /var -- -> VAR = VAR - 1;
                if cmd.parameters:
                    var_name = cmd.parameters[0].lstrip('/')
                    self.add_line(f"{var_name} = {var_name} - 1;")
                continue

            # Handle for loops
            if dfa_cmd == 'FOR':
                self._convert_for_command(cmd)
                continue

            if cmd.name == 'ENDFOR':
                self.add_line("ENDFOR;")
                continue

            # Handle output commands (SH, SHL, SHR, SHC, SHP)
            if dfa_cmd == 'OUTPUT':
                self._convert_output_command_dfa(cmd, current_x, current_y, current_font,
                                                 x_was_explicitly_set, y_was_explicitly_set, y_is_next_line)
                # After output, position becomes implicit and next output should advance to next line
                x_was_explicitly_set = False
                y_was_explicitly_set = False
                y_is_next_line = True
                continue

            # Handle positioning commands - store position for next OUTPUT
            if cmd.name == 'MOVETO':
                if len(cmd.parameters) >= 2:
                    try:
                        current_x = float(cmd.parameters[0])
                        current_y = float(cmd.parameters[1])
                        x_was_explicitly_set = True
                        y_was_explicitly_set = True
                        y_is_next_line = False  # Explicit Y position overrides NEXT
                    except ValueError:
                        pass
                continue

            if cmd.name == 'MOVEH':
                if cmd.parameters:
                    try:
                        current_x = float(cmd.parameters[0])
                        x_was_explicitly_set = True
                        y_was_explicitly_set = False  # Y becomes implicit (use SAME)
                        y_is_next_line = False  # MOVEH resets next-line flag, Y should be SAME
                    except ValueError:
                        pass
                continue

            # Handle box drawing
            if dfa_cmd == 'BOX':
                self._convert_box_command_dfa(cmd)
                continue

            # Handle segment/image calls
            if cmd.name == 'SCALL' or cmd.name == 'ICALL':
                self._convert_resource_command_dfa(cmd, current_x, current_y)
                continue

            # Handle SUBSTR (GETINTV in VIPP)
            # VIPP: /result source start length GETINTV SETVAR
            # DFA: result = SUBSTR(source, start+1, length, '');
            if dfa_cmd == 'SUBSTR':
                if len(cmd.parameters) >= 4:
                    # GETINTV now pops 4 parameters: /result, source, start, length
                    result_param = cmd.parameters[0]
                    source_var = cmd.parameters[1]
                    start = int(float(cmd.parameters[2]))
                    length = cmd.parameters[3]

                    # Extract result variable name (remove leading / if present)
                    result_var = result_param[1:] if result_param.startswith('/') else result_param

                    # XEROX uses 0-based indexing, DFA uses 1-based
                    dfa_start = start + 1
                    self.add_line(f"{result_var} = SUBSTR({source_var}, {dfa_start}, {length}, '');")
                continue

            # Handle CLIP/ENDCLIP - not supported in DFA
            if cmd.name in ('CLIP', 'ENDCLIP'):
                self.add_line("/* Note: DFA does not support CLIP/ENDCLIP. */")
                self.add_line("/* Use MARGIN, SHEET/LOGICALPAGE dimensions, WIDTH on TEXT, or image size params instead */")
                continue

            # Skip SETPAGEDEF silently - already handled at docformat level
            if cmd.name in ('SETLKF', 'SETPAGEDEF'):
                continue

            # Skip other unsupported VIPP commands with comment
            if cmd.name in ('CACHE', 'PAGEBRK', 'NEWFRAME',
                          'BOOKMARK', 'SETPAGENUMBER', 'PAGEDEF',
                          'CPCOUNT', 'GETITEM'):
                self.add_line(f"/* VIPP command not directly supported: {cmd.name} */")
                continue

        # Close OUTLINE if it was opened
        if outline_opened:
            self.dedent()
            self.add_line("ENDIO;")

        self.dedent()
    
    def _convert_if_command(self, cmd: XeroxCommand):
        """Convert an IF command to DFA."""
        # Split parameters if they're combined into a single string
        split_params = []
        for param in cmd.parameters:
            # If param contains spaces, split it into individual tokens
            if ' ' in param:
                split_params.extend(param.split())
            else:
                split_params.append(param)

        # Handle VIPP increment/decrement operators (++ / --)
        # In VIPP: /VAR ++ means increment VAR
        # Convert to DFA: VAR = VAR + 1; before the IF
        clean_params = []
        i = 0
        while i < len(split_params):
            param = split_params[i]
            if param == '++':
                # Previous param should be the variable to increment
                if clean_params:
                    var_name = clean_params[-1].lstrip('/')
                    self.add_line(f"{var_name} = {var_name} + 1;")
                    clean_params.pop()  # Remove the variable from condition
            elif param == '--':
                # Previous param should be the variable to decrement
                if clean_params:
                    var_name = clean_params[-1].lstrip('/')
                    self.add_line(f"{var_name} = {var_name} - 1;")
                    clean_params.pop()  # Remove the variable from condition
            else:
                clean_params.append(param)
            i += 1

        # Convert comparison operators (eq -> ==, ne -> <>, etc.)
        converted_ops = self._convert_comparison_operators(clean_params)
        condition = " ".join(self._convert_params(converted_ops))

        # Don't output empty conditions - just output IF with THEN
        if condition.strip():
            self.add_line(f"IF {condition}; THEN;")
        else:
            self.add_line("IF 1; THEN;")  # Default true condition if empty

        # Process children (IF body) if present
        if cmd.children:
            self._convert_case_commands(cmd.children)
            # IF blocks with children need ENDIF, but only if one wasn't already
            # processed as a child command (some VIPP blocks include ENDIF as last child)
            if not (cmd.children and cmd.children[-1].name == 'ENDIF'):
                self.add_line("ENDIF;")

    def _convert_for_command(self, cmd: XeroxCommand):
        """Convert a FOR loop to DFA."""
        # Extract loop parameters
        params = " ".join(self._convert_params(cmd.parameters))
        self.add_line(f"FOR {params};")
    
    def _convert_output_command(self, cmd: XeroxCommand):
        """Convert an output command (SH, SHL, SHR, SHr, SHC, SHP) to DFA."""
        # Extract text and parameters
        text = ""
        font = "ARIAL8"
        position = ""
        align = ""
        is_variable_output = False

        # Determine alignment based on original command
        if cmd.name == 'SHL':
            align = "ALIGN LEFT"
        elif cmd.name in ('SHR', 'SHr'):
            align = "ALIGN RIGHT"
        elif cmd.name == 'SHC':
            align = "ALIGN CENTER"
        elif cmd.name == 'SH':
            align = ""  # Default alignment (left)
        elif cmd.name == 'SHP':
            align = "ALIGN PARAM"  # Parameterized alignment

        # Extract parameters
        for param in cmd.parameters:
            if param == 'VSUB':
                # Skip VSUB marker - already handled inline
                continue
            elif param.startswith('/'):
                # Font reference
                font_alias = param.lstrip('/')
                font = self.font_mappings.get(font_alias, font_alias.upper())
            elif param.startswith('(') and param.endswith(')'):
                # Text string - check for VSUB and font switches
                text = param
            elif param.startswith('VAR_') or param.startswith('VAR') or param.startswith('FLD'):
                # Variable reference - output the variable directly
                text = param
                is_variable_output = True

        # Process text for VSUB variable substitution
        if text:
            if is_variable_output:
                # Variable reference - output directly without quotes
                output_parts = [f"OUTPUT {text}"]
                if font:
                    output_parts.append(f"FONT {font} NORMAL")
                if align:
                    output_parts.append(align)
                self.add_line(" ".join(output_parts) + ";")
                return

            inner_text = text.strip('()')
            # Check for VSUB patterns ($$VAR. or $VAR)
            if '$$' in inner_text or '$' in inner_text:
                inner_text = self._convert_vsub(inner_text)

            # Check for font switch sequences (~~FA, ~~FB, etc.)
            font_switch_result = self._convert_font_switch(inner_text)

            if isinstance(font_switch_result, list) and len(font_switch_result) > 1:
                # Multiple font switches - generate multiple OUTPUT statements
                self._generate_font_switched_output(font_switch_result, font, align)
                return

            # Wrap in quotes for DFA
            text = f"'{inner_text}'"

            # Generate DFA output command
            output_parts = [f"OUTPUT {text}"]
            if font:
                output_parts.append(f"FONT {font} NORMAL")
            if position:
                output_parts.append(position)
            if align:
                output_parts.append(align)

            self.add_line(" ".join(output_parts) + ";")

    def _convert_output_command_dfa(self, cmd: XeroxCommand, x_pos: float, y_pos: float, current_font: str,
                                   x_was_set: bool = True, y_was_set: bool = True, y_is_next: bool = False):
        """Convert an output command to proper DFA OUTPUT with FONT and POSITION."""
        text = ""
        is_variable = False

        # Extract text from parameters
        for param in cmd.parameters:
            if param == 'VSUB':
                continue
            elif param.startswith('(') and param.endswith(')'):
                text = param[1:-1]  # Remove parentheses
            elif param.startswith('VAR_') or param.startswith('VAR') or param.startswith('FLD'):
                text = param
                is_variable = True

        if not text:
            return

        # Process VSUB patterns
        if not is_variable and ('$$' in text or '$' in text):
            text = self._convert_vsub(text)
            # After VSUB conversion, if text contains ! concatenation, treat as variable
            if ' ! ' in text:
                is_variable = True

        # Determine alignment from command type
        alignment = None
        if cmd.name == 'SHL':
            alignment = 0  # Left
        elif cmd.name in ('SHR', 'SHr'):
            alignment = 1  # Right
        elif cmd.name == 'SHC':
            alignment = 2  # Center

        # Use flags to determine position format
        x_final = x_pos if x_was_set else 'SAME'
        if y_is_next:
            y_final = 'NEXT'  # After NL or previous OUTPUT, use NEXT to stay on the new line
        elif y_was_set:
            y_final = y_pos  # Explicit position
        else:
            y_final = 'SAME'  # Implicit position

        # Generate proper DFA OUTPUT with FONT and POSITION on separate lines
        # Format: OUTPUT text FONT fontname NORMAL POSITION x y [ALIGN ...];
        if is_variable:
            self.add_line(f"OUTPUT {text}")
        else:
            self.add_line(f"OUTPUT '{text}'")
        self.add_line(f"    FONT {current_font} NORMAL")
        self.add_line(f"    {self._format_position(x_final, y_final)}")

        # Add alignment if specified
        if alignment == 0:
            self.add_line("    ALIGN LEFT NOPAD;")
        elif alignment == 1:
            self.add_line("    ALIGN RIGHT NOPAD;")
        elif alignment == 2:
            self.add_line("    ALIGN CENTER NOPAD;")
        elif alignment == 3:
            self.add_line("    ALIGN JUSTIFY NOPAD;")
        else:
            self.add_line("    ;")

    def _convert_box_command_dfa(self, cmd: XeroxCommand):
        """Convert a box drawing command to proper DFA BOX."""
        if len(cmd.parameters) >= 4:
            x = cmd.parameters[0]
            y = cmd.parameters[1]
            width = cmd.parameters[2]
            height = cmd.parameters[3]
            self.add_line(f"BOX X {x} MM Y {y} MM WIDTH {width} MM HEIGHT {height} MM;")

    def _convert_resource_command_dfa(self, cmd: XeroxCommand, x_pos: float, y_pos: float):
        """Convert a resource call (SCALL/ICALL) to proper DFA SEGMENT."""
        if cmd.parameters:
            resource_name = cmd.parameters[0].strip('()')
            # Add segment position correction
            self.add_line(f"SEGMENT {resource_name} POSITION {x_pos} MM ({y_pos} MM-$MR_TOP+&CORSEGMENT);")

    def _generate_font_switched_output(self, parts: List, default_font: str, align: str):
        """
        Generate multiple OUTPUT statements for text with font switches.

        Args:
            parts: List of text parts and font aliases from font switch parsing
            default_font: Default font to use
            align: Alignment setting
        """
        current_font = default_font
        i = 0
        while i < len(parts):
            part = parts[i]
            if i + 1 < len(parts) and len(parts[i + 1]) <= 2:
                # Next element is a font alias
                text = part
                current_font = parts[i + 1].upper()
                i += 2
            else:
                text = part
                i += 1

            if text.strip():
                output_parts = [f"OUTPUT '{text}'", f"FONT {current_font} NORMAL"]
                if align:
                    output_parts.append(align)
                self.add_line(" ".join(output_parts) + ";")
    
    def _convert_position_command(self, cmd: XeroxCommand):
        """Convert a positioning command to DFA."""
        if cmd.name == 'MOVETO':
            # Extract x and y coordinates
            if len(cmd.parameters) >= 2:
                x, y = cmd.parameters[0], cmd.parameters[1]
                self.add_line(f"POSITION {x} MM {y} MM;")
        elif cmd.name == 'MOVEH':
            # Horizontal positioning
            if len(cmd.parameters) >= 1:
                x = cmd.parameters[0]
                self.add_line(f"POSITION {x} MM SAME;")
    
    def _convert_box_command(self, cmd: XeroxCommand):
        """Convert a box drawing command to DFA."""
        # Extract parameters
        params = self._convert_params(cmd.parameters)
        
        # Basic box command
        self.add_line("BOX")
        self.indent()
        
        # Extract position, width, height
        position = "POSITION 0 0"
        width = "WIDTH 10 MM"
        height = "HEIGHT 10 MM"
        color = "COLOR BLACK"
        thickness = "THICKNESS MEDIUM"
        type_line = "TYPE SOLID"
        
        # Parse parameters into DFA format
        self.add_line(position)
        self.add_line(width)
        self.add_line(height)
        self.add_line(color)
        self.add_line(thickness)
        self.add_line(type_line + ";")
        
        self.dedent()
    
    def _convert_resource_command(self, cmd: XeroxCommand):
        """Convert a resource (SCALL/ICALL) command to DFA."""
        # Extract resource name and parameters
        resource_name = ""
        position = "POSITION 0 0"

        for param in cmd.parameters:
            if param.startswith('(') and param.endswith(')'):
                # Resource name
                resource_name = param.strip('()')

        if cmd.name == 'SCALL':
            self.add_line(f"SEGMENT {resource_name}")
            self.indent()
            # Add segment position correction for vertical position
            self.add_line("POSITION (0 MM-$MR_LEFT) (0 MM-$MR_TOP+&CORSEGMENT);")
            self.dedent()
        elif cmd.name == 'ICALL':
            self.add_line(f"IMAGE '{resource_name}'")
            self.indent()
            self.add_line(position + ";")
            self.dedent()

    def _convert_cache_command(self, cmd: XeroxCommand):
        """
        Convert a VIPP CACHE command to DFA.

        CACHE is used for resource caching with scaling parameters.
        VIPP: (resource.eps) CACHE scale SCALL
        DFA: CACHE 'resource.eps' SCALE scale;
        """
        resource_name = ""
        scale = "1.0"

        for i, param in enumerate(cmd.parameters):
            if param.startswith('(') and param.endswith(')'):
                resource_name = param.strip('()')
            elif param.replace('.', '', 1).isdigit():
                scale = param

        if resource_name:
            self.add_line(f"CACHE '{resource_name}' SCALE {scale};")

    # NOTE: _convert_clip_command removed - DFA does not support CLIP/ENDCLIP
    # Use MARGIN, SHEET/LOGICALPAGE dimensions, WIDTH on TEXT, or image size params instead

    def _convert_newframe_command(self, cmd: XeroxCommand):
        """
        Convert a VIPP NEWFRAME command to DFA.

        NEWFRAME triggers frame overflow handling.
        """
        frame_name = ""
        if cmd.parameters:
            frame_name = cmd.parameters[0].strip('()/')

        if frame_name:
            self.add_line(f"NEWFRAME '{frame_name}';")
        else:
            self.add_line("NEWFRAME;")

    def _convert_setlkf_command(self, cmd: XeroxCommand):
        """
        Convert a VIPP SETLKF command to DFA.

        SETLKF defines linked frames for overflow handling.
        VIPP: [frame1 frame2] SETLKF
        DFA: LINKFRAMES frame1 frame2;
        """
        frames = []
        for param in cmd.parameters:
            if param.startswith('['):
                # Start of frame array
                param = param.lstrip('[')
            if param.endswith(']'):
                param = param.rstrip(']')
            if param:
                frames.append(param.strip('/'))

        if frames:
            frame_list = ' '.join(frames)
            self.add_line(f"LINKFRAMES {frame_list};")

    def _convert_setpagedef_command(self, cmd: XeroxCommand):
        """
        Convert a VIPP SETPAGEDEF command to DFA.

        SETPAGEDEF defines page arrays for overflow.
        """
        if cmd.parameters:
            params = " ".join(self._convert_params(cmd.parameters))
            self.add_line(f"PAGEDEF {params};")

    def _convert_bookmark_command(self, cmd: XeroxCommand):
        """
        Convert a VIPP BOOKMARK command to DFA.

        BOOKMARK creates PDF bookmarks for navigation.
        VIPP: (text) level BOOKMARK
        DFA: BOOKMARK 'text' LEVEL level;
        """
        bookmark_text = ""
        level = "1"

        for param in cmd.parameters:
            if param.startswith('(') and param.endswith(')'):
                bookmark_text = param.strip('()')
            elif param.isdigit():
                level = param

        if bookmark_text:
            # Handle VSUB in bookmark text
            if '$$' in bookmark_text or '$' in bookmark_text:
                bookmark_text = self._convert_vsub(bookmark_text)
            self.add_line(f"BOOKMARK '{bookmark_text}' LEVEL {level};")

    def _convert_pagenumber_command(self, cmd: XeroxCommand):
        """
        Convert a VIPP SETPAGENUMBER command to DFA.

        SETPAGENUMBER sets up page numbering.
        """
        if cmd.parameters:
            params = " ".join(self._convert_params(cmd.parameters))
            self.add_line(f"PAGENUMBER {params};")
        else:
            self.add_line("PAGENUMBER;")

    def _convert_params(self, params: List[str]) -> List[str]:
        """Convert Xerox command parameters to DFA format."""
        dfa_params = []
        
        for param in params:
            # Handle variable references
            if param.startswith('/'):
                var_name = param.lstrip('/')
                dfa_params.append(var_name)
            # Handle string literals
            elif param.startswith('(') and param.endswith(')'):
                text = param.strip('()')
                dfa_params.append(f"'{text}'")
            # Handle numeric values
            elif param.isdigit() or (param.replace('.', '', 1).isdigit() and param.count('.') <= 1):
                dfa_params.append(param)
            # Pass other parameters through
            else:
                dfa_params.append(param)
        
        return dfa_params

    def _generate_form_usage_info(self):
        """Generate form selection code for first page vs subsequent pages."""
        # List available forms
        frm_names = []
        for frm_filename in sorted(self.frm_files.keys()):
            frm_name = os.path.splitext(frm_filename)[0].upper()
            frm_name = ''.join(c for c in frm_name if c.isalnum() or c == '_')
            frm_names.append(frm_name)

        self.add_line("IF PP < 1; THEN;")
        self.indent()

        if len(frm_names) > 0:
            # Find first page form (ending in F)
            first_form = next((f for f in frm_names if f.endswith('F')), frm_names[0])
            subseq_form = next((f for f in frm_names if f.endswith('S')), frm_names[-1] if len(frm_names) > 1 else frm_names[0])
            self.add_line(f"USE FORMAT {first_form} EXTERNAL;")
        else:
            self.add_line("USE FORMAT FIRSTPAGE EXTERNAL;")

        self.dedent()
        self.add_line("ELSE;")
        self.indent()

        if len(frm_names) > 0:
            self.add_line(f"USE FORMAT {subseq_form} EXTERNAL;")
        else:
            self.add_line("USE FORMAT NEXTPAGE EXTERNAL;")

        self.dedent()
        self.add_line("ENDIF;")
        self.add_line("")

    def _generate_form_usage_in_printfooter(self):
        """
        Generate form selection code in PRINTFOOTER.
        Uses IF P < 1 to select first page vs subsequent pages.
        """
        # List available forms
        frm_names = []
        for frm_filename in sorted(self.frm_files.keys()):
            frm_name = os.path.splitext(frm_filename)[0].upper()
            frm_name = ''.join(c for c in frm_name if c.isalnum() or c == '_')
            frm_names.append(frm_name)

        if len(frm_names) == 0:
            return  # No forms to use

        # Find first page form (ending in F) and subsequent page form (ending in S)
        first_form = next((f for f in frm_names if f.endswith('F')), frm_names[0])
        subseq_form = next((f for f in frm_names if f.endswith('S')), frm_names[-1] if len(frm_names) > 1 else frm_names[0])

        self.add_line("      IF P<1;")
        self.add_line("      THEN;")
        self.add_line("        USE")
        self.add_line(f"          FORMAT {first_form} EXTERNAL;")
        self.add_line("      ELSE;")
        self.add_line("        USE")
        self.add_line(f"          FORMAT {subseq_form} EXTERNAL;")
        self.add_line("      ENDIF;")

    def _generate_variable_initialization(self):
        """
        Generate variable initialization from DBM commands.

        Processes the initialization section at the beginning of the DBM file
        (typically a VARINI IF block) and adds it to $_BEFOREFIRSTDOC.
        Since $_BEFOREFIRSTDOC only runs once, we don't need the VARINI IF pattern
        or /INI checks - variables don't exist yet.
        """
        self.add_line("/* Variable Initialization from DBM */")
        self.add_line("")

        # Add standard counter and flag initializations
        # These are typically inside the IF VARINI block in OCBC VIPP files
        # Note: SETLSP is already added to main DOCFORMAT after MARGIN
        self.add_line("")

        self.add_line("/* Counter initializations */")
        self.add_line("VAR_COUNTERC = 0;")
        self.add_line("VAR_COUNTERI = 0;")
        self.add_line("VAR_COUNT_TX = 0;")
        self.add_line("VAR_COUNTTX2 = 0;")
        self.add_line("VAR_COUNTTS2 = 0;")
        self.add_line("VAR_TXNF = 0;")
        self.add_line("VAR_NF = 0;")
        self.add_line("VAR_RACC = 0;")
        self.add_line("VAR_COUNTPAGE = 0;")
        self.add_line("VAR_COUNTERS = 0;")
        self.add_line("")

        self.add_line("/* Date format variables */")
        self.add_line("VARMdate = 0;")
        self.add_line("VARMmonth = 0;")
        self.add_line("VARMyear = 0;")
        self.add_line("VARTdate = 0;")
        self.add_line("VARTmonth = 0;")
        self.add_line("VARTyear = 0;")
        self.add_line("")

        self.add_line("/* Flag variables */")
        self.add_line("VAR_NoTrx = 1;  /* for multiple account without transaction */")
        self.add_line("VAR_NotBeign = 0;")
        self.add_line("VAR_New_DOC = 1;")
        self.add_line("VAR_DOC_count = 0;")
        self.add_line("VAR_Brk_count = '000';")
        self.add_line("")

        self.add_line("/* Page numbering */")
        self.add_line("VARtab = '';  /* Array placeholder */")
        self.add_line("VARdoc = 0;")
        self.add_line("")

        # Process any additional SETVAR commands from dbm.commands
        self._process_initialization_commands(self.dbm.commands)

        self.add_line("")

    def _process_initialization_commands(self, commands: List[XeroxCommand]):
        """Recursively process commands to extract variable initializations."""
        for cmd in commands:
            # Handle SETVAR commands (skip VARINI itself)
            if cmd.name == 'SETVAR':
                var_name = None
                var_value = None

                # Parse parameters: /VarName value [/INI] SETVAR
                params = cmd.parameters
                for i, param in enumerate(params):
                    if param.startswith('/') and param not in ('/INI',):
                        # Variable name (remove leading /)
                        var_name = param[1:]
                    elif param not in ('/INI', 'SETVAR') and var_name and var_value is None:
                        # This is the value
                        var_value = param

                if var_name and var_value is not None:
                    # Skip VARINI variable itself (it's just a guard)
                    if var_name == 'VARINI':
                        continue

                    # Convert value to DFA format
                    dfa_value = self._convert_setvar_value(var_value)

                    # Direct assignment (no IF check needed since $_BEFOREFIRSTDOC runs once)
                    self.add_line(f"{var_name} = {dfa_value};")

            # Handle IF commands - process children recursively
            elif cmd.name == 'IF':
                # If this IF has children (body), process them recursively
                if hasattr(cmd, 'children') and cmd.children:
                    self._process_initialization_commands(cmd.children)

            # Handle page layout commands
            elif cmd.name == 'SETUNIT':
                if cmd.parameters and cmd.parameters[0] == 'MM':
                    self.add_line("")
                    self.add_line("/* Page layout settings */")
                    self.add_line("SETUNITS MM;")

            elif cmd.name == 'SETLSP':
                if cmd.parameters:
                    spacing = cmd.parameters[0]
                    self.add_line(f"SETUNITS LINESP {spacing} MM;")

            elif cmd.name in ('ORITL', 'PORT', 'LAND'):
                # Orientation commands - convert to comment (DFA handles this differently)
                self.add_line(f"/* Orientation: {cmd.name} */")

            # Recursively process any children (for nested structures)
            if hasattr(cmd, 'children') and cmd.children:
                self._process_initialization_commands(cmd.children)

    def _convert_setvar_value(self, value: str) -> str:
        """
        Convert a VIPP SETVAR value to DFA format.

        Args:
            value: VIPP value (e.g., 'true', 'false', '0', '(000)')

        Returns:
            DFA-formatted value
        """
        # Boolean values
        if value == 'true':
            return '1'
        elif value == 'false':
            return '0'
        # String values (in parentheses)
        elif value.startswith('(') and value.endswith(')'):
            # Remove outer parentheses and add quotes
            return f"'{value[1:-1]}'"
        # Numeric values
        elif value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return value
        # Arrays like [[/VAR_pctot]]
        elif value.startswith('[[') and value.endswith(']]'):
            # This is an array initialization - keep as is for now
            return f"'{value}'"
        # Default: treat as string
        else:
            return f"'{value}'"

    def _generate_initialization(self):
        """Generate initialization code in $_BEFOREFIRSTDOC section following LucaB's pattern."""
        self.add_line("/* Initialize variables */")
        self.add_line("DOCFORMAT $_BEFOREFIRSTDOC;")
        self.indent()

        # Initialize page counters
        self.add_line("/* Current page */")
        self.add_line("PP = 0;")
        self.add_line("/* Total pages */")
        self.add_line("TP = 0;")
        self.add_line("")

        # Add position correction variables for Xerox alignment
        self.add_line("/* Correction for Xerox position */")
        self.add_line("/* Correction = ($SL_MAXY - $SL_MINY)/4 */")
        self.add_line("&CORFONT6 = -33;")
        self.add_line("&CORFONT7 = -37.5;")
        self.add_line("&CORFONT8 = -43.5;")
        self.add_line("&CORFONT10 = -55.5;")
        self.add_line("&CORFONT12 = -66;")
        self.add_line("&CORSEGMENT = 33;")
        self.add_line("")

        # Add variable initialization from DBM commands
        self._generate_variable_initialization()

        # Read data header to detect separator and field names (LucaB's pattern)
        self.add_line("/* Read data header */")
        delimiter = self.input_config.delimiter
        delimiter_literal = f"'{delimiter}'" if delimiter != "'" else '"\'"'
        self.add_line(f"&SEP = {delimiter_literal};")

        self.add_line("FOR I")
        self.indent()
        self.add_line("REPEAT 1;")

        # Read first line
        self.add_line("RECORD DATAHEADER")
        self.indent()
        self.add_line("REPEAT 1;")
        self.add_line("VARIABLE LINE1 SCALAR NOSPACE START 1;")
        self.dedent()
        self.add_line("ENDIO;")
        self.add_line("")

        # Check if header line contains field names
        self.add_line("/* Field (Standard) Names: FLD1, FLD2, etc. */")
        self.add_line("IF LEFT(LINE1, 7, '') == 'PREFIX|'; THEN;")
        self.indent()

        # Extract field names from header
        self.add_line("LINE1 = CHANGE(LINE1, 'PREFIX|', '');")
        self.add_line("D = EXTRACTALL(&FIELDS, LINE1, &SEP, '');")

        # Calculate max fields (excluding empty trailing field)
        self.add_line("IF &FIELDS[MAXINDEX(&FIELDS)] == ''; THEN;")
        self.indent()
        self.add_line("&MAXFIELDS = MAXINDEX(&FIELDS) - 1;")
        self.dedent()
        self.add_line("ELSE;")
        self.indent()
        self.add_line("&MAXFIELDS = MAXINDEX(&FIELDS);")
        self.dedent()
        self.add_line("ENDIF;")

        self.dedent()
        self.add_line("ELSE;")
        self.indent()

        # Reset counter to continue reading
        self.add_line("I = 0;")
        self.add_line("")

        # Check for SETDBSEP to extract separator
        self.add_line("/* Separator */")
        self.add_line("IF POS('SETDBSEP', LINE1, 1); THEN;")
        self.indent()
        self.add_line("POS1 = POS('(', LINE1, 1);")
        self.add_line("POS2 = POS(')', LINE1, 1);")
        self.add_line("&SEP = SUBSTR(LINE1, POS1+1, POS2-POS1-1, '');")
        self.dedent()
        self.add_line("ENDIF;")
        self.add_line("")

        # Check for SETPROJECT to extract procedure name
        self.add_line("/* Procedure to be called */")
        self.add_line("IF POS('SETPROJECT', LINE1, 1); THEN;")
        self.indent()
        self.add_line("/* Starting position for the second parenthesis... */")
        self.add_line("POS1 = POS('(', LINE1, 4);")
        self.add_line("POS2 = POS(')', LINE1, POS1+1);")
        self.add_line("&PROCEDURE = SUBSTR(LINE1, POS1+1, POS2-POS1-1, '');")
        self.dedent()
        self.add_line("ENDIF;")

        self.dedent()
        self.add_line("ENDIF;")

        self.dedent()
        self.add_line("ENDFOR;")
        self.dedent()
        self.add_line("")

        # Generate $_BEFOREDOC for per-document initialization
        self.add_line("/* Per-document initialization */")
        self.add_line("DOCFORMAT $_BEFOREDOC;")
        self.indent()
        self.add_line("P = 0;     /* Reset page counter for new document */")
        self.add_line("PP = 0;    /* Reset total page counter */")
        self.dedent()
        self.add_line("")


def main():
    """Main function to run the converter."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert Xerox FreeFlow to Papyrus DocDEF')
    parser.add_argument('input_path', help='Path to Xerox file or directory containing Xerox files')
    parser.add_argument('--output_dir', '-o', default='output', help='Directory for output DFA files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--single_file', '-s', action='store_true', help='Process a single file instead of a directory')
    parser.add_argument('--report', '-r', action='store_true', help='Generate a conversion report')
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Process files
    xerox_parser = XeroxParser()
    projects = {}
    conversion_report = []
    
    try:
        if args.single_file:
            # Process a single file
            if not os.path.isfile(args.input_path):
                logger.error(f"File not found: {args.input_path}")
                return
            
            logger.info(f"Processing single file: {args.input_path}")
            
            # Determine project name
            project_name = "DEFAULT"
            if args.input_path.lower().endswith('.dbm'):
                try:
                    dbm = xerox_parser.parse_file(args.input_path)
                    projects[project_name] = XeroxProject(name=project_name)
                    projects[project_name].dbm_files[os.path.basename(args.input_path)] = dbm

                    # Find related FRM files in the same directory
                    dir_path = os.path.dirname(args.input_path)
                    if dir_path:
                        for file in os.listdir(dir_path):
                            if file.lower().endswith('.frm'):
                                frm_path = os.path.join(dir_path, file)
                                try:
                                    frm = xerox_parser.parse_file(frm_path)
                                    projects[project_name].frm_files[file] = frm
                                    logger.info(f"Found related FRM file: {frm_path}")
                                except Exception as e:
                                    logger.error(f"Error parsing FRM file {frm_path}: {e}")

                except Exception as e:
                    logger.error(f"Error parsing DBM file {args.input_path}: {e}")
            elif args.input_path.lower().endswith('.jdt'):
                try:
                    jdt = xerox_parser.parse_file(args.input_path)
                    projects[project_name] = XeroxProject(name=project_name)
                    # Store JDT in a placeholder - we'll handle it differently
                    projects[project_name].jdt = jdt

                    # Find related FRM files in the same directory
                    dir_path = os.path.dirname(args.input_path)
                    if dir_path:
                        for file in os.listdir(dir_path):
                            if file.lower().endswith('.frm'):
                                frm_path = os.path.join(dir_path, file)
                                try:
                                    frm = xerox_parser.parse_file(frm_path)
                                    projects[project_name].frm_files[file] = frm
                                    logger.info(f"Found related FRM file: {frm_path}")
                                except Exception as e:
                                    logger.error(f"Error parsing FRM file {frm_path}: {e}")

                except Exception as e:
                    logger.error(f"Error parsing JDT file {args.input_path}: {e}")
            elif args.input_path.lower().endswith('.frm'):
                logger.error("Cannot convert standalone FRM file. Please provide a DBM or JDT file.")
                return
            else:
                logger.error(f"Unsupported file type: {args.input_path}")
                return
        else:
            # Process all files in the input directory
            if not os.path.isdir(args.input_path):
                logger.error(f"Directory not found: {args.input_path}")
                return
            
            # First pass: identify projects and files.
            # FRM files are collected into a shared pool so they can be
            # associated with every JDT project found in the directory.
            frm_pool: Dict[str, Any] = {}

            for root, dirs, files in os.walk(args.input_path):
                for file in files:
                    if not (file.lower().endswith('.dbm') or
                            file.lower().endswith('.frm') or
                            file.lower().endswith('.jdt')):
                        continue

                    file_path = os.path.join(root, file)
                    logger.info(f"Found Xerox file: {file_path}")

                    if file.lower().endswith('.dbm'):
                        project_name = "DEFAULT"
                        if project_name not in projects:
                            projects[project_name] = XeroxProject(name=project_name)
                        try:
                            dbm = xerox_parser.parse_file(file_path)
                            projects[project_name].dbm_files[file] = dbm
                        except Exception as e:
                            logger.error(f"Error parsing DBM file {file}: {e}")
                            if args.verbose:
                                logger.error(traceback.format_exc())

                    elif file.lower().endswith('.frm'):
                        try:
                            frm = xerox_parser.parse_file(file_path)
                            frm_pool[file] = frm
                            # Also attach to DEFAULT project for DBM+FRM projects
                            if "DEFAULT" not in projects:
                                projects["DEFAULT"] = XeroxProject(name="DEFAULT")
                            projects["DEFAULT"].frm_files[file] = frm
                        except Exception as e:
                            logger.error(f"Error parsing FRM file {file}: {e}")
                            if args.verbose:
                                logger.error(traceback.format_exc())

                    elif file.lower().endswith('.jdt'):
                        # Each JDT file is its own project, named after the file stem
                        project_name = os.path.splitext(file)[0].upper()
                        if project_name not in projects:
                            projects[project_name] = XeroxProject(name=project_name)
                        try:
                            jdt = xerox_parser.parse_file(file_path)
                            projects[project_name].jdt = jdt
                        except Exception as e:
                            logger.error(f"Error parsing JDT file {file}: {e}")
                            if args.verbose:
                                logger.error(traceback.format_exc())

            # Distribute the FRM pool to every JDT project so each one
            # has access to the shared form definitions.
            for project in projects.values():
                if project.jdt and not project.frm_files:
                    project.frm_files.update(frm_pool)
        
        # Second pass: convert each project
        for project_name, project in projects.items():
            logger.info(f"Converting project: {project_name}")
            
            # Convert each DBM file
            for dbm_file, dbm in project.dbm_files.items():
                try:
                    # Get associated FRM files
                    frm_files = project.frm_files

                    # Resolve font conflicts between DBM and FRM files
                    xerox_parser.resolve_font_conflicts(dbm, frm_files)

                    # Create converter
                    converter = VIPPToDFAConverter(dbm, frm_files)
                    
                    # Generate DFA code for main DBM
                    dfa_code = converter.generate_dfa_code()

                    # Write main output file
                    output_filename = os.path.splitext(dbm_file)[0] + '.dfa'
                    output_path = os.path.join(args.output_dir, output_filename)

                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(dfa_code)

                    logger.info(f"Converted {dbm_file} to {output_path}")

                    # Generate separate DFA files for each FRM
                    for frm_filename, frm in frm_files.items():
                        try:
                            frm_dfa_code = converter.generate_frm_dfa_code(frm, as_include=True)
                            frm_output_filename = os.path.splitext(frm_filename)[0] + '.dfa'
                            frm_output_path = os.path.join(args.output_dir, frm_output_filename)

                            with open(frm_output_path, 'w', encoding='utf-8') as f:
                                f.write(frm_dfa_code)

                            logger.info(f"Converted FRM {frm_filename} to {frm_output_path}")
                            conversion_report.append({
                                'source_file': frm_filename,
                                'output_file': frm_output_filename,
                                'status': 'SUCCESS',
                                'message': 'FRM conversion completed successfully.'
                            })
                        except Exception as e:
                            logger.error(f"Error converting FRM {frm_filename}: {e}")
                            if args.verbose:
                                logger.error(traceback.format_exc())
                    conversion_report.append({
                        'source_file': dbm_file,
                        'output_file': output_filename,
                        'status': 'SUCCESS',
                        'message': 'Conversion completed successfully.'
                    })
                    
                except Exception as e:
                    logger.error(f"Error converting {dbm_file}: {e}")
                    if args.verbose:
                        logger.error(traceback.format_exc())
                    
                    conversion_report.append({
                        'source_file': dbm_file,
                        'output_file': '',
                        'status': 'ERROR',
                        'message': str(e)
                    })

            # Convert JDT file if present
            if project.jdt:
                try:
                    logger.info(f"Converting JDT file: {project.jdt.filename}")

                    # Get associated FRM files
                    frm_files = project.frm_files

                    # Create converter for JDT
                    converter = VIPPToDFAConverter(jdt=project.jdt, frm_files=frm_files)

                    # Generate DFA code for JDT
                    dfa_code = converter.generate_dfa_code()

                    # Write output file
                    jdt_basename = os.path.basename(project.jdt.filename)
                    output_filename = os.path.splitext(jdt_basename)[0] + '.dfa'
                    output_path = os.path.join(args.output_dir, output_filename)

                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(dfa_code)

                    logger.info(f"Converted JDT {jdt_basename} to {output_path}")

                    # Generate separate DFA files for each FRM
                    for frm_filename, frm in frm_files.items():
                        try:
                            frm_dfa_code = converter.generate_frm_dfa_code(frm, as_include=True)
                            frm_output_filename = os.path.splitext(frm_filename)[0] + '.dfa'
                            frm_output_path = os.path.join(args.output_dir, frm_output_filename)

                            with open(frm_output_path, 'w', encoding='utf-8') as f:
                                f.write(frm_dfa_code)

                            logger.info(f"Converted FRM {frm_filename} to {frm_output_path}")
                            conversion_report.append({
                                'source_file': frm_filename,
                                'output_file': frm_output_filename,
                                'status': 'SUCCESS',
                                'message': 'FRM conversion completed successfully.'
                            })
                        except Exception as e:
                            logger.error(f"Error converting FRM {frm_filename}: {e}")
                            if args.verbose:
                                logger.error(traceback.format_exc())

                    conversion_report.append({
                        'source_file': jdt_basename,
                        'output_file': output_filename,
                        'status': 'SUCCESS',
                        'message': 'JDT conversion completed successfully.'
                    })

                except Exception as e:
                    logger.error(f"Error converting JDT file: {e}")
                    if args.verbose:
                        logger.error(traceback.format_exc())

                    conversion_report.append({
                        'source_file': os.path.basename(project.jdt.filename),
                        'output_file': '',
                        'status': 'ERROR',
                        'message': str(e)
                    })

        # Generate conversion report if requested
        if args.report and conversion_report:
            report_path = os.path.join(args.output_dir, 'conversion_report.json')
            try:
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(conversion_report, f, indent=2)
                logger.info(f"Conversion report saved to {report_path}")
            except Exception as e:
                logger.error(f"Error generating conversion report: {e}")
        
        logger.info("Conversion complete.")
    
    except Exception as e:
        logger.error(f"Error during conversion process: {e}")
        if args.verbose:
            logger.error(traceback.format_exc())
        return 1
    
    return 0


class ResourceExtractor:
    """Utility for extracting and copying resources referenced in Xerox files."""
    
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.resource_types = {
            'jpg': 'image',
            'tif': 'image',
            'eps': 'image',
            'png': 'image',
            'gif': 'image',
            'pdf': 'document',
            'ttf': 'font',
            'otf': 'font'
        }
        self.resources_found = {}
    
    def extract_resources(self, dbm: XeroxDBM, frm_files: Dict[str, XeroxFRM]) -> Dict[str, str]:
        """
        Extract resources referenced in DBM and FRM files.
        
        Args:
            dbm: The parsed DBM file
            frm_files: Dictionary of parsed FRM files
            
        Returns:
            Dictionary mapping resource names to file paths
        """
        resources = {}
        
        # Extract resources from DBM tokens
        for token in dbm.tokens:
            if token.type == 'string':
                resources.update(self._extract_resources_from_string(token.value))
        
        # Extract resources from FRM files
        for frm in frm_files.values():
            for token in frm.tokens:
                if token.type == 'string':
                    resources.update(self._extract_resources_from_string(token.value))
        
        # Copy resources to output directory
        for resource_name, resource_path in resources.items():
            if os.path.exists(resource_path):
                try:
                    dest_path = os.path.join(self.output_dir, os.path.basename(resource_path))
                    if not os.path.exists(dest_path):
                        import shutil
                        shutil.copy2(resource_path, dest_path)
                        logger.info(f"Copied resource: {resource_path} -> {dest_path}")
                except Exception as e:
                    logger.error(f"Error copying resource {resource_path}: {e}")
        
        return resources
    
    def _extract_resources_from_string(self, text: str) -> Dict[str, str]:
        """
        Extract resource references from a string.
        
        Args:
            text: The string to analyze
            
        Returns:
            Dictionary mapping resource names to file paths
        """
        resources = {}
        
        # Remove quotation marks and parentheses
        clean_text = text.strip("'\"()")
        
        # Check if the string references a resource file
        if '.' in clean_text:
            extension = clean_text.split('.')[-1].lower()
            if extension in self.resource_types:
                # This might be a resource file
                resource_name = clean_text
                
                # Try to find the resource in the input directory
                for root, dirs, files in os.walk(self.input_dir):
                    for file in files:
                        if file.lower() == resource_name.lower():
                            resources[resource_name] = os.path.join(root, file)
                            self.resources_found[resource_name] = os.path.join(root, file)
                            break
        
        return resources


if __name__ == "__main__":
    sys.exit(main())

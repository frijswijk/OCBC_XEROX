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
    is_initialization: bool = False  # For SETVAR with /INI flag


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
        'INDEXFONT', 'INDEXCOLOR', 'INDEXBAT', 'INDEXSST', 'XGFRESDEF',
        
        # Page and positioning
        'SETPAGESIZE', 'SETLSP', 'SETPAGENUMBER', 'SETPAGEDEF', 'SETLKF', 'SETFORM',
        'MOVETO', 'MOVEH', 'MOVEHR', 'LINETO', 'NL', 'ORITL', 'PORT', 'LAND', 'SHL', 'SHR', 'SHC', 'SHc', 'SHP', 'SHp', 'SHmf', 'FORMAT',
        'NEWFRONT', 'NEWBACK', 'NEWFRAME', 'PAGEBRK',
        
        # Resource handling
        'CACHE', 'ICALL', 'SCALL', 'DRAWB',
        
        # Forms specific
        'MM', 'CM', 'INCH', 'POINT',
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
            
            # Handle PostScript/VIPP hex string literals <XXYY...>
            # Must be checked before the generic '<' operator path
            if self.input[self.pos] == '<':
                j = self.pos + 1
                while j < len(self.input) and self.input[j] in '0123456789abcdefABCDEF \t':
                    j += 1
                if j < len(self.input) and self.input[j] == '>':
                    self._handle_hex_string()
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

    def _handle_hex_string(self):
        """Handle a PostScript/VIPP hex string literal <XXYY...>.

        In VIPP (PostScript-derived), <76> means the byte 0x76 = 'v'.
        Multi-byte: <4F43> means 'OC'.  Whitespace inside is ignored.
        Produces a 'string' token in VIPP parentheses form, e.g. '(v)'.
        """
        start_line = self.line
        start_col = self.col
        self.pos += 1  # Skip <
        self.col += 1

        hex_chars = []
        while self.pos < len(self.input) and self.input[self.pos] != '>':
            ch = self.input[self.pos]
            if ch in '0123456789abcdefABCDEF':
                hex_chars.append(ch)
            # Spaces/tabs inside hex string are legal whitespace — skip silently
            if ch == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.pos += 1

        if self.pos < len(self.input):  # consume closing '>'
            self.pos += 1
            self.col += 1

        # Convert hex digit pairs to characters (latin-1 / ISO-8859-1)
        hex_str = ''.join(hex_chars)
        if len(hex_str) % 2:
            hex_str = hex_str + '0'  # PostScript pads odd-length with trailing 0
        try:
            chars = bytes.fromhex(hex_str).decode('latin-1')
        except Exception:
            chars = hex_str  # fallback: keep raw hex digits as text

        token = XeroxToken(
            type='string',
            value=f'({chars})',
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
        
        # Include dot for unslashed VIPP variables like VAR.Y5 used in DRAWB flows.
        while self.pos < len(self.input) and (self.input[self.pos].isalnum() or 
                                         self.input[self.pos] in '_$.'):
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

        # Include hyphens for VIPP font names like /Helvetica-Bold, /Courier-BoldOblique
        # Include dots for VIPP array names like /VAR.Y1, /VAR.Y4
        while self.pos < len(self.input) and (self.input[self.pos].isalnum() or
                                         self.input[self.pos] in '_$-.'):
            self.pos += 1
            self.col += 1

        # Create token for the Xerox identifier
        identifier = self.input[start_pos:self.pos]
        if identifier == '/INI':
            logger.debug(f"Tokenizer created /INI token at line {start_line}")
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
        'SHc': 1,     # (text) SHc (case variant)
        'SHP': 3,     # var width align SHP or (text) width align SHP
        'SHp': 3,     # var width align SHp (case variant)

        # Positioning
        'MOVETO': 2,  # x y MOVETO
        'MOVEH': 1,   # x MOVEH
        'MOVEHR': 1,  # x MOVEHR (horizontal rule position — same as MOVEH)
        'NL': 0,      # NL (optional param for spacing)

        # Variable operations
        'SETVAR': 2,  # /var value SETVAR (can have /INI in between)
        '++': 1,      # /var ++ (increment)
        '--': 1,      # /var -- (decrement)

        # Drawing
        'DRAWB': 5,   # x y w h style DRAWB

        # Resources
        'SCALL': 1,   # (name) SCALL or (name) scale SCALL
        'ICALL': 3,   # (name) scale rotation ICALL
        'CACHE': 0,   # (name) CACHE [dimensions] - variable params, handled specially

        # Page layout
        'SETFORM': 1,     # (name.FRM) SETFORM
        'SETLKF': 1,      # [[...]] SETLKF
        'SETPAGEDEF': 1,  # [...] SETPAGEDEF
        'NEWFRAME': 0,    # NEWFRAME
        'PAGEBRK': 0,     # PAGEBRK
        'NEWFRONT': 0,    # NEWFRONT — force to front side; registered so it does NOT pollute stack
        'NEWBACK': 0,     # NEWBACK — force to back side; registered so it does NOT pollute stack
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
        'CASE': 0,    # Handled specially (prefix: CASE var {default} (val){body}... ENDCASE)
        'ENDCASE': 0,

        # Table commands
        'BEGINTABLE': 1,  # [...] BEGINTABLE
        'SHROW': 1,       # [...] SHROW

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
        'FORMAT': 0,   # value (pattern) FORMAT — binary operator, handled specially

        # Misc
        'SETUNIT': 0,  # MM SETUNIT
        'SETLSP': 1,   # n SETLSP
        'ORITL': 0,
        'PORT': 0,
        'LAND': 0,
        'SETFTSW': 2,  # (char) n SETFTSW
        'SETPARAMS': 1,  # [...] SETPARAMS
        'XGFRESDEF': 0,  # {...} XGFRESDEF
        'ADD': 2,      # /array value ADD — adds value to array
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

            # Debug: log /INI tokens
            if token.value == '/INI':
                logger.debug(f"Found /INI token: type={token.type}, value={token.value}, line={token.line_number}")

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
                    # Pop up to 4 params to handle /INI flag
                    params = []
                    while len(stack) > 0 and len(params) < 4:
                        p = stack.pop()
                        if isinstance(p, tuple) and p[0] == 'block':
                            # Convert block tokens to string using our method
                            params.insert(0, self._tokens_to_string(p[1]))
                        elif isinstance(p, tuple) and p[0] == 'FORMAT_EXPR':
                            # FORMAT_EXPR on stack before SETVAR — expand as value
                            params.insert(0, str(p[2]))  # pattern
                            params.insert(0, 'FORMAT')
                            params.insert(0, str(p[1]))  # value
                        else:
                            params.insert(0, str(p))
                    logger.debug(f"SETVAR params before filtering: {params}")
                    # Check for /INI flag before filtering
                    has_ini_flag = '/INI' in params
                    if has_ini_flag:
                        logger.debug(f"Found /INI SETVAR: {params}")
                    # Filter out /INI if present
                    params = [p for p in params if p != '/INI']
                    if len(params) >= 2:
                        cmd = XeroxCommand(
                            name='SETVAR',
                            line_number=token.line_number + line_offset,
                            column=token.column
                        )
                        cmd.parameters = params[:2]  # [var_name, value]
                        cmd.is_initialization = has_ini_flag  # Track /INI flag
                        if has_ini_flag:
                            logger.debug(f"Created SETVAR with is_initialization=True: {cmd.parameters}")
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

                elif cmd_name == 'FORMAT':
                    # FORMAT: value (pattern) FORMAT — binary operator
                    # Consumes 2 from stack (pattern on top, value below)
                    # Pushes back a FORMAT_EXPR tuple for the output handler
                    if len(stack) >= 2:
                        pattern = stack.pop()
                        value = stack.pop()
                        stack.append(('FORMAT_EXPR', str(value), str(pattern)))
                    else:
                        # Not enough items — just leave as-is
                        logger.warning(f"FORMAT operator at line {token.line_number}: insufficient stack items ({len(stack)})")

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

                elif cmd_name == 'CASE':
                    # CASE is prefix syntax: CASE variable {default} (value){body}... ENDCASE
                    # Convert to series of IF commands with children

                    # Variable name is ALWAYS the next token after CASE (prefix syntax)
                    case_var = None
                    j = i + 1
                    while j < len(tokens) and tokens[j].type == 'comment':
                        j += 1
                    if j < len(tokens) and tokens[j].type in ('identifier', 'variable', 'keyword'):
                        case_var = tokens[j].value
                        if case_var.startswith('/'):
                            case_var = case_var.lstrip('/')
                        j += 1

                    # Continue looking ahead to collect default block and case entries
                    while j < len(tokens) and tokens[j].type == 'comment':
                        j += 1

                    # Collect default block if present
                    if j < len(tokens) and tokens[j].value == '{':
                        _, block_end = self._collect_block(tokens, j)
                        j = block_end + 1

                    # Collect (value) {body} pairs until ENDCASE
                    case_entries = []
                    while j < len(tokens):
                        # Skip comments
                        while j < len(tokens) and tokens[j].type == 'comment':
                            j += 1
                        if j >= len(tokens):
                            break
                        if tokens[j].value == 'ENDCASE':
                            j += 1
                            break

                        # Expect a string value token
                        if tokens[j].type == 'string':
                            case_value = tokens[j].value
                            j += 1

                            # Skip comments
                            while j < len(tokens) and tokens[j].type == 'comment':
                                j += 1

                            # Expect a block
                            if j < len(tokens) and tokens[j].value == '{':
                                body_tokens, block_end = self._collect_block(tokens, j)
                                j = block_end + 1
                                case_entries.append((case_value, body_tokens))
                            else:
                                continue
                        else:
                            j += 1  # Skip unexpected tokens

                    # Update main loop index
                    i = j - 1

                    # Generate IF command for each case entry
                    for case_value, body_tokens in case_entries:
                        # Clean parenthesized value
                        clean_value = case_value
                        if clean_value.startswith('(') and clean_value.endswith(')'):
                            clean_value = clean_value[1:-1]

                        if_cmd = XeroxCommand(
                            name='IF',
                            line_number=token.line_number + line_offset,
                            column=token.column
                        )
                        # Build condition as the variable eq string comparison
                        if_cmd.parameters = [f"{case_var} eq ({clean_value})"]
                        # Parse body block recursively
                        child_commands = self._parse_vipp_block(body_tokens, line_offset)
                        if_cmd.children = child_commands
                        commands.append(if_cmd)

                elif cmd_name == 'ENDCASE':
                    # ENDCASE is consumed by CASE handler, but if we see a standalone one
                    # (e.g., in DBM prefix parsing), just skip it
                    pass

                elif cmd_name == 'BEGINTABLE':
                    # BEGINTABLE sets table defaults - consume from stack and skip
                    if len(stack) > 0:
                        stack.pop()  # Consume the defaults block
                    # No DFA output needed - SHROW handles the actual rows

                elif cmd_name == 'SHROW':
                    # SHROW: [...] SHROW — table row with cell definitions
                    # Extract cell text from the block on stack
                    if len(stack) > 0:
                        row_block = stack.pop()
                        cell_texts = []
                        cell_fonts = []
                        cell_widths = []

                        if isinstance(row_block, tuple) and row_block[0] == 'block':
                            block_tokens = row_block[1]
                            # Parse the cell array to extract /CellText values and /TextAtt fonts
                            current_cell_text = None
                            current_cell_font = None
                            current_cell_width = None
                            bi = 0
                            while bi < len(block_tokens):
                                bt = block_tokens[bi]
                                if bt.value == '/CellText':
                                    # Next token is the cell text
                                    bi += 1
                                    if bi < len(block_tokens):
                                        cell_val = block_tokens[bi].value
                                        if cell_val.startswith('(') and cell_val.endswith(')'):
                                            current_cell_text = cell_val[1:-1]
                                        elif cell_val.startswith('($$') and cell_val.endswith('.)'):
                                            # VSUB variable reference: ($$VAR_OFN.) -> VAR_OFN
                                            var_name = cell_val[3:-2]
                                            current_cell_text = ('VAR', var_name)
                                        else:
                                            current_cell_text = cell_val
                                elif bt.value == '/TextAtt':
                                    # Next token is font block {F3}
                                    bi += 1
                                    if bi < len(block_tokens):
                                        font_val = block_tokens[bi]
                                        if isinstance(font_val, XeroxToken) and font_val.value == '{':
                                            # Collect until }
                                            bi += 1
                                            font_parts = []
                                            while bi < len(block_tokens) and block_tokens[bi].value != '}':
                                                font_parts.append(block_tokens[bi].value)
                                                bi += 1
                                            current_cell_font = font_parts[0] if font_parts else None
                                        elif hasattr(font_val, 'value'):
                                            current_cell_font = font_val.value
                                elif bt.value in ('/Width', '/CellWdth'):
                                    # Next token is the cell width
                                    bi += 1
                                    if bi < len(block_tokens):
                                        width_tok = block_tokens[bi]
                                        width_val = width_tok.value if hasattr(width_tok, 'value') else str(width_tok)
                                        try:
                                            current_cell_width = float(width_val)
                                        except (TypeError, ValueError):
                                            current_cell_width = None
                                elif bt.value == ']':
                                    # End of cell - save accumulated text and font
                                    if current_cell_text is not None:
                                        cell_texts.append(current_cell_text)
                                        cell_fonts.append(current_cell_font)
                                        cell_widths.append(current_cell_width)
                                    current_cell_text = None
                                    current_cell_font = None
                                    current_cell_width = None
                                bi += 1

                        # Generate SHP command (TEXT block) with combined cell texts
                        if cell_texts:
                            # Combine cell texts with width-aware spacing to preserve
                            # basic table-column structure from SHROW definitions.
                            combined_parts = []
                            combined_font = cell_fonts[0] if cell_fonts else None
                            for idx, ct in enumerate(cell_texts):
                                if isinstance(ct, tuple) and ct[0] == 'VAR':
                                    combined_parts.append(f'$${ct[1]}.')
                                else:
                                    combined_parts.append(ct)
                                if idx < len(cell_texts) - 1:
                                    w = cell_widths[idx] if idx < len(cell_widths) else None
                                    if w and w > 0:
                                        pad_spaces = max(1, int(round(w / 3.0)))
                                    else:
                                        pad_spaces = 1
                                    combined_parts.append(' ' * pad_spaces)
                            combined_text = ''.join(combined_parts)

                            shp_cmd = XeroxCommand(
                                name='SHP',
                                line_number=token.line_number + line_offset,
                                column=token.column
                            )
                            shp_cmd.parameters = [f'({combined_text})', '185', '0']
                            if combined_font:
                                shp_cmd.font_override = combined_font
                            commands.append(shp_cmd)

                elif cmd_name == 'INDEXSST':
                    # INDEXSST: /alias /value INDEXSST — consume from stack and skip
                    if len(stack) >= 2:
                        stack.pop()
                        stack.pop()
                    elif len(stack) >= 1:
                        stack.pop()

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
                    # Only consume NL spacing when the source has an explicit numeric
                    # token directly before NL. This prevents stale numeric stack residue
                    # (from earlier commands) from becoming accidental NL spacing.
                    explicit_spacing = False
                    prev_idx = i - 1
                    while prev_idx >= 0 and tokens[prev_idx].type == 'comment':
                        prev_idx -= 1

                    if prev_idx >= 0 and tokens[prev_idx].type == 'number':
                        explicit_spacing = True
                    elif (prev_idx >= 1 and tokens[prev_idx].type == 'number'
                          and tokens[prev_idx - 1].value == '-'):
                        explicit_spacing = True

                    if explicit_spacing and len(stack) > 0:
                        # Check for unary minus pattern: stack [..., '-', '04'].
                        if len(stack) >= 2 and isinstance(stack[-1], str) and stack[-2] == '-':
                            num = stack[-1]
                            if num.replace('.', '', 1).isdigit():
                                stack.pop()
                                stack.pop()
                                params.append(f"-{num}")
                        # Direct numeric spacing.
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

                elif cmd_name in ('MOVEH', 'MOVEHR'):
                    # Preserve unary minus for horizontal move literals.
                    # Example in VIPP: -69 MOVEHR
                    params = []
                    if len(stack) > 0:
                        if (len(stack) >= 2 and isinstance(stack[-1], str)
                                and stack[-1].replace('.', '', 1).isdigit()
                                and stack[-2] == '-'):
                            num = stack.pop()
                            stack.pop()  # remove unary minus token
                            params.append(f"-{num}")
                        else:
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

                elif cmd_name in ('SHP', 'SHp'):
                    # SHP/SHp has variable parameter count depending on VSUB:
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

                    # Also check for FORMAT_EXPR on stack
                    if len(stack) >= 1 and isinstance(stack[-1], tuple) and stack[-1][0] == 'FORMAT_EXPR':
                        # FORMAT case: stack has FORMAT_EXPR tuple — pop it and expand
                        items_to_pop = 1

                    # Pop parameters
                    for _ in range(min(items_to_pop, len(stack))):
                        p = stack.pop()
                        if isinstance(p, tuple) and p[0] == 'block':
                            params.insert(0, self._tokens_to_string(p[1]))
                        elif isinstance(p, tuple) and p[0] == 'VSUB':
                            # VSUB-marked parameter - add both the parameter and VSUB marker
                            params.insert(0, str(p[1]))
                            params.insert(1, 'VSUB')  # Insert VSUB after the text parameter
                        elif isinstance(p, tuple) and p[0] == 'FORMAT_EXPR':
                            # FORMAT_EXPR: (value, pattern) → expand to [value, FORMAT, pattern]
                            params.insert(0, str(p[2]))  # pattern
                            params.insert(0, 'FORMAT')   # FORMAT marker
                            params.insert(0, str(p[1]))  # value
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
                        elif isinstance(p, tuple) and p[0] == 'FORMAT_EXPR':
                            # FORMAT_EXPR: (value, pattern) → expand to [value, FORMAT, pattern]
                            params.insert(0, str(p[2]))  # pattern
                            params.insert(0, 'FORMAT')   # FORMAT marker
                            params.insert(0, str(p[1]))  # value
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
                if token.value == '/INI':
                    logger.debug(f"Pushing /INI onto stack at position {i}")
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

    def parse_file(self, filename: str) -> Union[XeroxDBM, XeroxFRM]:
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
            else:
                logger.warning(f"Unknown file type: {filename}")
                # Try to guess based on content
                if 'STARTDBM' in content:
                    return self.parse_dbm(filename, content)
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
            else:
                # Try to guess based on content
                if 'STARTDBM' in content:
                    return self.parse_dbm(filename, content)
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

            # Handle top-level XGFRESDEF subroutine definitions: /NAME { ... } XGFRESDEF
            # These appear in the DBM preamble outside any CASE block.
            # Pattern: variable starting with '/' immediately followed by a '{' block,
            # with 'XGFRESDEF' as the next keyword after the closing '}'.
            if (token.type == 'variable' and token.value.startswith('/') and
                    self.pos + 1 < len(self.tokens) and
                    self.tokens[self.pos + 1].value == '{'):
                # Peek ahead: find the matching '}' and check if XGFRESDEF follows
                brace_pos = self.pos + 1
                block_tokens, end_idx = self._collect_case_block_tokens(brace_pos)
                next_pos = end_idx + 1
                if (next_pos < len(self.tokens) and
                        self.tokens[next_pos].value == 'XGFRESDEF'):
                    resource_name = token.value.lstrip('/')
                    resource_commands = self._parse_vipp_block(block_tokens, token.line_number)
                    xgf_cmd = XeroxCommand(
                        name='XGFRESDEF',
                        line_number=token.line_number,
                        column=token.column
                    )
                    xgf_cmd.parameters = [resource_name]
                    xgf_cmd.children = resource_commands
                    dbm.commands.append(xgf_cmd)
                    self.pos = next_pos + 1  # skip past XGFRESDEF keyword
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

            # Handle INDEXSST definitions: /S0 /SUP INDEXSST or /N0 null INDEXSST
            if (token.type == 'variable' and
                self.pos + 2 < len(self.tokens) and
                self.tokens[self.pos + 2].value == 'INDEXSST'):

                # Consume INDEXSST definitions so they don't leak into form commands
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

    # Font style mappings from VIPP to Papyrus.
    # Covers both symbolic aliases (ARIALB …) and Xerox printer-resident
    # font aliases (NHE, NTMR …).  Printer-resident fonts are mapped to the
    # closest TTF substitute; the migrate script copies those TTF files.
    FONT_STYLE_MAPPINGS = {
        # Standard VIPP symbolic names
        'ARIAL':      'Arial',
        'ARIALB':     'Arial Bold',
        'ARIALO':     'Arial Italic',
        'ARIALBO':    'Arial Bold Italic',
        'COURIER':    'Courier New',
        'COURIERB':   'Courier New Bold',
        'COURIERO':   'Courier New Italic',
        'COURIERBO':  'Courier New Bold Italic',
        'HELVETICA':  'Helvetica',
        'HELVE':      'Helvetica',
        'HELVEB':     'Helvetica Bold',
        'TIMES':      'Times New Roman',
        'TIMESB':     'Times New Roman Bold',
        'TIMESI':     'Times New Roman Italic',
        'TIMESBI':    'Times New Roman Bold Italic',
        'NZDB':       'Arial',  # Zapf Dingbats — no TTF available; use Arial + Unicode bullet substitution
        # Xerox VIPP printer-resident font aliases → TTF substitutes
        'NTMR':  'Times New Roman',
        'NTMI':  'Times New Roman Italic',
        'NTMB':  'Times New Roman Bold',
        'NHE':   'Helvetica',
        'NHEB':  'Helvetica Bold',
        'NHEBO': 'Helvetica Bold Italic',
        'NHEN':  'Arial Narrow',
        'NHENB': 'Arial Narrow Bold',
        'NCR':   'Courier New',
        'NCRB':  'Courier New Bold',
        'SBT':   'Stone Sans Bold',  # Unknown Xerox proprietary — needs manual TTF
    }

    # Command mappings from VIPP to DFA
    COMMAND_MAPPINGS = {
        'MOVETO': 'POSITION',
        'MOVEH': 'POSITION',
        'MOVEHR': 'POSITION',
        'NL': 'NL',
        'SH': 'OUTPUT',
        'SHL': 'OUTPUT',
        'SHR': 'OUTPUT',
        'SHr': 'OUTPUT',
        'SHC': 'OUTPUT',
        'SHc': 'OUTPUT',
        'SHP': 'OUTPUT',
        'SHp': 'OUTPUT',
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
        # 'PAGEBRK' intentionally NOT mapped here — its handler at _convert_case_commands
        # line 5604 emits USE LOGICALPAGE NEXT SIDE FRONT; (mapping to a /* comment */ string
        # that starts with '/' would cause the early-skip guard at line 5286 to swallow it).
        'NEWFRAME': '/* VIPP command not supported: NEWFRAME */',
        'SKIPPAGE': '/* VIPP command not supported: SKIPPAGE */',
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

    def __init__(self, dbm: XeroxDBM, frm_files: Dict[str, XeroxFRM] = None):
        """
        Initialize the converter with parsed DBM and FRM files.

        Args:
            dbm: Parsed DBM file structure
            frm_files: Dictionary of parsed FRM files
        """
        self.dbm = dbm
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

        # Track PREFIX references for stub generation
        self.referenced_prefixes = set()  # PREFIX values referenced in data or WIZVAR
        self.defined_prefixes = set()     # PREFIX values with generated DOCFORMATs

        # Track SETLSP (line spacing) from DBM
        self.line_spacing = None  # Will be set if SETLSP found in DBM
        # Track Xerox origin mode. ORITL means top-left origin and requires
        # inverted relative Y offsets in inlined SCALL/XGFRESDEF drawing.
        self.origin_is_oritl = False

        # Track SETPAGEDEF layout positions for OUTLINE generation
        self.page_layout_position = None  # (x, y) from last SETLKF in SETPAGEDEF

        # Track when to set box positioning anchors
        self.should_set_box_anchor = True  # Set anchors before first box in a group

        # FRM rendering mode:
        # FRM include formats already anchor at page origin, so subtracting
        # margins again can push content above/left of printable area.
        self.position_no_margins = False

        # Track last command type for positioning logic
        self.last_command_type = None  # 'OUTPUT', 'TEXT', 'NL'

        # Track subroutine definitions for SCALL handling
        self.subroutines = {}  # Maps subroutine name to {'commands': [...], 'type': 'simple'|'complex'}

        # Track page numbering semantics extracted from VIPP SETPAGENUMBER.
        # Defaults match the legacy generated footer output.
        self.page_number_expr = "'Page ' ! P ! ' of ' ! PP"
        self.page_number_x = "RIGHT-11 MM"
        self.page_number_y = "286 MM"
        self.page_number_align = "RIGHT"
        self.emit_page_index_marker = False

        # Track GETITEM tables (VIPP table lookup pattern).
        # table_name -> list of target variable names from header row
        self.getitem_table_fields = {}
        # table_name -> DFA array variable used to store appended rows
        self.getitem_store_vars = {}
        # Counter for generated temporary text-expression variables (SHP/SHp wrapping)
        self._tmp_text_counter = 0

        # Text-flow carry is now part of the default DBM behavior.
        # Keep scope conservative: only apply carry to selected continuation cases.
        self.dbm_textflow_cases = {'Y1'}

        # Auto-detect input format from DBM
        self._detect_input_format()
        self._build_format_registry()
        self._extract_layout_info()
        self._extract_subroutines()
        self._extract_page_number_settings()
        self._extract_getitem_table_definitions()

    def _escape_dfa_quotes(self, text: str) -> str:
        """
        Escape single quotes in text for DFA string literals.
        In DFA, single quotes within strings must be doubled.

        Example:
            "It's done" → "It''s done"
            "Payments 'Without Prejudice'" → "Payments ''Without Prejudice''"

        Args:
            text: The text to escape

        Returns:
            Text with escaped quotes
        """
        return text.replace("'", "''")

    @staticmethod
    def _sanitize_dfa_name(name: str) -> str:
        """Sanitize a name for use as a DFA identifier (variable, segment, format).

        DFA identifiers must be alphanumeric plus underscore only.
        Hyphens, spaces, and other special characters are removed.
        """
        import re
        # Remove all characters that are not alphanumeric or underscore
        return re.sub(r'[^A-Za-z0-9_]', '', name)

    @staticmethod
    def _is_total_page_var(name: str) -> bool:
        """Return True for known VIPP total-page variable aliases."""
        return name.upper() in ('VAR_PCTOT', 'VAR_PTOT', 'VARPTOT')

    def generate_dfa_code(self) -> str:
        """
        Generate DFA code from the parsed VIPP structures.

        Returns:
            Generated DFA code as a string
        """
        self.output_lines = []
        self.indent_level = 0

        # Generate header
        self._generate_header()

        # Generate font definitions
        self._generate_fonts()

        # Generate color definitions
        self._generate_colors()

        # Generate main document format
        self._generate_docformat_main()

        # Back-pass: verify every COLOR <name> reference has a DEFINE
        self._backpass_verify_color_definitions()

        # Validation pass: verify IF/ELSE/ENDIF balance
        self._validate_if_else_balance()

        return '\n'.join(self.output_lines)

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
        prev_position_no_margins = self.position_no_margins
        self.position_no_margins = True

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

        try:
            if not as_include:
                # Generate DOCFORMAT for this FRM
                self.add_line(f"DOCFORMAT {frm_name};")
                self.indent()
                # Set margins and units
                self.add_line("MARGIN TOP 0 MM BOTTOM 0 MM LEFT 0 MM RIGHT 0 MM;")
                self.add_line("SETUNITS LINESP AUTO;")
                self.add_line("")

                # Generate OUTLINE block for FRM content.
                # TOP can underflow in some environments; NEXT keeps first baseline
                # inside printable area while remaining page-anchored.
                self.add_line("OUTLINE")
                self.indent()
                self.add_line("POSITION LEFT NEXT")
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

                # Add OUTLINE wrapper for FRM commands.
                # External FRMs are rendered from PRINTFOOTER as full-page
                # backgrounds; anchor at TOP so internal absolute Y values
                # stay page-relative.
                self.add_line("OUTLINE ")
                self.indent()
                self.add_line("POSITION LEFT TOP")
                self.add_line("DIRECTION ACROSS;")
                self.add_line("")

                # Convert FRM commands
                self._convert_frm_commands(frm)

                # Close OUTLINE
                self.add_line("ENDIO;")

            return '\n'.join(self.output_lines)
        finally:
            self.position_no_margins = prev_position_no_margins

    def _convert_frm_commands(self, frm: XeroxFRM):
        """
        Convert FRM commands to DFA OUTPUT and control structures.

        Args:
            frm: Parsed FRM file structure
        """
        current_x = 0.0
        current_y = 0.0
        anchor_x = 0.0  # Base X for MOVEHR in FRM flows
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

        # Reset box anchor flag for this FRM conversion
        self.should_set_box_anchor = True

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
                        anchor_x = current_x
                        x_was_explicitly_set = True
                        y_was_explicitly_set = True
                        y_is_next_line = False  # Explicit Y position overrides NEXT
                    except ValueError:
                        pass
                continue

            # Handle horizontal move - MOVEH/MOVEHR
            if cmd.name in ('MOVEH', 'MOVEHR'):
                if cmd.parameters:
                    try:
                        move_val = float(cmd.parameters[0])
                        if cmd.name == 'MOVEHR':
                            # FRM semantics: horizontal move relative to section anchor
                            current_x = anchor_x + move_val
                        else:
                            current_x = move_val
                            anchor_x = current_x
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
                self.last_command_type = 'NL'
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
            if cmd.name in ('SH', 'SHL', 'SHR', 'SHr', 'SHC', 'SHc', 'SHP', 'SHp'):
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
                                         x_was_explicitly_set, y_was_explicitly_set,
                                         current_font)
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
        anchor_x = start_x  # Base X for MOVEHR in FRM child blocks
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
                        anchor_x = current_x
                        x_was_explicitly_set = True
                        y_was_explicitly_set = True
                        y_is_next_line = False  # Explicit Y position overrides NEXT
                    except ValueError:
                        pass
                continue

            # Handle horizontal move - MOVEH/MOVEHR
            if cmd.name in ('MOVEH', 'MOVEHR'):
                if cmd.parameters:
                    try:
                        move_val = float(cmd.parameters[0])
                        if cmd.name == 'MOVEHR':
                            # FRM semantics: horizontal move relative to section anchor
                            current_x = anchor_x + move_val
                        else:
                            current_x = move_val
                            anchor_x = current_x
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
                self.last_command_type = 'NL'
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
            if cmd.name in ('SH', 'SHL', 'SHR', 'SHr', 'SHC', 'SHc', 'SHP', 'SHp'):
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
                                         x_was_explicitly_set, y_was_explicitly_set,
                                         current_font)
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

    def _split_respecting_parens(self, text: str) -> List[str]:
        """Split a string on spaces while keeping parenthesized substrings intact."""
        parts = []
        current = []
        depth = 0
        for char in text:
            if char == '(':
                depth += 1
                current.append(char)
            elif char == ')':
                depth -= 1
                current.append(char)
            elif char == ' ' and depth == 0:
                if current:
                    parts.append(''.join(current))
                    current = []
            else:
                current.append(char)
        if current:
            parts.append(''.join(current))
        return parts

    def _convert_frm_condition(self, params: List[str]) -> str:
        """Convert FRM IF condition to DFA format."""
        if not params:
            return "TRUE"

        # Split parameters if they're combined into a single string
        # Use parenthesis-aware splitter to preserve multi-word strings like (monthly investment plan)
        split_params = []
        for param in params:
            if ' ' in param:
                split_params.extend(self._split_respecting_parens(param))
            else:
                split_params.append(param)

        # Filter out definition keywords that should not be in IF conditions
        DEFINITION_KEYWORDS = {'INDEXBAT', 'INDEXFONT', 'INDEXCOLOR', 'INDEXSST', 'SETUNIT', 'MM', 'CM', 'INCH', 'null'}

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
                # Multi-word parenthesized strings: wrap with NOSPACE() for string comparison
                clean_val = param[1:-1]
                condition_parts.append(f"'{clean_val}'")
            else:
                condition_parts.append(param)

        # Apply NOSPACE() wrapper to string comparisons
        # Pattern: VAR == 'value' → NOSPACE(VAR) == 'value'
        result = ' '.join(condition_parts)
        import re
        # Wrap variable names before == with NOSPACE() if comparing to string literals
        result = re.sub(r'\b([A-Z][A-Z0-9_]*)\s*==\s*\'', r"NOSPACE(\1) == '", result)

        return result

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
        # Detect FORMAT pattern: params like [VAR_X, 'FORMAT', '(pattern)']
        # Xerox FORMAT: value (pattern) FORMAT — applies numeric format mask to variable.
        # Convert to NUMPICTURE(VAR_X, 'pattern') expression in DFA.
        _has_format = 'FORMAT' in cmd.parameters
        if _has_format:
            fmt_idx = cmd.parameters.index('FORMAT')
            if fmt_idx > 0 and fmt_idx + 1 < len(cmd.parameters):
                fmt_var = cmd.parameters[fmt_idx - 1]
                fmt_pat_raw = cmd.parameters[fmt_idx + 1]
                # Strip surrounding parens from pattern if present
                if fmt_pat_raw.startswith('(') and fmt_pat_raw.endswith(')'):
                    fmt_pat_raw = fmt_pat_raw[1:-1]
                # Build NUMPICTURE expression - treated as expression (not a plain string literal)
                text = f"NUMPICTURE({fmt_var}, '{fmt_pat_raw}')"
                is_variable = True  # Emit without surrounding quotes
                _has_format = True
            else:
                _has_format = False

        if not _has_format:
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
                elif cmd.name in ('SHP', 'SHp'):
                    # SHP/SHp has 3 parameters: [var/text, width, align]
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
            elif cmd.name in ('SHC', 'SHc'):
                vsub_alignment = 2  # Center

        if not text:
            return

        # Check if SHP has width parameter - use TEXT command for line wrapping
        if shp_width is not None and shp_width > 0:
            # SHP with width requires TEXT command with WIDTH parameter and ALIGN JUSTIFY
            if has_vsub and not is_variable:
                _orig_had_vsub = '$$' in text or '$' in text
                text = self._convert_vsub(text)
                # After VSUB conversion, if text contains ! concatenation, treat as variable
                if ' ! ' in text:
                    is_variable = True
                elif _orig_had_vsub and "'" not in text and ' ' not in text.strip():
                    # Pure variable: ($$VAR_NAME.) → VAR_NAME — must not be quoted
                    is_variable = True
            # Default SHP alignment to JUSTIFY (3) if not explicitly set
            shp_alignment = vsub_alignment if vsub_alignment is not None else 3
            self._generate_text_with_width(text, x, y, font, shp_width, is_variable, shp_alignment,
                                          x_was_set, y_was_set, y_is_next, frm)
        # Check if text contains font switches
        elif '~~' in text and not is_variable:
            # Use TEXT command for font switching
            self._generate_text_with_font_switches(text, x, y, font, frm, vsub_alignment,
                                                   x_was_set, y_was_set, y_is_next, color)
        else:
            # Use simple OUTPUT command
            if has_vsub and not is_variable:
                _orig_had_vsub = '$$' in text or '$' in text
                text = self._convert_vsub(text)
                # After VSUB conversion, if text contains ! concatenation, treat as variable
                if ' ! ' in text:
                    is_variable = True
                elif _orig_had_vsub and "'" not in text and ' ' not in text.strip():
                    # Pure variable: ($$VAR_NAME.) → VAR_NAME — must not be quoted
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
            text_segment = text[last_pos:match.start()]
            if text_segment:
                segments.append((current_font, text_segment))
            elif current_font in self._SST_CODES:
                # SST code with no following text — still emit positioning command
                segments.append((current_font, ''))

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

            self.add_line(self._format_position(x_pos, y_pos, dfa_font, vertical_next_to_autospace=True))

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
            self.add_line(self._format_position(x_pos, y_pos, dfa_font, vertical_next_to_autospace=True))

        # Add font-switched segments
        for font_alias, text_seg in segments:
            # Skip empty segments (happens when text starts with font switch)
            if not text_seg or text_seg.isspace():
                continue

            # Map font alias to base font + style
            base_font, style = self._map_font_alias(font_alias, frm)

            # Use Unicode substitution for Zapf Dingbats characters
            if self._is_dingbats_font(font_alias, frm):
                self.add_line(f"FONT {base_font} {style}")
                self._emit_dingbats_text(text_seg)
                continue

            # Format the text segment for TEXT command
            formatted_seg = self._format_text_segment_for_text_cmd(text_seg)

            # Skip if formatted segment is just empty quotes (''')
            if formatted_seg.strip() in ["''", "'''", '""', '"""']:
                continue

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
        """Generate simple OUTPUT command with proper alignment.

        IMPORTANT: ALIGN JUSTIFY is NOT valid on OUTPUT — only LEFT/RIGHT/CENTER are.
        If alignment==3 (JUSTIFY), redirect to TEXT block with a reasonable default width.
        """
        # JUSTIFY is only valid inside TEXT blocks, not on OUTPUT.
        # Redirect to _generate_text_with_width with a default page-width estimate.
        if alignment == 3:
            # Estimate a reasonable width: if we have an x position, use remaining page width.
            # Default to 175 MM which is a common text column width for A4.
            justify_width = 175.0
            if x_was_set and isinstance(x, (int, float)):
                # Remaining width from x to right margin (~201 MM for A4)
                remaining = 201.0 - float(x)
                if remaining > 10.0:
                    justify_width = remaining
            self._generate_text_with_width(
                text, x, y, default_font, justify_width, is_variable,
                alignment=3, x_was_set=x_was_set, y_was_set=y_was_set,
                y_is_next=y_is_next, frm=frm
            )
            return

        # Generate OUTPUT
        if is_variable:
            self.add_line(f"OUTPUT {text}")
        else:
            self.add_line(f"OUTPUT '{self._escape_dfa_quotes(text)}'")

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

        # Empty literal OUTPUT ('') is a spacing carrier; keep original vertical semantics.
        use_autospace = not (not is_variable and text == '')

        # Add position using helper method (handles both keywords and numeric with margin correction)
        # Pass font for vertical position correction
        self.add_line(self._format_position(x_pos, y_pos, dfa_font, vertical_next_to_autospace=use_autospace))

        # Add color if specified
        if color:
            self.add_line(f"COLOR {color}")

        # Add alignment if specified (JUSTIFY is NOT valid on OUTPUT — handled above)
        if alignment == 0:
            self.add_line("ALIGN LEFT NOPAD")
        elif alignment == 1:
            self.add_line("ALIGN RIGHT NOPAD")
        elif alignment == 2:
            self.add_line("ALIGN CENTER NOPAD")

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
        self.add_line(self._format_position(x_pos, y_pos, dfa_font, vertical_next_to_autospace=True))

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

        # Add text content
        # For TEXT command, variables are in parentheses: (VAR)
        # Literals are in quotes: 'text'
        if is_variable:
            self.add_line(f"FONT {dfa_font}")
            self.add_line(style)
            # Variable reference - use parentheses
            # Check if it's VSUB-formatted (contains ! concatenation)
            if ' ! ' in text:
                # VSUB format: 'literal' ! VAR
                # TEXT command needs this reformatted
                self.add_line(text)
            else:
                # Simple variable
                self.add_line(f"({text})")
        elif '~~' in text:
            # Text contains VIPP ~~XX font switches — emit inline FONT changes
            self._emit_font_switched_text_content(text, default_font, frm)
        else:
            self.add_line(f"FONT {dfa_font}")
            self.add_line(style)
            # Literal text - quote it, escaping any embedded apostrophes
            self.add_line(f"'{self._escape_dfa_quotes(text)}'")

        self.add_line(";")
        self.dedent()

    # VIPP SST positioning codes (from INDEXSST definitions)
    _SST_CODES = {'P0', 'P1', 'P2', 'N0', 'U0'}

    # Zapf Dingbats character to DFA Unicode notation mapping.
    # NZDB font has no TTF available; substitute with Unicode equivalents.
    _ZAPF_DINGBATS_UNICODE = {
        'l': "U'25CF'",   # ● BLACK CIRCLE (bullet)
        'n': "U'25A0'",   # ■ BLACK SQUARE
        'm': "U'25CB'",   # ○ WHITE CIRCLE
        'u': "U'2756'",   # ❖ BLACK DIAMOND MINUS WHITE X
    }

    def _is_dingbats_font(self, alias: str, frm) -> bool:
        """Check if a font alias maps to Zapf Dingbats (NZDB)."""
        # Check FRM fonts
        if frm and alias in frm.fonts and frm.fonts[alias].name == 'NZDB':
            return True
        # Check via reverse rename map
        if frm:
            for orig, renamed in frm.font_rename_map.items():
                if renamed == alias and orig in frm.fonts and frm.fonts[orig].name == 'NZDB':
                    return True
        # Check DBM fonts
        if hasattr(self, 'dbm') and self.dbm and alias in self.dbm.fonts and self.dbm.fonts[alias].name == 'NZDB':
            return True
        return False

    def _emit_dingbats_text(self, text_seg: str):
        """Emit dingbats text as DFA Unicode notation instead of quoted characters."""
        for char in text_seg:
            ucode = self._ZAPF_DINGBATS_UNICODE.get(char)
            if ucode:
                self.add_line(ucode)
            else:
                self.add_line(f"'{self._escape_dfa_quotes(char)}'")

    def _emit_font_switched_text_content(self, text: str, default_font: str, frm=None):
        """
        Emit TEXT block content with inline FONT changes for ~~XX VIPP font switches.

        Handles:
        - ~~F1, ~~FA etc. → FONT F1_N NORMAL (mapped via _map_font_alias)
        - ~~P1 → SUPERSCRIPT
        - ~~P0 → NORMALSCRIPT
        - ~~P2 → SUPERSCRIPT (approximate custom subscript)
        - \\n  → NEWLINE (VIPP line break in strings)
        """
        segments = self._parse_font_switches(text, default_font)

        for font_alias, text_seg in segments:
            # Handle SST positioning codes (always emit, even if text is empty)
            if font_alias in ('P1', 'P2'):
                self.add_line("SUPERSCRIPT")
                self._emit_text_with_newlines(text_seg, frm is not None)
                continue
            elif font_alias == 'P0':
                self.add_line("NORMALSCRIPT")
                self._emit_text_with_newlines(text_seg, frm is not None)
                continue
            elif font_alias == 'U0':
                self.add_line("UNDERLINE(ON)")
                self._emit_text_with_newlines(text_seg, frm is not None)
                continue
            elif font_alias == 'N0':
                self.add_line("UNDERLINE(OFF)")
                self._emit_text_with_newlines(text_seg, frm is not None)
                continue

            # Skip empty text segments for regular font switches
            if not text_seg or text_seg.isspace():
                continue

            # Map font alias to DFA font name
            if frm:
                base_font, style = self._map_font_alias(font_alias, frm)
            else:
                base_font, style = font_alias.upper(), 'NORMAL'

            self.add_line(f"FONT {base_font}")
            self.add_line(style)

            # Emit text — use Unicode substitution for Zapf Dingbats characters
            if frm and self._is_dingbats_font(font_alias, frm):
                self._emit_dingbats_text(text_seg)
            else:
                self._emit_text_with_newlines(text_seg, True)

    def _emit_text_with_newlines(self, text_seg: str, emit_content: bool = True):
        """Emit text segment, converting \\n to NEWLINE commands."""
        if not text_seg or text_seg.isspace():
            return
        if not emit_content:
            return

        # Split on literal \n (two chars: backslash + n) for NEWLINE
        parts = text_seg.split('\\n')
        for j, part in enumerate(parts):
            part_clean = part
            if part_clean and not part_clean.isspace():
                self.add_line(f"'{self._escape_dfa_quotes(part_clean)}'")
            if j < len(parts) - 1:
                self.add_line("NEWLINE")

    def _convert_xgfresdef(self, cmd: XeroxCommand, frm: XeroxFRM):
        """
        Convert XGFRESDEF resource definition and store metadata.

        VIPP: /TXNB { 0 0 188 09 LMED DRAWB } XGFRESDEF
        DFA: Store definition, convert SCALL to BOX later

        Also stores subroutine commands for inlining simple subroutines.
        """
        if not cmd.parameters or not cmd.children:
            return

        resource_name = cmd.parameters[0]

        # Store all subroutine commands for potential inlining
        command_count = len(cmd.children)
        subroutine_type = 'simple' if command_count <= 5 else 'complex'

        self.subroutines[resource_name] = {
            'commands': cmd.children,
            'type': subroutine_type,
            'command_count': command_count,
            'xgfresdef': True,  # Flag: must be inlined as BOX/RULE at call site
        }

        # Count DRAWB children for logging
        drawb_count = sum(1 for c in cmd.children if c.name == 'DRAWB')
        logger.info(f"Found XGFRESDEF subroutine '{resource_name}' with {command_count} children "
                    f"({drawb_count} DRAWB) — will inline at SCALL sites")

        # Don't generate output for XGFRESDEF definitions themselves

    def _inline_xgfresdef_drawbs(self, resource_name: str, origin_x: float, origin_y: float,
                                 flow_relative_y: bool = False,
                                 anchor_x_var: str = None, anchor_y_var: str = None):
        """
        Inline an XGFRESDEF subroutine's DRAWB commands as absolute BOX/RULE at the call site.

        VIPP XGFRESDEF subroutines contain DRAWB commands with coordinates relative to
        the SCALL origin (the MOVETO position that preceded the SCALL).  Since DFA has no
        equivalent named drawing subroutine construct, we expand the calls inline with
        absolute page coordinates = origin + offset.

        VIPP coordinate system: Y increases downward; negative Y offsets go below the origin.
        DFA coordinate system:  Y increases downward from top margin.

        So:  abs_x = origin_x + drawb_x
             abs_y = origin_y + |drawb_y|   (drawb_y is usually negative for "below")

        Args:
            resource_name: The XGFRESDEF name (e.g. 'SABX') — used only for the comment
            origin_x:      X coordinate from the preceding MOVETO (mm from left edge)
            origin_y:      Y coordinate from the preceding MOVETO (mm from top edge)
            flow_relative_y: If True, emit Y positions as SAME+/-(offset) relative to
                             current cursor (DBM inline flow). If False, emit absolute
                             margin-relative Y coordinates (FRM/static contexts).
            anchor_x_var: If provided, emit X positions relative to this DFA variable.
            anchor_y_var: If provided, emit Y positions relative to this DFA variable.
        """
        subroutine_info = self.subroutines.get(resource_name)
        if not subroutine_info:
            self.add_line(f"/* XGFRESDEF '{resource_name}' not found — skipped */")
            return

        commands = subroutine_info.get('commands', [])
        drawb_count = sum(1 for c in commands if c.name == 'DRAWB')

        self.add_line(f"/* Inlined XGFRESDEF '{resource_name}': {drawb_count} DRAWB(s) "
                      f"at origin ({origin_x}, {origin_y}) mm */")

        for child in commands:
            if child.name != 'DRAWB':
                # Non-DRAWB children (text, etc.) are not supported in this inline path
                self.add_line(f"/* XGFRESDEF '{resource_name}': skipped non-DRAWB child "
                              f"'{child.name}' */")
                continue

            # Normalize parameters: merge split negative numbers.
            # The tokenizer may split '-08' into ['-', '08']. Rejoin these.
            raw_params = list(child.parameters)
            params = []
            i = 0
            while i < len(raw_params):
                if raw_params[i] == '-' and i + 1 < len(raw_params):
                    try:
                        float(raw_params[i + 1])  # confirm next token is numeric
                        params.append('-' + raw_params[i + 1])
                        i += 2
                        continue
                    except ValueError:
                        pass
                params.append(raw_params[i])
                i += 1

            # Handle "missing x" case: when VIPP RPN stack has 'x -y w h style DRAWB',
            # the tokenizer splits '-y' into '-' and 'y', and DRAWB pops 5 items:
            # [style, h, w, y, '-'] → params stored as ['-y', w, h, style] with x lost.
            # If after merging we have 4 params and the first is negative, the x was lost.
            # We cannot recover the exact x, so we default to x_offset=0 (i.e. origin_x).
            if len(params) == 4:
                try:
                    first_val = float(params[0])
                    if first_val < 0:
                        # params are [neg_y, width, height_or_thickness, style]
                        # Insert x_offset=0 at position 0
                        params.insert(0, '0')
                except ValueError:
                    pass

            if len(params) < 4:
                self.add_line(f"/* XGFRESDEF '{resource_name}': DRAWB with too few params "
                              f"({raw_params}) — skipped */")
                continue

            try:
                rel_x = float(params[0])
                rel_y = float(params[1])
                param3 = float(params[2])   # width or length
            except (ValueError, IndexError):
                self.add_line(f"/* XGFRESDEF '{resource_name}': DRAWB non-numeric params "
                              f"({raw_params}) — skipped */")
                continue

            param4_raw = params[3]           # height or thickness
            style = params[4] if len(params) > 4 else 'R_S1'

            # Compute absolute/relative page coordinates
            abs_x = origin_x + rel_x
            if anchor_x_var:
                if abs(rel_x) < 0.0001:
                    x_value = anchor_x_var
                elif rel_x > 0:
                    x_value = f"{anchor_x_var}+{rel_x} MM"
                else:
                    x_value = f"{anchor_x_var}-{abs(rel_x)} MM"
            else:
                x_value = str(abs_x)

            # VIPP Y-offset sign in SCALL segments depends on origin mode.
            # For ORITL: invert offset sign (-6 -> +6, +6 -> -6).
            rel_y_signed = -rel_y if self.origin_is_oritl else rel_y

            if anchor_y_var:
                if abs(rel_y_signed) < 0.0001:
                    y_value = anchor_y_var
                elif rel_y_signed > 0:
                    y_value = f"{anchor_y_var}+{rel_y_signed} MM"
                else:
                    y_value = f"{anchor_y_var}-{abs(rel_y_signed)} MM"
            elif flow_relative_y:
                y_delta = rel_y_signed
                if abs(y_delta) < 0.0001:
                    y_value = "SAME"
                elif y_delta > 0:
                    y_value = f"SAME+{y_delta} MM"
                else:
                    y_value = f"SAME-{abs(y_delta)} MM"
            else:
                # In absolute fallback mode apply signed Y offset.
                y_value = str(origin_y + rel_y_signed)

            # Build a synthetic XeroxCommand with the absolute coordinates so we can
            # reuse the full _convert_frm_rule logic (style mapping, line vs box, etc.)
            synthetic_params = [str(x_value), str(y_value), str(param3), param4_raw, style]
            synthetic_cmd = XeroxCommand(
                name='DRAWB',
                parameters=synthetic_params,
                children=[]
            )

            # _convert_frm_rule supports both numeric absolute Y and SAME+/- relative Y.
            self._convert_frm_rule(synthetic_cmd)

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

        # Parse parameters (x/y may be expressions for anchored inline SCALL drawing)
        x_raw = cmd.parameters[0]
        y_raw = cmd.parameters[1]
        x_expr = None
        y_expr = None
        try:
            x = float(x_raw)
        except (ValueError, TypeError):
            x = 0.0
            x_expr = str(x_raw)
        try:
            y = float(y_raw)
        except (ValueError, TypeError):
            y = 0.0
            y_expr = str(y_raw)
        try:
            param3 = float(cmd.parameters[2])  # width or length
        except (ValueError, IndexError):
            return

        # Parse param4 - can be numeric or keyword
        param4 = cmd.parameters[3]  # height or thickness
        style = cmd.parameters[4] if len(cmd.parameters) > 4 else "R_S1"

        # Classify style into line-only vs fill styles
        # Line weight styles: LTHN, LTHK, LDSH, LDOT — border only, no color, no shade
        # NOTE: LMED in line context means "medium line weight", BUT when used with
        # height > 1.0 (box context) it means "light-medium gray fill". We handle this
        # contextually below based on is_box. MED and XDRK are always fill colors.
        # Standalone shade styles: S1, S2, S3, S4 — border only (no color prefix)
        # Fill styles: R_S1, G_S1, B_S1, F_S1, LMED, MED, XDRK — filled, with color
        # CLIP: not a box style
        is_line_style = style in ('LT', 'LTHN', 'LTHK', 'LDSH', 'LDOT',
                                  'L_THN', 'L_THK', 'L_DSH', 'L_DOT',
                                  'S1', 'S2', 'S3', 'S4')
        # LMED in a pure line context (height <= 1.0) is a medium-weight line
        # LMED/MED/XDRK in a box context (height > 1.0) are fill colors — handled below
        is_lmed_line = style in ('LMED', 'L_MED')  # May be line or fill depending on context
        is_clip = style == 'CLIP'

        if is_clip:
            self.add_line(f"/* CLIP: clipping region — {' '.join(str(p) for p in cmd.parameters)} */")
            return

        # Handle legacy thickness keywords for param4
        param4_val = param4
        try:
            param4_float = float(param4)
        except ValueError:
            thickness_map = {
                'LTHN': 0.1,
                'LMED': 0.2,
                'LTHK': 0.5,
            }
            param4_float = thickness_map.get(param4, 0.2)
            param4_val = str(param4_float)

        # Invert Y coordinate (negative becomes positive) when numeric.
        # If y is an expression (e.g. YPOS-6 MM), pass through as-is.
        y_inverted = abs(y) if y_expr is None else y_expr

        # Convert tiny widths/heights to 0.01 MM for thin lines
        width = param3 if param3 >= 0.01 else 0.01
        height = param4_float if param4_float >= 0.01 else 0.01

        # Determine positioning pattern:
        # Pattern A: Absolute coords (x>0 or y!=0) → margin-relative: (x MM-$MR_LEFT) (y MM-$MR_TOP)
        # Pattern B: x=0 and y=0 (relative, e.g. inside XGFRESDEF) → use POSX/POSY anchor
        use_absolute = (x > 0 or y != 0 or x_expr is not None or y_expr is not None)

        # Determine if this is a BOX (rectangle) or RULE (line)
        is_box = param4_float > 1.0

        # Resolve final is_line_style considering context:
        # LMED/L_MED in a line context (height <= 1.0) = medium-weight line border
        # LMED/L_MED in a box context (height > 1.0) = light-medium gray fill color
        # MED and XDRK are always fill colors regardless of context
        if is_lmed_line and not is_box:
            is_line_style = True
            thickness_keyword = 'MEDIUM'
        elif is_lmed_line and is_box:
            # Treat as fill color in box context
            is_line_style = False

        # Parse color and shade from style parameter
        color = None
        line_type = "SOLID"
        shade = None
        thickness_keyword = None

        if is_line_style:
            # Line styles: emit THICKNESS <weight> TYPE <type> only — no COLOR, no SHADE
            line_thickness_map = {
                'LT': '0.1 MM', 'LTHN': '0.1 MM', 'L_THN': '0.1 MM',
                'LTHK': '0.8 MM', 'L_THK': '0.8 MM',
                'LDSH': '0.3 MM', 'L_DSH': '0.3 MM',
                'LDOT': '0.3 MM', 'L_DOT': '0.3 MM',
                'S1': '0.3 MM', 'S2': '0.3 MM', 'S3': '0.3 MM', 'S4': '0.3 MM',
            }
            thickness_keyword = line_thickness_map.get(style, '0.3 MM')
            if style in ('LDSH', 'L_DSH'):
                line_type = 'DASHED'
            elif style in ('LDOT', 'L_DOT'):
                line_type = 'DOTTED'
        else:
            # Fill styles: parse color — either a prefix (R/G/B/F) or a named color (LMED/MED/XDRK)
            if style in ('LMED', 'L_MED', 'MED'):
                # Light-medium gray fill — defined as DEFINE LMED COLOR RGB ... in output
                color = 'LMED'
            elif style == 'XDRK':
                # Dark gray fill
                color = 'XDRK'
            elif style.startswith('R'):
                color = 'R'
            elif style.startswith('G'):
                color = 'G'
            elif style.startswith('B') and not style.startswith('BLACK'):
                color = 'B'
            elif style.startswith('F'):
                color = 'FBLACK'

            # Parse shade suffix (S1=100%, S2=75%, S3=50%, S4=25%)
            if 'S1' in style or '_S1' in style:
                shade = 100
            elif 'S2' in style or '_S2' in style:
                shade = 75
            elif 'S3' in style or '_S3' in style:
                shade = 50
            elif 'S4' in style or '_S4' in style:
                shade = 25

        thin_box_as_vertical_rule = is_box and abs(width - 0.1) < 0.0001 and height > width

        if thin_box_as_vertical_rule:
            self.add_line("RULE")
            self.indent()

            if use_absolute:
                if x_expr is None and y_expr is None:
                    self.add_line(f"POSITION ({x} MM-$MR_LEFT) ({y_inverted + height} MM-$MR_TOP)")
                elif x_expr is not None and y_expr is None:
                    self.add_line(f"POSITION ({x_expr}) ({y_inverted + height} MM-$MR_TOP)")
                elif x_expr is None and y_expr is not None:
                    self.add_line(f"POSITION ({x} MM-$MR_LEFT) ({y_expr}+{height} MM)")
                else:
                    self.add_line(f"POSITION ({x_expr}) ({y_expr}+{height} MM)")
            else:
                self.add_line(f"POSITION (POSX+{x} MM) (POSY+{y_inverted + height} MM)")

            self.add_line("DIRECTION UP")
            if color:
                self.add_line(f"COLOR {color}")
            self.add_line(f"LENGTH {height} MM")
            self.add_line("THICKNESS 0.1 MM TYPE SOLID")
            self.add_line(";")
            self.dedent()
        elif is_box:
            self.add_line("BOX")
            self.indent()

            # Position — absolute or anchor-relative
            if use_absolute:
                if x_expr is None and y_expr is None:
                    self.add_line(f"POSITION ({x} MM-$MR_LEFT) ({y_inverted} MM-$MR_TOP)")
                elif x_expr is not None and y_expr is None:
                    self.add_line(f"POSITION ({x_expr}) ({y_inverted} MM-$MR_TOP)")
                elif x_expr is None and y_expr is not None:
                    self.add_line(f"POSITION ({x} MM-$MR_LEFT) ({y_expr})")
                else:
                    self.add_line(f"POSITION ({x_expr}) ({y_expr})")
            else:
                self.add_line(f"POSITION (POSX+{x} MM) (POSY+{y_inverted} MM)")

            self.add_line(f"WIDTH {width} MM")
            self.add_line(f"HEIGHT {height} MM")

            if is_line_style:
                # Border-only: thickness and type, no color, no shade
                self.add_line(f"THICKNESS {thickness_keyword} TYPE {line_type};")
            else:
                # Filled box: color, thickness 0, shade
                if color:
                    self.add_line(f"COLOR {color}")
                if shade is not None:
                    self.add_line(f"THICKNESS 0 TYPE SOLID SHADE {shade};")
                else:
                    self.add_line(f"THICKNESS 0 TYPE SOLID SHADE 100;")

            self.dedent()
        else:
            # RULE (line)
            length = width
            thickness = param4_val
            # 0/0.0001/0.001 MM lines from VIPP become nearly invisible in PDF.
            # Clamp to 0.01 MM as minimum.
            try:
                if float(thickness) < 0.01:
                    thickness = "0.01"
            except (TypeError, ValueError):
                pass

            try:
                length_f = float(length)
                thickness_f = float(thickness)
                direction = 'ACROSS' if length_f >= thickness_f else 'DOWN'
            except ValueError:
                direction = 'ACROSS'

            self.add_line("RULE")
            self.indent()

            if use_absolute:
                if x_expr is None and y_expr is None:
                    self.add_line(f"POSITION ({x} MM-$MR_LEFT) ({y_inverted} MM-$MR_TOP)")
                elif x_expr is not None and y_expr is None:
                    self.add_line(f"POSITION ({x_expr}) ({y_inverted} MM-$MR_TOP)")
                elif x_expr is None and y_expr is not None:
                    self.add_line(f"POSITION ({x} MM-$MR_LEFT) ({y_expr})")
                else:
                    self.add_line(f"POSITION ({x_expr}) ({y_expr})")
            else:
                self.add_line(f"POSITION (POSX+{x} MM) (POSY+{y_inverted} MM)")

            self.add_line(f"DIRECTION {direction}")

            if is_line_style:
                # Line style: thickness keyword and type only
                self.add_line(f"LENGTH {length} MM")
                self.add_line(f"THICKNESS {thickness_keyword} TYPE {line_type}")
            else:
                # Fill style on a rule (rare)
                if color:
                    self.add_line(f"COLOR {color}")
                self.add_line(f"LENGTH {length} MM")
                self.add_line(f"THICKNESS {thickness} MM TYPE {line_type}")

            self.add_line(";")
            self.dedent()

    def _convert_frm_segment(self, cmd: XeroxCommand, x: float, y: float, frm: XeroxFRM, cache_cmd: XeroxCommand = None,
                            x_was_set: bool = False, y_was_set: bool = False,
                            current_font: str = "ARIAL08"):
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

        # Sanitize resource name for DFA (no spaces, hyphens, special chars)
        resource_name = self._sanitize_dfa_name(resource_name)

        # Check if this is an XGFRESDEF graphical subroutine (boxes/lines).
        # DFA has no equivalent named drawing macro, so we inline the DRAWB commands
        # as absolute BOX/RULE commands using the MOVETO origin as the anchor.
        if not file_ext and resource_name in self.subroutines:
            sub = self.subroutines[resource_name]
            if sub.get('xgfresdef'):
                # Preserve FRM flow cursor around inlined SCALL drawings.
                self.add_line("YPOS = $SL_CURRY;")
                self.add_line("XPOS = $SL_CURRX;")
                if x_was_set:
                    self.add_line(f"XPOS = MM({x});")
                if y_was_set:
                    self.add_line(f"YPOS = MM({y});")

                # Inline all DRAWB children relative to saved anchors.
                origin_x = x if x_was_set else 0.0
                origin_y = y if y_was_set else 0.0
                self._inline_xgfresdef_drawbs(
                    resource_name, origin_x, origin_y,
                    anchor_x_var="XPOS",
                    anchor_y_var="YPOS"
                )

                # Restore cursor so SAME/NEXT flow continues after SCALL.
                self.add_line("OUTPUT ''")
                self.add_line(f"    FONT {current_font} NORMAL")
                self.add_line("    POSITION (XPOS) (YPOS);")
                return
            else:
                # Legacy non-XGFRESDEF subroutine: inline via command list (unchanged behaviour)
                if sub['type'] == 'simple':
                    self.add_line(f"/* Inlined subroutine: {resource_name} ({sub['command_count']} commands) */")
                    self._convert_frm_command_list(
                        sub['commands'],
                        start_x=x if x_was_set else 0.0,
                        start_y=y if y_was_set else 0.0,
                        start_font='',
                        frm=frm
                    )
                    return

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

        # Extract scale from SCALL parameters (VIPP: scale SCALL)
        # The scale is the first numeric parameter in the SCALL command itself.
        scall_scale = 0.0
        if cmd.parameters:
            for param in cmd.parameters:
                if not param.startswith('(') and not param.startswith('['):
                    try:
                        v = float(param)
                        if v > 0:
                            scall_scale = v
                            break
                    except (ValueError, TypeError):
                        pass

        # Compute fixed width from EPS BoundingBox when a scale is present.
        eps_fixed_width_mm = 0.0
        if scall_scale > 0.0 and abs(scall_scale - 1.0) > 0.001:
            import os as _os
            frm_dir = _os.path.dirname(frm.filename) if frm and frm.filename else ""
            if not frm_dir and self.dbm and hasattr(self.dbm, 'filename'):
                frm_dir = _os.path.dirname(self.dbm.filename)
            # The original SCALL filename (before sanitization) determines the EPS lookup
            eps_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
            for candidate in [
                _os.path.join(frm_dir, eps_name + '.eps'),
                _os.path.join(frm_dir, eps_name + '.EPS'),
            ]:
                bbox = self._read_eps_bbox(candidate)
                if bbox is not None:
                    width_pt, height_pt = bbox
                    eps_fixed_width_mm = (width_pt / 72.0) * 25.4 * scall_scale
                    logger.info(f"EPS BoundingBox for {eps_name}: {width_pt:.1f}x{height_pt:.1f} pt "
                                f"-> target width {eps_fixed_width_mm:.1f} MM at {scall_scale*100:.1f}%")
                    break

        # Generate DFA based on file type
        if file_ext in ('jpg', 'jpeg', 'tif', 'tiff'):
            other_type = 'JPG' if file_ext in ('jpg', 'jpeg') else 'TIF'
            dims = (cache_width, cache_height) if cache_width is not None else None
            self._emit_scaled_image(
                resource_name, other_type, "SAME", "SAME",
                scale=scall_scale, cache_dims=dims,
                fixed_width_mm=eps_fixed_width_mm,
            )

        elif file_ext == 'eps':
            # EPS converted to JPG by migrate script → treat as JPG
            dims = (cache_width, cache_height) if cache_width is not None else None
            self._emit_scaled_image(
                resource_name, 'JPG', "SAME", "SAME",
                scale=scall_scale, cache_dims=dims,
                fixed_width_mm=eps_fixed_width_mm,
            )

        else:
            # AFP page segment: SEGMENT requires .240/.300 files from psew3pic (unlicensed).
            # Commented out; use CREATEOBJECT IOBDLL to load JPG directly instead.
            # Re-enable SEGMENT block when psew3pic license is available.
            x_part = f"{x} MM-$MR_LEFT" if x_was_set else "SAME"
            y_part = f"{y} MM-$MR_TOP+&CORSEGMENT" if y_was_set else "SAME"
            self._emit_scaled_image(resource_name, 'JPG', x_part, y_part,
                                    scale=scall_scale, fixed_width_mm=eps_fixed_width_mm)

    def _emit_scaled_image(self, resource_name: str, ext: str,
                           x_expr: str, y_expr: str,
                           scale: float = 0.0,
                           cache_dims: "tuple | None" = None,
                           fixed_width_mm: float = 0.0):
        """Emit CREATEOBJECT IOBDLL for an image with optional scaling.

        Priority order:
        0. fixed_width_mm > 0 — pre-computed width (from EPS BoundingBox): emit constant
        1. cache_dims=(w,h) — explicit pixel dimensions from CACHE [w h]: use directly
        2. scale > 0 and != 1.0 — Xerox percentage scale: use Method 1 (IOB_INFO)
             IOB_INFO reads original dimensions → calculate MM width → IOBDEFS
        3. Otherwise — no size info: IOBDEFS with OBJECTMAPPING='2' only (auto-fit)

        IOB_INFO creates IMG_XSIZE / IMG_YSIZE in 1/1440-inch units.
        Formula: IMG_W_MM = (IMG_XSIZE / #1440) * #25.4 * #scale
        """
        pos = f"({x_expr}) ({y_expr})"

        if fixed_width_mm > 0.0:
            # Pre-computed target width (e.g. from EPS BoundingBox × scale)
            scale_pct = scale * 100 if scale > 0 else 0
            self.add_line(f"/* Scale {resource_name} to {scale_pct:.4g}% — "
                          f"target width {fixed_width_mm:.1f} MM (from EPS BoundingBox) */")
            self.add_line(f"IMG_W_MM = #{fixed_width_mm:.2f} ;")
            self.add_line("CREATEOBJECT IOBDLL(IOBDEFS)")
            self.indent()
            self.add_line(f"POSITION {pos}")
            self.add_line("PARAMETERS")
            self.indent()
            self.add_line(f"('FILENAME'='{resource_name}')")
            self.add_line("('OBJECTTYPE'='1')")
            self.add_line(f"('OTHERTYPES'='{ext}')")
            self.add_line("('OBJECTMAPPING'='2')")
            self.add_line("('XOBJECTAREASIZE'=IMG_W_MM);")
            self.dedent()
            self.dedent()

        elif cache_dims is not None:
            # Explicit pixel dimensions from CACHE [w h]
            self.add_line("CREATEOBJECT IOBDLL(IOBDEFS)")
            self.indent()
            self.add_line(f"POSITION {pos}")
            self.add_line("PARAMETERS")
            self.indent()
            self.add_line(f"('FILENAME'='{resource_name}')")
            self.add_line("('OBJECTTYPE'='1')")
            self.add_line(f"('OTHERTYPES'='{ext}')")
            self.add_line(f"('XOBJECTAREASIZE'='{cache_dims[0]}')")
            self.add_line(f"('YOBJECTAREASIZE'='{cache_dims[1]}')")
            self.add_line("('OBJECTMAPPING'='2');")
            self.dedent()
            self.dedent()

        elif scale > 0.0 and abs(scale - 1.0) > 0.001:
            # Method 1: IOB_INFO → calculate width → IOBDEFS
            scale_pct = scale * 100
            self.add_line(f"/* Scale {resource_name} to {scale_pct:.4g}% via IOB_INFO */")
            self.add_line("CREATEOBJECT IOBDLL(IOB_INFO)")
            self.indent()
            self.add_line("PARAMETERS")
            self.indent()
            self.add_line(f"('FILENAME'='{resource_name}')")
            self.add_line("('OBJECTTYPE'='1')")
            self.add_line(f"('OTHERTYPES'='{ext}')")
            self.add_line("('VARPREFIX'='IMG_');")
            self.dedent()
            self.dedent()
            # IMG_XSIZE is in 1/1440-inch units; convert to MM then apply scale
            self.add_line(f"IMG_W_MM = (IMG_XSIZE / #1440) * #25.4 * #{scale:.6g} ;")
            self.add_line("CREATEOBJECT IOBDLL(IOBDEFS)")
            self.indent()
            self.add_line(f"POSITION {pos}")
            self.add_line("PARAMETERS")
            self.indent()
            self.add_line(f"('FILENAME'='{resource_name}')")
            self.add_line("('OBJECTTYPE'='1')")
            self.add_line(f"('OTHERTYPES'='{ext}')")
            self.add_line("('OBJECTMAPPING'='2')")
            self.add_line("('XOBJECTAREASIZE'=IMG_W_MM);")
            self.dedent()
            self.dedent()

        else:
            # No scale info — OBJECTMAPPING='2' lets DocEXEC auto-fit
            self.add_line("CREATEOBJECT IOBDLL(IOBDEFS)")
            self.indent()
            self.add_line(f"POSITION {pos}")
            self.add_line("PARAMETERS")
            self.indent()
            self.add_line(f"('FILENAME'='{resource_name}')")
            self.add_line("('OBJECTTYPE'='1')")
            self.add_line(f"('OTHERTYPES'='{ext}')")
            self.add_line("('OBJECTMAPPING'='2');")
            self.dedent()
            self.dedent()

    @staticmethod
    def _read_eps_bbox(eps_path: str):
        """Read %%BoundingBox from an EPS file and return (width_pt, height_pt) or None.

        The BoundingBox line gives coordinates in PostScript points (1/72 inch):
            %%BoundingBox: llx lly urx ury
        Width = urx - llx, Height = ury - lly.
        """
        try:
            with open(eps_path, 'r', encoding='latin-1') as f:
                for line in f:
                    if line.startswith('%%BoundingBox:') and 'atend' not in line.lower():
                        parts = line.split()
                        if len(parts) >= 5:
                            llx, lly, urx, ury = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                            return (urx - llx, ury - lly)
                    if line.startswith('%%EndComments'):
                        break
        except (IOError, OSError, ValueError):
            pass
        return None

    def _convert_frm_image(self, cmd: XeroxCommand, x: float, y: float):
        """Convert FRM ICALL command to DFA CREATEOBJECT IOBDLL(IOBDEFS).

        VIPP ICALL format: (filename) scale rotation ICALL
        scale is the first numeric parameter (fraction of line measure).
        """
        resource_name = ""
        scale = 0.0
        found_scale = False

        for param in cmd.parameters:
            if param.startswith('(') and param.endswith(')'):
                resource_name = param[1:-1]
            elif not found_scale:
                try:
                    scale = float(param)
                    found_scale = True   # take only the FIRST numeric (scale), not rotation
                except (ValueError, TypeError):
                    pass

        if not resource_name:
            return

        import os as _os
        ext = _os.path.splitext(resource_name)[1].upper().lstrip('.') or 'JPG'

        self._emit_scaled_image(
            resource_name, ext,
            f"{x} MM-$MR_LEFT", f"{y} MM-$MR_TOP",
            scale=scale,
        )

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
        Also tracks referenced prefixes from WIZVAR.
        """
        self.format_registry = {}

        # Track PREFIX references from WIZVAR
        if hasattr(self.dbm, 'wizvar_prefixes') and self.dbm.wizvar_prefixes:
            for prefix_var in self.dbm.wizvar_prefixes:
                # Extract prefix value from variable name like "PREFIX_XX"
                # WIZVAR entries are like: PREFIX eq (XX), PREFIX eq (Y1), etc.
                # We'll track these when we see them in raw content
                pass

        # Also scan raw content for PREFIX references like "PREFIX eq (XX)"
        if self.dbm.raw_content:
            import re
            # Pattern to match: PREFIX eq (XX) or PREFIX ne (YY) etc.
            prefix_pattern = r'PREFIX\s+(?:eq|ne|gt|lt|ge|le)\s+\(([A-Z0-9]+)\)'
            matches = re.findall(prefix_pattern, self.dbm.raw_content, re.IGNORECASE)
            for prefix_value in matches:
                self.referenced_prefixes.add(prefix_value.upper())
                logger.debug(f"Found PREFIX reference: {prefix_value}")

        # Register CASE blocks as defined formats
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
            if cmd.name == 'ORITL':
                self.origin_is_oritl = True
                logger.info("Found ORITL: enabling Y-offset inversion for SCALL inlining")

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
                # Get the first match (initial page layout frame)
                # The first SETLKF defines the data area for the first section of pages.
                # Later SETLKFs (for subsequent sections) are handled per-PREFIX-case.
                first_match = matches[0]
                self.page_layout_position = (float(first_match[0]), float(first_match[1]))
                logger.info(f"Found SETPAGEDEF layout position from raw content: {self.page_layout_position}")

        # Backup ORITL detection from raw content if command parsing missed it.
        if not self.origin_is_oritl and self.dbm.raw_content and re.search(r'\bORITL\b', self.dbm.raw_content):
            self.origin_is_oritl = True
            logger.info("Found ORITL in raw content: enabling Y-offset inversion for SCALL inlining")

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

    def _extract_subroutines(self):
        """
        Extract XGFRESDEF subroutine definitions from DBM commands.
        Stores them in self.subroutines for later inlining or SEGMENT generation.
        """
        for cmd in self.dbm.commands:
            if cmd.name == 'XGFRESDEF' and cmd.parameters and cmd.children:
                resource_name = cmd.parameters[0]
                command_count = len(cmd.children)
                subroutine_type = 'simple' if command_count <= 5 else 'complex'

                drawb_count = sum(1 for c in cmd.children if c.name == 'DRAWB')
                self.subroutines[resource_name] = {
                    'commands': cmd.children,
                    'type': subroutine_type,
                    'command_count': command_count,
                    'xgfresdef': True,  # Flag: must be inlined as BOX/RULE at call site
                }

                logger.info(f"Found DBM XGFRESDEF subroutine '{resource_name}' with {command_count} children "
                            f"({drawb_count} DRAWB) — will inline at SCALL sites")

    def _iter_all_case_commands(self):
        """Yield all commands from CASE blocks recursively."""
        def _walk(cmds):
            for _cmd in cmds:
                yield _cmd
                if _cmd.children:
                    yield from _walk(_cmd.children)

        for case_cmds in self.dbm.case_blocks.values():
            yield from _walk(case_cmds)

    def _iter_all_commands(self):
        """Yield all DBM commands recursively (global + CASE)."""
        def _walk(cmds):
            for _cmd in cmds:
                yield _cmd
                if _cmd.children:
                    yield from _walk(_cmd.children)

        yield from _walk(self.dbm.commands)
        for case_cmds in self.dbm.case_blocks.values():
            yield from _walk(case_cmds)

    def _extract_page_number_settings(self):
        """
        Extract first SETPAGENUMBER command from DBM and map it to footer output.

        VIPP syntax supports several forms; in OCBC DBM we see:
            (format) start hpos vpos align SETPAGENUMBER
        """
        for cmd in self._iter_all_case_commands():
            if cmd.name != 'SETPAGENUMBER':
                continue

            self._convert_pagenumber_command(cmd, emit_now=False)
            return

    def _extract_getitem_table_definitions(self):
        """
        Extract GETITEM table headers from SETVAR definitions.

        Pattern from VIPP:
            /VARtab [[/VAR_pctot]] SETVAR
        """
        # Primary path: parse directly from raw DBM text because tokenizer may
        # normalize/trim bracket payloads used by VIPP table headers.
        if self.dbm.raw_content:
            header_pattern = re.compile(
                r'/([A-Za-z_][A-Za-z0-9_]*)\s+\[\[(.*?)\]\]\s+SETVAR',
                re.IGNORECASE
            )
            for match in header_pattern.finditer(self.dbm.raw_content):
                table_name = self._sanitize_dfa_name(match.group(1))
                header_body = match.group(2)
                fields = re.findall(r'/?([A-Za-z_][A-Za-z0-9_]*)', header_body)
                if not fields:
                    continue
                self.getitem_table_fields[table_name] = fields
                self.getitem_store_vars[table_name] = f"{table_name}_ROWS"

        # Fallback: use parsed command stream.
        for cmd in self._iter_all_commands():
            if cmd.name != 'SETVAR' or len(cmd.parameters) < 2:
                continue

            lhs = str(cmd.parameters[0]).lstrip('/')
            rhs = str(cmd.parameters[1])
            if '[[' not in rhs or ']]' not in rhs or '/' not in rhs:
                continue

            table_name = self._sanitize_dfa_name(lhs)
            # Header row contains /VAR_xxx tokens.
            fields = re.findall(r'/([A-Za-z_][A-Za-z0-9_]*)', rhs)
            if not fields:
                continue

            self.getitem_table_fields[table_name] = fields
            self.getitem_store_vars[table_name] = f"{table_name}_ROWS"

    def _convert_add_command(self, cmd: XeroxCommand):
        """
        Convert VIPP ADD command.

        - Numeric pattern: /VAR_X value ADD  -> VAR_X = VAR_X + value;
        - Table pattern:   /VARtab [ VAR_A VAR_B ] ADD -> append row to table store
        """
        if len(cmd.parameters) < 2:
            self.add_line("/* ADD with insufficient parameters */")
            return

        target_raw = str(cmd.parameters[0]).lstrip('/')
        target = self._sanitize_dfa_name(target_raw)
        value_raw = str(cmd.parameters[1]).strip()

        # Table append mode (for GETITEM-driven tables).
        if target in self.getitem_table_fields and '[' in value_raw and ']' in value_raw:
            store = self.getitem_store_vars.get(target, f"{target}_ROWS")
            fields = self.getitem_table_fields.get(target, [])
            # Special-case legacy total-page tables: footer rendering uses PP directly.
            if len(fields) == 1 and self._is_total_page_var(fields[0]):
                self.add_line("/* Skipped ADD to total-page table; PRINTFOOTER uses PP */")
                return
            # Extract row tokens inside [...] and map to DFA identifiers.
            inner = value_raw.replace('[', ' ').replace(']', ' ')
            tokens = [t for t in inner.split() if t]
            row_tokens = []
            for tok in tokens:
                if tok.startswith('/'):
                    row_tokens.append(self._sanitize_dfa_name(tok.lstrip('/')))
                elif tok.replace('.', '', 1).lstrip('-').isdigit():
                    row_tokens.append(tok)
                elif re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', tok):
                    row_tokens.append(self._sanitize_dfa_name(tok))
                else:
                    row_tokens.append(f"'{self._escape_dfa_quotes(tok)}'")

            # Build row payload for store array.
            if len(fields) <= 1 and row_tokens:
                payload = row_tokens[0]
            elif row_tokens:
                literalized = [rt if rt.startswith("'") or rt.replace('.', '', 1).lstrip('-').isdigit() else rt for rt in row_tokens]
                payload = " ! '|' ! ".join(literalized)
            else:
                payload = "''"

            # For single-column tables, use delimiter-packed scalar storage to avoid
            # indexed-array declaration warnings in DFA.
            if len(fields) <= 1:
                self.add_line(f"IF ISTRUE({store} == '');")
                self.add_line(f"THEN; {store} = {payload};")
                self.add_line(f"ELSE; {store} = {store} ! '|' ! {payload};")
                self.add_line("ENDIF;")
            else:
                self.add_line(f"{store}[MAXINDEX({store})+1] = {payload};")
            return

        # Numeric/regular add mode.
        rhs = value_raw

        # Xerox dynamic Y anchors:
        # /VAR.Y4 0 ADD  -> capture current flow Y for later DRAWB use.
        # Emit direct cursor binding instead of no-op arithmetic.
        if re.match(r'^VAR\.Y\d+$', target_raw, re.IGNORECASE):
            try:
                rhs_num = float(rhs)
            except (TypeError, ValueError):
                rhs_num = None
            if rhs_num is not None and abs(rhs_num) < 0.0001:
                self.add_line(f"{target} = $SL_CURRY;")
                return

        if rhs.startswith('/'):
            rhs = self._sanitize_dfa_name(rhs.lstrip('/'))
        elif rhs.startswith('(') and rhs.endswith(')'):
            rhs = f"'{self._escape_dfa_quotes(rhs[1:-1])}'"
        self.add_line(f"{target} = {target} + {rhs};")

    def _convert_getitem_command(self, cmd: XeroxCommand):
        """
        Convert VIPP GETITEM lookup from stored table rows.

        Pattern:
            VARtab VARdoc GETITEM
        """
        if len(cmd.parameters) < 2:
            self.add_line("/* GETITEM with insufficient parameters */")
            return

        table = self._sanitize_dfa_name(str(cmd.parameters[0]))
        index_var = self._sanitize_dfa_name(str(cmd.parameters[1]))
        fields = self.getitem_table_fields.get(table, [])
        store = self.getitem_store_vars.get(table, f"{table}_ROWS")

        if not fields:
            self.add_line(f"/* GETITEM table '{table}' has no extracted header definition */")
            return

        if len(fields) == 1:
            if self._is_total_page_var(fields[0]):
                self.add_line(f"/* Skipped GETITEM for {fields[0]}; PRINTFOOTER uses PP */")
                return
            self.add_line(f"GETITEM_CNT = EXTRACTALL(GETITEM_COL, {store}, '|', '');")
            self.add_line(f"{fields[0]} = GETITEM_COL[{index_var}];")
            return

        # Multi-column row payload separated by '|'
        self.add_line(f"GETITEM_ROW = {store}[{index_var}];")
        self.add_line("GETITEM_COUNT = EXTRACTALL(GETITEM_COL, GETITEM_ROW, '|', '');")
        for i, field in enumerate(fields, start=1):
            self.add_line(f"{field} = GETITEM_COL[{i}];")

    def _render_vipp_format_expr(self, raw_text: str) -> str:
        """
        Convert VIPP format text with '#' placeholders and VSUB vars to DFA expression.
        """
        text = raw_text
        if text.startswith('(') and text.endswith(')'):
            text = text[1:-1]

        # Tokenize literals, VIPP variables ($$VAR.), and page placeholders (###).
        parts = []
        i = 0
        while i < len(text):
            # $$VAR_NAME.
            if text.startswith('$$', i):
                j = i + 2
                while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                    j += 1
                if j < len(text) and text[j] == '.' and j > i + 2:
                    parts.append(('var', text[i + 2:j]))
                    i = j + 1
                    continue

            # $VAR_NAME
            if text.startswith('$', i) and not text.startswith('$$', i):
                j = i + 1
                while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                    j += 1
                if j > i + 1:
                    parts.append(('var', text[i + 1:j]))
                    i = j
                    continue

            # ### placeholder (current page number)
            if text[i] == '#':
                j = i
                while j < len(text) and text[j] == '#':
                    j += 1
                parts.append(('page', j - i))
                i = j
                continue

            # Literal run
            j = i
            while j < len(text):
                if text[j] == '#' or text.startswith('$$', j) or text.startswith('$', j):
                    break
                j += 1
            literal = text[i:j]
            if literal:
                parts.append(('lit', literal))
            i = j

        if not parts:
            return "''"

        expr_parts = []
        for part_type, value in parts:
            if part_type == 'lit':
                expr_parts.append(f"'{self._escape_dfa_quotes(value)}'")
            elif part_type == 'var':
                var_name = self._sanitize_dfa_name(value)
                # In OCBC sources, $$VAR_pctot. denotes total pages.
                # PRINTFOOTER always has final PP, so use PP directly to avoid scope warnings.
                if var_name.upper() in ('VAR_PCTOT', 'VAR_PTOT', 'VARPTOT'):
                    expr_parts.append("PP")
                else:
                    expr_parts.append(var_name)
            else:
                # Width 1 -> plain page number, width >1 -> zero-padded
                if value <= 1:
                    expr_parts.append("P")
                else:
                    expr_parts.append(f"NUMPICTURE(P,'{'0' * value}')")

        return ' ! '.join(expr_parts)

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
        self.add_line("SOURCERES 240")
        self.add_line("TARGETRES 240")
        self.add_line("PTXUNIT 1440")
        self.add_line("FDFINCLUDE YES")
        self.add_line("TLE YES")
        self.add_line("TLECPID YES")
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
        # FOOTER counts total pages (PP) during formatting pass
        # For multi-FRM documents (3+), also snapshot VAR_CURFORM per page
        # because PRINTFOOTER runs in the print pass where VAR_CURFORM has
        # only its FINAL value — not the per-page value set during formatting.
        is_multi_frm = self.frm_files and len(self.frm_files) > 2
        self.add_line("    FOOTER")
        self.add_line("        PP = PP + 1;")
        if is_multi_frm:
            self.add_line("        FRM_PAGE[PP] = VAR_CURFORM;")
        self.add_line("    FOOTEREND")
        # PRINTFOOTER: Renders FRM page background + page numbering.
        # FRM rendering happens in the print pass (PRINTFOOTER) because:
        # 1. It has an independent cursor context (won't interfere with data positioning)
        # 2. This matches VIPP SETFORM behavior where the form renders as a page background
        self.add_line("    PRINTFOOTER")
        if is_multi_frm:
            # Multi-FRM: increment P FIRST so FRM_PAGE[P] indexes the correct page.
            self.add_line("        P = P + 1;")
            self.add_line("        /* Render the FRM page background (per-page array) */")
            self.add_line("        IF ISTRUE(NOSPACE(FRM_PAGE[P])<>'');")
            self.add_line("        THEN;")
            self.add_line("            USE FORMAT REFERENCE(FRM_PAGE[P]) EXTERNAL;")
            self.add_line("        ENDIF;")
        elif self.frm_files:
            # 1-2 FRM: check BEFORE incrementing so IF P<1 correctly targets the first page.
            # P starts at 0 (reset in $_BEFOREDOC); first call → P=0 < 1 → first-page FRM.
            frm_sorted = sorted(self.frm_files.keys())
            frm_names = [''.join(c for c in os.path.splitext(f)[0].upper() if c.isalnum() or c == '_')
                         for f in frm_sorted]
            # Apply the same collision-avoidance as the file-writing loop: when the FRM base
            # name matches the DBM base name, the FRM file is written with an 'F' suffix
            # (e.g. UT00060F.dfa). The USE FORMAT name must match the written filename.
            frm_names = [
                (n + 'F' if n == docdef_name else n)
                for n in frm_names
            ]
            if len(frm_names) >= 2:
                first_form = next((f for f in frm_names if f.endswith('F')), frm_names[0])
                subseq_form = next((f for f in frm_names if f.endswith('S')), frm_names[-1])
                self.add_line("        /* Render the FRM page background (2-FRM: first / subsequent) */")
                self.add_line(f"        IF P<1; THEN; USE FORMAT {first_form} EXTERNAL; ELSE; USE FORMAT {subseq_form} EXTERNAL; ENDIF;")
            else:
                frm_name = frm_names[0]
                self.add_line("        /* Render the FRM page background */")
                self.add_line(f"        USE FORMAT {frm_name} EXTERNAL;")
            self.add_line("        P = P + 1;")
        else:
            self.add_line("        P = P + 1;")
        self.add_line("        /* Page numbering */")
        self.add_line("        OUTLINE")
        self.add_line("            POSITION RIGHT (0 MM)")
        self.add_line("            DIRECTION ACROSS;")
        self.add_line(f"            OUTPUT {self.page_number_expr}")
        self.add_line("                FONT F5_1")
        self.add_line(f"                POSITION ({self.page_number_x}) {self.page_number_y}")
        self.add_line(f"                ALIGN {self.page_number_align} NOPAD;")
        if self.emit_page_index_marker:
            self.add_line(f"            INDEX PAGE_MARKER = {self.page_number_expr};")
        self.add_line("        ENDIO;")
        self.add_line("    PRINTEND;")
        self.add_line("")

        # Add LOGICALPAGE 2 only for duplex printing (back side of page)
        # Detect duplex from source: look for active (uncommented) DUPLEX command
        is_duplex = self._detect_duplex()
        if is_duplex:
            self.add_line("LOGICALPAGE 2")
            self.add_line("    SIDE BACK")
            self.add_line("    POSITION 0 0")
            self.add_line("    WIDTH 210 MM")
            self.add_line("    HEIGHT 297 MM")
            self.add_line("    DIRECTION ACROSS")
            self.add_line("    FOOTER")
            self.add_line("        PP = PP + 1;")
            if is_multi_frm:
                self.add_line("        FRM_PAGE[PP] = VAR_CURFORM;")
            self.add_line("    FOOTEREND")
            self.add_line("    PRINTFOOTER")
            if is_multi_frm:
                self.add_line("        P = P + 1;")
                self.add_line("        /* Render the FRM page background (per-page array) */")
                self.add_line("        IF ISTRUE(NOSPACE(FRM_PAGE[P])<>'');")
                self.add_line("        THEN;")
                self.add_line("            USE FORMAT REFERENCE(FRM_PAGE[P]) EXTERNAL;")
                self.add_line("        ENDIF;")
            elif self.frm_files:
                frm_sorted = sorted(self.frm_files.keys())
                frm_names = [''.join(c for c in os.path.splitext(f)[0].upper() if c.isalnum() or c == '_')
                             for f in frm_sorted]
                # Apply collision-avoidance: FRM with same base name as DBM is written with 'F' suffix.
                frm_names = [
                    (n + 'F' if n == docdef_name else n)
                    for n in frm_names
                ]
                if len(frm_names) >= 2:
                    first_form = next((f for f in frm_names if f.endswith('F')), frm_names[0])
                    subseq_form = next((f for f in frm_names if f.endswith('S')), frm_names[-1])
                    self.add_line("        /* Render the FRM page background (2-FRM: first / subsequent) */")
                    self.add_line(f"        IF P<1; THEN; USE FORMAT {first_form} EXTERNAL; ELSE; USE FORMAT {subseq_form} EXTERNAL; ENDIF;")
                else:
                    frm_name = frm_names[0]
                    self.add_line("        /* Render the FRM page background */")
                    self.add_line(f"        USE FORMAT {frm_name} EXTERNAL;")
                self.add_line("        P = P + 1;")
            else:
                self.add_line("        P = P + 1;")
            self.add_line("        /* Page numbering */")
            self.add_line("        OUTLINE")
            self.add_line("            POSITION RIGHT (0 MM)")
            self.add_line("            DIRECTION ACROSS;")
            self.add_line(f"            OUTPUT {self.page_number_expr}")
            self.add_line("                FONT F5_1")
            self.add_line(f"                POSITION ({self.page_number_x}) {self.page_number_y}")
            self.add_line(f"                ALIGN {self.page_number_align} NOPAD;")
            if self.emit_page_index_marker:
                self.add_line(f"            INDEX PAGE_MARKER = {self.page_number_expr};")
            self.add_line("        ENDIO;")
            self.add_line("    PRINTEND;")

        self.dedent()
        self.add_line("")

    def _detect_duplex(self) -> bool:
        """Detect if the source document requires duplex printing.

        Checks for active (uncommented) DUPLEX command in DBM raw content,
        or FRM filenames containing 'B' suffix (e.g., CASIOB = back page).
        """
        # Check DBM raw content for DUPLEX command (not commented with %)
        if self.dbm and self.dbm.raw_content:
            for line in self.dbm.raw_content.split('\n'):
                stripped = line.strip()
                if stripped and not stripped.startswith('%'):
                    if 'DUPLEX' in stripped.upper():
                        return True
        # Check if any FRM filename ends with 'B' (back page convention)
        for frm_name in self.frm_files:
            base = os.path.splitext(frm_name)[0].upper()
            import re
            if re.search(r'B\d*$', base):
                return True
        return False

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

        # Standard color mappings to RGB values (0-255 scale)
        # Note: Converting from percentages to 0-255 scale
        # LMED/MED = RGB 217,217,217 (light gray 85%)
        # XDRK = RGB 166,166,166 (dark gray 65%)
        color_rgb_map = {
            'BLACK': (0, 0, 0),
            'FBLACK': (0, 0, 0),  # Same as BLACK
            'WHITE': (255, 255, 255),
            'RED': (255, 0, 0),
            'GREEN': (0, 255, 0),
            'BLUE': (0, 0, 255),
            'YELLOW': (255, 255, 0),
            'CYAN': (0, 255, 255),
            'MAGENTA': (255, 0, 255),
            'ORANGE': (255, 165, 0),
            'GRAY': (128, 128, 128),
            'LIGHTGRAY': (192, 192, 192),
            'DARKGRAY': (64, 64, 64),
            'LMED': (217, 217, 217),  # Light gray for OCBC
            'MED': (217, 217, 217),   # Same as LMED
            'XDRK': (166, 166, 166),  # Dark gray for OCBC
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
            # Convert RGB from 0-255 to 0-100 percentage scale
            r_pct = round(r * 100 / 255, 1)
            g_pct = round(g * 100 / 255, 1)
            b_pct = round(b * 100 / 255, 1)
            # Format as integer if whole number, otherwise keep decimal
            r_str = str(int(r_pct)) if r_pct == int(r_pct) else str(r_pct)
            g_str = str(int(g_pct)) if g_pct == int(g_pct) else str(g_pct)
            b_str = str(int(b_pct)) if b_pct == int(b_pct) else str(b_pct)
            # Use correct DEFINE COLOR syntax
            self.add_line(f"DEFINE {dfa_alias} COLOR RGB RVAL {r_str} GVAL {g_str} BVAL {b_str};")

        # Note: Only colors collected from source (DBM + FRM) are defined above.
        # No hardcoded OCBC colors are added — source-derived only.

        self.add_line("")

    def _backpass_verify_color_definitions(self):
        """Back-pass: find COLOR <name> references in output and ensure each has a DEFINE.

        If a color is referenced but not defined, insert a DEFINE at the top of output
        with a traceability comment.
        """
        # Standard color RGB map for fallback definitions
        color_rgb_map = {
            'BLACK': (0, 0, 0),
            'FBLACK': (0, 0, 0),
            'WHITE': (255, 255, 255),
            'RED': (255, 0, 0),
            'GREEN': (0, 255, 0),
            'BLUE': (0, 0, 255),
            'LMED': (217, 217, 217),
            'MED': (217, 217, 217),
            'XDRK': (166, 166, 166),
        }

        full_output = '\n'.join(self.output_lines)

        # Find all COLOR <name> references (not inside DEFINE lines)
        referenced_colors = set()
        for line in self.output_lines:
            stripped = line.strip()
            if stripped.startswith('DEFINE ') and ' COLOR ' in stripped:
                continue  # Skip DEFINE lines
            # Match COLOR <NAME> patterns
            for m in re.finditer(r'\bCOLOR\s+([A-Z][A-Z0-9_]*)', stripped):
                referenced_colors.add(m.group(1))

        # Find all defined colors
        defined_colors = set()
        for line in self.output_lines:
            stripped = line.strip()
            m = re.match(r'DEFINE\s+([A-Z][A-Z0-9_]*)\s+COLOR\b', stripped)
            if m:
                defined_colors.add(m.group(1))

        # Add missing definitions
        missing = referenced_colors - defined_colors
        if missing:
            # Find insertion point: after last DEFINE COLOR line
            insert_idx = 0
            for i, line in enumerate(self.output_lines):
                if 'DEFINE' in line and 'COLOR' in line:
                    insert_idx = i + 1

            new_lines = []
            for color_name in sorted(missing):
                r, g, b = color_rgb_map.get(color_name, (0, 0, 0))
                r_pct = round(r * 100 / 255, 1)
                g_pct = round(g * 100 / 255, 1)
                b_pct = round(b * 100 / 255, 1)
                r_str = str(int(r_pct)) if r_pct == int(r_pct) else str(r_pct)
                g_str = str(int(g_pct)) if g_pct == int(g_pct) else str(g_pct)
                b_str = str(int(b_pct)) if b_pct == int(b_pct) else str(b_pct)
                new_lines.append(f"DEFINE {color_name} COLOR RGB RVAL {r_str} GVAL {g_str} BVAL {b_str}; /* Added: referenced but not in source */")

            # Insert missing color definitions
            for j, new_line in enumerate(new_lines):
                self.output_lines.insert(insert_idx + j, new_line)

    def _validate_if_else_balance(self):
        """Validation pass: verify IF/ELSE/ENDIF balance in generated DFA output.

        Counts IF, ELSE, ENDIF tokens and logs warnings for mismatches.
        Does not modify output — diagnostic only.
        """
        if_count = 0
        else_count = 0
        endif_count = 0

        for line in self.output_lines:
            stripped = line.strip()
            # Skip comments
            if stripped.startswith('/*'):
                continue
            # Count all keyword occurrences using findall (not startswith/match).
            # This correctly handles one-liner compound statements such as:
            #   IF P==1; THEN; USE FORMAT CASIOS EXTERNAL; ENDIF;
            # A simple startswith('ENDIF') check would miss the ENDIF on such lines.
            # Use negative lookbehind (?<!END) to match IF only when NOT preceded by "END".
            n_if = len(re.findall(r'(?<!END)\bIF\b', stripped))
            n_else = len(re.findall(r'\bELSE\b', stripped))
            n_endif = len(re.findall(r'\bENDIF\b', stripped))
            if_count += n_if
            else_count += n_else
            endif_count += n_endif

        if if_count != endif_count:
            logger.warning(f"IF/ENDIF mismatch: {if_count} IF vs {endif_count} ENDIF")
        if else_count > if_count:
            logger.warning(f"Orphan ELSE detected: {else_count} ELSE with only {if_count} IF")

        logger.info(f"IF/ELSE/ENDIF validation: IF={if_count}, ELSE={else_count}, ENDIF={endif_count}")

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

    def _format_position(self, x, y, font: str = None, vertical_next_to_autospace: bool = False):
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
                # Numeric position - margin-corrected by default; FRM mode emits raw MM
                if self.position_no_margins:
                    x_part = f"({x} MM)"
                else:
                    x_part = f"({x} MM-$MR_LEFT)"
        else:
            # Numeric position - margin-corrected by default; FRM mode emits raw MM
            if self.position_no_margins:
                x_part = f"({x} MM)"
            else:
                x_part = f"({x} MM-$MR_LEFT)"

        # Handle Y coordinate
        font_correction = ""
        if font:
            font_correction = self._get_font_correction(font)

        if isinstance(y, str):
            y = y.strip()
            if vertical_next_to_autospace and y.upper() == 'NEXT':
                y = 'AUTOSPACE'
            elif vertical_next_to_autospace:
                y_upper_raw = y.upper()
                if y_upper_raw.startswith('SAME+') or y_upper_raw.startswith('SAME-'):
                    y = f"AUTOSPACE{y[4:]}"
            y_upper = y.upper()
            # Check if it's a keyword or starts with a keyword (for expressions like NEXT-(...) or LASTMAX+...)
            if y_upper in ('SAME', 'NEXT', 'AUTOSPACE', 'TOP', 'BOTTOM') or y_upper.startswith(('NEXT-', 'NEXT+', 'SAME-', 'SAME+', 'AUTOSPACE+', 'AUTOSPACE-', 'LASTMAX+', 'LASTMAX-')):
                y_part = f"({y})"
            else:
                # Numeric position - margin-corrected by default; FRM mode emits raw MM
                if self.position_no_margins:
                    if font_correction:
                        y_part = f"({y} MM+{font_correction})"
                    else:
                        y_part = f"({y} MM)"
                else:
                    if font_correction:
                        y_part = f"({y} MM-$MR_TOP+{font_correction})"
                    else:
                        y_part = f"({y} MM-$MR_TOP)"
        else:
            # Numeric position - margin-corrected by default; FRM mode emits raw MM
            if self.position_no_margins:
                if font_correction:
                    y_part = f"({y} MM+{font_correction})"
                else:
                    y_part = f"({y} MM)"
            else:
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
            'SH', 'SHL', 'SHR', 'SHr', 'SHC', 'SHc', 'SHP', 'SHp',  # Text output
            'DRAWB', 'SCALL', 'ICALL',                 # Graphics
            'SETLSP', 'NL'                             # Spacing/newlines
        }
        return any(cmd.name in output_commands for cmd in commands)

    def _should_generate_docformat(self, commands: List[XeroxCommand]) -> bool:
        """
        Check if a DOCFORMAT should be generated for this PREFIX case.

        Only generate DOCFORMAT if the case has meaningful content:
        - OUTPUT commands (SH, NL, MOVEH, etc.)
        - SETFORM/SETPAGEDEF/SETLKF (page layout)
        - Data manipulation (GETINTV, SUBSTR, VSUB)
        - Complex logic (IF/THEN with operations)
        - Page management (PAGEBRK, NEWFRAME, ADD with arrays)
        - PREFIX assignment (e.g., /VAR_Y2 PREFIX SETVAR)

        Skip truly empty cases that only have simple variable assignments.

        Args:
            commands: List of VIPP commands to check

        Returns:
            True if DOCFORMAT should be generated, False otherwise
        """
        # Include nested commands (IF/ELSE blocks) in significance checks.
        def _flatten(cmds):
            for c in cmds:
                yield c
                if c.children:
                    yield from _flatten(c.children)

        all_cmds = list(_flatten(commands))

        # Check for output commands
        output_commands = {
            'SH', 'SHL', 'SHR', 'SHr', 'SHC', 'SHc', 'SHP', 'SHp',  # Text output
            'DRAWB', 'SCALL', 'ICALL',                 # Graphics
            'NL', 'SETLSP', 'MOVETO', 'MOVEH', 'MOVEHR',  # Positioning
            'SETFORM', 'SETPAGEDEF', 'SETLKF',        # Page layout
        }
        has_output = any(cmd.name in output_commands for cmd in all_cmds)

        # Check for data manipulation commands (string/date parsing)
        data_commands = {'GETINTV', 'SUBSTR', 'VSUB', 'GETITEM'}
        has_data_manip = any(cmd.name in data_commands for cmd in all_cmds)

        # Check for page management commands
        page_commands = {'PAGEBRK', 'NEWFRAME', 'ADD', 'BOOKMARK'}
        has_page_mgmt = any(cmd.name in page_commands for cmd in all_cmds)

        # Check for increment/decrement
        has_counter = any(cmd.name in ['++', '--'] for cmd in all_cmds)

        # Check for IF blocks (structural logic)
        has_if = any(cmd.name == 'IF' for cmd in all_cmds)

        # Check for PREFIX assignment (e.g., /VAR_Y2 PREFIX SETVAR)
        # This is significant as it defines a record type prefix for data processing
        has_prefix_assignment = any(
            cmd.name == 'SETVAR' and
            len(cmd.parameters) >= 2 and
            str(cmd.parameters[1]).upper() == 'PREFIX'
            for cmd in all_cmds
        )

        # Generate if has ANY of:
        # 1. Output commands
        # 2. Data manipulation (GETINTV, SUBSTR)
        # 3. Page management commands (PAGEBRK/ADD/BOOKMARK etc.)
        # 4. Counters (++ or --)
        # 5. PREFIX assignment (important for data record definitions)
        return has_output or has_data_manip or has_page_mgmt or has_counter or has_prefix_assignment

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

    def _convert_vipp_format_to_dfa(self, vipp_format: str) -> str:
        """
        Convert VIPP numeric format pattern to DFA NUMPICTURE format.

        VIPP format: (@@@,@@@,@@@,@@#.##)
        DFA format: '#,##0.00'

        Conversion rules:
        - @ = optional digit → # in DFA
        - # = required digit → 0 in DFA
        - , = thousands separator → keep as ,
        - . = decimal point → keep as .

        For repeating patterns (like @@@,@@@,@@@), simplify to single group pattern.

        Args:
            vipp_format: VIPP format string (e.g., "(@@@,@@@,@@@,@@#.##)")

        Returns:
            DFA NUMPICTURE format string (e.g., "'#,##0.00'")
        """
        # Remove parentheses if present
        format_str = vipp_format.strip('()')

        # Split by decimal point to handle integer and decimal parts separately
        if '.' in format_str:
            integer_part, decimal_part = format_str.rsplit('.', 1)
        else:
            integer_part = format_str
            decimal_part = ""

        # For the integer part, simplify to standard thousands separator pattern
        # VIPP patterns with multiple groups (@@@,@@@,@@@,@@#) should use minimal DFA pattern
        # Standard DFA pattern is: #,##0 for thousands separator
        if ',' in integer_part:
            # Get all groups
            groups = integer_part.split(',')
            last_group = groups[-1]

            # Convert last group: @ -> # and # -> 0
            dfa_last_group = ""
            for char in last_group:
                if char == '@':
                    dfa_last_group += '#'
                elif char == '#':
                    dfa_last_group += '0'

            # Determine optimal prefix pattern
            # If there are more than 2 groups (indicating large numbers), use minimal pattern (#)
            # If there are exactly 2 groups, use the second-to-last group pattern
            if len(groups) > 2:
                # Multiple groups: use minimal standard pattern (#,##0 or similar)
                # Just use one optional digit before comma
                dfa_integer = f"#{',#' * (len(dfa_last_group) - 1)},{dfa_last_group}"
                # Simplify: if last group is ##0 or similar, standard is #,##0
                if len(dfa_last_group) == 3:
                    dfa_integer = f"#,{dfa_last_group}"
                else:
                    dfa_integer = f"#,{dfa_last_group}"
            else:
                # Exactly 2 groups: use both groups
                prev_group = groups[-2]
                dfa_prev = ""
                for char in prev_group:
                    if char == '@':
                        dfa_prev += '#'
                    elif char == '#':
                        dfa_prev += '0'
                dfa_integer = f"{dfa_prev},{dfa_last_group}"
        else:
            # No comma, just convert characters
            dfa_integer = ""
            for char in integer_part:
                if char == '@':
                    dfa_integer += '#'
                elif char == '#':
                    dfa_integer += '0'

        # Convert decimal part
        dfa_decimal = ""
        for char in decimal_part:
            if char == '@':
                dfa_decimal += '#'
            elif char == '#':
                dfa_decimal += '0'

        # Combine integer and decimal parts
        if dfa_decimal:
            dfa_format = f"{dfa_integer}.{dfa_decimal}"
        else:
            dfa_format = dfa_integer

        return f"'{dfa_format}'"

    def _convert_comparison_operators(self, params: List[str]) -> List[str]:
        """
        Convert VIPP comparison operators to DFA equivalents.
        Handles VIPP's Reverse Polish Notation (postfix) for logical operators.
        Also wraps variables in NOSPACE() when being compared to string literals.

        VIPP uses postfix notation for conditions:
            VAR_CCD '' eq VAR_CCD 'MY' eq or
        This should become (infix):
            NOSPACE(VAR_CCD) == '' or NOSPACE(VAR_CCD) == 'MY'

        Args:
            params: List of parameters that may contain comparison operators

        Returns:
            List with converted operators in infix notation
        """
        # Logical operators that use postfix notation in VIPP
        LOGICAL_OPERATORS = {'or': 'or', 'and': 'and'}

        # Check if we have any postfix logical operators
        has_postfix_logical = any(p.lower() in LOGICAL_OPERATORS for p in params)

        if has_postfix_logical:
            # Use RPN to infix conversion
            return self._convert_rpn_to_infix(params)
        else:
            # Simple linear conversion (no postfix logical operators)
            return self._convert_simple_comparison(params)

    def _convert_rpn_to_infix(self, params: List[str]) -> List[str]:
        """
        Convert VIPP condition to DFA infix notation.

        VIPP uses a hybrid notation:
        - Comparisons are INFIX: VAR_CCD eq ()  → VAR_CCD == ''
        - Logical operators are POSTFIX: [expr1] [expr2] or → expr1 or expr2

        VIPP format example:
            VAR_CCD eq () VAR_CCD eq (MY) or
        Should become:
            NOSPACE(VAR_CCD) == '' or NOSPACE(VAR_CCD) == 'MY'
        """
        LOGICAL_OPERATORS = {'or': 'or', 'and': 'and'}

        # First pass: convert parenthesized values to string literals
        converted_params = []
        for param in params:
            if param == '()':
                converted_params.append("''")
            elif param.startswith('(') and param.endswith(')') and len(param) > 2:
                content = param[1:-1]
                converted_params.append(f"'{content}'")
            else:
                converted_params.append(param)

        # Second pass: parse infix comparisons and postfix logical operators
        # VIPP comparison format: operand1 operator operand2 (infix)
        # Logical format: comparison1 comparison2 or/and (postfix)
        expressions = []
        i = 0
        while i < len(converted_params):
            param = converted_params[i]
            param_lower = param.lower()

            # Check for logical operators (postfix) - combine previous expressions
            if param_lower in LOGICAL_OPERATORS:
                dfa_logical = LOGICAL_OPERATORS[param_lower]
                if len(expressions) >= 2:
                    right = expressions.pop()
                    left = expressions.pop()
                    combined = f"{left} {dfa_logical} {right}"
                    expressions.append(combined)
                else:
                    # Not enough expressions - append as-is
                    expressions.append(dfa_logical)
                i += 1
            # Check for comparison operators (infix) - look for pattern: operand op operand
            elif param_lower in self.COMPARISON_OPERATORS:
                dfa_op = self.COMPARISON_OPERATORS[param_lower]
                # Get left operand (previous param) and right operand (next param)
                if i >= 1 and i + 1 < len(converted_params):
                    left = converted_params[i - 1]
                    right = converted_params[i + 1]
                    # Remove left from expressions if it was added
                    if expressions and expressions[-1] == left:
                        expressions.pop()
                    # Wrap left in NOSPACE() if it's a variable being compared to string
                    if right.startswith("'") and \
                       not left.startswith("NOSPACE(") and \
                       (left.startswith("VAR_") or left.startswith("FLD[") or left.startswith("&")):
                        left = f"NOSPACE({left})"
                    comparison = f"{left} {dfa_op} {right}"
                    expressions.append(comparison)
                    i += 2  # Skip the right operand as we've consumed it
                else:
                    # Can't form comparison - just add operator
                    expressions.append(dfa_op)
                    i += 1
            else:
                # Regular operand - add to expressions
                expressions.append(param)
                i += 1

        # Return the result as a single-element list
        if expressions:
            return [' '.join(expressions)]
        return []

    def _convert_simple_comparison(self, params: List[str]) -> List[str]:
        """
        Simple linear conversion for conditions without postfix logical operators.
        """
        result = []
        i = 0
        while i < len(params):
            param = params[i]

            # Check if this is a comparison operator
            if param.lower() in self.COMPARISON_OPERATORS:
                dfa_op = self.COMPARISON_OPERATORS[param.lower()]
                result.append(dfa_op)

                # Check if this is a string comparison (==, <>, etc.) and if so,
                # wrap the variable (before the operator) in NOSPACE()
                if dfa_op in ['==', '<>'] and len(result) >= 2:
                    # Look back at the previous parameter (the variable)
                    prev_param = result[-2]

                    # Check if the next parameter is a string literal
                    if i + 1 < len(params):
                        next_param = params[i + 1]

                        # If comparing to a string literal and prev is a variable
                        # Include VIPP (paren) string literals as well as already-quoted strings
                        is_string_rhs = (
                            next_param.startswith("'") or
                            next_param.upper() == next_param or
                            (next_param.startswith('(') and next_param.endswith(')'))
                        )
                        if is_string_rhs and \
                           not prev_param.startswith("NOSPACE(") and \
                           (prev_param.startswith("VAR_") or prev_param.startswith("FLD[") or prev_param.startswith("&")):
                            # Wrap the variable in NOSPACE()
                            result[-2] = f"NOSPACE({prev_param})"
            else:
                result.append(param)

            i += 1

        return result

    def _convert_frleft_condition(self, params: List[str]) -> tuple[str, bool]:
        """
        Convert FRLEFT (frame left) condition to DFA page break logic.

        VIPP: FRLEFT 60 lt → page has less than 60mm left
        DFA: $SL_MAXY>$LP_HEIGHT-MM(60)

        Args:
            params: List of parameters that may contain FRLEFT condition

        Returns:
            Tuple of (converted_condition, is_frleft) where is_frleft indicates if conversion happened
        """
        # Look for FRLEFT pattern in params
        # Pattern can be: FRLEFT 60 lt  OR  FRLEFT lt 60
        for i in range(len(params)):
            if params[i] == 'FRLEFT':
                # Check if we have at least 2 more parameters
                if i + 2 < len(params):
                    # Try both orders: FRLEFT 60 lt  and  FRLEFT lt 60
                    param1 = params[i + 1]
                    param2 = params[i + 2]

                    # Check if param1 is the operator (FRLEFT lt 60)
                    if param1.lower() in ['lt', '<', 'gt', '>', 'ge', '>=', 'le', '<=']:
                        operator = param1.lower()
                        threshold = param2
                    # Otherwise assume param2 is the operator (FRLEFT 60 lt)
                    else:
                        threshold = param1
                        operator = param2.lower()

                    # Convert to DFA condition
                    # Use $SL_LMAXY (last max Y from just-closed sublevel) because
                    # the FRLEFT check is emitted OUTSIDE the OUTLINE block (at
                    # DOCFORMAT level).  At that level $SL_MAXY is 0 (no active
                    # sublevel), but $SL_LMAXY retains the max Y from the OUTLINE
                    # that was just closed via ENDIO.
                    if operator in ['lt', '<']:
                        # FRLEFT 60 lt → page has less than 60mm left
                        # This means we're close to bottom of page
                        condition = f"$SL_LMAXY>$LP_HEIGHT-MM({threshold})"
                        return (condition, True)
                    elif operator in ['gt', '>']:
                        # FRLEFT 60 gt → page has more than 60mm left
                        condition = f"$SL_LMAXY<$LP_HEIGHT-MM({threshold})"
                        return (condition, True)
                    elif operator in ['ge', '>=']:
                        # FRLEFT 60 ge → page has at least 60mm left
                        condition = f"$SL_LMAXY<=$LP_HEIGHT-MM({threshold})"
                        return (condition, True)
                    elif operator in ['le', '<=']:
                        # FRLEFT 60 le → page has at most 60mm left
                        condition = f"$SL_LMAXY>=$LP_HEIGHT-MM({threshold})"
                        return (condition, True)

        return (None, False)

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

        # Generate initialization in $_BEFOREFIRSTDOC
        # IMPORTANT: Must appear BEFORE individual DOCFORMATs so DocEXEC's static
        # checker sees variable assignments before first use (avoids PPDE7101W).
        # Although $_BEFOREFIRSTDOC executes before all DOCFORMATs at runtime,
        # the static check is order-sensitive in the source file.
        self._generate_initialization()

        # Generate individual DOCFORMATs for each record type
        self._generate_individual_docformats()

        # Generate stub DOCFORMATs for undefined PREFIX cases
        self._generate_undefined_prefix_stubs()

        # End of document definition (no ENDDOCDEF in DFA — not a valid command)

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

        # Check if line is NOT document separator and NOT %%EOF
        # %%EOF may appear as a literal line in the data stream (VIPP preamble style)
        if self.dfa_config.enable_document_boundaries:
            separator = self.input_config.document_separator
            self.add_line(f"IF ISTRUE(LINE1 <> '{separator}' AND LINE1 <> '%%EOF');")
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
            self.add_line("/* Only read ahead if this was a '1' separator, not %%EOF itself */")
            self.add_line("IF ISTRUE(LINE1 <> '%%EOF'); THEN;")
            self.indent()
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

        # &SEP is set once in $_BEFOREFIRSTDOC from the PREFIX header line — do NOT re-assign here

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

        # &SEP is set once in $_BEFOREFIRSTDOC from the PREFIX header line — do NOT re-assign here

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
            self._convert_case_commands(commands, case_value=case_value)

        self.add_line("ENDSELECT;")
        self.add_line("")

    def _generate_individual_docformats(self):
        """
        Generate individual DOCFORMAT sections for each PREFIX case.
        Each record type gets its own DOCFORMAT for dynamic routing.
        Only generate DOCFORMATs that have meaningful content (not just variable assignments).
        """
        self.add_line("/* Individual DOCFORMAT sections for each record type */")
        self.add_line("")

        generated_count = 0
        skipped_prefixes = []
        is_first_docformat = True  # Track first PREFIX DOCFORMAT for PAGEBRK suppression

        for case_value, commands in self.dbm.case_blocks.items():
            if case_value == "{}":
                continue

            # Filter out empty DOCFORMATs - only generate if has meaningful content
            if not self._should_generate_docformat(commands):
                skipped_prefixes.append(case_value)
                logger.debug(f"Skipping empty DOCFORMAT for PREFIX '{case_value}' (only variable assignments)")
                continue

            docformat_name = f"DF_{case_value}"
            self.add_line(f"DOCFORMAT {docformat_name};")
            self.indent()

            # Track that this PREFIX has a defined DOCFORMAT
            self.defined_prefixes.add(case_value)

            # Generate case-specific processing.
            # For the first PREFIX case (document marker, e.g. MR): suppress the leading
            # PAGEBRK because DFA's ENDGROUP/ENDDOCUMENT handles document boundaries.
            self._convert_case_commands(
                commands,
                suppress_leading_pagebrk=is_first_docformat,
                case_value=case_value
            )
            is_first_docformat = False

            self.dedent()
            self.add_line("")
            generated_count += 1

        if skipped_prefixes:
            logger.info(f"Filtered out {len(skipped_prefixes)} empty DOCFORMATs: {', '.join(skipped_prefixes)}")
        logger.info(f"Generated {generated_count} DOCFORMATs with meaningful content")

        self.add_line("/* END OF INDIVIDUAL DOCFORMATS */")
        self.add_line("")

    def _generate_undefined_prefix_stubs(self):
        """
        Generate stub DOCFORMATs for undefined PREFIX cases.
        Creates empty DOCFORMAT stubs for prefixes that are referenced but don't have definitions.
        """
        undefined_prefixes = self.referenced_prefixes - self.defined_prefixes

        if not undefined_prefixes:
            return

        self.add_line("/* Stub DOCFORMATs for undefined PREFIX cases */")
        self.add_line("")

        for prefix in sorted(undefined_prefixes):
            docformat_name = f"DF_{prefix}"
            self.add_line(f"DOCFORMAT {docformat_name};")
            self.indent()
            self.add_line(f"/* {prefix} Prefix not found or commented out */")
            self.add_line("/* Add implementation here */")
            self.dedent()
            self.add_line("ENDFORMAT;")
            self.add_line("")

        logger.info(f"Generated {len(undefined_prefixes)} stub DOCFORMATs for undefined prefixes: {', '.join(sorted(undefined_prefixes))}")
        self.add_line("/* END OF STUB DOCFORMATS */")
        self.add_line("")

    def _convert_case_commands(self, commands: List[XeroxCommand], start_font: str = "ARIAL08",
                               start_color: str = None,
                               suppress_leading_pagebrk: bool = False, existing_outline: bool = False,
                               anchor_context: str = "root", case_value: str = None):
        """Convert VIPP commands within a case block to DFA."""
        self.indent()
        # Treat each DOCFORMAT case as an independent flow context.
        self.last_command_type = None

        # Track current position for OUTLINE generation
        current_x = 20  # Default x position in MM
        current_y = 40  # Default y position in MM
        current_linesp = 4.0  # Track active line spacing for NL without explicit value
        current_font = start_font  # Inherit font from caller (e.g. parent IF block)
        current_color = start_color

        # Track whether position was explicitly set (to distinguish from residual values)
        x_was_explicitly_set = False
        y_was_explicitly_set = False
        y_is_next_line = False  # Track if next OUTPUT should use NEXT (after NL)

        # Check if we need OUTLINE wrapper (for OUTPUT/TEXT/graphics commands)
        has_output = self._has_output_commands(commands)
        outline_opened = existing_outline
        outline_opened_here = False

        # Cases with no explicit absolute anchors should continue the current cursor
        # flow instead of restarting from LEFT/NEXT.
        def _flatten_cmds(cmds):
            for c in cmds:
                yield c
                if c.children:
                    yield from _flatten_cmds(c.children)
        has_absolute_anchor = any(
            c.name in ('MOVETO', 'SETLKF', 'SETPAGEDEF')
            for c in _flatten_cmds(commands)
        )
        # Only top-level reset commands should break continuation classification.
        # Nested FRLEFT IF blocks can contain PAGEBRK without meaning that the
        # case itself starts from a reset anchor.
        has_reset_anchor = any(
            c.name in ('PAGEBRK', 'NEWFRONT', 'NEWBACK')
            for c in commands
        )
        case_is_continuation = (not has_absolute_anchor and not has_reset_anchor)
        # Root-level DBM cases should keep legacy flow behavior (LEFT NEXT) unless
        # explicitly anchored. Nested IF bodies without anchors should continue in-place
        # (LEFT SAME) to avoid artificial Y resets inside conditional blocks.
        if has_absolute_anchor:
            outline_start_pos = "LEFT NEXT"
        elif anchor_context == "nested":
            outline_start_pos = "LEFT SAME"
        else:
            outline_start_pos = "LEFT NEXT"

        def _close_outline_and_store_textflow():
            nonlocal outline_opened, outline_opened_here
            if outline_opened:
                self.dedent()
                self.add_line("ENDIO;")
                outline_opened = False
                outline_opened_here = False
                self.add_line("TFLOW_Y = $SL_CURRY;")

        # Track consumed commands for lookahead processing (IF/ELSE/ENDIF)
        i = 0
        prev_cmd_was_pagebrk = False  # Track if previous command was PAGEBRK (to suppress NEWFRONT/NEWBACK double break)
        leading_pagebrk_suppressed = False  # For suppress_leading_pagebrk: only suppress the FIRST PAGEBRK
        last_cache_cmd = None  # Track preceding CACHE command for CACHE+SCALL image patterns
        while i < len(commands):
            cmd = commands[i]

            # Map command name if possible
            dfa_cmd = self.COMMAND_MAPPINGS.get(cmd.name, cmd.name)

            # Reset PAGEBRK tracking for non-PAGEBRK commands
            # (PAGEBRK handler will set this to True; NEWFRONT/NEWBACK handlers will read it)
            if cmd.name not in ('PAGEBRK', 'NEWFRONT', 'NEWBACK'):
                prev_cmd_was_pagebrk = False

            # Skip comments or unsupported commands
            if cmd.name.startswith('%') or dfa_cmd.startswith('/'):
                i += 1
                continue

            # Handle SETVAR -> direct assignment (DFA uses var = value; not ASSIGN)
            # Fix 6: Variable name (param[0]) is ALWAYS LHS, value (param[1]) ALWAYS RHS
            if cmd.name == 'SETVAR':
                if len(cmd.parameters) >= 2:
                    var_name = self._sanitize_dfa_name(cmd.parameters[0].lstrip('/'))  # LHS: sanitized variable name
                    var_value = cmd.parameters[1]              # RHS: always the value/expression

                    # Fix parameter order if they're swapped (parsing artifact)
                    # If var_name is an operator, parameters are in wrong order
                    if var_name in ('++', '--', '+', '-', '*', '/'):
                        # Swap parameters: value and var_name are reversed
                        var_name, var_value = self._sanitize_dfa_name(var_value.lstrip('/')), var_name
                        logger.debug(f"Swapped SETVAR parameters: {cmd.parameters} -> [{var_name}, {var_value}]")

                    # Detect malformed SETVAR patterns and comment them out
                    malformed_keywords = ['IF', 'ELSE', 'THEN',
                                         'ENDIF', 'PAGEBRK', '{', '}', '%']
                    # Note: Removed eq/ne/gt/lt/ge/le, CPCOUNT, GETITEM - can appear in valid expressions
                    is_malformed = (
                        var_value == '-' or  # Just a dash
                        var_value == '=' or  # Just an equals sign
                        var_name.replace('.', '').replace('-', '').isdigit() or  # Numeric-only LHS (stack contamination artifact)
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
                        i += 1
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
                            var_value = self._sanitize_dfa_name(var_value.lstrip('/'))
                        elif var_value in ('true', 'false'):
                            # Boolean literals: DFA uses 1/0
                            var_value = '1' if var_value == 'true' else '0'
                        elif var_value.startswith('(') and var_value.endswith(')'):
                            var_value = f"'{var_value[1:-1]}'"
                        self.add_line(f"{var_name} = {var_value};")
                i += 1
                continue

            # Handle SETFONT - store font for next OUTPUT
            if cmd.name == 'SETFONT':
                if cmd.parameters:
                    current_font = cmd.parameters[0].upper()
                i += 1
                continue

            # Handle SETCOLOR / standalone color alias tokens
            if cmd.name == 'SETCOLOR':
                if cmd.parameters:
                    color_alias = str(cmd.parameters[0]).upper().lstrip('/')
                    current_color = self.color_mappings.get(color_alias, color_alias)
                i += 1
                continue

            # Handle standalone font/color shortcut tokens from VIPP streams
            # (e.g. FI, FK, W, B) that set style state for subsequent output.
            cmd_upper = cmd.name.upper()
            if cmd_upper in self.font_mappings:
                current_font = self.font_mappings[cmd_upper]
                i += 1
                continue
            if cmd_upper in self.color_mappings:
                current_color = self.color_mappings[cmd_upper]
                i += 1
                continue

            # Open OUTLINE before first output command
            # All OUTPUT, TEXT, and graphics commands must be inside OUTLINE block
            if has_output and not outline_opened and cmd.name in ('NL', 'SH', 'SHL', 'SHR', 'SHr', 'SHC', 'SHc', 'SHP', 'SHp', 'DRAWB', 'SCALL', 'ICALL', 'MOVEHR'):
                # Note: SETLSP intentionally omitted — it is a global command valid
                # at DOCFORMAT level and should NOT force an OUTLINE block to open.
                # Keeping SETLSP outside OUTLINE ensures subsequent SETVAR commands
                # (from SETFORM, ++ operators etc.) are also emitted at DOCFORMAT level,
                # not trapped inside the OUTLINE where they are invalid.

                self.add_line("")
                use_textflow_carry_pos = (
                    case_is_continuation
                    and not existing_outline
                    and case_value is not None
                    and case_value.upper() in self.dbm_textflow_cases
                )
                if use_textflow_carry_pos:
                    self.add_line("IF ISTRUE(TFLOW_Y == '');")
                    self.add_line("THEN;")
                    self.indent()
                    self.add_line("TFLOW_Y = $SL_CURRY;")
                    self.dedent()
                    self.add_line("ENDIF;")
                self.add_line("OUTLINE")
                self.indent()
                if x_was_explicitly_set and y_was_explicitly_set:
                    x_expr = f"({current_x} MM-$MR_LEFT)"
                    y_expr = f"({current_y} MM-$MR_TOP)"
                    self.add_line("/* OUTLINE_ANCHOR_V2: ABS_XY */")
                    self.add_line(f"POSITION {x_expr} {y_expr}")
                elif x_was_explicitly_set:
                    x_expr = f"({current_x} MM-$MR_LEFT)"
                    self.add_line("/* OUTLINE_ANCHOR_V2: ABS_X_SAME_Y */")
                    self.add_line(f"POSITION {x_expr} SAME")
                else:
                    if use_textflow_carry_pos:
                        self.add_line("/* OUTLINE_ANCHOR_V2: TEXTFLOW_CARRY */")
                        self.add_line("POSITION LEFT (TFLOW_Y)")
                    else:
                        marker = (
                            "LEFT_SAME_FALLBACK"
                            if outline_start_pos == "LEFT SAME"
                            else "LEFT_NEXT_FALLBACK"
                        )
                        self.add_line(f"/* OUTLINE_ANCHOR_V2: {marker} */")
                        self.add_line(f"POSITION {outline_start_pos}")
                self.add_line("DIRECTION ACROSS;")
                self.add_line("")
                outline_opened = True
                outline_opened_here = True
                # Reset box anchor flag for new OUTLINE block
                self.should_set_box_anchor = True
                # After opening OUTLINE with its anchor, reset position flags so the first
                # OUTPUT/TEXT inside the OUTLINE uses SAME (not a re-emitted absolute coord).
                # Without this, MOVETO coords consumed as the OUTLINE anchor are re-emitted
                # inside the OUTLINE, doubling the X offset (PPDE7038W negative width).
                x_was_explicitly_set = False
                y_was_explicitly_set = False

            # Handle NL (newline) - generate OUTPUT '' POSITION SAME NEXT
            if cmd.name == 'NL':
                y_position = 'NEXT'
                spacing_delta = None

                # If NL has a spacing parameter
                if cmd.parameters:
                    try:
                        spacing_val = float(cmd.parameters[0])
                        spacing_delta = spacing_val
                        if spacing_val < 0:
                            distance_up = abs(spacing_val)
                            # If the very first vertical move in a case is negative,
                            # DFA can underflow because the case starts at LEFT NEXT.
                            # Clamp to NEXT for stability; subsequent relative NL
                            # movements keep original SAME- semantics.
                            if self.last_command_type is None:
                                y_position = 'NEXT'
                            elif self.last_command_type == 'TEXT':
                                # After TEXT blocks, anchor relative moves to LASTMAX
                                # (the text extent), not SAME baseline.
                                y_position = f"LASTMAX-{distance_up} MM"
                            else:
                                # Negative NL: move up by N mm from current position
                                # Example: -04 NL becomes SAME-4.0 MM
                                y_position = f"SAME-{distance_up} MM"
                        else:
                            # Positive NL: move down by N mm from current position
                            # Example: 0.3 NL becomes SAME+0.3 MM
                            if self.last_command_type == 'TEXT':
                                y_position = f"LASTMAX+{spacing_val} MM"
                            else:
                                y_position = f"SAME+{spacing_val} MM"
                    except ValueError:
                        pass
                else:
                    spacing_delta = current_linesp

                # Generate the newline as OUTPUT with POSITION SAME (NEXT or SAME+/-X MM)
                self.add_line("OUTPUT ''")
                self.add_line(f"    FONT {current_font} NORMAL")
                self.add_line(f"    {self._format_position('SAME', y_position)};")

                # Maintain an approximate flow cursor for subsequent SCALL anchors.
                if spacing_delta is not None:
                    current_y += spacing_delta

                # After NL, next OUTPUT should use NEXT (advance to next line)
                y_was_explicitly_set = False
                y_is_next_line = True
                self.last_command_type = 'NL'
                i += 1
                continue

            # Handle SETFORM: .ps form files → CREATEOBJECT PDF; .frm → USE FORMAT EXTERNAL
            if cmd.name == 'SETFORM':
                if cmd.parameters:
                    import os as _os
                    form_raw = cmd.parameters[0].strip('()')
                    form_ext = _os.path.splitext(form_raw)[1].lower()
                    if form_ext == '.ps':
                        pdf_name = _os.path.splitext(form_raw)[0] + '.pdf'
                        self.add_line("CREATEOBJECT IOBDLL(IOBDEFS)")
                        self.indent()
                        self.add_line("POSITION 0 0")
                        self.add_line("PARAMETERS")
                        self.indent()
                        self.add_line(f"('FILENAME'='{pdf_name}')")
                        self.add_line("('OBJECTTYPE'='1')")
                        self.add_line("('OTHERTYPES'='PDF');")
                        self.dedent()
                        self.dedent()
                    else:
                        form_stem = ''.join(
                            c for c in _os.path.splitext(form_raw)[0].upper()
                            if c.isalnum() or c == '_'
                        )
                        # Apply collision-avoidance: if the FRM base name matches the
                        # DBM base name, the FRM file was written with an 'F' suffix
                        # (e.g. UT00060F.dfa). VAR_CURFORM must use the suffixed name
                        # so that USE FORMAT REFERENCE(VAR_CURFORM) EXTERNAL resolves
                        # to the correct file.
                        _dbm_docdef = ''.join(
                            c for c in _os.path.splitext(_os.path.basename(self.dbm.filename))[0]
                            if c.isalnum()
                        )
                        if form_stem == _dbm_docdef:
                            form_stem = form_stem + 'F'
                        # SETFORM in VIPP marks the page background overlay for the
                        # current page — it does NOT immediately render content.
                        # In DFA, running USE FORMAT EXTERNAL in the DOCFORMAT body
                        # renders the FRM's OUTLINE immediately, causing all FRM content
                        # (from multiple PREFIX records) to pile up on the same physical page.
                        #
                        # Correct approach: store the form name in VAR_CURFORM variable.
                        # The PRINTFOOTER reads VAR_CURFORM and calls
                        #   USE FORMAT REFERENCE(VAR_CURFORM) EXTERNAL;
                        # once per physical page, selecting the right background.
                        self.add_line(f"VAR_CURFORM = '{form_stem}';")
                i += 1
                continue

            # Handle SETLSP (line spacing) - convert to SETUNITS LINESP
            if cmd.name == 'SETLSP':
                if cmd.parameters:
                    spacing_val = cmd.parameters[0]
                    self.add_line(f"SETUNITS LINESP {spacing_val} MM;")
                    try:
                        current_linesp = float(spacing_val)
                    except (TypeError, ValueError):
                        pass
                else:
                    # Default to AUTO (uses font's line spacing)
                    self.add_line("SETUNITS LINESP AUTO;")
                i += 1
                continue

            # Handle if/else conditions
            if dfa_cmd == 'IF':
                # FRLEFT IF blocks (page overflow checks) must be emitted at DOCFORMAT
                # level — not inside an OUTLINE block — because their bodies contain
                # USE LOGICALPAGE and VAR assignments which are invalid inside OUTLINE.
                # Detect FRLEFT by checking the IF command's parameters.
                is_frleft_if = any('FRLEFT' in str(p) for p in cmd.parameters)
                if is_frleft_if and outline_opened:
                    # Close the OUTLINE before emitting the page-break IF block
                    _close_outline_and_store_textflow()

                # Convert the IF command with lookahead for ELSE/ENDIF
                # Pass current_font so nested NL commands use the active font, not ARIAL08
                consumed = self._convert_if_command(
                    cmd,
                    commands,
                    i,
                    current_font,
                    current_color,
                    in_outline=outline_opened,
                    anchor_context=anchor_context,
                    case_value=case_value
                )
                # Skip the consumed commands (ELSE, ENDIF, and their bodies)
                i += consumed
                continue

            # ENDIF and ELSE are now handled within _convert_if_command
            # Skip them if they appear here (shouldn't happen with proper lookahead)
            if cmd.name in ('ENDIF', 'ELSE'):
                i += 1
                continue

            # Handle increment/decrement operators
            if cmd.name == '++':
                # /var ++ -> VAR = VAR + 1;
                if cmd.parameters:
                    var_name = cmd.parameters[0].lstrip('/')
                    self.add_line(f"{var_name} = {var_name} + 1;")
                i += 1
                continue

            if cmd.name == '--':
                # /var -- -> VAR = VAR - 1;
                if cmd.parameters:
                    var_name = cmd.parameters[0].lstrip('/')
                    self.add_line(f"{var_name} = {var_name} - 1;")
                i += 1
                continue

            # Handle for loops
            if dfa_cmd == 'FOR':
                self._convert_for_command(cmd)
                i += 1
                continue

            if cmd.name == 'ENDFOR':
                self.add_line("ENDFOR;")
                i += 1
                continue

            # Handle output commands (SH, SHL, SHR, SHC, SHP)
            if dfa_cmd == 'OUTPUT':
                self._convert_output_command_dfa(cmd, current_x, current_y, current_font,
                                                 x_was_explicitly_set, y_was_explicitly_set, y_is_next_line,
                                                 current_color)
                # After output, position becomes implicit and next output should advance to next line
                x_was_explicitly_set = False
                y_was_explicitly_set = False
                y_is_next_line = True
                i += 1
                continue

            # Handle positioning commands - store position for next OUTPUT
            if cmd.name == 'MOVETO':
                if len(cmd.parameters) >= 2:
                    try:
                        if outline_opened_here:
                            _close_outline_and_store_textflow()
                            self.add_line("")
                            self.should_set_box_anchor = True
                        current_x = float(cmd.parameters[0])
                        current_y = float(cmd.parameters[1])
                        x_was_explicitly_set = True
                        y_was_explicitly_set = True
                        y_is_next_line = False  # Explicit Y position overrides NEXT
                    except ValueError:
                        pass
                i += 1
                continue

            if cmd.name in ('MOVEH', 'MOVEHR'):
                if cmd.parameters:
                    try:
                        current_x = float(cmd.parameters[0])
                        x_was_explicitly_set = True
                        y_was_explicitly_set = False  # Y becomes implicit (use SAME)
                        y_is_next_line = False  # MOVEH/MOVEHR resets next-line flag, Y should be SAME
                    except ValueError:
                        pass
                i += 1
                continue

            # Handle box drawing
            if dfa_cmd == 'BOX':
                self._convert_box_command_dfa(cmd)
                i += 1
                continue

            # Handle CACHE command — store for the following SCALL
            if cmd.name == 'CACHE':
                last_cache_cmd = cmd
                i += 1
                continue

            # Handle segment/image calls
            if cmd.name == 'SCALL' or cmd.name == 'ICALL':
                if last_cache_cmd is not None:
                    # CACHE+SCALL pattern (e.g. "(OCBC.eps) CACHE 0.38 SCALL"):
                    # filename is in CACHE params, scale is in SCALL params.
                    # Delegate to _convert_frm_segment which handles EPS BoundingBox lookup,
                    # IMG_W_MM calculation, and XOBJECTAREASIZE emission correctly.
                    self._convert_frm_segment(cmd, current_x, current_y, None,
                                              last_cache_cmd,
                                              x_was_explicitly_set, y_was_explicitly_set,
                                              current_font)
                    last_cache_cmd = None  # Clear after use
                else:
                    self._convert_resource_command_dfa(
                        cmd,
                        current_x,
                        current_y,
                        current_font=current_font,
                        x_was_set=x_was_explicitly_set,
                        y_was_set=y_was_explicitly_set
                    )
                i += 1
                continue

            # Handle SUBSTR (GETINTV in VIPP)
            # VIPP: /result source start length GETINTV SETVAR
            # DFA: result = SUBSTR(source, start+1, length, '');
            if dfa_cmd == 'SUBSTR':
                if len(cmd.parameters) >= 4:
                    # GETINTV now pops 4 parameters: /result, source, start, length
                    result_param = cmd.parameters[0]
                    source_var = cmd.parameters[1]
                    start_param = cmd.parameters[2]
                    
                    # Try to parse start as integer, or use as-is if it's a variable/expression
                    try:
                        start = int(start_param)
                        # XEROX uses 0-based indexing, DFA uses 1-based
                        dfa_start = start + 1
                    except ValueError:
                        # If start is not an integer, it might be a variable or expression
                        # Use it as-is and add 1 in the expression
                        dfa_start = f"{start_param} + 1"
                        start = 0  # placeholder
                    length = cmd.parameters[3]

                    # Extract result variable name (remove leading / if present)
                    result_var = result_param[1:] if result_param.startswith('/') else result_param

                    # Note: dfa_start already set above in try/except
                    if 'dfa_start' not in dir():
                        dfa_start = start + 1
                    self.add_line(f"{result_var} = SUBSTR({source_var}, {dfa_start}, {length}, '');")
                i += 1
                continue

            # Handle CLIP/ENDCLIP - not supported in DFA
            if cmd.name in ('CLIP', 'ENDCLIP'):
                self.add_line("/* Note: DFA does not support CLIP/ENDCLIP. */")
                self.add_line("/* Use MARGIN, SHEET/LOGICALPAGE dimensions, WIDTH on TEXT, or image size params instead */")
                i += 1
                continue

            # Skip SETPAGEDEF silently - already handled at docformat level
            if cmd.name == 'SETPAGEDEF':
                i += 1
                continue

            # Handle SETLKF - position cursor at the data frame origin
            # SETLKF defines the printable area where subsequent data goes.
            # Emit a cursor-positioning OUTLINE so the next OUTLINE's NEXT/SAME
            # starts from the correct Y position on the page.
            if cmd.name == 'SETLKF':
                if cmd.parameters:
                    import re as _re
                    values = _re.findall(r'(\d+(?:\.\d+)?)', str(cmd.parameters[0]))
                    if len(values) >= 2:
                        frame_x = float(values[0])
                        frame_y = float(values[1])
                        # Close any open OUTLINE first
                        if outline_opened:
                            _close_outline_and_store_textflow()
                        # Emit cursor-positioning OUTLINE at frame origin
                        self.add_line(f"/* SETLKF: data area at ({frame_x}, {frame_y}) */")
                        self.add_line("OUTLINE")
                        self.indent()
                        self.add_line(f"POSITION ({frame_x} MM-$MR_LEFT) ({frame_y} MM-$MR_TOP);")
                        self.dedent()
                        self.add_line("ENDIO;")
                i += 1
                continue

            # Handle page break commands
            if cmd.name == 'PAGEBRK':
                # suppress_leading_pagebrk: In VIPP DBM mode, the first PREFIX case (e.g. MR)
                # starts with PAGEBRK NEWFRONT to separate documents. In DFA, document
                # boundaries (ENDGROUP/ENDDOCUMENT) already handle page separation, so the
                # first PAGEBRK in the first DOCFORMAT should be suppressed to avoid creating
                # a blank page 1.
                if suppress_leading_pagebrk and not leading_pagebrk_suppressed:
                    leading_pagebrk_suppressed = True
                    prev_cmd_was_pagebrk = True  # So following NEWFRONT is also suppressed
                    i += 1
                    continue
                # PAGEBRK → USE LOGICALPAGE NEXT (unconditional page break).
                # Must be at DOCFORMAT level, not inside an OUTLINE block.
                # Close any open OUTLINE first so the page break is emitted at the right level.
                # NOTE: "SIDE FRONT" is NOT valid in USE LOGICALPAGE — it is only valid
                # inside FORMATGROUP LOGICALPAGE definitions. USE LOGICALPAGE only takes NEXT/SAME/etc.
                if outline_opened:
                    _close_outline_and_store_textflow()
                self.add_line("USE LOGICALPAGE NEXT;")
                self.add_line("TFLOW_Y = $SL_CURRY;")
                prev_cmd_was_pagebrk = True
                i += 1
                continue

            if cmd.name == 'NEWFRONT':
                # NEWFRONT after PAGEBRK: in VIPP "PAGEBRK NEWFRONT" is ONE operation — the
                # PAGEBRK already emitted USE LOGICALPAGE NEXT, so NEWFRONT is suppressed.
                # NEWFRONT standalone (no preceding PAGEBRK): force a new front page.
                if not prev_cmd_was_pagebrk:
                    if outline_opened:
                        _close_outline_and_store_textflow()
                    self.add_line("USE LOGICALPAGE NEXT;")
                self.add_line("TFLOW_Y = $SL_CURRY;")
                # else: PAGEBRK already emitted the page break — suppress this one
                prev_cmd_was_pagebrk = False
                i += 1
                continue

            if cmd.name == 'NEWBACK':
                # Same logic as NEWFRONT — suppress if preceded by PAGEBRK.
                if not prev_cmd_was_pagebrk:
                    if outline_opened:
                        _close_outline_and_store_textflow()
                    self.add_line("USE LOGICALPAGE NEXT;")
                self.add_line("TFLOW_Y = $SL_CURRY;")
                prev_cmd_was_pagebrk = False
                i += 1
                continue

            if cmd.name == 'NEWFRAME':
                # NEWFRAME is not valid DFA — emit comment stub
                self.add_line("/* VIPP command not supported: NEWFRAME */")
                i += 1
                continue

            if cmd.name == 'ADD':
                self._convert_add_command(cmd)
                i += 1
                continue

            if cmd.name == 'GETITEM':
                self._convert_getitem_command(cmd)
                i += 1
                continue

            if cmd.name == 'BOOKMARK':
                # Emit bookmark indices at DOCFORMAT scope (outside OUTLINE).
                if outline_opened:
                    _close_outline_and_store_textflow()
                self._convert_bookmark_command(cmd)
                i += 1
                continue

            if cmd.name == 'SETPAGENUMBER':
                # Extracted for footer generation; keep trace for auditability.
                if outline_opened:
                    _close_outline_and_store_textflow()
                self._convert_pagenumber_command(cmd)
                i += 1
                continue

            # Skip other unsupported VIPP commands with comment
            if cmd.name in ('CACHE',
                          'PAGEDEF',
                          'CPCOUNT'):
                self.add_line(f"/* VIPP command not directly supported: {cmd.name} */")
                i += 1
                continue

            # Increment counter for any unhandled commands (shouldn't reach here)
            i += 1

        # Close OUTLINE only if this invocation opened it.
        if outline_opened and outline_opened_here:
            _close_outline_and_store_textflow()

        self.dedent()
    
    def _convert_if_command(self, cmd: XeroxCommand, commands: List[XeroxCommand] = None,
                            idx: int = -1, current_font: str = "ARIAL08",
                            current_color: str = None, in_outline: bool = False,
                            anchor_context: str = "root", case_value: str = None):
        """
        Convert an IF command to DFA, handling ELSE and ENDIF at the same nesting level.

        Args:
            cmd: The IF command to convert
            commands: Full list of commands (for lookahead to find ELSE/ENDIF)
            idx: Current index of the IF command in the commands list
            current_font: Active font at the call site, propagated into child blocks
            current_color: Active color at the call site, propagated into child blocks

        Returns:
            Number of commands consumed (including IF, ELSE, ENDIF, and their bodies)
        """
        # Split parameters if they're combined into a single string.
        # Use _split_respecting_parens so that multi-word VIPP string literals like
        # (monthly investment plan) are kept intact as one token.
        split_params = []
        for param in cmd.parameters:
            if ' ' in param:
                split_params.extend(self._split_respecting_parens(param))
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
                    var_name = self._sanitize_dfa_name(clean_params[-1].lstrip('/'))
                    self.add_line(f"{var_name} = {var_name} + 1;")
                    clean_params.pop()  # Remove the variable from condition
            elif param == '--':
                # Previous param should be the variable to decrement
                if clean_params:
                    var_name = self._sanitize_dfa_name(clean_params[-1].lstrip('/'))
                    self.add_line(f"{var_name} = {var_name} - 1;")
                    clean_params.pop()  # Remove the variable from condition
            else:
                clean_params.append(param)
            i += 1

        # Check for FRLEFT condition BEFORE converting comparison operators
        # (because we need to see 'lt' not '<')
        frleft_condition, is_frleft = self._convert_frleft_condition(clean_params)

        if is_frleft:
            # FRLEFT + PAGEBRK = section transition → unconditional page break.
            # In complex DBM architectures (like CASIO), FRM overlays render in
            # PRINTFOOTER (print pass) while the FRLEFT check evaluates during the
            # format pass.  The FRM overlay content fills most of the page, but
            # $SL_LMAXY during formatting only reflects the dynamic data output —
            # far less than the full page.  The FRLEFT condition therefore never
            # fires, so we emit the body unconditionally.
            # FRLEFT + NEWFRAME (without PAGEBRK) remains conditional — those are
            # genuine overflow guards for dynamic content like transaction details.
            has_pagebrk = cmd.children and any(c.name == 'PAGEBRK' for c in cmd.children)
            if has_pagebrk:
                self.add_line(f"/* FRLEFT section transition (unconditional) */")
                self._convert_case_commands(
                    cmd.children,
                    current_font,
                    current_color,
                    existing_outline=in_outline,
                    anchor_context="nested",
                    case_value=case_value
                )
                # Still need to consume ELSE/ENDIF siblings if present
                consumed = 1
                if commands is not None and idx >= 0:
                    nesting_level = 0
                    for j in range(idx + 1, len(commands)):
                        cmd_name = commands[j].name
                        if cmd_name == 'IF':
                            nesting_level += 1
                        elif cmd_name == 'ENDIF':
                            if nesting_level == 0:
                                consumed += (j - idx)
                                break
                            else:
                                nesting_level -= 1
                        elif cmd_name == 'ELSE' and nesting_level == 0:
                            # Skip ELSE body too
                            pass
                return consumed

            # Use FRLEFT condition directly (already in DFA format)
            condition = frleft_condition
            needs_istrue = True
        else:
            # Convert comparison operators (eq -> ==, ne -> <>, etc.)
            converted_ops = self._convert_comparison_operators(clean_params)
            condition = " ".join(self._convert_params(converted_ops))
            # Check if condition needs ISTRUE() wrapper:
            # - Expressions with comparison operators: IF ISTRUE(X == Y)
            # - Single bare variable (boolean test): IF ISTRUE(VAR_brkctl)
            #   DFA requires ISTRUE() for variable truthiness tests; bare IF VAR causes PPDE7006W
            has_comparison_op = any(op in condition for op in ['==', '<>', '>', '<', '>=', '<='])
            is_bare_variable = (
                len(converted_ops) == 1
                and re.match(r'^[A-Za-z_]\w*$', converted_ops[0])
            )
            needs_istrue = has_comparison_op or is_bare_variable

        # Detect always-true self-comparison wrapping PAGEBRK in a PREFIX case handler.
        # Two patterns:
        #   1. `IF PREFIX (STMTTP) eq { PAGEBRK }` — direct PREFIX comparison
        #   2. `IF VAR_DTL (DTL) eq { PAGEBRK }` — variable set to PREFIX at top of case
        # Both are always-true because the case handler is only entered when PREFIX matches.
        # In DFA this translates to an unconditional USE LOGICALPAGE NEXT, creating a blank page.
        # Replace with a proper page overflow check (same pattern as FRLEFT conversion).
        if not is_frleft and cmd.children:
            has_pagebrk_child = any(c.name == 'PAGEBRK' for c in cmd.children)
            # Catch both `PREFIX == 'X'` and `VAR_<name> == 'X'` patterns
            has_prefix_cmp = (('PREFIX' in condition or 'VAR_' in condition)
                              and '==' in condition)
            if has_prefix_cmp and has_pagebrk_child:
                condition = '$SL_LMAXY>$LP_HEIGHT-MM(20)'
                needs_istrue = True

        # Don't output empty conditions - just output IF with THEN
        if condition.strip():
            if needs_istrue:
                self.add_line(f"IF ISTRUE({condition});")
            else:
                self.add_line(f"IF {condition};")
        else:
            self.add_line("IF 1;")  # Default true condition if empty

        self.add_line("THEN;")

        # Initialize consumed commands counter (starts at 1 for the IF itself)
        consumed = 1

        # FRLEFT page-break IF blocks:
        # In VIPP, `IF FRLEFT N lt { PAGEBRK NEWFRONT (FRM.FRM) SETFORM }` means
        # "if less than N mm left on page, break to new front page and set FRM background."
        # Two cases:
        #   (a) Children contain PAGEBRK → _convert_case_commands will emit USE LOGICALPAGE NEXT;
        #       Do NOT emit pre-emptively (would double the break).
        #   (b) Children contain NEWFRAME (but not PAGEBRK) → NEWFRAME is "advance to next frame"
        #       in VIPP = a page overflow mechanism. Emit USE LOGICALPAGE NEXT; here since
        #       _convert_case_commands emits a comment stub for NEWFRAME.
        # NOTE: "SIDE FRONT" is NOT valid in USE LOGICALPAGE commands — only in definitions.
        if is_frleft and cmd.children:
            has_pagebrk = any(c.name == 'PAGEBRK' for c in cmd.children)
            has_newframe = any(c.name == 'NEWFRAME' for c in cmd.children)
            if has_newframe and not has_pagebrk:
                # NEWFRAME-only overflow — emit page break here; _convert_case_commands will
                # emit the comment stub for NEWFRAME itself.
                self.indent()
                self.add_line("/* Page overflow: NEWFRAME → USE LOGICALPAGE NEXT */")
                self.add_line("USE LOGICALPAGE NEXT;")
                self.dedent()
            # else: PAGEBRK children will emit USE LOGICALPAGE NEXT; — no pre-emptive emission needed

        # Process children (IF body) if present
        if cmd.children:
            self._convert_case_commands(
                cmd.children,
                current_font,
                current_color,
                existing_outline=in_outline,
                anchor_context="nested",
                case_value=case_value
            )
            # IF blocks with children still need lookahead for ELSE at parent level
            # In VIPP: IF cond { then_block } ELSE { else_block } ENDIF
            # Parser creates children for {block} but ELSE/ENDIF remain as siblings
            if commands is not None and idx >= 0:
                nesting_level = 0
                else_idx = -1
                endif_idx = -1
                for j in range(idx + 1, len(commands)):
                    cmd_name = commands[j].name
                    if cmd_name == 'IF':
                        nesting_level += 1
                    elif cmd_name == 'ENDIF':
                        if nesting_level == 0:
                            endif_idx = j
                            break
                        else:
                            nesting_level -= 1
                    elif cmd_name == 'ELSE' and nesting_level == 0:
                        else_idx = j

                if else_idx >= 0:
                    self.add_line("ELSE;")
                    else_cmd = commands[else_idx]
                    if else_cmd.children:
                        self._convert_case_commands(
                            else_cmd.children,
                            current_font,
                            current_color,
                            existing_outline=in_outline,
                            anchor_context="nested",
                            case_value=case_value
                        )
                    elif endif_idx > else_idx + 1:
                        self.indent()
                        else_commands = commands[else_idx + 1:endif_idx]
                        self._process_command_block(else_commands)
                        self.dedent()

                self.add_line("ENDIF;")
                # Total consumed = all commands from IF through ENDIF inclusive
                if endif_idx >= 0:
                    consumed = endif_idx - idx + 1
                elif else_idx >= 0:
                    consumed = else_idx - idx + 1
                return consumed

            self.add_line("ENDIF;")
            return consumed

        # If no children, we need to look ahead in the flat commands list
        # to find THEN block, ELSE (optional), and ENDIF at the same nesting level
        if commands is None or idx < 0:
            # No lookahead available - just close the IF
            self.add_line("ENDIF;")
            return consumed

        # Look ahead to find matching ELSE and ENDIF at same nesting level
        nesting_level = 0
        else_idx = -1
        endif_idx = -1

        for j in range(idx + 1, len(commands)):
            cmd_name = commands[j].name

            # Track nesting level
            if cmd_name == 'IF':
                nesting_level += 1
            elif cmd_name == 'ENDIF':
                if nesting_level == 0:
                    # Found matching ENDIF at our level
                    endif_idx = j
                    break
                else:
                    nesting_level -= 1
            elif cmd_name == 'ELSE' and nesting_level == 0:
                # Found matching ELSE at our level
                else_idx = j

        # Process THEN block commands (from idx+1 to else_idx or endif_idx)
        self.indent()
        then_end = else_idx if else_idx >= 0 else endif_idx
        if then_end > idx + 1:
            then_commands = commands[idx + 1:then_end]
            # Process commands with nested IF handling
            consumed += self._process_command_block(then_commands)
        self.dedent()

        # Process ELSE block if present
        if else_idx >= 0:
            self.add_line("ELSE;")
            consumed += 1  # Count the ELSE command

            self.indent()
            if endif_idx > else_idx + 1:
                else_commands = commands[else_idx + 1:endif_idx]
                # Process commands with nested IF handling
                consumed += self._process_command_block(else_commands)
            self.dedent()

        # Close the IF block
        self.add_line("ENDIF;")
        if endif_idx >= 0:
            consumed += 1  # Count the ENDIF command

        return consumed

    def _process_command_block(self, commands: List[XeroxCommand]) -> int:
        """
        Process a block of commands (e.g., THEN or ELSE block), handling nested IFs.

        Args:
            commands: List of commands to process

        Returns:
            Number of commands processed (for consumption tracking)
        """
        i = 0
        processed = 0
        while i < len(commands):
            cmd = commands[i]
            dfa_cmd = self.COMMAND_MAPPINGS.get(cmd.name, cmd.name)

            # Handle nested IF with lookahead
            if dfa_cmd == 'IF':
                consumed = self._convert_if_command(cmd, commands, i)
                i += consumed
                processed += consumed
            else:
                # Process single command
                self._process_single_command(cmd)
                i += 1
                processed += 1

        return processed

    def _process_single_command(self, cmd: XeroxCommand):
        """
        Process a single command within an IF/ELSE block.
        This is a simplified version of the main command loop in _convert_case_commands.
        Note: Nested IF/ELSE/ENDIF are handled by lookahead in _convert_if_command,
        so they won't appear here when processing flat command lists.
        """
        # Map command name if possible
        dfa_cmd = self.COMMAND_MAPPINGS.get(cmd.name, cmd.name)

        # Skip comments or unsupported commands
        if cmd.name.startswith('%') or dfa_cmd.startswith('/'):
            return

        # Handle SETVAR -> direct assignment
        if cmd.name == 'SETVAR':
            if len(cmd.parameters) >= 2:
                var_name = self._sanitize_dfa_name(cmd.parameters[0].lstrip('/'))
                var_value = cmd.parameters[1]

                # Fix parameter order if they're swapped
                if var_name in ('++', '--', '+', '-', '*', '/'):
                    var_name, var_value = self._sanitize_dfa_name(var_value.lstrip('/')), var_name

                # Detect malformed SETVAR patterns
                malformed_keywords = ['IF', 'ELSE', 'THEN', 'ENDIF', 'PAGEBRK', '{', '}', '%']
                is_malformed = (
                    var_value == '-' or
                    var_value == '=' or
                    any(keyword in str(cmd.parameters) for keyword in malformed_keywords) or
                    any(keyword in var_name for keyword in malformed_keywords)
                )

                if is_malformed:
                    assignment = f"{var_name} = {var_value};"
                    self.add_line(f"/* {assignment} */")
                    return

                # Handle increment/decrement operators
                if var_value == '++':
                    self.add_line(f"{var_name} = {var_name} + 1;")
                elif var_value == '--':
                    self.add_line(f"{var_name} = {var_name} - 1;")
                else:
                    # Convert to proper DFA direct assignment
                    if var_value.startswith('/'):
                        var_value = self._sanitize_dfa_name(var_value.lstrip('/'))
                    elif var_value in ('true', 'false'):
                        var_value = '1' if var_value == 'true' else '0'
                    elif var_value.startswith('(') and var_value.endswith(')'):
                        var_value = f"'{var_value[1:-1]}'"
                    self.add_line(f"{var_name} = {var_value};")
            return

        # Handle increment/decrement operators
        if cmd.name == '++':
            if cmd.parameters:
                var_name = cmd.parameters[0].lstrip('/')
                self.add_line(f"{var_name} = {var_name} + 1;")
            return

        if cmd.name == '--':
            if cmd.parameters:
                var_name = cmd.parameters[0].lstrip('/')
                self.add_line(f"{var_name} = {var_name} - 1;")
            return

        # Note: Nested IF commands should NOT appear here when processing flat lists,
        # because the parent _convert_if_command uses lookahead to consume them.
        # However, if cmd has children (hierarchical structure), process it.
        if dfa_cmd == 'IF':
            if cmd.children:
                self._convert_if_command(cmd)
            return

        # Skip ELSE/ENDIF - they should be consumed by lookahead
        if cmd.name in ('ELSE', 'ENDIF'):
            return

        if cmd.name == 'BOOKMARK':
            self._convert_bookmark_command(cmd)
            return

        if cmd.name == 'SETPAGENUMBER':
            self._convert_pagenumber_command(cmd)
            return

        if cmd.name == 'ADD':
            self._convert_add_command(cmd)
            return

        if cmd.name == 'GETITEM':
            self._convert_getitem_command(cmd)
            return

        # Log unhandled commands for debugging
        # This helps identify commands that need proper conversion
        logger.debug(f"Unhandled command in IF/ELSE block: {cmd.name} {cmd.parameters}")

    def _convert_for_command(self, cmd: XeroxCommand):
        """Convert a FOR loop to DFA."""
        # Extract loop parameters
        params = " ".join(self._convert_params(cmd.parameters))
        self.add_line(f"FOR {params};")
    
    def _convert_output_command(self, cmd: XeroxCommand):
        """Convert an output command (SH, SHL, SHR, SHr, SHC, SHP) to DFA."""
        # Extract text and parameters
        text = ""
        font = "ARIAL08"
        position = ""
        align = ""
        is_variable_output = False
        format_string = None  # Will hold the FORMAT pattern if detected

        # Determine alignment based on original command
        if cmd.name == 'SHL':
            align = "ALIGN LEFT"
        elif cmd.name in ('SHR', 'SHr'):
            align = "ALIGN RIGHT"
        elif cmd.name in ('SHC', 'SHc'):
            align = "ALIGN CENTER"
        elif cmd.name == 'SH':
            align = ""  # Default alignment (left)
        elif cmd.name in ('SHP', 'SHp'):
            align = "ALIGN PARAM"  # Parameterized alignment

        # Extract parameters
        # Note: In VIPP, /NAME can be either:
        # - Variable reference if it's the first/main parameter (what to output)
        # - Font reference if it comes after text (how to format)
        i = 0
        while i < len(cmd.parameters):
            param = cmd.parameters[i]
            if param == 'VSUB':
                # Skip VSUB marker - already handled inline
                i += 1
                continue
            elif param == 'FORMAT':
                # Next parameter is the format string
                if i + 1 < len(cmd.parameters):
                    format_string = cmd.parameters[i + 1]
                    i += 2  # Skip both FORMAT and the format pattern
                    continue
                else:
                    i += 1
                    continue
            elif param.startswith('(') and param.endswith(')'):
                # Could be text string or format pattern
                # If previous param was FORMAT, this is already handled above
                if not format_string or i == 0 or cmd.parameters[i-1] != 'FORMAT':
                    # Text string - check for VSUB and font switches
                    text = param
                i += 1
            elif param.startswith('/'):
                # If we haven't found text yet, this is a variable reference
                # If we already have text, this is a font reference
                if not text:
                    # Variable reference - output the variable directly (sanitize for DFA)
                    text = self._sanitize_dfa_name(param.lstrip('/'))
                    is_variable_output = True
                else:
                    # Font reference
                    font_alias = param.lstrip('/')
                    font = self.font_mappings.get(font_alias, font_alias.upper())
                i += 1
            elif param.startswith('VAR_') or param.startswith('VAR') or param.startswith('FLD') or param.startswith('$'):
                # Explicit variable or system variable reference
                text = param
                is_variable_output = True
                i += 1
            else:
                i += 1

        # Process text for VSUB variable substitution
        if text:
            if is_variable_output:
                # Variable reference - output directly without quotes
                # If FORMAT is detected, wrap in NUMPICTURE
                if format_string:
                    dfa_format = self._convert_vipp_format_to_dfa(format_string)
                    output_text = f"NUMPICTURE({text},{dfa_format})"
                else:
                    output_text = text

                output_parts = [f"OUTPUT {output_text}"]
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


    def _should_use_text_baseline(self, text: str, params: list, alignment: int = None) -> bool:
        """
        Determine if TEXT BASELINE should be used instead of OUTPUT.

        Use TEXT BASELINE if:
        - Text is long (> 50 chars)
        - Text contains font style markers (**F5, **FC, **BOLD, **ITALIC)
        - Multiple fonts referenced in parameters
        - Alignment is JUSTIFY (alignment == 3)

        Args:
            text: The text string to output
            params: Command parameters
            alignment: Alignment code (0=LEFT, 1=RIGHT, 2=CENTER, 3=JUSTIFY)

        Returns:
            True if should use TEXT BASELINE, False for OUTPUT
        """
        # JUSTIFY requires TEXT BASELINE (OUTPUT doesn't support JUSTIFY)
        if alignment == 3:
            return True

        # Check length
        if len(text) > 50:
            return True

        # Check for font style markers in text
        if '**' in text:
            return True

        # Check for multiple font references in parameters
        font_count = sum(1 for p in params if str(p).startswith('/') and str(p)[1:].isupper())
        if font_count > 1:
            return True

        return False

    def _generate_text_baseline(self, text: str, font: str, position: tuple, alignment: int, width: float = None):
        """
        Generate TEXT command with BASELINE positioning.

        Args:
            text: The text to output
            font: Font name
            position: (x, y) position tuple
            alignment: Alignment code (0=LEFT, 1=RIGHT, 2=CENTER, 3=JUSTIFY)
            width: Optional width for JUSTIFY alignment
        """
        x_pos, y_pos = position

        self.add_line("TEXT")
        self.indent()

        # Keep the caller-provided anchor position; forcing SAME SAME causes
        # wrapped paragraphs to overprint previous lines.
        self.add_line(f"{self._format_position(x_pos, y_pos, vertical_next_to_autospace=True)} BASELINE")

        # Width for wrapped paragraph output (SHP/SHp and JUSTIFY cases)
        if width:
            self.add_line(f"WIDTH {width} MM")

        # Font
        self.add_line(f"FONT {font}")

        # Alignment
        align_map = {0: 'LEFT', 1: 'RIGHT', 2: 'CENTER', 3: 'JUSTIFY'}
        if alignment in align_map:
            self.add_line(f"ALIGN {align_map[alignment]}")

        # Text - split long lines at ~70 chars
        if len(text) > 70:
            # Split into chunks at word boundaries
            chunks = []
            remaining = text
            while remaining:
                if len(remaining) <= 70:
                    chunks.append(remaining)
                    break
                # Find last space before 70 chars
                split_pos = remaining[:70].rfind(' ')
                if split_pos == -1:
                    split_pos = 70
                chunks.append(remaining[:split_pos])
                remaining = remaining[split_pos:].lstrip()

            for i, chunk in enumerate(chunks):
                if i == len(chunks) - 1:
                    # Last chunk gets semicolon
                    self.add_line(f"'{self._escape_dfa_quotes(chunk)}';")
                else:
                    self.add_line(f"'{self._escape_dfa_quotes(chunk)}'")
        else:
            self.add_line(f"'{self._escape_dfa_quotes(text)}';")

        self.dedent()



    def _convert_output_command_dfa(self, cmd: XeroxCommand, x_pos: float, y_pos: float, current_font: str,
                                   x_was_set: bool = True, y_was_set: bool = True, y_is_next: bool = False,
                                   current_color: str = None):
        """Convert an output command to proper DFA OUTPUT with FONT and POSITION."""
        text = ""
        is_variable = False
        format_string = None  # Will hold the FORMAT pattern if detected
        shp_width = None
        shp_alignment = None

        # Extract text from parameters
        # Note: In VIPP, /NAME can be either:
        # - Variable reference if it's the first/main parameter (what to output)
        # - Font reference if it comes after text (how to format)
        i = 0
        while i < len(cmd.parameters):
            param = cmd.parameters[i]
            if param == 'VSUB':
                i += 1
                continue
            elif param == 'FORMAT':
                # Next parameter is the format string
                if i + 1 < len(cmd.parameters):
                    format_string = cmd.parameters[i + 1]
                    i += 2  # Skip both FORMAT and the format pattern
                    continue
                else:
                    i += 1
                    continue
            elif param.startswith('(') and param.endswith(')'):
                # Could be text string or format pattern
                # If previous param was FORMAT, this is already handled above
                if not format_string or i == 0 or cmd.parameters[i-1] != 'FORMAT':
                    text = param[1:-1]  # Remove parentheses - this is a string literal
                i += 1
            elif param.startswith('/'):
                # If we haven't found text yet, this is a variable reference
                # If we already have text, this would be a font reference (skip here)
                if not text:
                    text = param.lstrip('/')
                    is_variable = True
                i += 1
            elif param.startswith('VAR_') or param.startswith('VAR') or param.startswith('FLD') or param.startswith('$'):
                # Explicit variable or system variable reference
                text = param
                is_variable = True
                i += 1
            else:
                i += 1

        # SHP/SHp carries width and alignment as numeric params.
        # Use trailing numeric values to avoid confusion with values embedded in text.
        if cmd.name in ('SHP', 'SHp'):
            numeric_vals = []
            for p in cmd.parameters:
                ps = str(p)
                try:
                    numeric_vals.append(float(ps))
                except (TypeError, ValueError):
                    continue
            if len(numeric_vals) >= 2:
                shp_width = numeric_vals[-2]
                try:
                    shp_alignment = int(numeric_vals[-1])
                except (TypeError, ValueError):
                    shp_alignment = None

        if not text:
            return

        # Process VSUB patterns
        if not is_variable and ('$$' in text or '$' in text):
            original_text_had_vsub = '$$' in text or '$' in text
            text = self._convert_vsub(text)
            # After VSUB conversion, if text contains ! concatenation, treat as variable
            if ' ! ' in text:
                is_variable = True
            elif original_text_had_vsub and "'" not in text and ' ' not in text.strip():
                # Pure variable substitution: ($$VAR_SCCL.) → VAR_SCCL (no literals, no concat)
                # The converted text is just a bare variable name — must not be quoted.
                is_variable = True

        # Determine alignment from command type / SHP parameter
        alignment = None
        if cmd.name == 'SHL':
            alignment = 0  # Left
        elif cmd.name in ('SHR', 'SHr'):
            alignment = 1  # Right
        elif cmd.name in ('SHC', 'SHc'):
            alignment = 2  # Center
        elif cmd.name in ('SHP', 'SHp') and shp_alignment is not None:
            alignment = shp_alignment

        # Use flags to determine position format
        # X position: pass raw numeric value if set (MM will be added by _format_position), SAME otherwise
        x_final = x_pos if x_was_set else 'SAME'

        # Y position: use LASTMAX+6MM after TEXT, NEXT after NL, explicit value when positioned
        if y_is_next:
            # Check if previous command was TEXT - use LASTMAX+6MM after TEXT
            if self.last_command_type == 'TEXT':
                y_final = 'LASTMAX+6 MM'
            else:
                y_final = 'NEXT'  # After NL or previous OUTPUT, use NEXT to stay on the new line
        elif y_was_set:
            y_final = y_pos  # Explicit position (MM will be added by _format_position)
        else:
            y_final = 'SAME'  # Implicit position

        # Check if we should use TEXT BASELINE instead of OUTPUT
        # Only for literal text (not variables)
        if not is_variable and self._should_use_text_baseline(text, cmd.parameters, alignment):
            # Use TEXT BASELINE for long strings, multi-font text, or JUSTIFY alignment
            # Use SHP width when available; otherwise fallback for JUSTIFY.
            width = shp_width if shp_width else (193.0 if alignment == 3 else None)
            self._generate_text_baseline(text, current_font, (x_final, y_final), alignment, width)
            self.last_command_type = 'TEXT'
        elif is_variable and cmd.name in ('SHP', 'SHp') and shp_width:
            # SHP with VSUB/variable content still needs WIDTH-based paragraph layout.
            self._tmp_text_counter += 1
            tmp_var = f"TMP_TXT_{self._tmp_text_counter}"

            if format_string:
                dfa_format = self._convert_vipp_format_to_dfa(format_string)
                expr = f"NUMPICTURE({text},{dfa_format})"
            else:
                expr = text

            self.add_line(f"{tmp_var} = {expr};")
            self.add_line("TEXT")
            self.indent()
            self.add_line(f"{self._format_position(x_final, y_final, vertical_next_to_autospace=True)} BASELINE")
            self.add_line(f"WIDTH {shp_width} MM")
            self.add_line(f"FONT {current_font}")
            align_map = {0: 'LEFT', 1: 'RIGHT', 2: 'CENTER', 3: 'JUSTIFY'}
            if alignment in align_map:
                self.add_line(f"ALIGN {align_map[alignment]}")
            self.add_line(f"({tmp_var});")
            self.dedent()
            self.last_command_type = 'TEXT'
        else:
            # Generate proper DFA OUTPUT with FONT and POSITION on separate lines
            # Format: OUTPUT text FONT fontname NORMAL POSITION x y [ALIGN ...];
            if is_variable:
                # If FORMAT is detected, wrap in NUMPICTURE
                if format_string:
                    dfa_format = self._convert_vipp_format_to_dfa(format_string)
                    self.add_line(f"OUTPUT NUMPICTURE({text},{dfa_format})")
                else:
                    self.add_line(f"OUTPUT {text}")
            else:
                self.add_line(f"OUTPUT '{self._escape_dfa_quotes(text)}'")
            self.add_line(f"    FONT {current_font} NORMAL")
            use_autospace_output = not (not is_variable and text == '')
            self.add_line(f"    {self._format_position(x_final, y_final, vertical_next_to_autospace=use_autospace_output)}")
            if current_color:
                self.add_line(f"    COLOR {current_color}")

            # Add alignment if specified (but NOT JUSTIFY - that's not valid for OUTPUT)
            if alignment == 0:
                self.add_line("    ALIGN LEFT NOPAD;")
            elif alignment == 1:
                self.add_line("    ALIGN RIGHT NOPAD;")
            elif alignment == 2:
                self.add_line("    ALIGN CENTER NOPAD;")
            else:
                self.add_line("    ;")
            self.last_command_type = 'OUTPUT'

    def _convert_box_command_dfa(self, cmd: XeroxCommand):
        """Convert a box drawing command to proper DFA BOX.

        Uses absolute margin-relative positioning for non-zero coords.
        For x=0 y=0 in DBM inline context, uses SAME SAME (current position)
        since POSX/POSY are only valid inside SEGMENT/XGFRESDEF definitions.

        VIPP: 00 -13.5 193 0.001 XDRK DRAWB
        DFA:  POSITION (0 MM-$MR_LEFT) (13.5 MM-$MR_TOP)
        """
        if len(cmd.parameters) < 4:
            return

        # Parse dimensions first (must be numeric)
        try:
            width = float(cmd.parameters[2])
            height = float(cmd.parameters[3])
        except (ValueError, IndexError, TypeError):
            return

        x_raw = str(cmd.parameters[0])
        y_raw = str(cmd.parameters[1])

        def _num_or_none(v: str):
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        x_num = _num_or_none(x_raw)
        y_num = _num_or_none(y_raw)

        # Build position expressions:
        # - numeric coordinates keep current behavior (Y uses absolute inversion)
        # - variable/identifier coordinates are emitted as dynamic MM expressions
        if x_num is not None:
            x_expr = f"{x_num} MM-$MR_LEFT"
        else:
            x_var = self._sanitize_dfa_name(x_raw.lstrip('/'))
            if not x_var:
                return
            x_expr = f"{x_var}-$MR_LEFT"

        y_var_name = None
        if y_num is not None:
            y_expr = f"{abs(y_num)} MM-$MR_TOP"
        else:
            # In DBM inline flows (e.g. CASIO Y0), variable Y operands such as VAR.Y5
            # are often zero-offset placeholders and must follow current cursor Y.
            # Mapping them to absolute margin coordinates pushes lines to page top.
            y_var = self._sanitize_dfa_name(y_raw.lstrip('/'))
            if not y_var:
                return
            y_var_name = y_var
            y_expr = "SAME"

        # Convert tiny widths/heights to 0.01 MM for thin lines
        if width < 0.01:
            width = 0.01
        if height < 0.01:
            height = 0.01

        # Parse style parameter if present
        style = str(cmd.parameters[4]).upper() if len(cmd.parameters) >= 5 else None
        is_line_style = style in ('LT', 'LMED', 'LTHN', 'LTHK', 'LDSH', 'LDOT',
                                  'L_MED', 'L_THN', 'L_THK', 'L_DSH', 'L_DOT') if style else False

        # Determine positioning pattern
        # x>0 or y!=0 → absolute margin-relative position
        # x=0 and y=0 → DBM inline context: "current position" → use SAME SAME
        # Note: POSX/POSY anchors are only valid inside XGFRESDEF-generated SEGMENTs,
        # not in top-level DOCFORMAT/OUTLINE blocks.
        use_absolute = (x_num is None or y_num is None or x_num > 0 or y_num != 0)

        # Convert thin vertical boxes (width 0.1 MM) to RULE UP.
        if abs(width - 0.1) < 0.0001 and height > width:
            if y_var_name:
                # Keep Xerox-like dynamic anchor immediately before each draw.
                self.add_line(f"{y_var_name} = $SL_CURRY;")
            self.add_line("RULE")
            self.indent()
            if use_absolute:
                if y_var_name:
                    y_start = f"{y_var_name}+{height} MM"
                elif y_expr == "SAME":
                    y_start = f"SAME+{height} MM"
                else:
                    y_start = f"{y_expr}+{height} MM"
                self.add_line(f"POSITION ({x_expr}) ({y_start})")
            else:
                self.add_line(f"POSITION (POSX+{x_num} MM) (POSY+{height} MM)")
            self.add_line("DIRECTION UP")
            if style:
                color = 'FBLACK'
                if style.startswith('R'):
                    color = 'R'
                elif style.startswith('G'):
                    color = 'G'
                elif style.startswith('B') and style != 'BLACK':
                    color = 'B'
                elif style in ('XDRK', 'MED', 'LMED', 'FBLACK'):
                    color = style
                self.add_line(f"COLOR {color}")
            self.add_line(f"LENGTH {height} MM")
            self.add_line("THICKNESS 0.1 MM TYPE SOLID")
            self.add_line(";")
            self.dedent()
            return

        # Generate BOX
        self.add_line("BOX")
        self.indent()

        if use_absolute:
            self.add_line(f"POSITION ({x_expr}) ({y_expr})")
        else:
            # x=0 y=0: draw at current inline position
            self.add_line("POSITION (SAME) (SAME)")

        self.add_line(f"WIDTH {width} MM HEIGHT {height} MM")

        if is_line_style:
            line_thickness_map = {
                'LT': '0.1 MM', 'LTHN': '0.1 MM', 'L_THN': '0.1 MM',
                'LMED': '0.3 MM', 'L_MED': '0.3 MM',
                'LTHK': '0.8 MM', 'L_THK': '0.8 MM',
            }
            tk = line_thickness_map.get(style, '0.3 MM')
            self.add_line(f"THICKNESS {tk} TYPE SOLID;")
        elif style:
            # Fill style — determine color and shade
            color = 'FBLACK'
            if style.startswith('R'):
                color = 'R'
            elif style.startswith('G'):
                color = 'G'
            elif style.startswith('B') and style != 'BLACK':
                color = 'B'
            elif style in ('XDRK', 'MED', 'LMED', 'FBLACK'):
                color = style

            shade = 100
            if 'S2' in style or '_S2' in style:
                shade = 75
            elif 'S3' in style or '_S3' in style:
                shade = 50
            elif 'S4' in style or '_S4' in style:
                shade = 25

            self.add_line(f"COLOR {color}")
            self.add_line(f"THICKNESS 0 TYPE SOLID SHADE {shade};")
        else:
            self.add_line("THICKNESS 0 TYPE SOLID SHADE 100;")

        self.dedent()

    def _convert_resource_command_dfa(self, cmd: XeroxCommand, x_pos: float, y_pos: float,
                                      current_font: str = "ARIAL08",
                                      x_was_set: bool = False, y_was_set: bool = False):
        """Convert a resource call (SCALL/ICALL) to proper DFA SEGMENT or inlined BOX/RULE.

        For XGFRESDEF subroutines (drawing macros): inline DRAWB children as absolute BOX/RULE
        commands using (x_pos, y_pos) as the origin.
        For AFP page segments (raster images): generate SEGMENT name POSITION ...;
        """
        if not cmd.parameters:
            return
        resource_name = self._sanitize_dfa_name(cmd.parameters[0].strip('()'))
        sub = self.subroutines.get(resource_name)
        if sub and sub.get('xgfresdef'):
            # Save current cursor before drawing inline segment content.
            self.add_line("YPOS = $SL_CURRY;")
            self.add_line("XPOS = $SL_CURRX;")
            if x_was_set:
                self.add_line(f"XPOS = MM({x_pos});")
            if y_was_set:
                self.add_line(f"YPOS = MM({y_pos});")

            # Inline XGFRESDEF relative to saved XPOS/YPOS anchors.
            self._inline_xgfresdef_drawbs(
                resource_name,
                x_pos,
                y_pos,
                anchor_x_var="XPOS",
                anchor_y_var="YPOS"
            )

            # Restore cursor so subsequent SAME/NEXT flow continues from pre-SCALL location.
            self.add_line("OUTPUT ''")
            self.add_line(f"    FONT {current_font} NORMAL")
            self.add_line("    POSITION (XPOS) (YPOS);")
        else:
            # AFP page segment: SEGMENT requires .240/.300 files from psew3pic (unlicensed).
            # Commented out; use CREATEOBJECT IOBDLL to load JPG directly instead.
            # Re-enable SEGMENT when psew3pic license is available.
            self.add_line(f"/* SEGMENT {resource_name} POSITION ({x_pos} MM-$MR_LEFT) ({y_pos} MM-$MR_TOP+&CORSEGMENT); */")
            self.add_line("CREATEOBJECT IOBDLL(IOBDEFS)")
            self.indent()
            self.add_line(f"POSITION ({x_pos} MM-$MR_LEFT) ({y_pos} MM-$MR_TOP+&CORSEGMENT)")
            self.add_line("PARAMETERS")
            self.indent()
            self.add_line(f"('FILENAME'='{resource_name}')")
            self.add_line("('OBJECTTYPE'='1')")
            self.add_line("('OTHERTYPES'='JPG')")
            self.add_line("('OBJECTMAPPING'='2');")
            self.dedent()
            self.dedent()

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
                output_parts = [f"OUTPUT '{self._escape_dfa_quotes(text)}'", f"FONT {current_font} NORMAL"]
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
        elif cmd.name in ('MOVEH', 'MOVEHR'):
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
                resource_name = self._sanitize_dfa_name(param.strip('()'))

        if cmd.name == 'SCALL':
            self.add_line(f"SEGMENT {resource_name}")
            self.indent()
            # Add segment position correction for vertical position
            self.add_line("POSITION (0 MM-$MR_LEFT) (0 MM-$MR_TOP+&CORSEGMENT);")
            self.dedent()
        elif cmd.name == 'ICALL':
            # DFA has no IMAGE command — use CREATEOBJECT IOBDLL(IOBDEFS)
            import os as _os
            ext = _os.path.splitext(resource_name)[1].upper().lstrip('.')
            if not ext:
                ext = 'JPG'
            # Extract scale parameter (2nd numeric parameter after filename)
            scale = 1.0
            for p in cmd.parameters:
                if not (p.startswith('(') and p.endswith(')')):
                    try:
                        scale = float(p)
                        break
                    except (ValueError, TypeError):
                        pass
            # XOBJECTAREASIZE = scale × line_measure (180 MM standard)
            LINE_MEASURE_MM = 180.0
            estimated_width = max(5, min(200, round(scale * LINE_MEASURE_MM)))
            self.add_line("CREATEOBJECT IOBDLL(IOBDEFS)")
            self.indent()
            self.add_line("POSITION (0 MM-$MR_LEFT) (0 MM-$MR_TOP)")
            self.add_line("PARAMETERS")
            self.indent()
            self.add_line(f"('FILENAME'='{resource_name}')")
            self.add_line("('OBJECTTYPE'='1')")
            self.add_line(f"('OTHERTYPES'='{ext}')")
            self.add_line(f"('XOBJECTAREASIZE'='{estimated_width}')")
            self.add_line("('OBJECTMAPPING'='2')")
            self.dedent()
            self.add_line(";")
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

        NEWFRAME is not valid DFA — emit comment stub.
        """
        frame_name = ""
        if cmd.parameters:
            frame_name = cmd.parameters[0].strip('()/')

        if frame_name:
            self.add_line(f"/* VIPP command not supported: NEWFRAME '{frame_name}' */")
        else:
            self.add_line("/* VIPP command not supported: NEWFRAME */")

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

        VIPP BOOKMARK semantics are mapped to PDF index records in DFA.
        We generate GROUPINDEX so PDF output can build bookmark trees.
        """
        bookmark_param = None

        for param in cmd.parameters:
            if param == 'VSUB':
                continue
            if isinstance(param, str) and (param.startswith('(') or '$$' in param or param.startswith('$') or param.startswith('VAR_')):
                bookmark_param = param
                break

        if not bookmark_param:
            self.add_line("/* BOOKMARK without resolvable text parameter */")
            return

        expr = self._render_vipp_format_expr(bookmark_param)
        self.add_line(f"GROUPINDEX BOOKMARK = {expr};")

    def _convert_pagenumber_command(self, cmd: XeroxCommand, emit_now: bool = True):
        """
        Convert a VIPP SETPAGENUMBER command to DFA.

        We apply its format/position metadata to generated PRINTFOOTER output.
        """
        if not cmd.parameters:
            if emit_now:
                self.add_line("/* SETPAGENUMBER without parameters */")
            return

        # Expected frequent form:
        # (format) [VSUB] start hpos vpos align SETPAGENUMBER
        # Keep numeric operands in encountered order.
        fmt_param = None
        numeric_params = []
        for param in cmd.parameters:
            if param == 'VSUB':
                continue
            if fmt_param is None and isinstance(param, str) and param.startswith('(') and param.endswith(')'):
                fmt_param = param
                continue
            if isinstance(param, str) and (param.replace('.', '', 1).lstrip('-').isdigit()):
                numeric_params.append(param)

        if fmt_param:
            self.page_number_expr = self._render_vipp_format_expr(fmt_param)
            self.emit_page_index_marker = True

        # start hpos vpos align
        if len(numeric_params) >= 4:
            self.page_number_x = f"{numeric_params[1]} MM-$MR_LEFT"
            self.page_number_y = f"{numeric_params[2]} MM"
            align_map = {'5': 'LEFT', '6': 'RIGHT', '7': 'CENTER'}
            self.page_number_align = align_map.get(numeric_params[3], self.page_number_align)

        if emit_now:
            self.add_line("/* SETPAGENUMBER mapped to PRINTFOOTER page-number output */")

    def _convert_params(self, params: List[str]) -> List[str]:
        """Convert Xerox command parameters to DFA format."""
        dfa_params = []

        for param in params:
            # Handle variable references
            if param.startswith('/'):
                var_name = self._sanitize_dfa_name(param.lstrip('/'))
                dfa_params.append(var_name)
            # Handle string literals
            elif param.startswith('(') and param.endswith(')'):
                text = param.strip('()')
                dfa_params.append(f"'{self._escape_dfa_quotes(text)}'")
            # Handle numeric values
            elif param.isdigit() or (param.replace('.', '', 1).isdigit() and param.count('.') <= 1):
                dfa_params.append(param)
            # Pass other parameters through
            else:
                dfa_params.append(param)
        
        return dfa_params

    def _generate_form_usage_info(self):
        """Generate form selection code for first page vs subsequent pages.

        NOTE: This is the legacy function. PRINTFOOTER routing is now handled
        by _generate_form_usage_in_printfooter() which uses the P counter.
        This function is kept for backward compatibility but delegates to
        the PRINTFOOTER function pattern.
        """
        # List available forms.
        # Apply collision-avoidance: FRM with same base name as DBM is written
        # with an 'F' suffix on disk; the USE FORMAT reference must match.
        dbm_docdef_name = ''.join(c for c in os.path.splitext(os.path.basename(self.dbm.filename))[0] if c.isalnum())
        frm_names = []
        for frm_filename in sorted(self.frm_files.keys()):
            frm_name = os.path.splitext(frm_filename)[0].upper()
            frm_name = ''.join(c for c in frm_name if c.isalnum() or c == '_')
            if frm_name == dbm_docdef_name:
                frm_name = frm_name + 'F'
            frm_names.append(frm_name)

        if len(frm_names) > 0:
            first_form = next((f for f in frm_names if f.endswith('F')), frm_names[0])
            subseq_form = next((f for f in frm_names if f.endswith('S')), frm_names[-1] if len(frm_names) > 1 else frm_names[0])
        else:
            first_form = "FIRSTPAGE"
            subseq_form = "NEXTPAGE"

        self.add_line("IF P < 1; THEN;")
        self.indent()
        self.add_line(f"USE FORMAT {first_form} EXTERNAL;")
        self.dedent()
        self.add_line("ELSE;")
        self.indent()
        self.add_line(f"USE FORMAT {subseq_form} EXTERNAL;")
        self.dedent()
        self.add_line("ENDIF;")
        self.add_line("")

    def _generate_form_usage_in_printfooter(self):
        """
        Generate form selection code in PRINTFOOTER.

        2-FRM pattern (e.g. SIBS_CAST — simple documents where form alternates predictably):
            IF P<1; THEN; USE FORMAT <first_F> EXTERNAL; ELSE; USE FORMAT <subseq_S> EXTERNAL; ENDIF;
            P = P + 1;

        Multi-FRM pattern (3+ FRMs, e.g. CASIO — data-driven form selection):
            The SETFORM command in each PREFIX CASE sets VAR_CURFORM = 'FORMNAME'.
            PRINTFOOTER uses USE FORMAT REFERENCE(VAR_CURFORM) EXTERNAL to select the
            right background for each physical page based on which prefix record ran last.
            P is still incremented for page numbering ("Page X of Y").

        The critical difference from the old P-counter approach: for complex multi-FRM
        documents, the form selection is DATA-DRIVEN, not position-sequential. Using a
        fixed P counter would select the wrong FRM for pages where the order varies by
        customer data.
        """
        # List available forms
        # Compute the DBM docdef name so we can apply the same collision-avoidance
        # as the file-writing loop: when an FRM has the same base name as the DBM,
        # the FRM file is written with an 'F' suffix (e.g. UT00060F.dfa), so the
        # USE FORMAT reference must also use the suffixed name.
        dbm_docdef_name = ''.join(c for c in os.path.splitext(os.path.basename(self.dbm.filename))[0] if c.isalnum())
        frm_names = []
        for frm_filename in sorted(self.frm_files.keys()):
            frm_name = os.path.splitext(frm_filename)[0].upper()
            frm_name = ''.join(c for c in frm_name if c.isalnum() or c == '_')
            if frm_name == dbm_docdef_name:
                frm_name = frm_name + 'F'
            frm_names.append(frm_name)

        if len(frm_names) == 0:
            return  # No forms to use

        if len(frm_names) <= 2:
            # 2-FRM pattern: IF P<1 → first page form; ELSE → subsequent page form
            # P starts at 0 (reset in $_BEFOREDOC), so first call gets F form
            first_form = next((f for f in frm_names if f.endswith('F')), frm_names[0])
            subseq_form = next((f for f in frm_names if f.endswith('S')), frm_names[-1] if len(frm_names) > 1 else frm_names[0])

            self.add_line(f"      IF P<1; THEN; USE FORMAT {first_form} EXTERNAL; ELSE; USE FORMAT {subseq_form} EXTERNAL; ENDIF;")
            self.add_line(f"      P = P + 1;")
        else:
            # Multi-FRM pattern (3+ FRMs): use per-page FRM_PAGE[] array.
            # During formatting (FOOTER), each page snapshots VAR_CURFORM into FRM_PAGE[PP].
            # During printing (PRINTFOOTER), FRM_PAGE[P] gives the correct form for each page.
            # This is required because PRINTFOOTER runs in the print pass where VAR_CURFORM
            # has only its FINAL value — not the per-page value set during formatting.
            self.add_line(f"      P = P + 1;")
            self.add_line(f"      IF ISTRUE(NOSPACE(FRM_PAGE[P]) <> '');")
            self.add_line(f"      THEN; USE FORMAT REFERENCE(FRM_PAGE[P]) EXTERNAL;")
            self.add_line(f"      ENDIF;")

    def _generate_variable_initialization(self):
        """
        Generate variable initialization from DBM commands.

        Scans raw DBM content for /INI SETVAR patterns in the VARINI block.
        Since $_BEFOREFIRSTDOC only runs once, we don't need the VARINI IF pattern
        - variables don't exist yet so they will be created with these initial values.
        """
        self.add_line("/* Variable Initialization from DBM */")
        self.add_line("")

        # First try parsed commands
        self._process_initialization_commands(self.dbm.commands)

        # Fallback: scan raw content for /VarName value /INI SETVAR patterns
        # This catches variables inside IF VARINI blocks that the parser may not
        # propagate with the is_initialization flag
        if self.dbm.raw_content:
            import re
            init_count = 0
            already_emitted = set()  # Track only variables emitted in THIS section

            # Scan for /VarName value /INI SETVAR within the VARINI block
            # Variable names can contain hyphens (e.g., VAR_COUNT-TX)
            in_varini_block = False
            for line in self.dbm.raw_content.split('\n'):
                stripped = line.strip()
                # Skip comments
                if stripped.startswith('%'):
                    continue
                # Detect VARINI block boundaries
                if re.search(r'IF\s+VARINI', stripped):
                    in_varini_block = True
                    continue
                if in_varini_block and stripped.startswith('}'):
                    in_varini_block = False
                    continue
                if not in_varini_block:
                    continue

                # Match /VarName value /INI SETVAR (with /INI flag)
                m = re.match(r'/([\w-]+)\s+(.+?)\s+/INI\s+SETVAR', stripped)
                if m:
                    var_name = self._sanitize_dfa_name(m.group(1))
                    var_value = m.group(2).strip()
                    if var_name == 'VARINI' or var_name in already_emitted:
                        continue
                    dfa_value = self._convert_setvar_value(var_value)
                    self.add_line(f"{var_name} = {dfa_value};")
                    already_emitted.add(var_name)
                    init_count += 1
                    continue

                # Match /VarName () /INI (no SETVAR keyword — empty string init, e.g. VAR_ARRAY1F1)
                # This is a VIPP pattern: /VAR_ARRAY1F1 () /INI declares an empty string variable.
                m_arr = re.match(r'/([\w.-]+)\s+\(\)\s+/INI\s*$', stripped)
                if m_arr:
                    var_name = self._sanitize_dfa_name(m_arr.group(1))
                    if var_name == 'VARINI' or var_name in already_emitted:
                        continue
                    self.add_line(f"{var_name} = '';")
                    already_emitted.add(var_name)
                    init_count += 1
                    continue

                # Match /VarName value SETVAR (without /INI, e.g., /VARdoc 0 SETVAR)
                m2 = re.match(r'/([\w-]+)\s+(\S+)\s+SETVAR', stripped)
                if m2 and '/INI' not in stripped:
                    var_name = self._sanitize_dfa_name(m2.group(1))
                    var_value = m2.group(2)
                    if var_name == 'VARINI' or var_name in already_emitted:
                        continue
                    dfa_value = self._convert_setvar_value(var_value)
                    self.add_line(f"{var_name} = {dfa_value};")
                    already_emitted.add(var_name)
                    init_count += 1

            if init_count > 0:
                logger.info(f"Extracted {init_count} initialization variables from raw DBM content")

        # Initialize GETITEM backing stores so DFA does not warn on first indexed read.
        for store_var in sorted(set(self.getitem_store_vars.values())):
            self.add_line(f"{store_var} = '';")

        self.add_line("")

    def _process_initialization_commands(self, commands: List[XeroxCommand]):
        """Recursively process commands to extract variable initializations."""
        init_var_count = 0
        for cmd in commands:
            # Handle SETVAR commands with /INI flag (initialization variables only)
            if cmd.name == 'SETVAR' and cmd.is_initialization:
                init_var_count += 1
                var_name = None
                var_value = None

                # Parse parameters: /VarName value SETVAR (already filtered /INI)
                params = cmd.parameters
                for i, param in enumerate(params):
                    if param.startswith('/'):
                        # Variable name (remove leading /, sanitize for DFA)
                        var_name = self._sanitize_dfa_name(param[1:])
                    elif var_name and var_value is None:
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

        logger.debug(f"Processed {init_var_count} initialization variables")

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

        # DFA has built-in true/false literals — no constant definitions needed

        # Initialize page counters
        self.add_line("/* Current page */")
        self.add_line("PP = 0;")
        self.add_line("/* Total pages */")
        self.add_line("TP = 0;")
        self.add_line("")

        # Add position correction variables for Xerox alignment
        self.add_line("/* Correction for Xerox position — VIPP and DFA share the same */")
        self.add_line("/* absolute coordinate space; correction factors are 0 */")
        self.add_line("&CORFONT6 = 0;")
        self.add_line("&CORFONT7 = 0;")
        self.add_line("&CORFONT8 = 0;")
        self.add_line("&CORFONT10 = 0;")
        self.add_line("&CORFONT12 = 0;")
        self.add_line("&CORSEGMENT = 0;")
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

        # Check if header line contains field names — check first 6 chars only ('PREFIX')
        # so the check is separator-agnostic (works for '|', '~', etc.)
        self.add_line("/* Field (Standard) Names: FLD1, FLD2, etc. */")
        self.add_line("IF LEFT(LINE1, 6, '') == 'PREFIX'; THEN;")
        self.indent()

        # Detect separator dynamically from the 7th character of the PREFIX header line
        self.add_line("/* Detect separator: the character immediately after 'PREFIX' */")
        self.add_line("&SEP = SUBSTR(LINE1, 7, 1, '');")

        # Extract field names from header
        self.add_line("LINE1 = CHANGE(LINE1, 'PREFIX'!&SEP, '');")
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
        self.add_line("VAR_CURFORM = '';  /* Reset FRM selector — set by SETFORM-equivalent DOCFORMATs */")
        self.add_line("TFLOW_Y = $SL_CURRY;")
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
            elif args.input_path.lower().endswith('.frm'):
                logger.error("Cannot convert standalone FRM file. Please provide a DBM file.")
                return
            else:
                logger.error(f"Unsupported file type: {args.input_path}")
                return
        else:
            # Process all files in the input directory
            if not os.path.isdir(args.input_path):
                logger.error(f"Directory not found: {args.input_path}")
                return
            
            # First pass: identify projects and files
            for root, dirs, files in os.walk(args.input_path):
                for file in files:
                    if file.lower().endswith('.dbm') or file.lower().endswith('.frm'):
                        file_path = os.path.join(root, file)
                        logger.info(f"Found Xerox file: {file_path}")

                        # Try to determine project name from file content
                        project_name = "DEFAULT"

                        # Add file to the appropriate project
                        if project_name not in projects:
                            projects[project_name] = XeroxProject(name=project_name)

                        if file.lower().endswith('.dbm'):
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
                                projects[project_name].frm_files[file] = frm
                            except Exception as e:
                                logger.error(f"Error parsing FRM file {file}: {e}")
                                if args.verbose:
                                    logger.error(traceback.format_exc())
        
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

                    # Generate separate DFA files for each FRM and collect referenced colors
                    frm_referenced_colors = set()
                    frm_dfa_outputs = {}
                    for frm_filename, frm in frm_files.items():
                        try:
                            # FRM files are referenced via USE FORMAT ... EXTERNAL.
                            # External format files must NOT have a DOCFORMAT wrapper —
                            # that causes PPDE9087E "Mainlevel INCLUDE contains illegal
                            # command type". They DO need an OUTLINE wrapper for their
                            # output commands (as_include=True).
                            # CRITICAL: USE FORMAT CASIOS EXTERNAL must never be called from
                            # inside an already-open OUTLINE (causes PPDE7209E). The SETFORM
                            # handler in _convert_case_commands closes any open OUTLINE before
                            # emitting USE FORMAT ... EXTERNAL.
                            frm_dfa_code = converter.generate_frm_dfa_code(frm, as_include=True)
                            frm_dfa_outputs[frm_filename] = frm_dfa_code
                            # Collect COLOR references from FRM DFA
                            for m in re.finditer(r'\bCOLOR\s+([A-Z][A-Z0-9_]*)', frm_dfa_code):
                                frm_referenced_colors.add(m.group(1))
                        except Exception as e:
                            logger.error(f"Error generating FRM DFA for {frm_filename}: {e}")

                    # Patch main DFA: add any FRM-referenced colors not already defined
                    if frm_referenced_colors:
                        defined_in_main = set(re.findall(r'DEFINE\s+([A-Z][A-Z0-9_]*)\s+COLOR\b', dfa_code))
                        missing_frm_colors = frm_referenced_colors - defined_in_main
                        if missing_frm_colors:
                            color_rgb_fallback = {
                                'BLACK': (0, 0, 0), 'FBLACK': (0, 0, 0),
                                'WHITE': (255, 255, 255), 'RED': (255, 0, 0),
                                'GREEN': (0, 255, 0), 'BLUE': (0, 0, 255),
                                'LMED': (217, 217, 217), 'MED': (217, 217, 217),
                                'XDRK': (166, 166, 166),
                            }
                            insert_lines = []
                            for cn in sorted(missing_frm_colors):
                                r, g, b = color_rgb_fallback.get(cn, (0, 0, 0))
                                r_pct = round(r * 100 / 255, 1)
                                g_pct = round(g * 100 / 255, 1)
                                b_pct = round(b * 100 / 255, 1)
                                r_s = str(int(r_pct)) if r_pct == int(r_pct) else str(r_pct)
                                g_s = str(int(g_pct)) if g_pct == int(g_pct) else str(g_pct)
                                b_s = str(int(b_pct)) if b_pct == int(b_pct) else str(b_pct)
                                insert_lines.append(f"DEFINE {cn} COLOR RGB RVAL {r_s} GVAL {g_s} BVAL {b_s}; /* Added: referenced in FRM */")
                            # Find last DEFINE COLOR line and insert after it
                            lines = dfa_code.split('\n')
                            insert_idx = 0
                            for idx_l, line in enumerate(lines):
                                if 'DEFINE' in line and 'COLOR' in line:
                                    insert_idx = idx_l + 1
                            for j, il in enumerate(insert_lines):
                                lines.insert(insert_idx + j, il)
                            dfa_code = '\n'.join(lines)
                            # Rewrite main DFA with patched colors
                            with open(output_path, 'w', encoding='utf-8') as f:
                                f.write(dfa_code)
                            logger.info(f"Added {len(missing_frm_colors)} FRM-referenced colors to main DFA: {', '.join(sorted(missing_frm_colors))}")

                    # Write FRM DFA files
                    dbm_basename = os.path.splitext(dbm_file)[0].upper()
                    for frm_filename, frm in frm_files.items():
                        try:
                            frm_dfa_code = frm_dfa_outputs.get(frm_filename, '')
                            if not frm_dfa_code:
                                continue
                            frm_basename = os.path.splitext(frm_filename)[0]
                            # Avoid collision: if FRM has same base name as DBM, append 'F' suffix
                            if frm_basename.upper() == dbm_basename:
                                frm_output_filename = frm_basename + 'F.dfa'
                            else:
                                frm_output_filename = frm_basename + '.dfa'
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

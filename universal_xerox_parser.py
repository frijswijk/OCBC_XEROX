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
        'INDEXFONT', 'INDEXCOLOR', 'INDEXBAT', 'XGFRESDEF',
        
        # Page and positioning
        'SETPAGESIZE', 'SETLSP', 'SETPAGENUMBER', 'SETPAGEDEF', 'SETLKF', 'SETFORM',
        'MOVETO', 'MOVEH', 'LINETO', 'NL', 'ORITL', 'PORT', 'LAND', 'SHL', 'SHR', 'SHC', 'SHP',
        
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

        # Track SETPAGEDEF layout positions for OUTLINE generation
        self.page_layout_position = None  # (x, y) from last SETLKF in SETPAGEDEF

        # Track when to set box positioning anchors
        self.should_set_box_anchor = True  # Set anchors before first box in a group

        # Track last command type for positioning logic
        self.last_command_type = None  # 'OUTPUT', 'TEXT', 'NL'

        # Track subroutine definitions for SCALL handling
        self.subroutines = {}  # Maps subroutine name to {'commands': [...], 'type': 'simple'|'complex'}

        # Auto-detect input format from DBM
        self._detect_input_format()
        self._build_format_registry()
        self._extract_layout_info()
        self._extract_subroutines()

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
            'command_count': command_count
        }

        # Analyze commands to determine resource type (for backward compatibility)
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

        # First box in a group should set anchors
        if self.should_set_box_anchor:
            self.add_line("POSY = $SL_CURRY;")
            self.add_line("POSX = $SL_CURRX;")
            self.should_set_box_anchor = False

        # Parse parameters
        try:
            x = float(cmd.parameters[0])
            y = float(cmd.parameters[1])
            param3 = float(cmd.parameters[2])  # width or length
        except (ValueError, IndexError):
            return

        # Parse param4 - can be numeric or keyword
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

        # Invert Y coordinate (negative becomes positive)
        y_inverted = abs(y)

        # Convert tiny widths/heights to 0.1 MM for thin lines
        width = param3 if param3 >= 0.01 else 0.1
        height = param4_float if param4_float >= 0.01 else 0.1

        # Determine if this is a BOX (rectangle) or RULE (line)
        # If param4 (height/thickness) > 1.0 mm, it's a BOX
        is_box = param4_float > 1.0

        if is_box:
            # Generate BOX command with anchored position
            self.add_line("BOX")
            self.indent()

            # Position with anchors and inverted Y
            self.add_line(f"POSITION (POSX+{x} MM) (POSY+{y_inverted} MM)")

            # Dimensions
            self.add_line(f"WIDTH {width} MM")
            self.add_line(f"HEIGHT {height} MM")

            # Color if specified
            if color:
                self.add_line(f"COLOR {color}")

            # Thickness with shade if specified
            if shade is not None:
                self.add_line(f"THICKNESS 0 TYPE {line_type} SHADE {shade};")
            else:
                self.add_line(f"THICKNESS MEDIUM TYPE {line_type};")

            self.dedent()
        else:
            # Generate RULE command (line) with anchored position
            length = width
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

            # Position with anchors and inverted Y
            self.add_line(f"POSITION (POSX+{x} MM) (POSY+{y_inverted} MM)")

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

        # Check if this is a subroutine that can be inlined
        # Inlining criteria: Simple subroutine (<=5 commands), no file extension (internal resource)
        if not file_ext and resource_name in self.subroutines:
            subroutine_info = self.subroutines[resource_name]

            if subroutine_info['type'] == 'simple':
                # Inline the subroutine commands
                self.add_line(f"/* Inlined subroutine: {resource_name} ({subroutine_info['command_count']} commands) */")

                # Convert the subroutine commands directly
                self._convert_frm_command_list(
                    subroutine_info['commands'],
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

                self.subroutines[resource_name] = {
                    'commands': cmd.children,
                    'type': subroutine_type,
                    'command_count': command_count
                }

                logger.info(f"Found subroutine '{resource_name}' with {command_count} commands ({subroutine_type})")

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

        # Increment P counter BEFORE form selection
        self.add_line("        P = P + 1;")
        self.add_line("")

        # Add form usage in PRINTFOOTER (moved from main DOCFORMAT)
        self.add_line("        /* Cycle through FRM files */")
        self._generate_form_usage_in_printfooter()
        self.add_line("")

        # Page numbering
        self.add_line("        /* Page numbering */")
        self.add_line("        OUTLINE")
        self.add_line("            POSITION RIGHT (0 MM)")
        self.add_line("            DIRECTION ACROSS;")
        self.add_line("            OUTPUT 'Page '!P!' of '!PP")
        self.add_line("                FONT F5_1")
        self.add_line("                POSITION (RIGHT-11 MM)286 MM")
        self.add_line("                ALIGN RIGHT NOPAD;")
        self.add_line("        ENDIO;")
        self.add_line("    PRINTEND;")
        self.add_line("")

        # Add LOGICALPAGE 2 for duplex printing (back side of page)
        self.add_line("LOGICALPAGE 2")
        self.add_line("    SIDE FRONT")
        self.add_line("    POSITION 0 0")
        self.add_line("    WIDTH 210 MM")
        self.add_line("    HEIGHT 297 MM")
        self.add_line("    DIRECTION ACROSS")
        self.add_line("    FOOTER")
        self.add_line("        PP = PP + 1;")
        self.add_line("    FOOTEREND")
        self.add_line("    PRINTFOOTER")

        # Increment P counter BEFORE form selection
        self.add_line("        P = P + 1;")
        self.add_line("")

        # Add form usage in PRINTFOOTER for page 2 (same as page 1)
        self.add_line("        /* Cycle through FRM files */")
        self._generate_form_usage_in_printfooter()
        self.add_line("")

        # Page numbering
        self.add_line("        /* Page numbering */")
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
            self.add_line(f"COLOR {dfa_alias} AS RGB {r} {g} {b};")

        # Always add standard OCBC colors if not already defined
        standard_ocbc_colors = {
            'FBLACK': (0, 0, 0),
            'LMED': (217, 217, 217),
            'MED': (217, 217, 217),
            'XDRK': (166, 166, 166),
        }

        for color_name, (r, g, b) in standard_ocbc_colors.items():
            if color_name not in self.color_mappings.values():
                self.color_mappings[color_name] = color_name
                self.add_line(f"COLOR {color_name} AS RGB {r} {g} {b};")

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
            # Check if it's a keyword or starts with a keyword (for expressions like NEXT-(...) or LASTMAX+...)
            if y_upper in ('SAME', 'NEXT', 'TOP', 'BOTTOM') or y_upper.startswith(('NEXT-', 'NEXT+', 'SAME-', 'SAME+', 'LASTMAX+')):
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
        # Check for output commands
        output_commands = {
            'SH', 'SHL', 'SHR', 'SHr', 'SHC', 'SHP',  # Text output
            'DRAWB', 'SCALL', 'ICALL',                 # Graphics
            'NL', 'SETLSP', 'MOVETO', 'MOVEH',        # Positioning
            'SETFORM', 'SETPAGEDEF', 'SETLKF',        # Page layout
        }
        has_output = any(cmd.name in output_commands for cmd in commands)

        # Check for data manipulation commands (string/date parsing)
        data_commands = {'GETINTV', 'SUBSTR', 'VSUB', 'GETITEM'}
        has_data_manip = any(cmd.name in data_commands for cmd in commands)

        # Check for page management commands
        page_commands = {'PAGEBRK', 'NEWFRAME', 'ADD', 'BOOKMARK'}
        has_page_mgmt = any(cmd.name in page_commands for cmd in commands)

        # Check for increment/decrement
        has_counter = any(cmd.name in ['++', '--'] for cmd in commands)

        # Check for IF blocks (structural logic)
        has_if = any(cmd.name == 'IF' for cmd in commands)

        # Check for PREFIX assignment (e.g., /VAR_Y2 PREFIX SETVAR)
        # This is significant as it defines a record type prefix for data processing
        has_prefix_assignment = any(
            cmd.name == 'SETVAR' and
            len(cmd.parameters) >= 2 and
            str(cmd.parameters[1]).upper() == 'PREFIX'
            for cmd in commands
        )

        # Generate if has ANY of:
        # 1. Output commands
        # 2. Data manipulation (GETINTV, SUBSTR)
        # 3. Page management + IF (like page counting)
        # 4. Counters (++ or --)
        # 5. PREFIX assignment (important for data record definitions)
        return has_output or has_data_manip or (has_page_mgmt and has_if) or has_counter or has_prefix_assignment

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
        Also wraps variables in NOSPACE() when being compared to string literals.

        Args:
            params: List of parameters that may contain comparison operators

        Returns:
            List with converted operators and NOSPACE() wrappers
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
                        if (next_param.startswith("'") or next_param.upper() == next_param) and \
                           not prev_param.startswith("NOSPACE(") and \
                           (prev_param.startswith("VAR_") or prev_param.startswith("FLD[")):
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
                    if operator in ['lt', '<']:
                        # FRLEFT 60 lt → page has less than 60mm left
                        # This means we're close to bottom of page
                        condition = f"$SL_MAXY>$LP_HEIGHT-MM({threshold})"
                        return (condition, True)
                    elif operator in ['gt', '>']:
                        # FRLEFT 60 gt → page has more than 60mm left
                        condition = f"$SL_MAXY<$LP_HEIGHT-MM({threshold})"
                        return (condition, True)
                    elif operator in ['ge', '>=']:
                        # FRLEFT 60 ge → page has at least 60mm left
                        condition = f"$SL_MAXY<=$LP_HEIGHT-MM({threshold})"
                        return (condition, True)
                    elif operator in ['le', '<=']:
                        # FRLEFT 60 le → page has at most 60mm left
                        condition = f"$SL_MAXY>=$LP_HEIGHT-MM({threshold})"
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

        # Generate individual DOCFORMATs for each record type
        self._generate_individual_docformats()

        # Generate stub DOCFORMATs for undefined PREFIX cases
        self._generate_undefined_prefix_stubs()

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
        Only generate DOCFORMATs that have meaningful content (not just variable assignments).
        """
        self.add_line("/* Individual DOCFORMAT sections for each record type */")
        self.add_line("")

        generated_count = 0
        skipped_prefixes = []

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

            # Generate case-specific processing
            self._convert_case_commands(commands)

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

        # Track consumed commands for lookahead processing (IF/ELSE/ENDIF)
        i = 0
        while i < len(commands):
            cmd = commands[i]

            # Map command name if possible
            dfa_cmd = self.COMMAND_MAPPINGS.get(cmd.name, cmd.name)

            # Skip comments or unsupported commands
            if cmd.name.startswith('%') or dfa_cmd.startswith('/'):
                i += 1
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
                            var_value = var_value.lstrip('/')
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
                # Reset box anchor flag for new OUTLINE block
                self.should_set_box_anchor = True

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
                self.last_command_type = 'NL'
                i += 1
                continue

            # Handle SETLSP (line spacing) - convert to SETUNITS LINESP
            if cmd.name == 'SETLSP':
                if cmd.parameters:
                    spacing_val = cmd.parameters[0]
                    self.add_line(f"SETUNITS LINESP {spacing_val} MM;")
                else:
                    # Default to AUTO (uses font's line spacing)
                    self.add_line("SETUNITS LINESP AUTO;")
                i += 1
                continue

            # Handle if/else conditions
            if dfa_cmd == 'IF':
                # Convert the IF command with lookahead for ELSE/ENDIF
                consumed = self._convert_if_command(cmd, commands, i)
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
                                                 x_was_explicitly_set, y_was_explicitly_set, y_is_next_line)
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
                        current_x = float(cmd.parameters[0])
                        current_y = float(cmd.parameters[1])
                        x_was_explicitly_set = True
                        y_was_explicitly_set = True
                        y_is_next_line = False  # Explicit Y position overrides NEXT
                    except ValueError:
                        pass
                i += 1
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
                i += 1
                continue

            # Handle box drawing
            if dfa_cmd == 'BOX':
                self._convert_box_command_dfa(cmd)
                i += 1
                continue

            # Handle segment/image calls
            if cmd.name == 'SCALL' or cmd.name == 'ICALL':
                self._convert_resource_command_dfa(cmd, current_x, current_y)
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
            if cmd.name in ('SETLKF', 'SETPAGEDEF'):
                i += 1
                continue

            # Handle page break commands
            if cmd.name == 'PAGEBRK':
                # PAGEBRK → USE LP NEXT (or let DFA handle automatically)
                self.add_line("USE LP NEXT;")
                i += 1
                continue

            if cmd.name == 'NEWFRONT':
                # NEWFRONT → USE LP NEXT SIDE FRONT
                self.add_line("USE LP NEXT SIDE FRONT;")
                i += 1
                continue

            if cmd.name == 'NEWBACK':
                # NEWBACK → USE LP NEXT SIDE BACK
                self.add_line("USE LP NEXT SIDE BACK;")
                i += 1
                continue

            if cmd.name == 'NEWFRAME':
                # NEWFRAME → USE LP NEXT (automatic page break)
                self.add_line("USE LP NEXT;")
                i += 1
                continue

            # Skip other unsupported VIPP commands with comment
            if cmd.name in ('CACHE',
                          'BOOKMARK', 'SETPAGENUMBER', 'PAGEDEF',
                          'CPCOUNT', 'GETITEM'):
                self.add_line(f"/* VIPP command not directly supported: {cmd.name} */")
                i += 1
                continue

            # Increment counter for any unhandled commands (shouldn't reach here)
            i += 1

        # Close OUTLINE if it was opened
        if outline_opened:
            self.dedent()
            self.add_line("ENDIO;")

        self.dedent()
    
    def _convert_if_command(self, cmd: XeroxCommand, commands: List[XeroxCommand] = None, idx: int = -1):
        """
        Convert an IF command to DFA, handling ELSE and ENDIF at the same nesting level.

        Args:
            cmd: The IF command to convert
            commands: Full list of commands (for lookahead to find ELSE/ENDIF)
            idx: Current index of the IF command in the commands list

        Returns:
            Number of commands consumed (including IF, ELSE, ENDIF, and their bodies)
        """
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

        # Check for FRLEFT condition BEFORE converting comparison operators
        # (because we need to see 'lt' not '<')
        frleft_condition, is_frleft = self._convert_frleft_condition(clean_params)

        if is_frleft:
            # Use FRLEFT condition directly (already in DFA format)
            condition = frleft_condition
            needs_istrue = True
        else:
            # Convert comparison operators (eq -> ==, ne -> <>, etc.)
            converted_ops = self._convert_comparison_operators(clean_params)
            condition = " ".join(self._convert_params(converted_ops))
            # Check if condition needs ISTRUE() wrapper (has comparison operators)
            needs_istrue = any(op in condition for op in ['==', '<>', '>', '<', '>=', '<='])

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

        # Process children (IF body) if present
        if cmd.children:
            self._convert_case_commands(cmd.children)
            # IF blocks with children need ENDIF
            # No lookahead needed - children are already parsed
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
                var_name = cmd.parameters[0].lstrip('/')
                var_value = cmd.parameters[1]

                # Fix parameter order if they're swapped
                if var_name in ('++', '--', '+', '-', '*', '/'):
                    var_name, var_value = var_value.lstrip('/'), var_name

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
                        var_value = var_value.lstrip('/')
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
        font = "ARIAL8"
        position = ""
        align = ""
        is_variable_output = False
        format_string = None  # Will hold the FORMAT pattern if detected

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
                    # Variable reference - output the variable directly
                    text = param.lstrip('/')
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

        # Position SAME SAME BASELINE
        self.add_line("POSITION SAME SAME BASELINE")

        # Width for JUSTIFY
        if alignment == 3 and width:
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

        self.dedent()



    def _convert_output_command_dfa(self, cmd: XeroxCommand, x_pos: float, y_pos: float, current_font: str,
                                   x_was_set: bool = True, y_was_set: bool = True, y_is_next: bool = False):
        """Convert an output command to proper DFA OUTPUT with FONT and POSITION."""
        text = ""
        is_variable = False
        format_string = None  # Will hold the FORMAT pattern if detected

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
            # For width, use a default of 193 MM (common page width) for JUSTIFY
            width = 193.0 if alignment == 3 else None
            self._generate_text_baseline(text, current_font, (x_final, y_final), alignment, width)
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
            self.add_line(f"    {self._format_position(x_final, y_final)}")

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
        """Convert a box drawing command to proper DFA BOX with anchoring.

        Uses POSX/POSY anchors for relative positioning and inverts Y coordinates.

        VIPP: 00 -13.5 193 0.001 XDRK DRAWB (Y = -13.5)
        DFA:  POSITION (POSX+0 MM) (POSY+13.5 MM) (Y = +13.5)
        """
        if len(cmd.parameters) < 4:
            return

        # First box in a group should set anchors
        if self.should_set_box_anchor:
            self.add_line("POSY = $SL_CURRY;")
            self.add_line("POSX = $SL_CURRX;")
            self.should_set_box_anchor = False

        # Parse parameters
        try:
            x = float(cmd.parameters[0])
            y = float(cmd.parameters[1])
            width = float(cmd.parameters[2])
            height = float(cmd.parameters[3])
        except (ValueError, IndexError):
            return

        # Invert Y coordinate (negative becomes positive)
        y_inverted = abs(y)

        # Convert tiny widths/heights to 0.1 MM for thin lines
        if width < 0.01:
            width = 0.1
        if height < 0.01:
            height = 0.1

        # Parse color parameter if present
        color = None
        if len(cmd.parameters) >= 5:
            color_param = str(cmd.parameters[4]).upper()
            if color_param in ['LMED', 'MED', 'XDRK', 'FBLACK', 'LTHN', 'LTHK']:
                color = color_param

        # Generate BOX with anchored position
        self.add_line("BOX")
        self.indent()
        self.add_line(f"POSITION (POSX+{x} MM) (POSY+{y_inverted} MM)")
        self.add_line(f"WIDTH {width} MM HEIGHT {height} MM")

        # Add color if specified
        if color:
            self.add_line(f"COLOR {color}")

        # Use THICKNESS 0 for filled boxes (SHADE 100)
        self.add_line("THICKNESS 0 TYPE SOLID SHADE 100;")
        self.dedent()

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
                dfa_params.append(f"'{self._escape_dfa_quotes(text)}'")
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
        Cycles through all FRM files using P counter pattern.

        Order priority: S (subsequent) → F (first) → TNC → F3 → B (back) → others
        """
        # List available forms
        frm_names = []
        for frm_filename in sorted(self.frm_files.keys()):
            frm_name = os.path.splitext(frm_filename)[0].upper()
            frm_name = ''.join(c for c in frm_name if c.isalnum() or c == '_')
            frm_names.append(frm_name)

        if len(frm_names) == 0:
            return  # No forms to use

        # Custom sorting based on FRM naming conventions
        # Priority: S (subsequent) → F (first) → TNC → F3 → B (back) → B2 → others
        def frm_sort_key(name):
            base_name = name.rsplit('_', 1)[0] if '_' in name else name
            # Extract suffix (last character or _TNC)
            if name.endswith('_TNC'):
                suffix = '_TNC'
            elif name.endswith('S'):
                suffix = 'S'
            elif name.endswith('F3'):
                suffix = 'F3'
            elif name.endswith('F'):
                suffix = 'F'
            elif name.endswith('B2'):
                suffix = 'B2'
            elif name.endswith('B'):
                suffix = 'B'
            else:
                suffix = 'Z'  # Others at the end

            # Priority order
            priority = {
                'S': 0,     # Subsequent pages (CASIOS, SIBS_CASTS)
                'F': 1,     # First page (CASIOF, SIBS_CASTF)
                '_TNC': 2,  # Terms & Conditions (CASIO_TNC)
                'F3': 3,    # First page variant 3 (CASIOF3)
                'B': 4,     # Back page (CASIOB)
                'B2': 5,    # Back page variant 2 (CASIOB2)
                'Z': 99     # Others
            }

            return (priority.get(suffix, 99), base_name, name)

        frm_names = sorted(frm_names, key=frm_sort_key)

        # Generate cycling logic through all FRM files
        # Pattern: P counter cycles through FRM files (1, 2, 3, ..., N, then back to 1)
        for idx, frm_name in enumerate(frm_names, start=1):
            self.add_line(f"      IF P=={idx}; THEN; USE FORMAT {frm_name} EXTERNAL; ENDIF;")

        # Reset P if it exceeds the number of FRMs
        if frm_names:
            first_frm = frm_names[0]
            self.add_line(f"      IF P>{len(frm_names)}; THEN; P=1; USE FORMAT {first_frm} EXTERNAL; ENDIF;")

    def _generate_variable_initialization(self):
        """
        Generate variable initialization from DBM commands.

        Processes the initialization section at the beginning of the DBM file
        (typically a VARINI IF block) and extracts all /INI SETVAR commands.
        Since $_BEFOREFIRSTDOC only runs once, we don't need the VARINI IF pattern
        - variables don't exist yet so they will be created with these initial values.
        """
        self.add_line("/* Variable Initialization from DBM */")
        self.add_line("")

        # Extract /INI SETVAR commands from DBM
        # These are the variables defined with /INI flag in the VARINI block
        self._process_initialization_commands(self.dbm.commands)

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
                        # Variable name (remove leading /)
                        var_name = param[1:]
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
        self.add_line("")
        self.add_line("/* Transaction description counter (undeclared variable) */")
        self.add_line("VAR_COUNTTD = 0;")
        self.add_line("")
        self.add_line("/* Undeclared variables - incorrect values for BOXes */")
        self.add_line("VAR = MM(40);")
        self.add_line("Y5 = MM(40);")
        self.add_line("Y3 = MM(40);")
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

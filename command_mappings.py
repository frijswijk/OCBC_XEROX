"""
VIPP to DFA Command Mappings Reference

This module contains comprehensive mappings between Xerox VIPP commands and Papyrus DFA commands,
along with transformation logic for complex commands.
"""

# Comprehensive mappings of VIPP commands to DFA commands
VIPP_TO_DFA_COMMANDS = {
    # Positioning and movement
    'MOVETO': 'POSITION',
    'MOVEH': 'POSITION',
    'NL': 'OUTPUT_NL',        # Newline as OUTPUT '' POSITION SAME NEXT
    'SH': 'OUTPUT',           # Show text (default alignment)
    'SHL': 'OUTPUT',          # Left-aligned text
    'SHR': 'OUTPUT',          # Right-aligned text (uppercase R)
    'SHr': 'OUTPUT',          # Right-aligned text (lowercase r)
    'SHC': 'OUTPUT',          # Center-aligned text
    'SHP': 'OUTPUT',          # Parameterized alignment

    # Page orientation and units
    'PORT': 'PORT',
    'LAND': 'LAND',
    'MM': 'MM',
    'CM': 'CM',
    'INCH': 'INCH',
    'POINT': 'POINT',
    'SETUNIT': 'SETUNITS',
    'SETLSP': 'SETUNITS_LINESP',  # Line spacing - SETUNITS LINESP n MM

    # Flow control
    'IF': 'IF',
    'ENDIF': 'ENDIF',
    'ELSE': 'ELSE',
    'FOR': 'FOR',
    'ENDFOR': 'ENDFOR',

    # Variable handling
    'SETVAR': 'SETVAR',
    'VSUB': 'VSUB',           # Variable substitution

    # Drawing and resources
    'DRAWB': 'RULE',  # Lines in DFA use RULE command, not BOX
    'SCALL': 'SEGMENT',
    'ICALL': 'IMAGE',
    'CACHE': 'CACHE',
    'RULE': 'RULE',

    # NOTE: CLIP/ENDCLIP removed - DFA does not support clipping
    # Use MARGIN, SHEET/LOGICALPAGE dimensions, WIDTH on TEXT, or image size params instead

    # Forms and page handling
    'SETPAGEDEF': 'SETPAGEDEF',
    'SETFORM': 'SETFORM',
    'SETLKF': 'SETLKF',       # Link frame definition
    'BEGINPAGE': 'BEGINPAGE',
    'ENDPAGE': 'ENDPAGE',
    'PAGEBRK': '/* VIPP command not supported: PAGEBRK */',   # Page break trigger - not valid DFA
    'NEWFRAME': 'NEWFRAME',   # Frame overflow
    'SKIPPAGE': 'SKIPPAGE',   # Skip page logic

    # PDF features
    'BOOKMARK': 'BOOKMARK',   # PDF bookmark creation
    'SETPAGENUMBER': 'PAGENUMBER',  # Page numbering setup

    # String functions
    'GETINTV': 'SUBSTR',      # Interval/substring extraction
    'GETITEM': 'GETITEM',     # Get array item

    # Case handling
    'CASE': 'CASE',
    'ENDCASE': 'ENDCASE',

    # Records and data
    'RECORD': 'RECORD',
    'ENDIO': 'ENDIO',
    'OUTLINE': 'OUTLINE',
    'TABLE': 'TABLE',
    'COLUMN': 'COLUMN',
}

# VIPP alignment options to DFA alignment
VIPP_TO_DFA_ALIGNMENT = {
    'SH': '',               # Default alignment (left)
    'SHL': 'ALIGN LEFT',
    'SHR': 'ALIGN RIGHT',
    'SHr': 'ALIGN RIGHT',   # Lowercase r variant
    'SHC': 'ALIGN CENTER',
    'SHP': 'ALIGN PARAM',   # Parameterized alignment
}

# VIPP font styles to DFA font names
VIPP_TO_DFA_FONTS = {
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
}

# VIPP color names to DFA color names
VIPP_TO_DFA_COLORS = {
    'BLACK': 'BLACK',
    'WHITE': 'WHITE',
    'RED': 'RED',
    'GREEN': 'GREEN',
    'BLUE': 'BLUE',
    'YELLOW': 'YELLOW',
    'MAGENTA': 'MAGENTA',
    'CYAN': 'CYAN',
    'DARKGRAY': 'DARKGRAY',
    'LIGHTGRAY': 'LIGHTGRAY',
    'DARKRED': 'DARKRED',
    'DARKGREEN': 'DARKGREEN',
    'DARKBLUE': 'DARKBLUE',
    'ORANGE': 'ORANGE',
    'PURPLE': 'PURPLE',
}

# VIPP box drawing parameters to DFA parameters
VIPP_BOX_PARAMS = {
    'LMED': 'THICKNESS MEDIUM TYPE SOLID',
    'LTHN': 'THICKNESS THIN TYPE SOLID',
    'LTHK': 'THICKNESS THICK TYPE SOLID',
    'LDSH': 'THICKNESS MEDIUM TYPE DASHED',
    'LDOT': 'THICKNESS MEDIUM TYPE DOTTED',
    'F_S1': 'COLOR BLACK SHADE 100', 
    'F_S2': 'COLOR BLACK SHADE 75',
    'F_S3': 'COLOR BLACK SHADE 50',
    'F_S4': 'COLOR BLACK SHADE 25',
    'R_S1': 'COLOR RED SHADE 100',
    'R_S2': 'COLOR RED SHADE 75',
    'R_S3': 'COLOR RED SHADE 50',
    'R_S4': 'COLOR RED SHADE 25',
    'G_S1': 'COLOR GREEN SHADE 100',
    'G_S2': 'COLOR GREEN SHADE 75',
    'G_S3': 'COLOR GREEN SHADE 50',
    'G_S4': 'COLOR GREEN SHADE 25',
    'B_S1': 'COLOR BLUE SHADE 100',
    'B_S2': 'COLOR BLUE SHADE 75',
    'B_S3': 'COLOR BLUE SHADE 50',
    'B_S4': 'COLOR BLUE SHADE 25',
}

# Special VIPP commands and their DFA equivalents
VIPP_SPECIAL_COMMANDS = {
    'TXNB': 'BOX',               # Transaction box in bank statements
    'ORITL': 'ORIENTATION',      # Page orientation
    'SETPAGENUMBER': 'PAGENUMBER', # Page numbering
    'SETFTSW': 'SETFTSW',        # Font switch character
    'SETPARAMS': None,           # No direct equivalent, needs special handling
    'XGFRESDEF': None,           # No direct equivalent, resource definition
}

# VIPP operators to DFA operators
VIPP_TO_DFA_OPERATORS = {
    # Standard operators
    '==': '==',
    '!=': '<>',
    '<': '<',
    '>': '>',
    '<=': '<=',
    '>=': '>=',
    '&&': 'AND',
    '||': 'OR',
    '!': 'NOT',
    '+': '+',
    '-': '-',
    '*': '*',
    '/': '/',
    '++': None,    # Needs translation to VAR = VAR + 1
    '--': None,    # Needs translation to VAR = VAR - 1

    # VIPP PostScript-style comparison operators
    'eq': '==',    # Equal
    'ne': '<>',    # Not equal
    'lt': '<',     # Less than
    'gt': '>',     # Greater than
    'le': '<=',    # Less than or equal
    'ge': '>=',    # Greater than or equal
}

# VIPP system variables to DFA system variables
VIPP_TO_DFA_SYSTEM_VARS = {
    '_PAGE': '_PAGE',            # Current page number
    '_MAXPAGE': '_MAXPAGE',      # Maximum page number
    '$SL_CURRX': '$SL_CURRX',    # Current X position in sublevel
    '$SL_CURRY': '$SL_CURRY',    # Current Y position in sublevel
    '$SL_XPOS': '$SL_XPOS',      # X position in sublevel
    '$SL_YPOS': '$SL_YPOS',      # Y position in sublevel
    '$SL_LMINX': '$SL_LMINX',    # Last minimum X position in sublevel
    '$SL_LMINY': '$SL_LMINY',    # Last minimum Y position in sublevel
    '$SL_LMAXX': '$SL_LMAXX',    # Last maximum X position in sublevel
    '$SL_LMAXY': '$SL_LMAXY',    # Last maximum Y position in sublevel
    '$ML_XPOS': '$ML_XPOS',      # X position in main level
    '$ML_YPOS': '$ML_YPOS',      # Y position in main level
    '$ML_LMINX': '$ML_LMINX',    # Last minimum X position in main level
    '$ML_LMINY': '$ML_LMINY',    # Last minimum Y position in main level
    '$ML_LMAXX': '$ML_LMAXX',    # Last maximum X position in main level
    '$ML_LMAXY': '$ML_LMAXY',    # Last maximum Y position in main level
    '$MR_LEFT': '$MR_LEFT',      # Left margin
    '$MR_RIGHT': '$MR_RIGHT',    # Right margin
    '$MR_TOP': '$MR_TOP',        # Top margin
    '$MR_BOTTOM': '$MR_BOTTOM',  # Bottom margin
    '$LP_WIDTH': '$LP_WIDTH',    # Logical page width
    '$LP_HEIGHT': '$LP_HEIGHT',  # Logical page height
    '$LINESP': '$LINESP',        # Line spacing
    '$FONT_CDP': '$FONT_CDP',    # Font code page
}

# VIPP functions to DFA functions
VIPP_TO_DFA_FUNCTIONS = {
    'GETITEM': 'GETITEM',        # Get array item
    'GETINTV': 'GETINTV',        # Get interval from string
    'LEFT': 'LEFT',              # Left substring
    'RIGHT': 'RIGHT',            # Right substring
    'SUBSTR': 'SUBSTR',          # Substring
    'MAXINDEX': 'MAXINDEX',      # Maximum index of array
    'NOSPACE': 'NOSPACE',        # Remove spaces
    'EXTRACT': 'EXTRACT',        # Extract part of string
    'EXTRACTALL': 'EXTRACTALL',  # Extract all parts of string into array
    'CHANGE': 'CHANGE',          # Change substring
    'SUBCHANGE': 'SUBCHANGE',    # Change using substitution table
    'POS': 'POS',                # Position of substring
    'LENGTH': 'LENGTH',          # Length of string
    'CONVERT': 'CONVERT',        # Convert using external function
    'UPPER': 'UPPER',            # Convert to uppercase
    'LOWER': 'LOWER',            # Convert to lowercase
    'UNHEX': 'UNHEX',            # Convert hex to decimal
    'CHAR': 'CHAR',              # Character from code
    'MM': 'MM',                  # Millimeters
    'CM': 'CM',                  # Centimeters 
    'INCH': 'INCH',              # Inches
    'POINT': 'POINT',            # Points
}

def translate_vipp_command(cmd_name, params):
    """
    Translates a VIPP command and its parameters to the corresponding DFA command.
    
    Args:
        cmd_name: The VIPP command name
        params: List of parameters
        
    Returns:
        Tuple of (dfa_cmd, dfa_params)
    """
    # First check direct mappings
    dfa_cmd = VIPP_TO_DFA_COMMANDS.get(cmd_name)
    
    # If no direct mapping, check special commands
    if not dfa_cmd and cmd_name in VIPP_SPECIAL_COMMANDS:
        dfa_cmd = VIPP_SPECIAL_COMMANDS.get(cmd_name)
    
    # If still no mapping, keep the original name as fallback
    if not dfa_cmd:
        dfa_cmd = cmd_name
    
    # Special handling for specific commands
    if cmd_name in ('SHL', 'SHR', 'SHC', 'SHP'):
        # Text output commands
        return translate_output_command(cmd_name, params)
    elif cmd_name == 'MOVETO' or cmd_name == 'MOVEH':
        # Positioning commands
        return translate_position_command(cmd_name, params)
    elif cmd_name == 'DRAWB':
        # Box drawing
        return translate_box_command(params)
    elif cmd_name == 'SCALL' or cmd_name == 'ICALL':
        # Resource handling
        return translate_resource_command(cmd_name, params)
    elif cmd_name == 'SETVAR':
        # Variable assignment
        return translate_variable_assignment(params)
    elif cmd_name == 'IF' or cmd_name == 'ELSE' or cmd_name == 'ENDIF':
        # Conditional commands
        return translate_conditional_command(cmd_name, params)
    elif cmd_name == 'FOR' or cmd_name == 'ENDFOR':
        # Loop commands
        return translate_loop_command(cmd_name, params)
    elif cmd_name == 'CASE':
        # Case statement
        return translate_case_command(params)
    elif cmd_name == 'TXNB':
        # Special transaction box
        return translate_txnb_command(params)
    else:
        # Default parameter handling for other commands
        dfa_params = translate_params(params)
        return (dfa_cmd, dfa_params)

def translate_output_command(cmd_name, params):
    """
    Translates a VIPP output command (SHL, SHR, SHC, SHP) to DFA OUTPUT.
    
    Args:
        cmd_name: VIPP command name
        params: VIPP parameters
        
    Returns:
        Tuple of (dfa_cmd, dfa_params) where dfa_params includes text, font, position and alignment
    """
    dfa_cmd = 'OUTPUT'
    dfa_params = {
        'text': '',
        'font': None,
        'position': None,
        'align': VIPP_TO_DFA_ALIGNMENT.get(cmd_name, '')
    }
    
    # Extract text and parameters
    for param in params:
        if param.startswith('/'):
            # Font reference
            font_name = param.lstrip('/')
            dfa_params['font'] = font_name
        elif param.startswith('(') and param.endswith(')'):
            # Text string
            dfa_params['text'] = param.strip('()')
    
    return (dfa_cmd, dfa_params)

def translate_position_command(cmd_name, params):
    """
    Translates a VIPP positioning command to DFA POSITION.
    
    Args:
        cmd_name: VIPP command name
        params: VIPP parameters
        
    Returns:
        Tuple of (dfa_cmd, dfa_params)
    """
    dfa_cmd = 'POSITION'
    dfa_params = {}
    
    if cmd_name == 'MOVETO' and len(params) >= 2:
        # MOVETO x y => POSITION x MM y MM
        x, y = params[0], params[1]
        dfa_params['x'] = f"{x} MM"
        dfa_params['y'] = f"{y} MM"
    elif cmd_name == 'MOVEH' and len(params) >= 1:
        # MOVEH x => POSITION x MM SAME
        x = params[0]
        dfa_params['x'] = f"{x} MM"
        dfa_params['y'] = "SAME"
    
    return (dfa_cmd, dfa_params)

def translate_box_command(params):
    """
    Translates a VIPP DRAWB command to DFA BOX.
    
    Args:
        params: VIPP parameters
        
    Returns:
        Tuple of (dfa_cmd, dfa_params)
    """
    dfa_cmd = 'BOX'
    dfa_params = {
        'position': 'POSITION 0 0',
        'width': 'WIDTH 10 MM',
        'height': 'HEIGHT 10 MM',
        'thickness': 'THICKNESS MEDIUM',
        'type': 'TYPE SOLID',
        'color': 'COLOR BLACK'
    }
    
    # Parse parameters
    if len(params) >= 4:
        # DRAWB x y width height [style]
        x, y, width, height = params[0:4]
        dfa_params['position'] = f"POSITION {x} MM {y} MM"
        dfa_params['width'] = f"WIDTH {width} MM"
        dfa_params['height'] = f"HEIGHT {height} MM"
        
        # Check for style parameter
        if len(params) >= 5:
            style = params[4]
            if style in VIPP_BOX_PARAMS:
                style_params = VIPP_BOX_PARAMS[style].split()
                for i in range(0, len(style_params), 2):
                    if i+1 < len(style_params):
                        param_name = style_params[i].lower()
                        param_value = style_params[i+1]
                        if param_name == 'thickness':
                            dfa_params['thickness'] = f"THICKNESS {param_value}"
                        elif param_name == 'type':
                            dfa_params['type'] = f"TYPE {param_value}"
                        elif param_name == 'color':
                            dfa_params['color'] = f"COLOR {param_value}"
                        elif param_name == 'shade':
                            dfa_params['shade'] = f"SHADE {param_value}"
    
    return (dfa_cmd, dfa_params)

def translate_resource_command(cmd_name, params):
    """
    Translates a VIPP resource command (SCALL/ICALL) to DFA SEGMENT/IMAGE.
    
    Args:
        cmd_name: VIPP command name
        params: VIPP parameters
        
    Returns:
        Tuple of (dfa_cmd, dfa_params)
    """
    if cmd_name == 'SCALL':
        dfa_cmd = 'SEGMENT'
    else:  # ICALL
        dfa_cmd = 'IMAGE'
    
    dfa_params = {
        'name': '',
        'position': 'POSITION 0 0',
        'scale': None
    }
    
    # Extract resource name and parameters
    for i, param in enumerate(params):
        if param.startswith('(') and param.endswith(')') and i == 0:
            # Resource name
            dfa_params['name'] = param.strip('()')
        elif i == 1 and cmd_name == 'SCALL':
            # Scale factor for SCALL
            dfa_params['scale'] = param
    
    return (dfa_cmd, dfa_params)

def translate_variable_assignment(params):
    """
    Translates a VIPP SETVAR command to DFA variable assignment.
    
    Args:
        params: VIPP parameters
        
    Returns:
        Tuple of (dfa_cmd, dfa_params)
    """
    dfa_cmd = 'SETVAR'
    dfa_params = {
        'variable': '',
        'value': ''
    }
    
    if len(params) >= 2:
        var_name = params[0].lstrip('/')
        var_value = params[1]
        dfa_params['variable'] = var_name
        dfa_params['value'] = var_value
    
    return (dfa_cmd, dfa_params)

def translate_conditional_command(cmd_name, params):
    """
    Translates a VIPP conditional command (IF/ELSE/ENDIF) to DFA.
    
    Args:
        cmd_name: VIPP command name
        params: VIPP parameters
        
    Returns:
        Tuple of (dfa_cmd, dfa_params)
    """
    # Direct mapping for these commands
    dfa_cmd = VIPP_TO_DFA_COMMANDS.get(cmd_name, cmd_name)
    dfa_params = {}
    
    if cmd_name == 'IF':
        # Translate condition
        condition = ' '.join(translate_params(params))
        dfa_params['condition'] = condition
    
    return (dfa_cmd, dfa_params)

def translate_loop_command(cmd_name, params):
    """
    Translates a VIPP loop command (FOR/ENDFOR) to DFA.
    
    Args:
        cmd_name: VIPP command name
        params: VIPP parameters
        
    Returns:
        Tuple of (dfa_cmd, dfa_params)
    """
    # Direct mapping for these commands
    dfa_cmd = VIPP_TO_DFA_COMMANDS.get(cmd_name, cmd_name)
    dfa_params = {}
    
    if cmd_name == 'FOR':
        # Extract loop parameters
        if len(params) >= 1:
            dfa_params['variable'] = params[0].lstrip('/')
            
            if len(params) >= 3 and params[1].upper() == 'REPEAT':
                dfa_params['repeat'] = params[2]
    
    return (dfa_cmd, dfa_params)

def translate_case_command(params):
    """
    Translates a VIPP CASE command to DFA CASE.
    
    Args:
        params: VIPP parameters
        
    Returns:
        Tuple of (dfa_cmd, dfa_params)
    """
    dfa_cmd = 'CASE'
    dfa_params = {
        'value': ''
    }
    
    if len(params) >= 1:
        case_value = params[0]
        # If enclosed in parentheses, strip them
        if case_value.startswith('(') and case_value.endswith(')'):
            case_value = case_value.strip('()')
        dfa_params['value'] = case_value
    
    return (dfa_cmd, dfa_params)

def translate_txnb_command(params):
    """
    Translates a VIPP TXNB command (transaction box) to DFA BOX.
    
    Args:
        params: VIPP parameters
        
    Returns:
        Tuple of (dfa_cmd, dfa_params)
    """
    # TXNB is a custom-defined box in VIPP, translate to standard BOX
    dfa_cmd = 'BOX'
    dfa_params = {
        'position': 'POSITION 0 0',
        'width': 'WIDTH 188 MM',
        'height': 'HEIGHT 9 MM',
        'thickness': 'THICKNESS MEDIUM',
        'type': 'TYPE SOLID'
    }
    
    return (dfa_cmd, dfa_params)

def translate_params(params):
    """
    Translates a list of VIPP parameters to DFA format.
    
    Args:
        params: List of VIPP parameters
        
    Returns:
        List of DFA parameters
    """
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
        # Handle system variables
        elif param.startswith('$') or param.startswith('_'):
            sys_var = VIPP_TO_DFA_SYSTEM_VARS.get(param, param)
            dfa_params.append(sys_var)
        # Pass other parameters through
        else:
            dfa_params.append(param)
    
    return dfa_params
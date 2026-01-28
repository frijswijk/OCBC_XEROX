# OCBC Xerox to DFA Converter

A comprehensive Python-based converter for transforming Xerox VIPP (Variable data Intelligent PostScript Printware) files to ISIS Papyrus DFA (DocDef) format, developed for OCBC bank document migration.

## Overview

This project provides automated conversion tools for migrating Xerox FreeFlow variable data printing jobs to ISIS Papyrus document processing format. The converter handles complex PostScript-based VIPP syntax and generates equivalent DFA code with proper structure, formatting, and logic preservation.

## Features

- **Complete VIPP Parser**: Handles PostScript/RPN syntax including stack operations
- **Command Mapping**: Comprehensive Xerox to DFA command translation
- **Font System**: Automatic font family mapping and conversion
- **Color Management**: RGB/CMYK color space conversion
- **Layout Preservation**: Maintains positioning, margins, and page structure
- **Variable Substitution**: VSUB command processing with pattern matching
- **Resource Handling**: External resource references (fonts, images)
- **Validation**: DFA field validation and syntax checking
- **Test Suite**: Comprehensive testing framework

## Project Structure

```
OCBC_XEROX/
├── universal_xerox_parser.py      # Main conversion engine (210KB)
├── xerox_jdt_dfa.py              # Xerox JDT to DFA converter (257KB)
├── command_mappings.py            # Command mapping definitions (18KB)
├── conversion_example.py          # Usage examples
├── validate_dfa_fields.py        # DFA validation tool
├── debug_vsub.py                 # VSUB debugging utility
├── test_*.py                     # Test suite
├── XEROX2DFA.MD                  # Complete conversion guide
├── output/                       # Generated DFA files
├── SamplePDF/                    # Sample Xerox files
└── snapshot_working_jan9/        # Stable version backup
```

## Quick Start

### Prerequisites

- Python 3.6 or higher
- No external dependencies required

### Basic Usage

```bash
# Convert Xerox files to DFA
python universal_xerox_parser.py <input_directory>

# Example
python universal_xerox_parser.py "SamplePDF/SIBS_CAST - codes"
```

### What It Does

1. Scans input directory for VIPP files (.DBM, .FRM)
2. Parses PostScript/RPN syntax with stack operations
3. Converts Xerox commands to DFA equivalents
4. Generates DFA files in `output/` directory
5. Creates HTML reports for validation

## Input Files

The converter processes:

- **DBM files** (.DBM) - Database modules with data processing logic
- **FRM files** (.FRM) - Form templates with layout/design
- **JDT files** (.JDT) - Job definition tickets

**Example directory structure:**
```
SamplePDF/SIBS_CAST/
├── SIBS_CAST.DBM          # Main processing logic
├── SIBS_CASTF.FRM         # First page form template
├── SIBS_CASTS.FRM         # Subsequent page form
└── SIBS_CAST.JDT          # Job definition
```

## Conversion Architecture

### Xerox VIPP vs DFA

| Aspect | VIPP | DFA |
|--------|------|-----|
| **Syntax** | PostScript RPN | Procedural/declarative |
| **Comments** | `%` line, `/* */` block | `/* */` block |
| **Variables** | `/VAR value SETVAR` | `VAR = value;` |
| **Strings** | `(text)` parentheses | `'text'` quotes |
| **Operators** | `eq ne lt gt` | `== <> < >` |
| **Position** | `X Y MOVETO` | `POSITION X Y` |
| **Output** | `(text) SHOW` | `OUTPUT 'text'` |

### Command Conversion Examples

**Font Selection:**
```
Xerox: /Helvetica 10 SELECTFONT
DFA:   FONT HELVETICA ... HEIGHT 10.0;
```

**Text Output:**
```
Xerox: (Hello World) SHOW
DFA:   OUTPUT 'Hello World';
```

**Variable Assignment:**
```
Xerox: /CUSTOMER (John Doe) SETVAR
DFA:   CUSTOMER = 'John Doe';
```

**Positioning:**
```
Xerox: 100 200 MOVETO
DFA:   POSITION 100 MM 200 MM
```

## Python Modules

### Core Converter (`universal_xerox_parser.py`)

**Main conversion engine with:**
- PostScript RPN parser with stack simulation
- Command translation engine
- Variable substitution (VSUB) processor
- Font and color mapping
- Layout management
- Resource handling

**Usage:**
```python
python universal_xerox_parser.py <input_dir>
```

### JDT Converter (`xerox_jdt_dfa.py`)

**Job Definition Ticket converter:**
- JDT parsing and transformation
- Job parameter mapping
- Resource linking

### Command Mappings (`command_mappings.py`)

**Comprehensive mapping database:**
- 100+ Xerox commands mapped to DFA
- Font family mappings
- Color space conversions
- Operator translations

### Validation (`validate_dfa_fields.py`)

**DFA syntax validator:**
- Field syntax checking
- Command structure validation
- Error reporting

### Testing Suite

- `test_dfa_simulation.py` - DFA simulation tests
- `test_frm_conversion.py` - FRM format tests
- `test_negative_nl_conversion.py` - Negative number line tests
- `test_vsub.py` - Variable substitution tests
- `debug_vsub.py` - VSUB debugging tool

## Key Features

### 1. VSUB (Variable Substitution)

Processes pattern-based variable substitution:

```
Xerox: (%DATE%) ('2024-01-15') VSUB
DFA:   DATE = '2024-01-15';
```

### 2. Font Mapping

Automatic font family conversion:

| Xerox Font | DFA Font |
|------------|----------|
| Helvetica | ARIAL |
| Times | TIMES |
| Courier | COURIER |
| UniversCondensed | UNIVERS |

### 3. Color System

RGB and CMYK color space support:

```
Xerox: 0.5 0.5 0.5 SETGRAY
DFA:   COLOR RGB 128 128 128;
```

### 4. Layout System

Page layout with margins and positioning:

```
DFA:
MARGIN TOP 20 MM BOTTOM 20 MM LEFT 15 MM RIGHT 15 MM;
POSITION 100 MM 200 MM;
```

### 5. Variable System

User and system variables:

```
DFA:
VARIABLE CUSTOMER START 1 LENGTH 50;
VARIABLE &GLOBAL_VAR;
```

## Sample Conversions

### SIBS_CAST Project

**Input:**
- SIBS_CAST.DBM - Main database module
- SIBS_CASTF.FRM - First page form
- SIBS_CASTS.FRM - Subsequent pages

**Output:**
- SIBS_CAST.dfa - Complete DFA document definition

### CASIO Project

**Input:**
- CASIO.DBM - Processing logic
- CASIOF.FRM - Forms

**Output:**
- CASIO.dfa - Converted DFA

## Testing and Validation

### Running Tests

```bash
# Run all tests
python test_dfa_simulation.py
python test_frm_conversion.py
python test_vsub.py

# Debug VSUB processing
python debug_vsub.py
```

### Validation

```bash
# Validate generated DFA
python validate_dfa_fields.py output/SIBS_CAST.dfa
```

## Documentation

Complete documentation available in:

- **XEROX2DFA.MD** - Complete conversion guide (100+ pages)
  - Command reference
  - Conversion examples
  - Best practices
  - Troubleshooting

- **Analysis Reports:**
  - `DFA_TEST_REPORT.md` - Testing results
  - `ANALYSIS_REPORT.md` - Code analysis
  - `FIXES_IMPLEMENTED_SUMMARY.md` - Bug fixes
  - `SESSION_SUMMARY.md` - Development sessions
  - `SIBS_VS_CASIO_COMPARISON.md` - Project comparison

## Recent Updates

### Version 3.0 (January 9, 2026)

- Enhanced VSUB processing
- Negative number line handling
- FRM format improvements
- Shape width implementation
- Isolated ENDIF fixes
- LUCA round 2 corrections

See individual summary files for detailed changelogs:
- `ADDITIONAL_ADJUSTMENTS_SUMMARY.md`
- `FIXES_IMPLEMENTED_SUMMARY.md`
- `NEGATIVE_NL_FIX_SUMMARY.md`
- `PARSER_FIXES_SUMMARY.md`
- `SHP_WIDTH_IMPLEMENTATION_SUMMARY.md`

## Sample Data

Located in `SamplePDF/`:
- Xerox FreeFlow reference guides (PDF)
- Sample VIPP files (.DBM, .FRM, .JDT)
- Test data archives (.7z)

## Configuration

### Conversion Settings

Edit `universal_xerox_parser.py` for:
- Output directory path
- Font mapping tables
- Color conversion rules
- Default margins and units
- Validation rules

## Output Files

Generated in `output/`:
- `.dfa` files - DFA document definitions
- `.html` files - Visual reports for validation
- Subdirectories for multi-file conversions

## Troubleshooting

### Common Issues

1. **Font mapping errors**
   - Check `command_mappings.py` font table
   - Add missing fonts to mapping

2. **VSUB processing**
   - Use `debug_vsub.py` for debugging
   - Check pattern matching rules

3. **Layout issues**
   - Verify positioning units (MM, INCH, POINT)
   - Check margin calculations

4. **Validation errors**
   - Run `validate_dfa_fields.py`
   - Check DFA syntax in output

See `XEROX2DFA.MD` for detailed troubleshooting guide.

## Development Snapshots

- `snapshot_working_jan9/` - Stable version from January 9, 2026
- Contains backup of working parser before major changes

## Technologies

- **Python 3.6+** - Core language
- **No external dependencies** - Pure Python implementation
- **PostScript parsing** - Custom RPN parser
- **Stack simulation** - For PostScript operations

## Integration

The converter integrates with:
- **ISIS Papyrus** - Production DFA runtime
- **DFA Language Server** - IDE support and validation
- **IntelliSTOR** - Document processing pipeline

## Use Cases

1. **Bank Document Migration** - OCBC Xerox to Papyrus migration
2. **Statement Generation** - Customer statements conversion
3. **Form Templates** - Business forms transformation
4. **Variable Data Printing** - VDP job migration
5. **Multi-Channel Output** - Print, PDF, email delivery

## Best Practices

1. Test conversions with sample data before production
2. Validate output DFA files with validation tools
3. Review generated HTML reports for accuracy
4. Maintain backup of working versions
5. Document custom mappings and modifications

## Contributing

Areas for improvement:
- Additional Xerox command support
- Enhanced error handling
- Performance optimization
- Extended validation rules
- GUI conversion tool

## Version History

- **v3.0** (Jan 9, 2026) - VSUB enhancements, FRM fixes
- **v2.0** - Major parser refactor
- **v1.0** - Initial release

## License

Proprietary - OCBC Xerox to DFA Migration Project

## Credits

- Developed by Claude Opus 4.5 and Claude Sonnet 4.5
- For OCBC Bank document migration project
- Based on Xerox FreeFlow VIPP and ISIS Papyrus DFA specifications

## Support

For issues or questions:
- Review `XEROX2DFA.MD` complete guide
- Check analysis and summary documentation
- Run validation and test tools
- Examine HTML output reports

## Related Projects

- **DFA** - DFA language server and tools
- **IntelliSTOR** - Document processing and pattern recognition
- **IntelliSTOR_Migration** - Database migration tools

Last Updated: 2026-01-28

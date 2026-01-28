# Universal Xerox FreeFlow to Papyrus DocDEF Converter

This tool converts Xerox FreeFlow Designer files (DBM and FRM) to Papyrus DocDEF (DFA) format. It provides a comprehensive solution for migrating Xerox document applications to the Papyrus platform.

## Features

- Parses Xerox FreeFlow DBM and FRM files
- Extracts fonts, colors, variables, and resource definitions
- Converts VIPP commands to equivalent Papyrus DFA commands
- Handles case-based record processing structures
- Preserves page layout and formatting
- Supports resource extraction and copying
- Generates detailed conversion reports

## Requirements

- Python 3.7 or higher
- No external dependencies beyond the Python standard library

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/xerox-to-papyrus.git
cd xerox-to-papyrus
```

2. (Optional) Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Usage

### Basic Usage

Convert a single Xerox FreeFlow DBM file:

```bash
python universal_xerox_parser.py path/to/your/file.dbm --output_dir output_directory
```

Convert all Xerox FreeFlow files in a directory:

```bash
python universal_xerox_parser.py path/to/your/directory --output_dir output_directory
```

### Command Line Options

```
usage: universal_xerox_parser.py [-h] [--output_dir OUTPUT_DIR] [--verbose] [--single_file] [--report] input_path

Convert Xerox FreeFlow to Papyrus DocDEF

positional arguments:
  input_path            Path to Xerox file or directory containing Xerox files

optional arguments:
  -h, --help            show this help message and exit
  --output_dir OUTPUT_DIR, -o OUTPUT_DIR
                        Directory for output DFA files
  --verbose, -v         Enable verbose logging
  --single_file, -s     Process a single file instead of a directory
  --report, -r          Generate a conversion report
```

### Example: Converting the SIBS_CAST.DBM Sample

```bash
python conversion_example.py --input_dir samples --output_dir output
```

## Conversion Process

The converter works in these main steps:

1. **Parsing**: Reads and tokenizes the Xerox FreeFlow files
2. **Analysis**: Analyzes the structure, variables, and resources
3. **Transformation**: Maps VIPP commands to Papyrus DFA commands
4. **Generation**: Generates the complete DFA file with equivalent functionality

## Supported VIPP Commands

The converter supports a wide range of VIPP commands including:

- Positioning and movement (MOVETO, MOVEH, NL)
- Text output (SHL, SHR, SHC, SHP)
- Flow control (IF/ELSE/ENDIF, FOR/ENDFOR)
- Variable handling (SETVAR)
- Drawing (DRAWB, RULE)
- Resource handling (SCALL, ICALL)
- Page and form handling

## Limitations

- Some advanced VIPP features may require manual adjustment after conversion
- Custom resources need to be available in both environments
- Complex conditional logic might need optimization
- Highly specialized Xerox extensions may not have direct equivalents

## Post-Conversion Steps

After converting your application, you should:

1. Open the generated DFA file in Papyrus Designer
2. Verify the input data reading structure
3. Check the layout and formatting
4. Make any necessary adjustments to match the original output
5. Ensure all referenced resources are available
6. Run tests with sample data

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This tool was created to facilitate migrations from Xerox FreeFlow to Papyrus DocDEF
- Based on the VIPP Language Reference Manual for command mappings

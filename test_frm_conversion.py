#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test FRM Conversion with Position Corrections
"""

import os
import sys
import logging

# Import the converter modules
from universal_xerox_parser import XeroxParser, VIPPToDFAConverter

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('FRMTest')

def convert_frm_files():
    """Convert the FRM files to DFA format."""

    input_dir = "SamplePDF/SIBS_CAST - codes"
    output_dir = "output_test_corrections"

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Parse the DBM file first (needed for context)
    dbm_path = os.path.join(input_dir, 'SIBS_CAST.DBM')
    xerox_parser = XeroxParser()

    try:
        dbm = xerox_parser.parse_file(dbm_path)

        # Find and parse FRM files
        frm_files = {}
        for file in os.listdir(input_dir):
            if file.endswith('.FRM') or file.endswith('.frm'):
                frm_path = os.path.join(input_dir, file)
                try:
                    frm = xerox_parser.parse_file(frm_path)
                    frm_files[file] = frm
                    logger.info(f"Parsed FRM file: {frm_path}")
                except Exception as e:
                    logger.error(f"Error parsing FRM file {frm_path}: {e}")

        # Create converter
        converter = VIPPToDFAConverter(dbm, frm_files)

        # Generate DFA code for each FRM file
        for frm_filename, frm in frm_files.items():
            logger.info(f"Generating DFA for FRM: {frm_filename}")
            dfa_code = converter.generate_frm_dfa_code(frm)

            # Write output file
            frm_base = os.path.splitext(frm_filename)[0]
            output_path = os.path.join(output_dir, f'{frm_base}.dfa')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(dfa_code)

            logger.info(f"Generated: {output_path}")

            # Display statistics
            line_count = dfa_code.count('\n') + 1
            logger.info(f"  - {line_count} lines of code")

        return 0

    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(convert_frm_files())

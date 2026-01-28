#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIBS_CAST.DBM Conversion Example

This script demonstrates how to convert the SIBS_CAST.DBM file to Papyrus DocDEF format
using the Universal Xerox FreeFlow to Papyrus DocDEF Converter.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add the parent directory to the Python path to import the converter
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)

# Import the converter modules
from universal_xerox_parser import XeroxParser, VIPPToDFAConverter

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ConversionExample')

def convert_sibs_cast():
    """Convert the SIBS_CAST.DBM file to DFA format."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert SIBS_CAST.DBM to Papyrus DocDEF')
    parser.add_argument('--input_dir', default='input', help='Directory containing SIBS_CAST.DBM and related files')
    parser.add_argument('--output_dir', default='output', help='Directory for output DFA file')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Full paths
    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir)
    
    # Find the DBM file
    dbm_path = os.path.join(input_dir, 'SIBS_CAST.DBM')
    if not os.path.exists(dbm_path):
        logger.error(f"DBM file not found: {dbm_path}")
        return 1
    
    # Parse the DBM file
    logger.info(f"Parsing DBM file: {dbm_path}")
    xerox_parser = XeroxParser()
    
    try:
        dbm = xerox_parser.parse_file(dbm_path)
        
        # Find related FRM files
        frm_files = {}
        for file in os.listdir(input_dir):
            if file.endswith('.FRM') or file.endswith('.frm'):
                frm_path = os.path.join(input_dir, file)
                try:
                    frm = xerox_parser.parse_file(frm_path)
                    frm_files[file] = frm
                    logger.info(f"Parsed related FRM file: {frm_path}")
                except Exception as e:
                    logger.error(f"Error parsing FRM file {frm_path}: {e}")
        
        # Create converter
        converter = VIPPToDFAConverter(dbm, frm_files)
        
        # Generate DFA code
        logger.info("Generating DFA code...")
        dfa_code = converter.generate_dfa_code()
        
        # Write output file
        output_path = os.path.join(output_dir, 'SIBS_CAST.dfa')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(dfa_code)
        
        logger.info(f"Conversion complete! Output saved to: {output_path}")
        
        # Display output statistics
        line_count = dfa_code.count('\n') + 1
        logger.info(f"Generated DFA file has {line_count} lines of code")
        
        # Suggest next steps
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Open the generated DFA file in Papyrus Designer")
        logger.info("2. Verify the input data reading structure")
        logger.info("3. Check the layout and formatting")
        logger.info("4. Make any necessary adjustments to match the original output")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(convert_sibs_cast())

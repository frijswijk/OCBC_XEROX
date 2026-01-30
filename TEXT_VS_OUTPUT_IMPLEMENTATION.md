# TEXT vs OUTPUT Decision Logic Implementation

## Overview

Successfully implemented intelligent decision logic to choose between `OUTPUT` and `TEXT BASELINE` commands based on text characteristics, improving DFA output quality and reducing line count.

## Changes Made

### 1. Added Helper Methods to VIPPToDFAConverter Class

#### `_should_use_text_baseline(text, params, alignment)`
**Location:** `universal_xerox_parser.py` line 4920

**Purpose:** Determines whether to use TEXT BASELINE instead of OUTPUT

**Decision Criteria:**
- ✅ **JUSTIFY alignment** (alignment == 3) → Use TEXT BASELINE
  - OUTPUT doesn't support JUSTIFY, only LEFT/RIGHT/CENTER
- ✅ **Long text** (> 50 characters) → Use TEXT BASELINE
  - Reduces verbosity and improves readability
- ✅ **Font style markers** (`**BOLD`, `**ITALIC`, `**F5`, `**FC`) → Use TEXT BASELINE
  - Handles inline style changes properly
- ✅ **Multiple font references** in parameters → Use TEXT BASELINE
  - Supports complex typography

#### `_generate_text_baseline(text, font, position, alignment, width)`
**Location:** `universal_xerox_parser.py` line 4954

**Purpose:** Generates proper TEXT BASELINE output

**Features:**
- Uses `POSITION SAME SAME BASELINE` for proper text flow
- Adds `WIDTH` parameter for JUSTIFY alignment (default: 193 MM)
- Automatically splits long text at ~70 characters at word boundaries
- Properly escapes quotes in text
- Handles all alignment types: LEFT, RIGHT, CENTER, JUSTIFY

### 2. Modified `_convert_output_command_dfa` Method
**Location:** `universal_xerox_parser.py` line 5019-5120

**Changes:**
- Added decision logic before generating output (line 5091)
- Calls `_should_use_text_baseline()` for literal text (not variables)
- Routes to `_generate_text_baseline()` when conditions are met
- Removed JUSTIFY from OUTPUT alignment options (line 5109-5118)
  - OUTPUT now only supports LEFT, RIGHT, CENTER
  - JUSTIFY automatically uses TEXT BASELINE

### 3. Fixed Missing Code
**Location:** `universal_xerox_parser.py` line 4917

- Added missing `self.add_line(" ".join(output_parts) + ";")` statement
- Fixed incomplete `_convert_output_command` method

## Test Results

All tests passed successfully:

### Test 1: Decision Logic
- ✅ Short text with LEFT → Uses OUTPUT
- ✅ Long text (>50 chars) → Uses TEXT BASELINE
- ✅ JUSTIFY alignment → Uses TEXT BASELINE
- ✅ Font markers (`**`) → Uses TEXT BASELINE
- ✅ Multiple fonts → Uses TEXT BASELINE

### Test 2: TEXT BASELINE Generation
- ✅ Simple short text with proper formatting
- ✅ Long text split at word boundaries (~70 chars)
- ✅ JUSTIFY with WIDTH parameter

### Test 3: Integration
- ✅ Short text generates OUTPUT command
- ✅ Long text generates TEXT BASELINE command

## Example Output

### Before (Incorrect):
```dfa
OUTPUT 'Please issue separate cheque payment(s) for each of your card account(s)...'
    FONT F3 ALIGN JUSTIFY NOPAD;  ← WRONG: JUSTIFY not valid for OUTPUT
```

### After (Correct):
```dfa
TEXT
    POSITION SAME SAME BASELINE
    WIDTH 193 MM
    FONT F3_3
    ALIGN JUSTIFY
    'Please issue separate cheque payment(s) for each of your card'
    'account(s) when mailing with this payment slip';
```

## Benefits

1. **Correctness**: JUSTIFY alignment now works properly
2. **Reduced Line Count**: Long strings use TEXT instead of verbose OUTPUT
3. **Better Readability**: Text is split at natural word boundaries
4. **LucaB Compliance**: Follows the rules for TEXT vs OUTPUT usage

## Files Modified

- `universal_xerox_parser.py`
  - Added `_should_use_text_baseline()` method
  - Added `_generate_text_baseline()` method
  - Modified `_convert_output_command_dfa()` method
  - Fixed `_convert_output_command()` method

## Files Added

- `test_text_baseline.py` - Comprehensive test suite for the new logic

## Technical Notes

- Methods added to `VIPPToDFAConverter` class (lines 4920-5010)
- Decision logic only applies to literal text, not variables
- Default width for JUSTIFY is 193 MM (common page width)
- Text splitting occurs at ~70 characters for readability
- Proper quote escaping using `_escape_dfa_quotes()` method

## Validation

Run the test suite:
```bash
cd C:\Users\freddievr\claude-projects\OCBC_XEROX
python test_text_baseline.py
```

Expected output: `ALL TESTS PASSED SUCCESSFULLY!`

# Xerox Conversion Skill - Quick Reference

## Skill: `/xerox-convert`

Convert Xerox VIPP files (JDT, DBM, FRM) to Papyrus DocDEF (DFA) format.

## How to Use

In your next Claude Code session, simply type:

```
/xerox-convert
```

Then describe what you want to convert:

### Example 1: Convert Single JDT File
```
/xerox-convert

Convert the merstmtd.jdt file in SAMPLES/FIN886/FIN886 - codes/
```

### Example 2: Convert DBM File
```
/xerox-convert

I need to convert SIBS_CAST.dbm to DFA format
```

### Example 3: Convert All Files in Directory
```
/xerox-convert

Convert all Xerox files in the SAMPLES/FIN886 directory
```

### Example 4: Troubleshooting
```
/xerox-convert

I'm getting errors when converting my JDT file, can you help debug?
```

## What the Skill Does

1. ✅ Identifies file type (JDT, DBM, or FRM)
2. ✅ Runs the appropriate conversion command
3. ✅ Shows conversion progress and statistics
4. ✅ Verifies the output DFA structure
5. ✅ Reports any errors or warnings
6. ✅ Provides next steps and guidance

## Expected Output

```
Converting: SAMPLES/FIN886/FIN886 - codes/merstmtd.jdt

Running conversion...

✅ Conversion successful!

Parsing Statistics:
- Fonts parsed: 24
- Conditions parsed: 28
- RPE lines: 18
- Related forms: 2 (MESTDc.frm, MESTDi.frm)

Generated Files:
- output/merstmtd.dfa (6,534 bytes) - Main JDT
- output/MESTDc.dfa (2,384 bytes) - Form
- output/MESTDi.dfa (6,868 bytes) - Form

DFA Features:
✅ CHANNEL-CODE NO
✅ Arrays: CC[C], CONTENT[C]
✅ ENDGROUP for document separation
✅ Standard fonts: NCR, F7, F6, FA, F2
✅ Color names: B, WHITE, R
✅ All DOCFORMAT sections present (14 total)

Next Steps:
1. Review generated DFA files
2. Test with Papyrus DocExec
3. Process sample data to verify output
```

## File Types Supported

| Extension | Type | Description |
|-----------|------|-------------|
| `.jdt` | Job Descriptor Ticket | Line mode processing with carriage control |
| `.dbm` | Database Master | Database mode with delimited records |
| `.frm` | Form | Static layout/presentation layer |

## Features Included

All Luca's feedback fixes are implemented:

### Data Handling
- ✅ CHANNEL-CODE NO (not ANSI for JDT)
- ✅ Arrays CC[C] and CONTENT[C]
- ✅ Counter C increment
- ✅ N=0 in correct position
- ✅ Header reading in $_BEFOREFIRSTDOC

### Document Structure
- ✅ ENDGROUP before ENDDOCUMENT
- ✅ IF/THEN conditional routing
- ✅ All DOCFORMAT sections generated

### Output Formatting
- ✅ Standard fonts with TTF mappings
- ✅ Short color names (B, R, WHITE)
- ✅ OUTPUT CONTENT[C] with COLOR B
- ✅ Proper array references

## Common Commands

The skill will execute these commands for you:

```bash
# Single JDT file
python xerox_jdt_dfa.py "path/to/file.jdt" --single_file -o output/dir

# Single DBM file
python xerox_jdt_dfa.py "path/to/file.dbm" --single_file -o output/dir

# Directory of files
python xerox_jdt_dfa.py "path/to/directory" -o output/dir

# With verbose logging
python xerox_jdt_dfa.py "path/to/file.jdt" --single_file --verbose -o output/dir
```

## Troubleshooting

If you get errors, the skill will help you:

1. **Check file format** - Verify it's a valid JDT/DBM/FRM file
2. **Review parsing logs** - Check what was successfully parsed
3. **Validate output** - Ensure all required sections present
4. **Provide solutions** - Suggest fixes for common issues

## Files Generated

For a JDT file like `merstmtd.jdt`, you'll get:

```
output/
  └── merstmtd.dfa/
      ├── merstmtd.dfa  (Main JDT conversion)
      ├── MESTDc.dfa    (Related form)
      └── MESTDi.dfa    (Related form)
```

## Skill Location

```
.claude/skills/xerox-convert.json
```

## Version

**v1.0.0** - Initial release (2026-01-16)

## Requirements

- Python 3.7+
- xerox_jdt_dfa.py (included in project)
- Sample files in SAMPLES/ directory

## Quick Test

To test the skill is working:

```
/xerox-convert

Test the conversion with the FIN886 merchant statement sample
```

This will convert `SAMPLES/FIN886/FIN886 - codes/merstmtd.jdt` and verify all features work correctly.

---

**Ready to use in your next Claude Code session!**

Just type `/xerox-convert` and describe what you want to convert.

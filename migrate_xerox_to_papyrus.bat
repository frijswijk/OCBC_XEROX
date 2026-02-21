@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   Xerox FreeFlow  -^>  Papyrus Designer Migration Tool
echo ============================================================
echo.
echo This tool migrates a Xerox FreeFlow VIPP project into a
echo structured Papyrus Designer project folder.
echo.
echo Press ENTER to skip any optional parameter.
echo ============================================================
echo.

:: ------------------------------------------------------------------
:: Required parameters
:: ------------------------------------------------------------------

:ask_source
set "SOURCE="
set /p SOURCE="[Required] Source Xerox project folder: "
if "!SOURCE!"=="" (
    echo   ^ Please enter a source folder path.
    goto ask_source
)
if not exist "!SOURCE!" (
    echo   ^ Folder not found: !SOURCE!
    goto ask_source
)

:ask_output
set "OUTPUT="
set /p OUTPUT="[Required] Output Papyrus project folder: "
if "!OUTPUT!"=="" (
    echo   ^ Please enter an output folder path.
    goto ask_output
)

:ask_name
set "PROJNAME="
set /p PROJNAME="[Required] Project name (no spaces, e.g. SIBS_CAST): "
if "!PROJNAME!"=="" (
    echo   ^ Please enter a project name.
    goto ask_name
)

:: ------------------------------------------------------------------
:: Optional parameters
:: ------------------------------------------------------------------

echo.
echo --- Optional parameters (press ENTER to skip) ---
echo.

set "CODES="
set /p CODES="Codes subfolder name (auto-detected if blank): "

set "CONVERTER="
set /p CONVERTER="Converter [universal/jdt] (auto-detected if blank): "

set "RESOURCES="
set /p RESOURCES="Central shared resources folder (blank = inside project): "

set "FONTSRC="
set /p FONTSRC="Custom fonts source folder (blank = Windows Fonts only): "

:: ------------------------------------------------------------------
:: Flags
:: ------------------------------------------------------------------

echo.
echo --- Options ---
echo.

set "FORCE="
set /p FORCE="Overwrite existing output folder? [Y/N, default N]: "

set "RUNDOCEXEC="
set /p RUNDOCEXEC="Run DocEXEC after migration? [Y/N, default N]: "

set "VERBOSE="
set /p VERBOSE="Show converter output in real time? [Y/N, default N]: "

:: ------------------------------------------------------------------
:: Log file — DISABLED (PowerShell tee causes pipe deadlock issues)
:: Re-enable when a reliable tee solution is available.
:: ------------------------------------------------------------------
set "SAVELOG=N"

:: ------------------------------------------------------------------
:: Build command
:: ------------------------------------------------------------------

:build_cmd
set "CMD=py -3 "%~dp0migrate_xerox_to_papyrus.py""
set "CMD=!CMD! --source "!SOURCE!""
set "CMD=!CMD! --output "!OUTPUT!""
set "CMD=!CMD! --project-name "!PROJNAME!""

if not "!CODES!"==""     set "CMD=!CMD! --codes-subfolder "!CODES!""
if not "!CONVERTER!"=="" set "CMD=!CMD! --converter !CONVERTER!"
if not "!RESOURCES!"=="" set "CMD=!CMD! --resources-dir "!RESOURCES!""
if not "!FONTSRC!"==""   set "CMD=!CMD! --fonts-source-dir "!FONTSRC!""

if /I "!FORCE!"=="Y"       set "CMD=!CMD! --force"
if /I "!RUNDOCEXEC!"=="Y"  set "CMD=!CMD! --run-docexec"
if /I "!VERBOSE!"=="Y"     set "CMD=!CMD! --verbose"

:: ------------------------------------------------------------------
:: Confirm and run
:: ------------------------------------------------------------------

echo.
echo ============================================================
echo   Command to execute:
echo.
echo   !CMD!
echo.
echo ============================================================

set "CONFIRM="
set /p CONFIRM="Proceed? [Y/N, default Y]: "
if /I "!CONFIRM!"=="N" (
    echo Cancelled.
    goto end
)

echo.

:: Run the migration directly (no log file)
!CMD!

:end
echo.
pause
endlocal

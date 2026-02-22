@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   Xerox VIPP Source Code Beautifier
echo ============================================================
echo.
echo Removes commented-out code, normalizes indentation, and
echo preserves meaningful comments and DSC headers.
echo.
echo Press ENTER to skip any optional parameter.
echo ============================================================
echo.

:: ------------------------------------------------------------------
:: Required parameters
:: ------------------------------------------------------------------

:ask_source
set "SOURCE="
set /p SOURCE="[Required] Source folder with VIPP files (.dbm/.frm/.jdt): "
if "!SOURCE!"=="" (
    echo   ^ Please enter a source folder path.
    goto ask_source
)
if not exist "!SOURCE!" (
    echo   ^ Folder not found: !SOURCE!
    goto ask_source
)

:ask_target
set "TARGET="
set /p TARGET="[Required] Target base folder (e.g. C:\OCBC\XEROX): "
if "!TARGET!"=="" (
    echo   ^ Please enter a target folder path.
    goto ask_target
)

:ask_name
set "PROJNAME="
set /p PROJNAME="[Required] Project name (e.g. SIBS_CAST): "
if "!PROJNAME!"=="" (
    echo   ^ Please enter a project name.
    goto ask_name
)

:: Build the output path: TARGET\PROJNAME
set "OUTPATH=!TARGET!\!PROJNAME!"

:: ------------------------------------------------------------------
:: Confirm and run
:: ------------------------------------------------------------------

echo.
echo ============================================================
echo   Source  : !SOURCE!
echo   Output : !OUTPATH!
echo   Project: !PROJNAME!
echo ============================================================

set "CONFIRM="
set /p CONFIRM="Proceed? [Y/N, default Y]: "
if /I "!CONFIRM!"=="N" (
    echo Cancelled.
    goto end
)

echo.

py -3 "%~dp0xerox_beautifier.py" "!SOURCE!" --output "!OUTPATH!"

:end
echo.
pause
endlocal

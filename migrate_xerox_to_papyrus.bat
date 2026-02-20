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
:: Log file
:: ------------------------------------------------------------------

echo.
echo --- Output log ---
echo.

:: Generate a timestamp using PowerShell (locale-independent)
for /f %%T in ('powershell -nologo -command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TIMESTAMP=%%T"

:: Default log path: <output folder>\migrate_<project>_<timestamp>.log
set "LOGFILE_DEFAULT=!OUTPUT!\migrate_!PROJNAME!_!TIMESTAMP!.log"

set "SAVELOG=Y"
set /p SAVELOG="Save console output to a log file? [Y/N, default Y]: "

if /I "!SAVELOG!"=="N" goto build_cmd

set "LOGFILE=!LOGFILE_DEFAULT!"
echo   Default log file: !LOGFILE_DEFAULT!
set /p LOGFILE="Log file path (press ENTER for default): "
if "!LOGFILE!"=="" set "LOGFILE=!LOGFILE_DEFAULT!"

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
if /I not "!SAVELOG!"=="N" (
    echo.
    echo   Log file: !LOGFILE!
)
echo.
echo ============================================================

set "CONFIRM="
set /p CONFIRM="Proceed? [Y/N, default Y]: "
if /I "!CONFIRM!"=="N" (
    echo Cancelled.
    goto end
)

echo.

:: Ensure the output folder exists before writing the log
if /I not "!SAVELOG!"=="N" (
    if not exist "!OUTPUT!" mkdir "!OUTPUT!" 2>nul
)

:: Run — with or without tee to log file
if /I "!SAVELOG!"=="N" (
    !CMD!
) else (
    :: cmd.exe treats | as a pipe operator even inside "double quotes", so we
    :: cannot write  powershell -command "... | Tee-Object ..."  inline.
    :: Solution: write the tee logic to a temp .ps1 file where cmd.exe never
    :: parses it, then invoke PowerShell with -File.
    ::
    :: IMPORTANT: Do NOT use "$input | Tee-Object" — $input is pre-enumerated
    :: in PowerShell, causing a deadlock when output exceeds the 64KB pipe
    :: buffer (PowerShell waits for EOF before reading; cmd waits for the pipe
    :: to drain — neither proceeds).  Use a process{} block instead so
    :: PowerShell consumes and forwards each line as it arrives.
    set "PSSCRIPT=%TEMP%\migrate_tee_!PROJNAME!.ps1"
    (
        echo param([string]$lf^)
        echo begin  { $sw = [IO.StreamWriter]::new($lf, $false, [Text.Encoding]::UTF8^) }
        echo process{ Write-Host $_; $sw.WriteLine($_^) }
        echo end    { $sw.Close(^) }
    ) > "!PSSCRIPT!"
    !CMD! 2>&1 | powershell -nologo -NonInteractive -File "!PSSCRIPT!" -lf "!LOGFILE!"
    del "!PSSCRIPT!" 2>nul
    echo.
    echo Log saved to: !LOGFILE!
)

:end
echo.
pause
endlocal

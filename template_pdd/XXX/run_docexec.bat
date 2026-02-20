@echo off
call run_env.bat
CD /d %cd%\userisis
%PDE64%\pdew6.exe %CD%\..\docdef\%PRJNAME%.prj /FORCEPDF="YES" >%CD%\..\docdef\%PRJNAME%_docexec.log 2<&1
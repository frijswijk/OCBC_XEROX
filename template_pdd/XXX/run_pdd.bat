call run_env.bat
CD /d %cd%\userisis
%PDD32%\pddw3.exe %CD%\..\docdef\%PRJNAME%.prj /profile=%cd%\pdd.prf

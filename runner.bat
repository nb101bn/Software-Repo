@echo off
REM
REM Python Script Runner (.bat file)
REM
REM =================================================================
REM INSTRUCTIONS:
REM 1. Save this file as "run_script.bat" (or any name ending in .bat).
REM 2. Update the SCRIPT_PATH variable below to the absolute path of your .py file.
REM    If the path contains spaces, make sure to use double quotes!
REM =================================================================

REM Replace the example path below with your actual Python file path:
set SCRIPT_PATH="C:\Users\nathan\Documents\GitHub\Software-Repo\SkewTSoftware\Skew-T_Plotting.py"

REM --- Execution ---

REM Check if the 'python' command is available
where python >nul 2>nul
if %errorlevel% neq 0 (
echo.
echo ERROR: Python is not recognized as an internal or external command.
echo Please ensure Python is installed and added to your system's PATH environment variables.
goto :end
)

echo Starting Python script: %SCRIPT_PATH%
echo -----------------------------------------------------------------

REM Execute the Python script
python %SCRIPT_PATH%

echo -----------------------------------------------------------------
echo Script finished.

:end
REM Keep the window open until a key is pressed so you can see the output.
pause
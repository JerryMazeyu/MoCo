@echo off
set ROOT_PATH=%~dp0
set ROOT_PATH=%ROOT_PATH:~0,-1%
for %%i in ("%ROOT_PATH%") do set PARENT_PATH=%%~dpi
set PARENT_PATH=%PARENT_PATH:~0,-1%

REM Check if PYTHONPATH exists
for /f "tokens=2 delims==" %%A in ('reg query "HKCU\Environment" /v PYTHONPATH 2^>nul') do set OLD_PYTHONPATH=%%A

echo %OLD_PYTHONPATH% | find "%ROOT_PATH%" > nul
if %errorlevel% equ 0 (
    echo PYTHONPATH has got %PARENT_PATH%
) else (
    REM Add to existing PYTHONPATH (if exists)
    if defined OLD_PYTHONPATH (
        setx PYTHONPATH "%OLD_PYTHONPATH%;%PARENT_PATH%"
    ) else (
        setx PYTHONPATH "%PARENT_PATH%"
    )
    echo Add %PARENT_PATH% to PYTHONPATH
)

REM Display current PYTHONPATH
reg query "HKCU\Environment" /v PYTHONPATH

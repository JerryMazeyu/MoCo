@echo off
REM ======== Configuration section ========
REM Set virtual environment name (modify as needed)
set ENV_NAME=moco

REM ======== Script start ========
REM Set Chinese encoding
chcp 65001 > nul
REM Set window title
title MoCo application

REM Switch to script directory
cd /d "%~dp0"
echo Current directory: %CD%
cd ..
echo Working directory: %CD%

where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 'conda' command not found, try to find conda installation path and add to PATH...
    
    set CONDA_FOUND=false
    
    if exist "%USERPROFILE%\Anaconda3\Scripts\conda.exe" (
        echo 找到conda: %USERPROFILE%\Anaconda3\Scripts\conda.exe
        set "PATH=%PATH%;%USERPROFILE%\Anaconda3;%USERPROFILE%\Anaconda3\Scripts;%USERPROFILE%\Anaconda3\Library\bin"
        set CONDA_FOUND=true
    )
    
    if "%CONDA_FOUND%"=="false" if exist "%USERPROFILE%\Miniconda3\Scripts\conda.exe" (
        echo Found conda: %USERPROFILE%\Miniconda3\Scripts\conda.exe
        set "PATH=%PATH%;%USERPROFILE%\Miniconda3;%USERPROFILE%\Miniconda3\Scripts;%USERPROFILE%\Miniconda3\Library\bin"
        set CONDA_FOUND=true
    )
    
    if "%CONDA_FOUND%"=="false" if exist "C:\ProgramData\Anaconda3\Scripts\conda.exe" (
        echo Found conda: C:\ProgramData\Anaconda3\Scripts\conda.exe
        set "PATH=%PATH%;C:\ProgramData\Anaconda3;C:\ProgramData\Anaconda3\Scripts;C:\ProgramData\Anaconda3\Library\bin"
        set CONDA_FOUND=true
    )
    
    if "%CONDA_FOUND%"=="true" (
        where conda >nul 2>&1
        if %ERRORLEVEL% NEQ 0 (
            echo Failed to add conda to PATH, please manually add conda to environment variables
        ) else (
            echo Successfully added conda to PATH
        )
    ) else (
        echo Failed to find conda installation path, please install conda or manually add it to environment variables
        echo You can download Miniconda from the following URL: https://docs.conda.io/en/latest/miniconda.html
    )
)

echo Checking application files...
set FOUND_FILE=false

if exist views\main_window.py (
    set APP_PATH=views\main_window.py
    set FOUND_FILE=true
    echo Found application: %APP_PATH%
) else if exist main_window.py (
    set APP_PATH=main_window.py
    set FOUND_FILE=true
    echo Found application: %APP_PATH%
) else (
    echo Warning: main_window.py not found, start searching...
    for /r %%i in (*main_window.py) do (
        echo Found possible file: %%i
        set APP_PATH=%%i
        set FOUND_FILE=true
    )
)

if "%FOUND_FILE%"=="false" (
    echo Error: main_window.py file not found!
    echo Current directory: %CD%
    echo Please ensure that the application file exists
    pause
    exit /b 1
)

echo Trying to activate conda environment %ENV_NAME% ...
call conda activate %ENV_NAME% 2>nul
set PYTHON_ACTIVATED=false

if %ERRORLEVEL% EQU 0 (
    where python >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set PYTHON_ACTIVATED=true
        echo Successfully activated conda environment: %ENV_NAME%
    )
) else (
    echo Failed to activate conda environment %ENV_NAME%, try other ways...
    
    if exist C:\Users\%USERNAME%\Anaconda3\Scripts\activate.bat (
        echo Trying path: C:\Users\%USERNAME%\Anaconda3\Scripts\activate.bat
        call C:\Users\%USERNAME%\Anaconda3\Scripts\activate.bat %ENV_NAME%
        where python >nul 2>&1
        if %ERRORLEVEL% EQU 0 set PYTHON_ACTIVATED=true
    )
    
    if "%PYTHON_ACTIVATED%"=="false" if exist C:\ProgramData\Anaconda3\Scripts\activate.bat (
        echo Trying path: C:\ProgramData\Anaconda3\Scripts\activate.bat
        call C:\ProgramData\Anaconda3\Scripts\activate.bat %ENV_NAME%
        where python >nul 2>&1
        if %ERRORLEVEL% EQU 0 set PYTHON_ACTIVATED=true
    )
    
    if "%PYTHON_ACTIVATED%"=="false" if exist C:\Users\%USERNAME%\miniconda3\Scripts\activate.bat (
        echo Trying path: C:\Users\%USERNAME%\miniconda3\Scripts\activate.bat
        call C:\Users\%USERNAME%\miniconda3\Scripts\activate.bat %ENV_NAME%
        where python >nul 2>&1
        if %ERRORLEVEL% EQU 0 set PYTHON_ACTIVATED=true
    )
)

if "%PYTHON_ACTIVATED%"=="false" (
    echo Warning: Failed to activate conda environment, try using system Python...
    where python >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Python not found! Please ensure Python is installed and added to PATH.
        echo You can download Python from the following URL: https://www.python.org/downloads/
        pause
        exit /b 1
    ) else (
        echo Using system Python
    )
)

echo Environment prepared, start running application...

echo Starting application: python %APP_PATH%
python "%APP_PATH%"
if %ERRORLEVEL% NEQ 0 (
    echo Application execution failed, error code: %ERRORLEVEL%
    echo Possible reasons:
    echo 1. Python cannot find the required modules
    echo 2. Application code contains errors
    echo 3. Environment configuration is incorrect
    echo Suggestions: Ensure that all necessary Python packages are installed, you can try running:
    echo pip install -r requirements.txt
)

echo Application execution completed
pause
exit

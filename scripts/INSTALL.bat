chcp 65001 > nul
@echo off
echo ========================================
echo    MoCo project environment installation script
echo ========================================
echo.

where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: conda command not found. Please ensure that Anaconda or Miniconda is installed and added to the system PATH.
    pause
    exit /b 1
)

echo Step 1: Create conda environment
call "%~dp0\create_conda_env.bat"


echo Step 2: Config tsinghua conda mirror
call "%~dp0\config_conda_mirror.bat"


echo Step 3: Install packages
call "%~dp0\install_packages.bat"
if %errorlevel% neq 0 (
    echo Error: Failed to install packages!
    pause
    exit /b 1
)
echo.

echo ========================================
echo    Installation completed!
echo ========================================

pause

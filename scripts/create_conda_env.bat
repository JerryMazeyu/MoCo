@echo off
setlocal enabledelayedexpansion

echo ======================================
echo    Create conda environment...
echo ======================================

set /p ENV_NAME=Please input the name of the conda environment: 

echo Creating new conda environment: %ENV_NAME%...
call conda create -n %ENV_NAME% python=3.10

echo Conda environment %ENV_NAME% created!

:end

echo %ENV_NAME%> "%~dp0\env_name.txt"

endlocal 
@echo off
echo ======================================
echo    Install packages...
echo ======================================


set /p ENV_NAME=<"%~dp0\env_name.txt"

echo Installing packages for environment %ENV_NAME%...


call conda activate %ENV_NAME%


if not exist "%~dp0..\requirements.txt" (
    echo Error: requirements.txt file not found!
    exit /b 1
)


echo Installing packages in requirements.txt...
call pip install -r "%~dp0..\requirements.txt"

echo All packages installed! 
@echo off
setlocal enabledelayedexpansion

echo ======================================
echo    创建Conda环境
echo ======================================

set /p ENV_NAME=请输入要创建的Conda环境名称: 

echo 正在创建新的Conda环境: %ENV_NAME%...
call conda create -n %ENV_NAME% python=3.10

echo Conda环境 %ENV_NAME% 创建完成！

:end

echo %ENV_NAME%> "%~dp0\env_name.txt"

endlocal 
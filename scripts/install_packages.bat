@echo off
echo ======================================
echo    安装依赖包
echo ======================================


set /p ENV_NAME=<"%~dp0\env_name.txt"

echo 正在为环境 %ENV_NAME% 安装依赖包...


call conda activate %ENV_NAME%


if not exist "%~dp0..\requirements.txt" (
    echo 错误：requirements.txt文件不存在！
    exit /b 1
)


echo 正在安装requirements.txt中的依赖包...
call pip install -r "%~dp0..\requirements.txt"

echo 所有依赖包安装完成！ 
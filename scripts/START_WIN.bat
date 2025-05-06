@echo off
REM 设置中文编码
chcp 65001 > nul
REM 设置窗口标题
title MoCo应用程序

REM 切换到脚本所在目录
cd /d "%~dp0"
echo 当前目录: %CD%
cd ..
echo 工作目录: %CD%

REM 检查main_window.py是否存在及可能的位置
echo 正在检查应用程序文件...
set FOUND_FILE=false

if exist views\main_window.py (
    set APP_PATH=views\main_window.py
    set FOUND_FILE=true
    echo 找到应用程序: %APP_PATH%
) else if exist main_window.py (
    set APP_PATH=main_window.py
    set FOUND_FILE=true
    echo 找到应用程序: %APP_PATH%
) else (
    echo 警告: 找不到main_window.py，开始搜索...
    for /r %%i in (*main_window.py) do (
        echo 找到可能的文件: %%i
        set APP_PATH=%%i
        set FOUND_FILE=true
    )
)

if "%FOUND_FILE%"=="false" (
    echo 错误: 无法找到main_window.py文件！
    echo 当前目录: %CD%
    echo 请确保应用程序文件存在
    pause
    exit /b 1
)

REM 激活Conda环境
echo 正在尝试激活conda环境...
call conda activate moco
if %ERRORLEVEL% NEQ 0 (
    echo conda activate moco 命令失败，尝试其他方式...
    
    REM 尝试其他可能的conda激活路径
    if exist C:\Users\%USERNAME%\Anaconda3\Scripts\activate.bat (
        echo 尝试路径: C:\Users\%USERNAME%\Anaconda3\Scripts\activate.bat
        call C:\Users\%USERNAME%\Anaconda3\Scripts\activate.bat moco
    ) else if exist C:\ProgramData\Anaconda3\Scripts\activate.bat (
        echo 尝试路径: C:\ProgramData\Anaconda3\Scripts\activate.bat
        call C:\ProgramData\Anaconda3\Scripts\activate.bat moco
    ) else if exist C:\Users\%USERNAME%\miniconda3\Scripts\activate.bat (
        echo 尝试路径: C:\Users\%USERNAME%\miniconda3\Scripts\activate.bat
        call C:\Users\%USERNAME%\miniconda3\Scripts\activate.bat moco
    ) else (
        echo 警告: 无法找到conda环境，将使用系统Python
    )
)

echo 环境准备完成，开始运行应用程序...

REM 运行Python应用程序
echo 正在启动应用: python %APP_PATH%
python "%APP_PATH%"
if %ERRORLEVEL% NEQ 0 (
    echo 应用程序执行失败，错误代码: %ERRORLEVEL%
)

echo 程序执行完毕
pause
exit

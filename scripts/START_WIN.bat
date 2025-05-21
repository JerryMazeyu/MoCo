@echo off
REM ======== 配置部分 ========
REM 设置虚拟环境名称（按需修改）
set ENV_NAME=py310

REM ======== 脚本开始 ========
REM 设置中文编码
chcp 65001 > nul
REM 设置窗口标题
title MoCo应用程序

REM 切换到脚本所在目录
cd /d "%~dp0"
echo 当前目录: %CD%
cd ..
echo 工作目录: %CD%

REM 检查conda是否在PATH中，如果不在，尝试找到它并添加到PATH
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 'conda'命令未找到，尝试查找conda安装路径并添加到PATH...
    
    REM 检查常见的conda安装位置
    set CONDA_FOUND=false
    
    REM 检查用户目录下的Anaconda3
    if exist "%USERPROFILE%\Anaconda3\Scripts\conda.exe" (
        echo 找到conda: %USERPROFILE%\Anaconda3\Scripts\conda.exe
        set "PATH=%PATH%;%USERPROFILE%\Anaconda3;%USERPROFILE%\Anaconda3\Scripts;%USERPROFILE%\Anaconda3\Library\bin"
        set CONDA_FOUND=true
    )
    
    REM 检查用户目录下的Miniconda3
    if "%CONDA_FOUND%"=="false" if exist "%USERPROFILE%\Miniconda3\Scripts\conda.exe" (
        echo 找到conda: %USERPROFILE%\Miniconda3\Scripts\conda.exe
        set "PATH=%PATH%;%USERPROFILE%\Miniconda3;%USERPROFILE%\Miniconda3\Scripts;%USERPROFILE%\Miniconda3\Library\bin"
        set CONDA_FOUND=true
    )
    
    REM 检查程序目录下的Anaconda3
    if "%CONDA_FOUND%"=="false" if exist "C:\ProgramData\Anaconda3\Scripts\conda.exe" (
        echo 找到conda: C:\ProgramData\Anaconda3\Scripts\conda.exe
        set "PATH=%PATH%;C:\ProgramData\Anaconda3;C:\ProgramData\Anaconda3\Scripts;C:\ProgramData\Anaconda3\Library\bin"
        set CONDA_FOUND=true
    )
    
    REM 如果找到了conda，再次检查
    if "%CONDA_FOUND%"=="true" (
        where conda >nul 2>&1
        if %ERRORLEVEL% NEQ 0 (
            echo 添加conda到PATH失败，请手动将conda添加到环境变量
        ) else (
            echo 成功将conda添加到PATH
        )
    ) else (
        echo 无法找到conda安装路径，请安装conda或手动将其添加到环境变量
        echo 您可以从以下网址下载Miniconda: https://docs.conda.io/en/latest/miniconda.html
        REM 继续执行，尝试使用系统Python
    )
)

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

REM 首先尝试使用conda环境中的Python
echo 正在尝试激活conda环境 %ENV_NAME% ...
call conda activate %ENV_NAME% 2>nul
set PYTHON_ACTIVATED=false

if %ERRORLEVEL% EQU 0 (
    where python >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set PYTHON_ACTIVATED=true
        echo 成功激活conda环境: %ENV_NAME%
    )
) else (
    echo conda activate %ENV_NAME% 命令失败，尝试其他方式...
    
    REM 尝试其他可能的conda激活路径
    if exist C:\Users\%USERNAME%\Anaconda3\Scripts\activate.bat (
        echo 尝试路径: C:\Users\%USERNAME%\Anaconda3\Scripts\activate.bat
        call C:\Users\%USERNAME%\Anaconda3\Scripts\activate.bat %ENV_NAME%
        where python >nul 2>&1
        if %ERRORLEVEL% EQU 0 set PYTHON_ACTIVATED=true
    )
    
    if "%PYTHON_ACTIVATED%"=="false" if exist C:\ProgramData\Anaconda3\Scripts\activate.bat (
        echo 尝试路径: C:\ProgramData\Anaconda3\Scripts\activate.bat
        call C:\ProgramData\Anaconda3\Scripts\activate.bat %ENV_NAME%
        where python >nul 2>&1
        if %ERRORLEVEL% EQU 0 set PYTHON_ACTIVATED=true
    )
    
    if "%PYTHON_ACTIVATED%"=="false" if exist C:\Users\%USERNAME%\miniconda3\Scripts\activate.bat (
        echo 尝试路径: C:\Users\%USERNAME%\miniconda3\Scripts\activate.bat
        call C:\Users\%USERNAME%\miniconda3\Scripts\activate.bat %ENV_NAME%
        where python >nul 2>&1
        if %ERRORLEVEL% EQU 0 set PYTHON_ACTIVATED=true
    )
)

REM 如果conda环境激活失败，尝试使用系统Python
if "%PYTHON_ACTIVATED%"=="false" (
    echo 警告: 无法激活conda环境，尝试使用系统Python...
    where python >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo 错误: 找不到Python! 请确保Python已安装并添加到PATH中。
        echo 您可以从以下网址下载Python: https://www.python.org/downloads/
        pause
        exit /b 1
    ) else (
        echo 将使用系统Python
    )
)

echo 环境准备完成，开始运行应用程序...

REM 运行Python应用程序
echo 正在启动应用: python %APP_PATH%
python "%APP_PATH%"
if %ERRORLEVEL% NEQ 0 (
    echo 应用程序执行失败，错误代码: %ERRORLEVEL%
    echo 可能的原因:
    echo 1. Python无法找到所需模块
    echo 2. 应用程序代码存在错误
    echo 3. 环境配置不正确
    echo 建议: 确保已安装所有必要的Python包，可尝试运行:
    echo pip install -r requirements.txt
)

echo 程序执行完毕
pause
exit

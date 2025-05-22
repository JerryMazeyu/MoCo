chcp 65001 > nul
@echo off
echo ========================================
echo    MoCo项目环境安装脚本
echo ========================================
echo.

:: 检查conda是否已安装
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误：未检测到conda命令。请确保已安装Anaconda或Miniconda，并将其添加到系统PATH中。
    pause
    exit /b 1
)

:: 运行创建环境脚本
echo 第1步：创建Conda环境
call "%~dp0\create_conda_env.bat"


:: 运行配置清华源脚本
echo 第2步：配置清华源
call "%~dp0\config_conda_mirror.bat"


:: 运行安装依赖包脚本
echo 第3步：安装依赖包
call "%~dp0\install_packages.bat"
if %errorlevel% neq 0 (
    echo 安装依赖包失败！
    pause
    exit /b 1
)
echo.

echo ========================================
echo    安装完成！
echo ========================================

pause

@echo off
echo ======================================
echo    配置Conda清华源
echo ======================================

set /p ENV_NAME=<"%~dp0\env_name.txt"

echo 正在为Conda配置清华源...


call conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
call conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
call conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
call conda config --set show_channel_urls yes


mkdir "%USERPROFILE%\pip" 2>nul
echo [global] > "%USERPROFILE%\pip\pip.conf"
echo index-url = https://pypi.tuna.tsinghua.edu.cn/simple >> "%USERPROFILE%\pip\pip.conf"
echo trusted-host = pypi.tuna.tsinghua.edu.cn >> "%USERPROFILE%\pip\pip.conf"

echo Conda和Pip清华源配置完成！ 
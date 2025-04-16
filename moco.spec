# -*- mode: python ; coding: utf-8 -*-
import site
import os
import mingzi
# 在 moco.spec 中添加这段代码来打印 mingzi 模块的位置
mingzi_path = os.path.dirname(mingzi.__file__)
mingzi_data = os.path.join(mingzi_path, 'data.json')

print(f"mingzi module path: {mingzi_path}")
print(f"data.json path: {mingzi_data}")

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/resources/icons/*.png', 'app/resources/icons'),  # 修改这行，确保包含所有PNG图标
        ('app/config', 'app/config'),        # 配置文件
        ('app/utils', 'app/utils'),          # 工具模块
        ('app/views', 'app/views'),          # 视图模块
        ('app/services', 'app/services'),    # 服务模块
        ('app/models', 'app/models'),        # 模型模块
        # 添加 mingzi 模块的 data.json 文件
        (mingzi_data, 'mingzi'),  # 使用实际路径
    ],
    hiddenimports=[
        'PyQt5',
        'pandas',
        'oss2',
        'pypinyin',
        'geopy',
        'google_search_results',
        'markdown',
        'mingzi',
        'numpy',
        'openai',
        'openpyxl',
        'pydantic',
        'yaml',
        'requests',
        'translate',
        'xlrd',
        'xlwt'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MoCo数据助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app/resources/icons/oil.png'  # 如果有图标的话
)

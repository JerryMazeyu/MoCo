# -*- mode: python ; coding: utf-8 -*-
import os
import mingzi

block_cipher = None

# 获取 mingzi 模块及其 data.json 的路径
mingzi_path = os.path.dirname(mingzi.__file__)
mingzi_data = os.path.join(mingzi_path, 'data.json')

# 1. 分析脚本及依赖
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/resources/icons/*.png', 'app/resources/icons'),
        ('app/config', 'app/config'),
        ('app/utils', 'app/utils'),
        ('app/views', 'app/views'),
        ('app/services', 'app/services'),
        ('app/models', 'app/models'),
        (mingzi_data, 'mingzi'),
    ],
    hiddenimports=[
        'PyQt5', 'pandas', 'oss2', 'pypinyin', 'geopy',
        'google_search_results', 'markdown', 'mingzi',
        'numpy', 'openai', 'openpyxl', 'pydantic',
        'yaml', 'requests', 'translate', 'xlrd', 'xlwt'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

# 2. 打包纯 Python 模块
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 3. 生成无二进制的可执行器（排除二进制文件，交给 COLLECT 处理）
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='MoCo数据助手',
    debug=False,
    strip=False,
    upx=True,
    console=False,  # windowed 模式，不打开终端
)

# 4. 收集所有二进制、数据文件等
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MoCo数据助手',  # 目录名，可随意
)

# 5. 将收集好的文件打包为 .app bundle
app = BUNDLE(
    coll,
    name='MoCo数据助手.app',
    icon='app/resources/icons/app_icon.icns',       # 你的 icns 图标
    bundle_identifier='com.yourcompany.moco',       # 可选：反向域名标识
)

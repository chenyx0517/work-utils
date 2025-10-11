# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/m10003000054/work-python/font_trans.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('/Users/m10003000054/work-python/index.html', '.'),
        ('/Users/m10003000054/work-python/unicode-zh-CN.txt', '.'),
        ('/Users/m10003000054/work-python/unicode-zh-TW.txt', '.'),
        ('/Users/m10003000054/work-python/unicode-ja.txt', '.')
    ],
    hiddenimports=['brotli', 'brotlicffi', 'fontTools', 'webview'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FontConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/Users/m10003000054/work-python/icon.icns'],
)
app = BUNDLE(
    exe,
    name='FontConverter.app',
    icon='/Users/m10003000054/work-python/icon.icns',
    bundle_identifier=None,
)

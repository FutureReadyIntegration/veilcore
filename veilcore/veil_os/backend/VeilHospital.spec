# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['veil/hospital_gui/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('veil/hospital_gui/templates', 'veil/hospital_gui/templates'), ('veil/hospital_gui/static', 'veil/hospital_gui/static')],
    hiddenimports=['uvicorn.logging', 'uvicorn.protocols.http', 'uvicorn.protocols.websockets', 'uvicorn.lifespan.on', 'veil.hospital_gui.database'],
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
    name='VeilHospital',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

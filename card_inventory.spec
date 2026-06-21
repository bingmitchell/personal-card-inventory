# -*- mode: python ; coding: utf-8 -*-
# Build with: pyinstaller card_inventory.spec
# Output:     dist/CardInventory  (Mac .app or Windows .exe)

block_cipher = None

a = Analysis(
    ['scripts/launcher.py'],
    pathex=['scripts'],
    binaries=[],
    datas=[
        ('scripts/templates', 'templates'),
        ('scripts/lib',       'lib'),
    ],
    hiddenimports=['sqlite3', 'lib.db', 'lib.schema', 'lib.validators'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['psycopg2'],
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
    name='CardInventory',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # flip to False to hide the terminal window once stable
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# macOS .app bundle (ignored on Windows)
app = BUNDLE(
    exe,
    name='Card Inventory.app',
    icon=None,
    bundle_identifier='com.personal.card-inventory',
)

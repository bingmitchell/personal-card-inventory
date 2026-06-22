# -*- mode: python ; coding: utf-8 -*-
# Build:   python3 -m PyInstaller card_inventory.spec --noconfirm
# Output:  dist/Card Inventory.app   (macOS)
#          dist/CardInventory/       (folder — double-click CardInventory inside)

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
    [],                 # no binaries here — COLLECT handles them (onedir mode)
    exclude_binaries=True,
    name='CardInventory',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CardInventory',
)

# macOS .app bundle wrapping the onedir output
app = BUNDLE(
    coll,
    name='Card Inventory.app',
    icon='assets/CardInventory.icns',
    bundle_identifier='com.personal.card-inventory',
)

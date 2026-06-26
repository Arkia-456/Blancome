# blancome.spec — PyInstaller build spec for Blancome
from PyInstaller.utils.hooks import collect_all

block_cipher = None

vosk_datas, vosk_binaries, vosk_hiddenimports = collect_all("vosk")
qta_datas,  qta_binaries,  qta_hiddenimports  = collect_all("qtawesome")
sd_datas,   sd_binaries,   sd_hiddenimports   = collect_all("sounddevice")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[*vosk_binaries, *qta_binaries, *sd_binaries],
    datas=[
        ("loading_messages.json", "."),
        ("assets",                "assets"),
        ("models/vosk-model",     "models/vosk-model"),
        *vosk_datas,
        *qta_datas,
        *sd_datas,
    ],
    hiddenimports=[
        *vosk_hiddenimports,
        *qta_hiddenimports,
        *sd_hiddenimports,
        # Conditional imports in main.py that the analyser may miss
        "assistant.ui",
        "assistant.splash",
        # Command modules loaded via brain.py
        "commands.music.play",
        "commands.music.stop",
        "commands.music.next",
        "commands.music.pause",
        "commands.music.previous",
        "commands.music.shuffle",
        "commands.shopping.add",
        "commands.shopping.send_sms",
        "commands.shopping.list",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Blancome",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Blancome",
)

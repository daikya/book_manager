# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata


project_root = Path(SPECPATH).resolve().parents[1]
source_root = project_root / "src"
icon_path = (
    project_root
    / "assets"
    / "windows"
    / "book_manager.ico"
)
version_file = (
    project_root
    / "build"
    / "windows_version_info.txt"
)

application_assets = [
    (
        str(
            project_root
            / "assets"
            / "windows"
            / "book_manager.ico"
        ),
        "assets/windows",
    ),
    (
        str(
            project_root
            / "assets"
            / "windows"
            / "book_manager.png"
        ),
        "assets/windows",
    ),
]

application_metadata = copy_metadata("book-manager")

analysis = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(source_root)],
    binaries=[],
    datas=application_assets + application_metadata,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="BookManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
    version=str(version_file),
)

distribution = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BookManager",
)

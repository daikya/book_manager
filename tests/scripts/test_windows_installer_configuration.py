"""Windowsインストーラー構成のテスト。"""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INNO_SETUP_SCRIPT = (
    PROJECT_ROOT / "packaging" / "inno_setup" / "book_manager.iss"
)
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_windows_installer.ps1"


def read_inno_setup_script() -> str:
    """Inno Setupスクリプトを読み込む。"""
    return INNO_SETUP_SCRIPT.read_text(encoding="utf-8")


def read_build_script() -> str:
    """PowerShellビルドスクリプトを読み込む。"""
    return BUILD_SCRIPT.read_text(encoding="utf-8")


def test_inno_setup_uses_fixed_application_id() -> None:
    """上書き更新用の固定AppIdを使用する。"""
    content = read_inno_setup_script()
    assert "0E99B7C8-54CB-4D31-9DE3-F36E2B6F2A8C" in content


def test_inno_setup_requires_external_version() -> None:
    """Versionを外部定義として受け取る。"""
    content = read_inno_setup_script()
    assert "#ifndef AppVersion" in content
    assert "AppVersion={#AppVersion}" in content
    assert "VersionInfoVersion={#AppVersion}" in content


def test_inno_setup_is_non_administrative_user_install() -> None:
    """利用者単位かつ非管理者でインストールする。"""
    content = read_inno_setup_script()
    assert "PrivilegesRequired=lowest" in content
    assert "DefaultDirName={localappdata}\\Programs\\BookManager" in content


def test_inno_setup_targets_windows_x64() -> None:
    """Windows x64用インストーラーを作成する。"""
    content = read_inno_setup_script()
    assert "SetupArchitecture=x64" in content
    assert "ArchitecturesAllowed=x64compatible" in content


def test_inno_setup_uses_only_pyinstaller_output() -> None:
    """PyInstallerのonedir成果物だけを収集する。"""
    content = read_inno_setup_script()
    source_entries = re.findall(r'^Source:\s*"([^"]+)"', content, re.MULTILINE)
    assert source_entries == [r"..\..\dist\BookManager\*"]
    assert "recursesubdirs" in content


def test_inno_setup_does_not_delete_user_data() -> None:
    """アンインストール時に利用者データを削除しない。"""
    content = read_inno_setup_script()
    assert "[UninstallDelete]" not in content
    assert r"book_manager\data" not in content
    assert r"book_manager\backups" not in content


def test_inno_setup_configures_application_icon() -> None:
    """インストーラーへ専用アイコンを設定する。"""
    content = read_inno_setup_script()
    assert "SetupIconFile=..\\..\\assets\\windows\\book_manager.ico" in content
    assert "UninstallDisplayIcon={app}\\{#AppExeName}" in content


def test_inno_setup_creates_start_menu_shortcut() -> None:
    """スタートメニューショートカットを作成する。"""
    content = read_inno_setup_script()
    assert 'Name: "{group}\\{#AppName}"' in content


def test_desktop_shortcut_is_optional() -> None:
    """デスクトップショートカットを任意選択にする。"""
    content = read_inno_setup_script()
    assert 'Name: "desktopicon"' in content
    assert "Flags: unchecked" in content
    assert 'Name: "{autodesktop}\\{#AppName}"' in content
    assert "Tasks: desktopicon" in content


def test_post_install_run_is_skipped_when_silent() -> None:
    """サイレント導入ではアプリケーションを起動しない。"""
    content = read_inno_setup_script()
    assert "postinstall" in content
    assert "skipifsilent" in content


def test_installer_filename_contains_version_and_architecture() -> None:
    """成果物名へVersionとx64を含める。"""
    content = read_inno_setup_script()
    assert (
        "OutputBaseFilename="
        "BookManager-{#AppVersion}-windows-x64-setup"
    ) in content


def test_build_script_reads_version_from_pyproject() -> None:
    """pyproject.tomlをVersionの正本として扱う。"""
    content = read_build_script()
    assert '"pyproject.toml"' in content
    assert "Get-ProjectVersion" in content
    assert "major.minor.patch" in content


def test_build_script_checks_pyinstaller_output() -> None:
    """onedir成果物の必須要素を検証する。"""
    content = read_build_script()
    assert '"dist\\BookManager"' in content
    assert '"BookManager.exe"' in content
    assert '"_internal"' in content
    assert "VersionInfo.ProductVersion" in content


def test_build_script_searches_user_and_system_inno_setup() -> None:
    """利用者単位とシステム単位のISCC.exeを探索する。"""
    content = read_build_script()
    assert "$env:LOCALAPPDATA" in content
    assert "$env:ProgramFiles" in content
    assert "${env:ProgramFiles(x86)}" in content
    assert '"Programs\\Inno Setup 7\\ISCC.exe"' in content
    assert '"Inno Setup 6\\ISCC.exe"' in content


def test_build_script_passes_version_to_iscc() -> None:
    """ISCC.exeへVersion定義を渡す。"""
    content = read_build_script()
    assert '"--define=AppVersion=$version"' in content
    assert "$installerScript" in content


def test_build_script_generates_sha256() -> None:
    """インストーラーのSHA-256を生成する。"""
    content = read_build_script()
    assert "Get-FileHash" in content
    assert "-Algorithm SHA256" in content
    assert '"$installerPath.sha256.txt"' in content


def test_build_script_checks_forbidden_files() -> None:
    """利用者データと秘密情報の混入を検出する。"""
    content = read_build_script()
    for forbidden_name in (
        ".env",
        "config.local.json",
        "books.db",
        "book_manager.db",
        "*.db-wal",
        "*.db-shm",
    ):
        assert forbidden_name in content


def test_build_script_deletes_only_named_installer_artifacts() -> None:
    """既存成果物の削除対象を限定する。"""
    content = read_build_script()
    remove_commands = [
        line.strip()
        for line in content.splitlines()
        if line.strip().startswith("Remove-Item")
    ]
    assert remove_commands == ["Remove-Item $existingArtifact -Force"]
    assert "Remove-Item $installerOutputDirectory" not in content

[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipArchive
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
$originalLocation = Get-Location

$workDirectory = Join-Path $projectRoot "build\pyinstaller"
$versionFile = Join-Path $projectRoot "build\windows_version_info.txt"
$distributionDirectory = Join-Path $projectRoot "dist\BookManager"
$executablePath = Join-Path $distributionDirectory "BookManager.exe"
$specPath = Join-Path `
    $projectRoot `
    "packaging\pyinstaller\book_manager.spec"
$versionScript = Join-Path `
    $projectRoot `
    "scripts\generate_windows_version_info.py"

try {
    Set-Location $projectRoot

    if ($env:OS -ne "Windows_NT") {
        throw "Windows上でビルドしてください。"
    }

    if ([string]::IsNullOrWhiteSpace($env:VIRTUAL_ENV)) {
        throw "プロジェクトの仮想環境を有効にしてください。"
    }

    python -c "import PyInstaller"

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstallerを読み込めません。"
    }

    if (-not $SkipTests) {
        python -m pytest -q

        if ($LASTEXITCODE -ne 0) {
            throw "pytestが失敗したためビルドを中止します。"
        }
    }

    if (Test-Path $workDirectory) {
        Remove-Item $workDirectory -Recurse -Force
    }

    if (Test-Path $distributionDirectory) {
        Remove-Item $distributionDirectory -Recurse -Force
    }

    if (Test-Path $versionFile) {
        Remove-Item $versionFile -Force
    }

    $version = python $versionScript `
        --pyproject (Join-Path $projectRoot "pyproject.toml") `
        --output $versionFile

    if ($LASTEXITCODE -ne 0) {
        throw "Windows Version情報を生成できませんでした。"
    }

    $version = $version.Trim()

    if ([string]::IsNullOrWhiteSpace($version)) {
        throw "アプリケーションVersionを取得できませんでした。"
    }

    python -m PyInstaller `
        --noconfirm `
        --clean `
        --distpath (Join-Path $projectRoot "dist") `
        --workpath $workDirectory `
        $specPath

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstallerビルドに失敗しました。"
    }

    if (-not (Test-Path $executablePath -PathType Leaf)) {
        throw "BookManager.exeが生成されていません。"
    }

    $forbiddenFiles = Get-ChildItem `
        $distributionDirectory `
        -Recurse `
        -File |
        Where-Object {
            $_.Name -in @(
                ".env",
                "config.local.json",
                "books.db",
                "book_manager.db"
            ) -or
            $_.Name -like "*.db-wal" -or
            $_.Name -like "*.db-shm"
        }

    if ($forbiddenFiles) {
        $paths = $forbiddenFiles.FullName -join [Environment]::NewLine
        throw "配布禁止ファイルを検出しました。`n$paths"
    }

    Write-Host "実行ファイルを作成しました。"
    Write-Host $executablePath

    $warningFile = Get-ChildItem `
        $workDirectory `
        -Recurse `
        -File `
        -Filter "warn-*.txt" |
        Select-Object -First 1

    if ($warningFile) {
        Write-Host "PyInstaller警告ファイル:"
        Write-Host $warningFile.FullName
    }

    if (-not $SkipArchive) {
        $archiveName = "BookManager-$version-windows-x64.zip"
        $archivePath = Join-Path $projectRoot "dist\$archiveName"
        $checksumPath = "$archivePath.sha256.txt"

        if (Test-Path $archivePath) {
            Remove-Item $archivePath -Force
        }

        if (Test-Path $checksumPath) {
            Remove-Item $checksumPath -Force
        }

        Compress-Archive `
            -Path $distributionDirectory `
            -DestinationPath $archivePath `
            -CompressionLevel Optimal

        $hash = Get-FileHash `
            $archivePath `
            -Algorithm SHA256

        "$($hash.Hash)  $archiveName" |
            Set-Content `
                -Path $checksumPath `
                -Encoding ascii

        Write-Host "検証用ZIPを作成しました。"
        Write-Host $archivePath
        Write-Host "SHA-256を作成しました。"
        Write-Host $checksumPath
        Write-Host $hash.Hash
    }
}
finally {
    Set-Location $originalLocation
}

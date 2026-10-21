[CmdletBinding()]
param(
    [switch]$VerificationBuild
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
$originalLocation = Get-Location
$pyprojectPath = Join-Path $projectRoot "pyproject.toml"
$applicationDirectory = Join-Path $projectRoot "dist\BookManager"
$executablePath = Join-Path $applicationDirectory "BookManager.exe"
$internalDirectory = Join-Path $applicationDirectory "_internal"
$installerScript = Join-Path `
    $projectRoot `
    "packaging\inno_setup\book_manager.iss"
$installerOutputDirectory = Join-Path $projectRoot "dist\installer"

function Get-ProjectVersion {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $content = Get-Content $Path -Raw
    $projectSection = [regex]::Match(
        $content,
        '(?ms)^\[project\]\s*(.*?)(?=^\[|\z)'
    )

    if (-not $projectSection.Success) {
        throw "pyproject.tomlに[project]がありません。"
    }

    $versionMatch = [regex]::Match(
        $projectSection.Groups[1].Value,
        '(?m)^\s*version\s*=\s*["'']([^"'']+)["'']\s*$'
    )

    if (-not $versionMatch.Success) {
        throw "pyproject.tomlにproject.versionがありません。"
    }

    $version = $versionMatch.Groups[1].Value.Trim()

    if ($version -notmatch '^\d+\.\d+\.\d+$') {
        throw "project.versionはmajor.minor.patch形式で指定してください。"
    }

    return $version
}

function Find-InnoSetupCompiler {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 7\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 7\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate -PathType Leaf) {
            return $candidate
        }
    }

    $searchedPaths = $candidates -join [Environment]::NewLine
    throw "ISCC.exeが見つかりません。Inno Setup 7を導入してください。探索先:`n$searchedPaths"
}

try {
    Set-Location $projectRoot

    if ($env:OS -ne "Windows_NT") {
        throw "Windows上でビルドしてください。"
    }

    foreach ($requiredFile in @($pyprojectPath, $executablePath, $installerScript)) {
        if (-not (Test-Path $requiredFile -PathType Leaf)) {
            throw "必要なファイルがありません: $requiredFile"
        }
    }

    if (-not (Test-Path $internalDirectory -PathType Container)) {
        throw "PyInstaller成果物の_internalディレクトリがありません: $internalDirectory"
    }

    $version = Get-ProjectVersion -Path $pyprojectPath
    $productVersion = (Get-Item $executablePath).VersionInfo.ProductVersion

    if ($productVersion -ne $version) {
        throw "BookManager.exeとpyproject.tomlのVersionが一致しません。EXE: $productVersion / project: $version"
    }

    $forbiddenFiles = Get-ChildItem $applicationDirectory -Recurse -File |
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

    $isccPath = Find-InnoSetupCompiler
    $installerName = "BookManager-$version-windows-x64-setup.exe"
    if ($VerificationBuild) {
        $installerName = "BookManager-Verification-$version-windows-x64-setup.exe"
    }
    $installerPath = Join-Path $installerOutputDirectory $installerName
    $checksumPath = "$installerPath.sha256.txt"

    New-Item $installerOutputDirectory -ItemType Directory -Force |
        Out-Null

    foreach ($existingArtifact in @($installerPath, $checksumPath)) {
        if (Test-Path $existingArtifact -PathType Leaf) {
            Remove-Item $existingArtifact -Force
        }
    }

    $compilerArguments = @("--define=AppVersion=$version")
    if ($VerificationBuild) {
        $compilerArguments += "--define=VerificationBuild=1"
    }
    & $isccPath @compilerArguments $installerScript

    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setupによるインストーラービルドに失敗しました。"
    }

    if (-not (Test-Path $installerPath -PathType Leaf)) {
        throw "インストーラーが生成されていません: $installerPath"
    }

    $hash = Get-FileHash $installerPath -Algorithm SHA256
    "$($hash.Hash)  $installerName" |
        Set-Content -Path $checksumPath -Encoding ascii

    Write-Host "Windowsインストーラーを作成しました。"
    Write-Host $installerPath
    Write-Host "SHA-256を作成しました。"
    Write-Host $checksumPath
    Write-Host $hash.Hash
}
finally {
    Set-Location $originalLocation
}

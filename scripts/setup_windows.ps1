[CmdletBinding()]
param(
    [switch]$Apply,
    [ValidateSet('4.6.7','4.7.0')][string]$Version = '4.7.0',
    [string]$SourceDir,
    [string]$Config
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($SourceDir)) { $SourceDir = $env:AGT_SRC_DIR }
# Resolve an executable, then validate its reported version; existence alone is not enough.
$python = $null
foreach ($candidate in @('python.exe','python3.exe', (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'))) {
    if ($candidate -like '*.exe' -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { $python = (Resolve-Path -LiteralPath $candidate).Path; break }
    if ($candidate -match '^python' -and -not $python) {
        $found = (& where.exe $candidate 2>$null | Select-Object -First 1)
        if ($found -and (Test-Path -LiteralPath $found.Trim() -PathType Leaf)) { $python = $found.Trim(); break }
    }
}
if (-not $python) { throw '需要 Python 3.11+；不会安装' }
$pyVersion = (& $python -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or -not ($pyVersion -as [version]) -or [version]$pyVersion -lt [version]'3.11') { throw "需要 Python 3.11+，当前 $pyVersion" }
if ([string]::IsNullOrWhiteSpace($SourceDir) -or -not (Test-Path -LiteralPath $SourceDir -PathType Container)) { throw '需要已有 AGT 源码目录；不会克隆' }
$env:PYTHONPATH = "$root\scripts;$root\configs\agt"
try {
    if ($Config) { $cfg = (Resolve-Path -LiteralPath $Config -ErrorAction Stop).Path }
    else { $cfg = (& $python -c "import sys; from platform_tools import select_config; print(select_config())").Trim() }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $cfg -PathType Leaf)) { throw "配置发现失败或不存在: $cfg" }
    $git = (& $python -c "from platform_tools import discover_git; print(discover_git() or '')").Trim()
    if ($LASTEXITCODE -ne 0 -or -not $git) { throw '未发现 Git；不会安装' }
    $env:PATH = "$(Split-Path -Parent $git);$env:PATH"
    $bash = (& $python -c "from platform_tools import candidate_bash_paths; p=candidate_bash_paths(); print(p[0] if p else '')").Trim()
    if ($LASTEXITCODE -ne 0 -or -not $bash) { throw '未发现 Git Bash；不会安装' }
    Write-Host "预检通过: src=$SourceDir config=$cfg git=$git bash=$bash version=$Version; dry-run=$(-not $Apply)"
    & $python "$root\configs\agt\apply_refresh_interval.py" --config $cfg --dry-run
    if ($LASTEXITCODE -ne 0) { throw 'invalid config; no source changed' }
    & $python "$root\scripts\apply_agt_patch.py" $SourceDir --version $Version --dry-run
    if ($LASTEXITCODE -ne 0) { throw 'patch preflight failed; no source or config changed' }
    if ($Apply) {
        & $python "$root\scripts\apply_agt_patch.py" $SourceDir --version $Version
        if ($LASTEXITCODE -ne 0) { throw 'AGT patch failed; configuration was not changed' }
        & $python "$root\configs\agt\apply_refresh_interval.py" --config $cfg
        if ($LASTEXITCODE -ne 0) { throw 'configuration update failed' }
    }
} catch { Write-Error $_; exit 1 }

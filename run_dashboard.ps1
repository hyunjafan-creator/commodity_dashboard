param([switch]$LocalOnly, [switch]$NoOpen)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$logPath = Join-Path $PSScriptRoot 'run.log'
$exitCode = 1
$lock = $null
function Log([string]$Message) {
    $Message | Tee-Object -FilePath $logPath -Append | Out-Host
}
function Invoke-Git {
    param([string[]]$GitArgs)
    $ErrorActionPreference = 'Continue'
    & git @GitArgs 2>&1 | ForEach-Object { Log "$_" }
    $gitCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($gitCode -ne 0) { throw "git $($GitArgs -join ' ') failed ($gitCode)" }
}
try {
    $lock = [IO.File]::Open((Join-Path $PSScriptRoot '.update.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    Log ("===== " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + " =====")
    # Resolve an actual Python executable; do not rely on a launcher on PATH.
    $pythonExe = $env:COMMODITY_PYTHON
    if (-not $pythonExe) {
        $candidates = @()
        foreach ($cmd in @('py', 'python', 'python3')) {
            $found = Get-Command $cmd -ErrorAction SilentlyContinue
            if ($found) {
                try {
                    $resolved = & $found.Source -c "import sys; print(sys.executable)" 2>$null
                    if ($LASTEXITCODE -eq 0) { $candidates += [string]$resolved }
                } catch {}
            }
        }
        $candidates += (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
        foreach ($candidate in $candidates) {
            if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
                $pythonExe = $candidate
                break
            }
        }
    }
    if (-not $pythonExe -or -not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
        throw 'Python 3 was not found. Install Python or set COMMODITY_PYTHON to python.exe.'
    }
    Log "Python: $pythonExe"
    $ErrorActionPreference = 'Continue'
    & $pythonExe -u run.py 2>&1 | ForEach-Object { Log "$_" }
    $collectExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($collectExit -notin @(0, 2)) {
        throw "Collection failed ($collectExit). Existing prices retained; upload stopped. See run.log."
    }
    $status = Get-Content -LiteralPath 'data/update_status.json' -Raw -Encoding UTF8 | ConvertFrom-Json
    Log "Collection: $($status.state); OK=$($status.ok), failed=$($status.fail), skipped=$($status.skipped)"
    foreach ($item in $status.items) {
        if ($item.stale) { Log "STALE: $($item.id) / $($item.latest_date)" }
    }
    if (-not $LocalOnly) {
        $env:GIT_TERMINAL_PROMPT = '0'
        $env:GCM_INTERACTIVE = 'never'
        # Stage only dashboard source and public price outputs, never browser sessions.
        Invoke-Git -GitArgs @('add', '--', '*.py', '*.bat', '*.ps1', '*.html', 'README.md', '.gitignore', 'data/*.csv', 'data/update_status.json', '.github/workflows/update.yml')
        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 1) {
            Invoke-Git -GitArgs @('commit', '-m', ('dashboard update ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')))
        } elseif ($LASTEXITCODE -ne 0) { throw 'Cannot inspect staged changes.' }
        Invoke-Git -GitArgs @('fetch', 'origin', 'main')
        $ErrorActionPreference = 'Continue'
        & $pythonExe -u sync_remote.py 2>&1 | ForEach-Object { Log "$_" }
        $syncExit = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'
        if ($syncExit -ne 0) { throw 'Cloud price synchronization failed; upload stopped. See run.log.' }
        Invoke-Git -GitArgs @('push', 'origin', 'HEAD:main')
        Log 'PUSH OK. GitHub Pages deployment can take a few minutes.'
        Log ('Web: https://hyunjafan-creator.github.io/commodity_dashboard/?v=' + (Get-Date -Format 'yyyyMMddHHmmss'))
    }
    $exitCode = $collectExit
    if ($collectExit -eq 2) { Log 'PARTIAL: Some sources failed; their last known prices remain marked with source dates.' }
    else { Log 'DONE: Collection and dashboard build completed.' }
} catch {
    Log ("FAILED: " + $_.Exception.Message)
    $exitCode = 1
} finally {
    if ($lock) { $lock.Dispose() }
    $dashboard = Join-Path $PSScriptRoot 'index.html'
    if (-not $NoOpen -and (Test-Path -LiteralPath $dashboard)) {
        $uri = [Uri]::new($dashboard).AbsoluteUri + '?v=' + (Get-Date -Format 'yyyyMMddHHmmss')
        try { Start-Process $uri } catch { Log "Open manually: $dashboard" }
    }
}
exit $exitCode

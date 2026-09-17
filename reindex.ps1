<#
.SYNOPSIS
    SORA Multi-Repo Unified Reindexer Script
.DESCRIPTION
    Re-indexes all Sora videos across 5 repositories:
      - RadinX/sora
      - RadinX/luqmanz
      - RadinX/sora-standup-1
      - RadinX/sora-standup-2
      - RadinX/sora-standup-3
.EXAMPLE
    .\reindex.ps1
    .\reindex.ps1 -Token "github_pat_..."
    .\reindex.ps1 -LocalDir ".."
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$false)]
    [string]$Token,

    [Parameter(Mandatory=$false)]
    [string]$LocalDir,

    [Parameter(Mandatory=$false)]
    [string]$Out,

    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

$scriptPath = Join-Path $PSScriptRoot "reindex.js"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js tidak ditemukan di PATH. Silakan instal Node.js terlebih dahulu."
    exit 1
}

$nodeArgs = @($scriptPath)

if ($Token) {
    $nodeArgs += @("--token", $Token)
}

if ($LocalDir) {
    $nodeArgs += @("--local-dir", $LocalDir)
}

if ($Out) {
    $nodeArgs += @("--out", $Out)
}

if ($RemainingArgs) {
    $nodeArgs += $RemainingArgs
}

Write-Host "Menjalankan reindex.js..." -ForegroundColor Cyan
& node @nodeArgs

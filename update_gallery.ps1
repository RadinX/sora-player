<#
.SYNOPSIS
    SORA Multi-Repo Unified Reindexer Script
.DESCRIPTION
    Re-indexes all Sora videos across 5 repositories:
      - yolajeni90/sora
      - yolajeni90/luqmanz
      - yolajeni90/sora-standup-1
      - yolajeni90/sora-standup-2
      - yolajeni90/sora-standup-3
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

Write-Host "Menjalankan update gallery (reindex.js)..." -ForegroundColor Cyan
& node @nodeArgs

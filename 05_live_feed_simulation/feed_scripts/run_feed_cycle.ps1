<#
run_feed_cycle.ps1

One cycle performs:
  1) Admissions
  2) Transfers
  3) Discharges
  4) CBP refresh (CONCURRENTLY)

After EACH phase, CPU and memory are sampled using collectors.

Example:
  powershell -ExecutionPolicy Bypass -File run_feed_cycle.ps1 `
    -Admissions 10 -Transfers 5 -Discharges 5
#>

param (
    [int]$Admissions = 10,
    [int]$Transfers  = 5,
    [int]$Discharges = 5,

    [int]$Seed       = 42,

    [string]$DbHost  = "127.0.0.1",
    [int]$DbPort     = 55432,
    [string]$DbName  = "acbp_db",
    [string]$DbUser  = "acbp",
    [string]$DbPass  = "acbp",

    [string]$Container = "acbp-postgres"
)

$ErrorActionPreference = "Stop"

# Paths
$ROOT = Resolve-Path "$PSScriptRoot\..\.."
$FEEDS = Join-Path $ROOT "05_live_feed_simulation\feed_scripts"
$COLLECTORS = Join-Path $ROOT "07_metrics_collection\collectors"
$LOGS  = Join-Path $ROOT "05_live_feed_simulation\logs"

New-Item -ItemType Directory -Force -Path $LOGS | Out-Null

$Timestamp = (Get-Date).ToString("yyyy-MM-ddTHH-mm-ssZ")
$LogFile = Join-Path $LOGS "feed_cycle_$Timestamp.log"

function Log($msg) {
    $line = "$(Get-Date -Format o) | $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Sample-Resources($phase) {
    Log "Sampling resources after $phase"
    python "$COLLECTORS\collect_cpu.py" --samples 1 --container $Container
    python "$COLLECTORS\collect_memory.py" --samples 1 --container $Container
}

Log "=== FEED CYCLE START ==="

if ($Admissions -gt 0) {
    Log "Admissions: $Admissions"
    python "$FEEDS\simulate_admission.py" `
        --n $Admissions `
        --seed $Seed `
        --host $DbHost `
        --port $DbPort `
        --db   $DbName `
        --user $DbUser `
        --password $DbPass `
        --allow_unbedded

    Sample-Resources "Admissions"
}

if ($Transfers -gt 0) {
    Log "Transfers: $Transfers"
    python "$FEEDS\simulate_transfer.py" `
        --k $Transfers `
        --seed $Seed `
        --host $DbHost `
        --port $DbPort `
        --db   $DbName `
        --user $DbUser `
        --password $DbPass `
        --transfer_probability 0.6

    Sample-Resources "Transfers"
}

if ($Discharges -gt 0) {
    Log "Discharges: $Discharges"
    python "$FEEDS\simulate_discharge.py" `
        --k $Discharges `
        --seed $Seed `
        --host $DbHost `
        --port $DbPort `
        --db   $DbName `
        --user $DbUser `
        --password $DbPass

    Sample-Resources "Discharges"
}

Log "CBP refresh (CONCURRENTLY)"
docker exec -i $Container psql `
    -U $DbUser `
    -d $DbName `
    -c "SELECT cbp.refresh_fac01_all(true);"

Sample-Resources "CBP_refresh"

Log "=== FEED CYCLE END ==="
param(
  [string]$DB_HOST = "127.0.0.1",
  [string]$DB_PORT = "55432",
  [string]$DB_NAME = "acbp",
  [string]$DB_USER = "postgres",
  [string]$DB_PASSWORD = ""
)

$ErrorActionPreference = "Stop"

$ROOT = "D:\ICDM2026\ACBP_Clinical_Dashboard_Experiment"
$EXT  = Join-Path $ROOT "11_validity_stress_extension"

if ($DB_PASSWORD -ne "") {
  $env:PGPASSWORD = $DB_PASSWORD
}

Write-Host "Running ACBP validity-stress extension..."

psql -v ON_ERROR_STOP=1 -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$EXT\sql\00_create_extension_schema.sql"
psql -v ON_ERROR_STOP=1 -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$EXT\sql\01_build_live_observed_surface.sql"
psql -v ON_ERROR_STOP=1 -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$EXT\sql\02_build_cbp_observed_surface.sql"
psql -v ON_ERROR_STOP=1 -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$EXT\sql\03_build_synthetic_invalid_space.sql"
psql -v ON_ERROR_STOP=1 -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$EXT\sql\04_apply_acbp_validity_labels.sql"
psql -v ON_ERROR_STOP=1 -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$EXT\sql\05_dotk_complexity_summary.sql"
psql -v ON_ERROR_STOP=1 -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$EXT\sql\06_export_ml_dataset.sql"

$pythonArgs = @(
  "$EXT\scripts\run_validity_ml.py",
  "--host", $DB_HOST,
  "--port", $DB_PORT,
  "--db", $DB_NAME,
  "--user", $DB_USER,
  "--outdir", "$EXT\outputs"
)

if ($DB_PASSWORD -ne "") {
  $pythonArgs += @("--password", $DB_PASSWORD)
}

python @pythonArgs

Write-Host "Validity-stress extension complete."

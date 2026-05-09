# setup_dwh.ps1 — Crea los schemas dwh y marts desde cero.
#
# Ejecutar UNA VEZ antes del primer run_etl.py, o cada vez que se
# quiera recrear la estructura de tablas (los DDLs son idempotentes:
# DROP TABLE IF EXISTS + CREATE TABLE).
#
# Uso (desde GD_proyecto_final/):
#   $env:PGPASSWORD = "tu_contrasena"
#   .\scripts\setup_dwh.ps1
#
# Requiere: psql en el PATH y el archivo .env con DB_USER / DB_NAME.

$ErrorActionPreference = "Stop"

foreach ($linea in Get-Content ".env") {
    if ($linea -match '^\s*([^#][^=]*?)\s*=\s*(.*)\s*$') {
        $clave = $Matches[1].Trim()
        $valor = $Matches[2].Trim().Trim('"').Trim("'")
        Set-Item -Path "env:$clave" -Value $valor
    }
}

$PG_USER = $env:DB_USER
$PG_DB   = $env:DB_NAME
if (-not $env:PGPASSWORD) { $env:PGPASSWORD = $env:DB_PASSWORD }

Write-Host ""
Write-Host "========================================================"
Write-Host " SETUP DWH — $PG_DB"
Write-Host "========================================================"

Write-Host ""
Write-Host "[1/2] Creando schema dwh (src/etl/sql/dwh_schema.sql)..."
psql -U $PG_USER -d $PG_DB -f "src/etl/sql/dwh_schema.sql"

Write-Host ""
Write-Host "[2/2] Creando schema marts (src/etl/sql/marts_schema.sql)..."
psql -U $PG_USER -d $PG_DB -f "src/etl/sql/marts_schema.sql"

Write-Host ""
Write-Host "========================================================"
Write-Host " Setup completado. Lanza run_etl.py para cargar datos."
Write-Host "========================================================"
Write-Host ""

# reset_y_verifica.ps1
# Prueba de reproducibilidad completa: drop → restore → limpieza → exploración → diff.
#
# Uso (desde GD_proyecto_final/):
#   $env:PGPASSWORD = "tu_contraseña"
#   .\scripts\reset_y_verifica.ps1
#
# Requiere: pg_restore, createdb, dropdb y psql en el PATH.

$ErrorActionPreference = "Stop"

# ── Configuración ────────────────────────────────────────────────────────────

# Leer credenciales desde .env (mismo formato que usa Python)
foreach ($linea in Get-Content ".env") {
    if ($linea -match '^\s*([^#][^=]*?)\s*=\s*(.*)\s*$') {
        $clave = $Matches[1].Trim()
        $valor = $Matches[2].Trim().Trim('"').Trim("'")
        Set-Item -Path "env:$clave" -Value $valor
    }
}

$PG_USER = $env:DB_USER
$PG_DB   = $env:DB_NAME
$DUMP    = "saleshealthBackupGD.sql"
$REPORT_NUEVO = "reports\exploracion_reproducibilidad.md"

if (-not $env:PGPASSWORD) { $env:PGPASSWORD = $env:DB_PASSWORD }

Write-Host ""
Write-Host "========================================================"
Write-Host " RESET Y VERIFICACIÓN — $PG_DB"
Write-Host "========================================================"
Write-Host ""

# ── Paso 1: Terminar conexiones activas ──────────────────────────────────────
Write-Host "[1/6] Terminando conexiones activas a '$PG_DB'..."
psql -U $PG_USER -d postgres -c `
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$PG_DB' AND pid<>pg_backend_pid();" `
    | Out-Null

# ── Paso 2: Drop + Create ────────────────────────────────────────────────────
Write-Host "[2/6] Eliminando base de datos '$PG_DB'..."
dropdb -U $PG_USER --if-exists $PG_DB

Write-Host "[3/6] Creando base de datos '$PG_DB' (UTF8, LC_COLLATE=C)..."
createdb -U $PG_USER -E UTF8 --lc-collate=C --lc-ctype=C -T template0 $PG_DB

# ── Paso 3: Restaurar dump ───────────────────────────────────────────────────
Write-Host "[4/6] Restaurando dump '$DUMP'..."
if (-not (Test-Path $DUMP)) {
    Write-Error "No se encuentra el dump en: $DUMP"
    exit 1
}
pg_restore -U $PG_USER -d $PG_DB --no-owner --no-privileges $DUMP
Write-Host "      Restauración completada."

# ── Paso 4: Limpieza ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[5/6] Ejecutando script de limpieza..."
python src/limpieza/limpieza.py

# ── Paso 5: Exploración ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "[6/6] Ejecutando exploración (output: $REPORT_NUEVO)..."
python src/exploracion/explorar_bd.py --output $REPORT_NUEVO

# ── Paso 6: Diff de cifras clave ─────────────────────────────────────────────
Write-Host ""
Write-Host "========================================================"
Write-Host " VERIFICACIÓN FINAL — cifras clave post-reset"
Write-Host "========================================================"

$sql = @"
SELECT 'sale_item'       AS tabla, COUNT(*) AS filas FROM public.sale_item
UNION ALL SELECT 'sale',           COUNT(*)          FROM public.sale
UNION ALL SELECT 'central_product',COUNT(*)          FROM public.central_product
UNION ALL SELECT 'return_item',    COUNT(*)          FROM public.return_item
ORDER BY filas DESC;
"@
Write-Host "`n-- Volúmenes (esperado: sale_item=42313, sale=20000, central_product=50, return_item=2330)"
psql -U $PG_USER -d $PG_DB -c $sql

$sql2 = @"
SELECT
    COUNT(*) FILTER (WHERE offer_id IS NULL)  AS offer_id_nulls,
    COUNT(*) FILTER (WHERE offer_id IS NOT NULL) AS offer_id_con_valor
FROM public.sale_item;
"@
Write-Host "`n-- Nulos en offer_id (esperado: nulls=42305, con_valor=8)"
psql -U $PG_USER -d $PG_DB -c $sql2

$sql3 = @"
SELECT COUNT(*) AS duplicados_sale_item
FROM (
    SELECT sale_id, product_id, quantity, unit_price, offer_id, subtotal
    FROM public.sale_item
    GROUP BY sale_id, product_id, quantity, unit_price, offer_id, subtotal
    HAVING COUNT(*) > 1
) t;
"@
Write-Host "`n-- Duplicados en sale_item (esperado: 0)"
psql -U $PG_USER -d $PG_DB -c $sql3

$sql4 = @"
SELECT COUNT(*) AS ventas_total_incorrecto
FROM public.sale s
WHERE ABS(s.total - COALESCE(
    (SELECT SUM(si.subtotal) FROM public.sale_item si WHERE si.sale_id = s.sale_id), 0
)) > 0.01;
"@
Write-Host "`n-- Ventas con total incorrecto (esperado: 0)"
psql -U $PG_USER -d $PG_DB -c $sql4

$sql5 = @"
SELECT product_id, name, category_id, unit_cost, unit_price
FROM public.central_product WHERE product_id = 29;
"@
Write-Host "`n-- Product 29 en central_product (esperado: 1 fila con unit_cost NOT NULL)"
psql -U $PG_USER -d $PG_DB -c $sql5

$sql6 = @"
SELECT
    (SELECT COUNT(*) FROM public.sale_item si LEFT JOIN public.sale s ON s.sale_id=si.sale_id WHERE s.sale_id IS NULL)       AS huerfanos_si_sale,
    (SELECT COUNT(*) FROM public.sale_item si LEFT JOIN public.product p ON p.product_id=si.product_id WHERE p.product_id IS NULL) AS huerfanos_si_product,
    (SELECT COUNT(*) FROM public.return_item ri LEFT JOIN public.sale_item si ON si.sale_item_id=ri.sale_item_id WHERE si.sale_item_id IS NULL) AS huerfanos_ri_si,
    (SELECT COUNT(*) FROM public.product p LEFT JOIN public.central_product cp ON cp.product_id=p.product_id WHERE cp.product_id IS NULL) AS productos_sin_central;
"@
Write-Host "`n-- Integridad referencial (esperado: todo 0)"
psql -U $PG_USER -d $PG_DB -c $sql6

Write-Host ""
Write-Host "========================================================"
Write-Host " Informe completo guardado en: $REPORT_NUEVO"
Write-Host " Compara con:                  reports\exploracion.md"
Write-Host "========================================================"
Write-Host ""

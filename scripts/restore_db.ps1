# Восстановление готовой БД DubaiCost из дампа delivery/dubaicost.dump.
# Запускать в PowerShell из корня проекта:
#     .\scripts\restore_db.ps1
# Параметры можно переопределить:
#     .\scripts\restore_db.ps1 -DbPassword "МойПароль" -PgBin "C:\Program Files\PostgreSQL\16\bin"
#
# Требуется: установленный PostgreSQL 16 + PostGIS. Скрипт создаёт роль и БД,
# включает PostGIS и заливает дамп. Идемпотентен — повторный запуск пересоздаёт БД.

param(
    [string]$PgBin       = "C:\Program Files\PostgreSQL\16\bin",
    [string]$PgHost      = "127.0.0.1",
    [int]   $PgPort      = 5432,
    [string]$SuperUser   = "postgres",       # суперпользователь для CREATE DATABASE
    [string]$DbName      = "dubaicost",
    [string]$DbUser      = "dubaicost",
    [string]$DbPassword  = "changeme",        # пароль роли приложения (совпадает с backend/.env)
    [string]$DumpFile    = "delivery\dubaicost.dump"
)

$ErrorActionPreference = "Stop"
$psql       = Join-Path $PgBin "psql.exe"
$pgrestore  = Join-Path $PgBin "pg_restore.exe"

if (-not (Test-Path $DumpFile)) { throw "Не найден дамп: $DumpFile (его отдают отдельно, в git его нет)" }
if (-not (Test-Path $psql))     { throw "Не найден psql: $psql — проверь -PgBin" }

Write-Host "1/5 Пароль суперпользователя '$SuperUser' (ввод скрыт)..."
$superPw = Read-Host -AsSecureString "Пароль $SuperUser"
$env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($superPw))

Write-Host "2/5 Создаю роль '$DbUser' (если нет)..."
& $psql -U $SuperUser -h $PgHost -p $PgPort -v ON_ERROR_STOP=0 -c `
  "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='$DbUser') THEN CREATE ROLE $DbUser LOGIN PASSWORD '$DbPassword'; END IF; END `$`$;"

Write-Host "3/5 Пересоздаю БД '$DbName'..."
& $psql -U $SuperUser -h $PgHost -p $PgPort -c "DROP DATABASE IF EXISTS $DbName;"
& $psql -U $SuperUser -h $PgHost -p $PgPort -c "CREATE DATABASE $DbName OWNER $DbUser;"
& $psql -U $SuperUser -h $PgHost -p $PgPort -d $DbName -c "CREATE EXTENSION IF NOT EXISTS postgis;"

Write-Host "4/5 Заливаю дамп (одно безобидное предупреждение про COMMENT ON EXTENSION — это норма)..."
$env:PGPASSWORD = $DbPassword
& $pgrestore -U $DbUser -h $PgHost -p $PgPort -d $DbName --no-owner --no-privileges $DumpFile

Write-Host "5/5 Проверка..."
& $psql -U $DbUser -h $PgHost -p $PgPort -d $DbName -c `
  "SELECT (SELECT count(*) FROM buildings) AS buildings, (SELECT count(*) FROM latest_building_metrics) AS metrics;"

Write-Host "Готово. Дальше — backend/.env с DATABASE_URL и запуск (см. РАЗВЁРТЫВАНИЕ.md)." -ForegroundColor Green

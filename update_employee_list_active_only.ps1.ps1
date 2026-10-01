$ErrorActionPreference = "Stop"

$main = Join-Path $PSScriptRoot "backend\app\main.py"
if (-not (Test-Path -LiteralPath $main)) {
    throw "main.py topilmadi: $main"
}

$content = Get-Content -LiteralPath $main -Raw -Encoding UTF8
$old = @"
            WHERE u.organization_id = :organization_id
              AND r.name IN (
"@
$new = @"
            WHERE u.organization_id = :organization_id
              AND u.status = 'ACTIVE'
              AND r.name IN (
"@

if (-not $content.Contains($old)) {
    throw "Kerakli WHERE bloki topilmadi yoki allaqachon yangilangan."
}

$backup = "$main.before_active_employee_list"
Copy-Item -LiteralPath $main -Destination $backup -Force

$content = $content.Replace($old, $new)
Set-Content -LiteralPath $main -Value $content -Encoding UTF8

Write-Host "UPDATED: $main"
Write-Host "BACKUP:  $backup"
Write-Host "OK: employee list now returns ACTIVE accounts only."

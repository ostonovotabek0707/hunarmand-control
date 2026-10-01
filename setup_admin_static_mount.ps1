$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$main = Join-Path $root "backend\app\main.py"
$adminSource = Join-Path $root "admin\index.html"
$adminDir = Join-Path $root "backend\app\admin"
$adminTarget = Join-Path $adminDir "index.html"

if (-not (Test-Path -LiteralPath $main)) {
    throw "main.py topilmadi: $main"
}
if (-not (Test-Path -LiteralPath $adminSource)) {
    throw "admin\index.html topilmadi: $adminSource"
}

New-Item -ItemType Directory -Force -Path $adminDir | Out-Null
Copy-Item -LiteralPath $adminSource -Destination $adminTarget -Force

$content = Get-Content -LiteralPath $main -Raw -Encoding UTF8

if ($content -match 'from fastapi\.staticfiles import StaticFiles') {
    $hasStaticImport = $true
} else {
    $hasStaticImport = $false
    $content = "from fastapi.staticfiles import StaticFiles`r`n" + $content
}

if ($content -match 'app\.mount\("/admin"') {
    Write-Host "Admin mount already exists. HTML copied."
} else {
    $marker = 'app = FastAPI('
    $idx = $content.IndexOf($marker)
    if ($idx -lt 0) {
        throw "app = FastAPI( topilmadi."
    }

    $lineEnd = $content.IndexOf("`n", $idx)
    if ($lineEnd -lt 0) {
        throw "FastAPI qatori tugashi topilmadi."
    }

    $insertAt = $lineEnd + 1
    $mountBlock = @'
from pathlib import Path

ADMIN_DIR = Path(__file__).resolve().parent / "admin"
app.mount("/admin", StaticFiles(directory=ADMIN_DIR, html=True), name="admin")
'@

    $content = $content.Substring(0, $insertAt) + $mountBlock + "`r`n" + $content.Substring($insertAt)
}

$backup = "$main.before_admin_static_mount"
Copy-Item -LiteralPath $main -Destination $backup -Force
Set-Content -LiteralPath $main -Value $content -Encoding UTF8

Write-Host "ADMIN HTML: $adminTarget"
Write-Host "UPDATED:    $main"
Write-Host "BACKUP:     $backup"
Write-Host "OK: /admin static mount configured."

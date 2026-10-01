$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$main = Join-Path $root "backend\app\main.py"
$adminHtml = Join-Path $root "backend\app\admin\index.html"

if (-not (Test-Path -LiteralPath $main)) {
    throw "main.py topilmadi: $main"
}
if (-not (Test-Path -LiteralPath $adminHtml)) {
    throw "admin\index.html topilmadi: $adminHtml"
}

$content = Get-Content -LiteralPath $main -Raw -Encoding UTF8

# Add required import safely at the very top.
if ($content -notmatch '(?m)^from pathlib import Path\s*$') {
    $content = "from pathlib import Path`r`n" + $content
}
if ($content -notmatch '(?m)^from fastapi\.responses import FileResponse\s*$') {
    $content = "from fastapi.responses import FileResponse`r`n" + $content
}

# Do not duplicate the route.
if ($content -match '@app\.get\("/admin/"') {
    Write-Host "Admin route already exists. Nothing else to add."
} else {
    $route = @'
@app.get("/admin/", include_in_schema=False)
def admin_page():
    admin_file = Path(__file__).resolve().parent / "admin" / "index.html"
    return FileResponse(admin_file)
'@

    $rootPattern = '(?m)^@app\.get\("/")\s*$'
    if ($content -notmatch $rootPattern) {
        throw "Root @app.get('/') route topilmadi."
    }

    $backup = "$main.before_admin_fileresponse"
    Copy-Item -LiteralPath $main -Destination $backup -Force

    $content = [regex]::Replace(
        $content,
        $rootPattern,
        ($route.TrimEnd() + "`r`n`r`n" + '$0'),
        1
    )

    Set-Content -LiteralPath $main -Value $content -Encoding UTF8
    Write-Host "UPDATED: $main"
    Write-Host "BACKUP:  $backup"
}

Write-Host "OK: /admin/ FileResponse route configured."

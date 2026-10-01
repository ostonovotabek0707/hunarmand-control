$ErrorActionPreference = "Stop"

$main = Join-Path $PSScriptRoot "backend\app\main.py"
$backup = Join-Path $PSScriptRoot "backend\app\main.py.before_employee_list_all_roles.ps1"

if (-not (Test-Path -LiteralPath $main)) {
    throw "main.py topilmadi: $main"
}

$content = Get-Content -LiteralPath $main -Raw -Encoding UTF8

$pattern = '(?s)@app\.get\("/api/v1/admin/employees"\)\s+def list_employees\(.*?(?=\r?\n@app\.)'

$newEndpoint = @'
@app.get("/api/v1/admin/employees")
def list_employees(
    current_user: dict = Depends(get_current_user)
):
    allowed_roles = {
        "SUPER_ADMIN",
        "REGIONAL_HEAD",
        "REGIONAL_MANAGER",
        "DISTRICT_HEAD"
    }

    if current_user["role_name"] not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    with engine.begin() as conn:
        base_sql = """
            SELECT
                u.id,
                u.phone,
                u.status,
                u.created_at,
                r.name AS role_name,
                ep.full_name,
                ep.position,
                ep.employee_number,
                ep.hire_date,
                ep.birth_date,
                ep.education,
                d.name AS district_name,
                dep.name AS department_name
            FROM users u
            JOIN roles r
                ON r.id = u.role_id
            JOIN employee_profiles ep
                ON ep.user_id = u.id
            LEFT JOIN departments dep
                ON dep.id = ep.department_id
            LEFT JOIN districts d
                ON d.id = dep.district_id
            WHERE u.organization_id = :organization_id
              AND r.name IN (
                  'SUPER_ADMIN',
                  'REGIONAL_HEAD',
                  'REGIONAL_MANAGER',
                  'DISTRICT_HEAD',
                  'EMPLOYEE'
              )
        """

        params = {
            "organization_id": current_user["organization_id"]
        }

        if current_user["role_name"] == "DISTRICT_HEAD":
            base_sql += """
              AND d.id = (
                  SELECT d2.id
                  FROM employee_profiles ep2
                  JOIN departments dep2
                      ON dep2.id = ep2.department_id
                  JOIN districts d2
                      ON d2.id = dep2.district_id
                  WHERE ep2.user_id = :current_user_id
                  LIMIT 1
              )
            """
            params["current_user_id"] = current_user["id"]

        base_sql += """
            ORDER BY
                CASE r.name
                    WHEN 'SUPER_ADMIN' THEN 1
                    WHEN 'REGIONAL_HEAD' THEN 2
                    WHEN 'REGIONAL_MANAGER' THEN 3
                    WHEN 'DISTRICT_HEAD' THEN 4
                    WHEN 'EMPLOYEE' THEN 5
                    ELSE 9
                END,
                ep.full_name
        """

        rows = conn.execute(
            text(base_sql),
            params
        ).mappings().all()

    return {
        "ok": True,
        "count": len(rows),
        "employees": [dict(row) for row in rows]
    }
'@

$matches = [regex]::Matches($content, $pattern)
if ($matches.Count -ne 1) {
    throw "GET /api/v1/admin/employees блоклари сони 1 эмас: $($matches.Count)"
}

Copy-Item -LiteralPath $main -Destination $backup -Force

$updated = [regex]::Replace($content, $pattern, $newEndpoint, 1)

Set-Content -LiteralPath $main -Value $updated -Encoding UTF8

Write-Host "UPDATED: $main"
Write-Host "BACKUP:  $backup"
Write-Host "OK: employee list endpoint updated."

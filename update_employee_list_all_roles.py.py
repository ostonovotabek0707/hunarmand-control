from pathlib import Path
import re

MAIN = Path(r"C:\Users\hp computers\Desktop\HunarmandControl\hunarmand-control\backend\app\main.py")

NEW_ENDPOINT = """
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
        rows = conn.execute(
            text("""
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
            """),
            {
                "organization_id": current_user["organization_id"]
            }
        ).mappings().all()

    return {
        "ok": True,
        "count": len(rows),
        "employees": [dict(row) for row in rows]
    }
"""

text = MAIN.read_text(encoding="utf-8")

pattern = r'@app\.get\("/api/v1/admin/employees"\)\s+def list_employees\(.*?(?=\n@app\.)'
match = re.search(pattern, text, flags=re.S)
if not match:
    raise SystemExit("GET /api/v1/admin/employees block not found")

backup = MAIN.with_suffix(".py.before_employee_list_all_roles")
backup.write_text(text, encoding="utf-8")

updated = text[:match.start()] + NEW_ENDPOINT.strip() + "\n\n" + text[match.end():]
MAIN.write_text(updated, encoding="utf-8")

print("UPDATED:", MAIN)
print("BACKUP:", backup)
print("OK: employee list endpoint updated.")

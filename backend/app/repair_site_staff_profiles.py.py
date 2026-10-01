import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "/app/app")

from main import engine
from sqlalchemy import text

DATA_FILE = Path("/app/app/hunarmand_control_staff_import_16.json")

DISTRICT_NAMES = {
    "g‘ijduvon tumani": "G‘ijduvon tumani",
    "romitan tumani": "Romitan tumani",
    "vobkent tumani": "Vobkent tumani",
    "jondor tumani": "Jondor tumani",
    "buxoro tumani": "Buxoro tumani",
    "kogon shahri": "Kogon shahri",
}


def parse_birth_date(value: str) -> str:
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", (value or "").strip())
    if not m:
        raise ValueError(f"Invalid birth date: {value!r}")
    d, mth, y = m.groups()
    return f"{y}-{mth}-{d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    records = data.get("records", [])
    if len(records) != 16:
        raise SystemExit(f"Expected 16 records, found {len(records)}")

    with engine.begin() as conn:
        district_rows = conn.execute(
            text("""
                SELECT d.name, dep.id
                FROM districts d
                JOIN departments dep ON dep.district_id = d.id
                WHERE d.active = TRUE
                  AND dep.active = TRUE
                  AND dep.name = 'Hunarmand'
            """)
        ).fetchall()

        district_map = {
            row[0].strip().lower(): row[1]
            for row in district_rows
        }

        print("PROFILE REPAIR PLAN")
        print("-" * 100)

        for item in records:
            site_id = int(item["id"])
            employee_number = f"SITE-{site_id:03d}"
            name = item["name"].strip()
            position = item["position"].strip()
            birth_date = parse_birth_date(item["birth"])
            education = (item.get("education") or "").strip()
            source_district = (item.get("district") or "").strip()

            department_id = None
            district_label = "Regional office"
            if source_district:
                key = source_district.lower()
                department_id = district_map.get(key)
                if not department_id:
                    raise SystemExit(
                        f"Department not found for {name}: {source_district}"
                    )
                district_label = source_district

            existing = conn.execute(
                text("""
                    SELECT ep.user_id, ep.full_name, ep.position, ep.birth_date,
                           ep.education, ep.department_id
                    FROM employee_profiles ep
                    WHERE ep.employee_number = :employee_number
                """),
                {"employee_number": employee_number},
            ).fetchone()

            action = "FOUND / WILL UPDATE" if existing else "NOT FOUND"
            print(
                f"{employee_number} | {name} | {position} | "
                f"{birth_date} | {district_label} | {action}"
            )

            if args.apply:
                if not existing:
                    raise SystemExit(
                        f"Cannot repair missing profile: {employee_number} / {name}"
                    )

                conn.execute(
                    text("""
                        UPDATE employee_profiles
                        SET full_name = :full_name,
                            position = :position,
                            birth_date = :birth_date,
                            education = :education,
                            department_id = :department_id
                        WHERE employee_number = :employee_number
                    """),
                    {
                        "full_name": name,
                        "position": position,
                        "birth_date": birth_date,
                        "education": education,
                        "department_id": department_id,
                        "employee_number": employee_number,
                    },
                )

        print("-" * 100)
        if args.apply:
            print("PROFILE REPAIR COMPLETED.")
        else:
            print("PREVIEW ONLY: no database changes.")
            print("To apply: --apply")


if __name__ == "__main__":
    main()

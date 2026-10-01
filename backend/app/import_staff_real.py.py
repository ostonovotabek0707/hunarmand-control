import argparse
import json
import re
import secrets
import string
from pathlib import Path

# main.py is copied into /app/app in this project.
import sys
sys.path.insert(0, "/app/app")

from main import engine, pwd_context
from sqlalchemy import text

DATA_FILE = Path("/app/app/hunarmand_control_staff_import_16.json")


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("998") and len(digits) == 12:
        return "+" + digits
    if len(digits) == 9:
        return "+998" + digits
    raise ValueError(f"Invalid Uzbekistan phone number: {value!r}")


def make_temp_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def parse_birth_date(value: str):
    value = (value or "").strip()
    match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", value)
    if not match:
        raise ValueError(f"Invalid birth date: {value!r}")
    day, month, year = match.groups()
    return f"{year}-{month}-{day}"


def main():
    parser = argparse.ArgumentParser(
        description="Import staff from buxoro-hunarmandlari.uz into Hunarmand Control."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write changes to PostgreSQL. Without this flag the script is a preview only.",
    )
    args = parser.parse_args()

    if not DATA_FILE.exists():
        raise SystemExit(f"JSON file not found: {DATA_FILE}")

    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    records = payload.get("records", [])

    if len(records) != 16:
        raise SystemExit(f"Expected 16 records, found {len(records)}")

    print(f"Loaded {len(records)} staff records.")
    print("Mode:", "APPLY" if args.apply else "PREVIEW ONLY")
    print()

    with engine.begin() as conn:
        org = conn.execute(
            text("""
                SELECT id
                FROM organizations
                WHERE type = 'REGIONAL' AND active = TRUE
                ORDER BY created_at
                LIMIT 1
            """)
        ).fetchone()
        if not org:
            raise SystemExit("Active regional organization not found")
        organization_id = org[0]

        role_rows = conn.execute(
            text("SELECT id, name FROM roles")
        ).fetchall()
        role_ids = {row[1]: row[0] for row in role_rows}

        required_roles = {
            "SUPER_ADMIN",
            "REGIONAL_HEAD",
            "REGIONAL_MANAGER",
            "DISTRICT_HEAD",
            "EMPLOYEE",
        }
        missing_roles = required_roles - set(role_ids)
        if missing_roles:
            raise SystemExit(f"Missing roles: {sorted(missing_roles)}")

        district_rows = conn.execute(
            text("""
                SELECT d.id, d.name, dep.id
                FROM districts d
                JOIN departments dep ON dep.district_id = d.id
                WHERE d.active = TRUE
                  AND dep.active = TRUE
                  AND dep.name = 'Hunarmand'
            """)
        ).fetchall()

        district_map = {}
        for district_id, district_name, department_id in district_rows:
            district_map[district_name.strip().lower()] = (
                district_id,
                department_id,
                district_name,
            )

        # Existing users indexed by normalized phone.
        existing_rows = conn.execute(
            text("""
                SELECT id, phone, role_id
                FROM users
                WHERE organization_id = :organization_id
            """),
            {"organization_id": organization_id},
        ).fetchall()

        existing_by_phone = {
            normalize_phone(row[1]): (row[0], row[2])
            for row in existing_rows
            if row[1]
        }

        plan = []
        generated_credentials = []

        for item in records:
            source_id = int(item["id"])
            name = item["name"].strip()
            position = item["position"].strip()
            phone = normalize_phone(item["phone"])
            target_role = item.get("target_role") or "EMPLOYEE"
            source_district = (item.get("district") or "").strip()

            department_id = None
            resolved_district = "Regional office"
            birth_date = parse_birth_date(item.get("birth", ""))
            education = (item.get("education") or "").strip()

            if source_district:
                key = source_district.lower()
                if key not in district_map:
                    raise SystemExit(
                        f"District not found in database for {name}: {source_district}"
                    )
                _, department_id, resolved_district = district_map[key]

            employee_number = f"SITE-{source_id:03d}"

            if phone in existing_by_phone:
                user_id, existing_role_id = existing_by_phone[phone]
                existing_role = next(
                    (r for r, rid in role_ids.items() if str(rid) == str(existing_role_id)),
                    "UNKNOWN",
                )

                # Do not downgrade or overwrite an existing account role.
                if phone == normalize_phone("+998882820707"):
                    action = "EXISTING SUPER_ADMIN — keep role, ensure profile"
                elif existing_role != target_role:
                    action = f"EXISTING ROLE {existing_role} — keep role, review manually"
                else:
                    action = "EXISTING ACCOUNT — update profile"
            else:
                user_id = None
                existing_role = None
                action = "CREATE ACCOUNT"

            plan.append(
                {
                    "source_id": source_id,
                    "name": name,
                    "phone": phone,
                    "target_role": target_role,
                    "district": resolved_district,
                    "department_id": str(department_id) if department_id else None,
                    "employee_number": employee_number,
                    "birth_date": birth_date,
                    "education": education,
                    "action": action,
                    "user_id": str(user_id) if user_id else None,
                }
            )

            if args.apply and user_id is None:
                generated_credentials.append(
                    (name, phone, make_temp_password())
                )

        print("IMPORT PLAN")
        print("-" * 88)
        for row in plan:
            print(
                f'{row["source_id"]:>2}. {row["name"]} | {row["target_role"]} | '
                f'{row["district"]} | {row["action"]}'
            )

        print("-" * 88)

        if not args.apply:
            print("PREVIEW ONLY: no database changes.")
            print("To apply this exact plan, run with: --apply")
            return

        # Apply changes in the same transaction.
        credential_iter = iter(generated_credentials)

        for row in plan:
            source_id = row["source_id"]
            name = row["name"]
            phone = row["phone"]
            target_role = row["target_role"]
            department_id = row["department_id"]
            employee_number = row["employee_number"]

            existing = conn.execute(
                text("""
                    SELECT id, role_id
                    FROM users
                    WHERE organization_id = :organization_id
                      AND phone = :phone
                    LIMIT 1
                """),
                {
                    "organization_id": organization_id,
                    "phone": phone,
                },
            ).fetchone()

            if existing:
                user_id, existing_role_id = existing
                # Preserve the existing SUPER_ADMIN account.
                should_set_role = False
                if str(user_id) != "62d22827-19ae-4a2d-88c1-8cdd655d7306":
                    current_role = conn.execute(
                        text("SELECT name FROM roles WHERE id = :role_id"),
                        {"role_id": existing_role_id},
                    ).scalar()
                    should_set_role = current_role == target_role

                if should_set_role:
                    conn.execute(
                        text("""
                            UPDATE users
                            SET role_id = :role_id,
                                organization_id = :organization_id
                            WHERE id = :user_id
                        """),
                        {
                            "role_id": role_ids[target_role],
                            "organization_id": organization_id,
                            "user_id": user_id,
                        },
                    )
            else:
                try:
                    cred_name, cred_phone, temp_password = next(credential_iter)
                except StopIteration as exc:
                    raise RuntimeError("Credential generation mismatch") from exc

                password_hash = pwd_context.hash(temp_password)

                user_id = conn.execute(
                    text("""
                        INSERT INTO users (
                            phone,
                            role_id,
                            organization_id,
                            status,
                            password_hash
                        )
                        VALUES (
                            :phone,
                            :role_id,
                            :organization_id,
                            'ACTIVE',
                            :password_hash
                        )
                        RETURNING id
                    """),
                    {
                        "phone": phone,
                        "role_id": role_ids[target_role],
                        "organization_id": organization_id,
                        "password_hash": password_hash,
                    },
                ).scalar()

            profile_exists = conn.execute(
                text("""
                    SELECT 1
                    FROM employee_profiles
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id},
            ).fetchone()

            if profile_exists:
                conn.execute(
                    text("""
                        UPDATE employee_profiles
                        SET full_name = :full_name,
                            position = :position,
                            employee_number = :employee_number,
                            department_id = :department_id,
                            birth_date = :birth_date,
                            education = :education
                        WHERE user_id = :user_id
                    """),
                    {
                        "full_name": name,
                        "position": position,
                        "employee_number": employee_number,
                        "department_id": department_id,
                        "birth_date": row["birth_date"],
                        "education": row["education"],
                        "user_id": user_id,
                    },
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO employee_profiles (
                            user_id,
                            full_name,
                            position,
                            employee_number,
                            department_id,
                            birth_date,
                            education
                        )
                        VALUES (
                            :user_id,
                            :full_name,
                            :position,
                            :employee_number,
                            :department_id,
                            :birth_date,
                            :education
                        )
                    """),
                    {
                        "user_id": user_id,
                        "full_name": name,
                        "position": position,
                        "employee_number": employee_number,
                        "department_id": department_id,
                        "birth_date": row["birth_date"],
                        "education": row["education"],
                    },
                )

        print("IMPORT COMPLETED.")
        print("New account temporary credentials:")
        print("-" * 88)
        if generated_credentials:
            for name, phone, password in generated_credentials:
                print(f"{name} | {phone} | {password}")
        else:
            print("No new accounts were created.")
        print("-" * 88)
        print("IMPORTANT: change temporary passwords after first login.")


if __name__ == "__main__":
    main()

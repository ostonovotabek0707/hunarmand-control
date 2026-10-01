import json
from pathlib import Path

DATA_FILE = Path("/app/app/hunarmand_control_staff_import_16.json")

ROLE_BY_ID = {
    1: "REGIONAL_HEAD",
    2: "REGIONAL_MANAGER",
    3: "EMPLOYEE",
    4: "EMPLOYEE",
    5: "EMPLOYEE",
    6: "EMPLOYEE",
    7: "EMPLOYEE",
    8: "EMPLOYEE",
    9: "EMPLOYEE",
    10: "DISTRICT_HEAD",
    11: "EMPLOYEE",
    12: "DISTRICT_HEAD",
    13: "DISTRICT_HEAD",
    14: "DISTRICT_HEAD",
    15: "DISTRICT_HEAD",
    16: "DISTRICT_HEAD",
}

def main():
    if not DATA_FILE.exists():
        raise SystemExit(f"JSON file not found: {DATA_FILE}")

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    records = data.get("records", [])

    print(f"Records loaded: {len(records)}")
    print("-" * 72)

    for item in records:
        person_id = item.get("id")
        name = item.get("name", "").strip()
        position = item.get("position", "").strip()
        district = item.get("district")
        role = item.get("target_role") or ROLE_BY_ID.get(person_id, "EMPLOYEE")

        print(f"{person_id:>2}. {name}")
        print(f"    ROLE: {role}")
        print(f"    DISTRICT: {district or 'Regional office'}")
        print(f"    POSITION: {position}")
        print()

    roles = {}
    for item in records:
        role = item.get("target_role") or ROLE_BY_ID.get(item.get("id"), "EMPLOYEE")
        roles[role] = roles.get(role, 0) + 1

    print("-" * 72)
    print("ROLE SUMMARY")
    for role, count in sorted(roles.items()):
        print(f"{role}: {count}")

    print("-" * 72)
    print("DRY RUN: no database changes")

if __name__ == "__main__":
    main()

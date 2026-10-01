import getpass
import os
from sqlalchemy import create_engine, text
from passlib.context import CryptContext

engine = create_engine(os.getenv("DATABASE_URL"))
ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

p1 = getpass.getpass("Yangi ADMIN paroli: ")
p2 = getpass.getpass("Yangi ADMIN parolini qayta kiriting: ")

if not p1:
    print("ERROR: parol bosh bo'lishi mumkin emas")
    raise SystemExit

if p1 != p2:
    print("ERROR: parollar bir xil emas")
    raise SystemExit

if len(p1.encode("utf-8")) > 72:
    print("ERROR: parol 72 baytdan uzun")
    raise SystemExit

new_hash = ctx.hash(p1)

with engine.begin() as conn:
    result = conn.execute(
        text("""
            UPDATE users
            SET password_hash=:hash
            WHERE phone=:phone
            RETURNING phone, status
        """),
        {"hash": new_hash, "phone": "+998882820707"}
    ).mappings().first()

if not result:
    print("USER_NOT_FOUND")
else:
    print("ADMIN_PASSWORD_RESET_OK")
    print("PHONE =", result["phone"])
    print("STATUS =", result["status"])

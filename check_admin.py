import getpass
import os
from sqlalchemy import create_engine, text
from passlib.context import CryptContext

engine = create_engine(os.getenv("DATABASE_URL"))
ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

with engine.connect() as conn:
    row = conn.execute(
        text("SELECT password_hash FROM users WHERE phone=:phone"),
        {"phone": "+998882820707"}
    ).scalar_one_or_none()

if not row:
    print("USER_NOT_FOUND")
    raise SystemExit

password = getpass.getpass("ADMIN paroli: ")
print("PASSWORD_OK =", ctx.verify(password, row))

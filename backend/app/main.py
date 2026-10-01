import hashlib
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import datetime, timezone, timedelta
import os

import jwt
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# ============================================================
# CONFIG
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    ""
)

JWT_SECRET = os.getenv(
    "JWT_SECRET",
    "CHANGE_THIS_SECRET_IN_PRODUCTION"
)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 12

engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800
)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def create_password_setup_token():
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    return token, token_hash, expires_at

security = HTTPBearer(auto_error=True)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Hunarmand Control API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MODELS
# ============================================================

class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict


class PasswordSetupRequest(BaseModel):
    setup_token: str
    new_password: str


class PasswordSetupResponse(BaseModel):
    ok: bool
    message: str


class EmployeeCreateRequest(BaseModel):
    phone: str
    password: str | None = None
    full_name: str
    position: str | None = None
    employee_number: str | None = None
    department_id: str | None = None
    hire_date: str | None = None


# ============================================================
# HELPERS
# ============================================================

def normalize_phone(phone: str) -> str:
    return phone.strip().replace(" ", "").replace("-", "")


def create_access_token(user: dict) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user["id"]),
        "phone": user["phone"],
        "role": user["role_name"],
        "organization_id": (
            str(user["organization_id"])
            if user["organization_id"]
            else None
        ),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def get_current_user_from_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid access token"
            )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Access token expired"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token"
        )

    with engine.connect() as conn:
        user = conn.execute(
            text(
                """
                SELECT
                    u.id,
                    u.phone,
                    u.role_id,
                    u.organization_id,
                    u.status,
                    r.name AS role_name
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = CAST(:user_id AS uuid)
                """
            ),
            {"user_id": user_id}
        ).mappings().first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if user["status"] != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    return dict(user)


def get_bearer_token(authorization: str | None):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required"
        )

    parts = authorization.split(" ", 1)

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Bearer token required"
        )

    return parts[1]


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    return get_current_user_from_token(credentials.credentials)


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    return {
        "ok": True,
        "server_time": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ============================================================
# SERVER TIME
# ============================================================

@app.get("/api/v1/server-time")
def server_time():

    with engine.connect() as conn:
        value = conn.execute(
            text(
                "SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC'"
            )
        ).scalar_one()

    return {
        "server_time_utc": value.isoformat(),
        "timezone": "UTC"
    }


# ============================================================
# LOGIN
# ============================================================

@app.post(
    "/api/v1/auth/login",
    response_model=TokenResponse
)
def login(request: LoginRequest):

    phone = normalize_phone(request.phone)

    with engine.begin() as conn:

        user = conn.execute(
            text(
                """
                SELECT
                    u.id,
                    u.phone,
                    u.role_id,
                    u.organization_id,
                    u.status,
                    u.password_hash,
                    r.name AS role_name
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.phone = :phone
                """
            ),
            {"phone": phone}
        ).mappings().first()

        if not user:

            raise HTTPException(
                status_code=401,
                detail="РќРѕС‚СћТ“СЂРё С‚РµР»РµС„РѕРЅ СЂР°Т›Р°РјРё С‘РєРё РїР°СЂРѕР»СЊ"
            )

        if user["status"] != "ACTIVE":

            raise HTTPException(
                status_code=403,
                detail="Р¤РѕР№РґР°Р»Р°РЅСѓРІС‡Рё Р°РєРєР°СѓРЅС‚Рё С„Р°РѕР» СЌРјР°СЃ"
            )

        password_hash = user["password_hash"]

        if not password_hash:

            raise HTTPException(
                status_code=403,
                detail="РђРєРєР°СѓРЅС‚ СѓС‡СѓРЅ РїР°СЂРѕР»СЊ СћСЂРЅР°С‚РёР»РјР°РіР°РЅ"
            )

        try:
            valid_password = pwd_context.verify(
                request.password,
                password_hash
            )
        except Exception:
            valid_password = False

        if not valid_password:

            conn.execute(
                text(
                    """
                    UPDATE users
                    SET
                        failed_login_attempts =
                            COALESCE(failed_login_attempts, 0) + 1
                    WHERE id = :id
                    """
                ),
                {"id": str(user["id"])}
            )

            raise HTTPException(
                status_code=401,
                detail="РќРѕС‚СћТ“СЂРё С‚РµР»РµС„РѕРЅ СЂР°Т›Р°РјРё С‘РєРё РїР°СЂРѕР»СЊ"
            )

        # Successful login
        conn.execute(
            text(
                """
                UPDATE users
                SET
                    last_login_at = CURRENT_TIMESTAMP,
                    failed_login_attempts = 0,
                    locked_until = NULL
                WHERE id = :id
                """
            ),
            {"id": str(user["id"])}
        )

    user_data = {
        "id": str(user["id"]),
        "phone": user["phone"],
        "role_name": user["role_name"],
        "organization_id": (
            str(user["organization_id"])
            if user["organization_id"]
            else None
        )
    }

    access_token = create_access_token(user_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_MINUTES * 60,
        "user": user_data
    }


# ============================================================
# PASSWORD SETUP
# ============================================================

@app.post(
    "/api/v1/auth/set-password",
    response_model=PasswordSetupResponse
)
def set_password(request: PasswordSetupRequest):

    setup_token = request.setup_token.strip()
    new_password = request.new_password

    if not setup_token:
        raise HTTPException(
            status_code=400,
            detail="Setup token is required"
        )

    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    token_hash = hashlib.sha256(
        setup_token.encode()
    ).hexdigest()

    with engine.begin() as conn:

        user = conn.execute(
            text("""
                SELECT
                    id,
                    status,
                    must_set_password,
                    password_setup_expires_at
                FROM users
                WHERE password_setup_token_hash = :token_hash
            """),
            {
                "token_hash": token_hash
            }
        ).mappings().first()

        if not user:
            raise HTTPException(
                status_code=400,
                detail="Invalid setup token"
            )

        if user["status"] != "ACTIVE":
            raise HTTPException(
                status_code=403,
                detail="User account is inactive"
            )

        if not user["must_set_password"]:
            raise HTTPException(
                status_code=400,
                detail="Password has already been set"
            )

        if (
            not user["password_setup_expires_at"]
            or user["password_setup_expires_at"] < datetime.now(timezone.utc)
        ):
            raise HTTPException(
                status_code=400,
                detail="Setup token expired"
            )

        password_hash = pwd_context.hash(new_password)

        conn.execute(
            text("""
                UPDATE users
                SET
                    password_hash = :password_hash,
                    must_set_password = FALSE,
                    password_setup_token_hash = NULL,
                    password_setup_expires_at = NULL,
                    failed_login_attempts = 0,
                    locked_until = NULL
                WHERE id = :user_id
            """),
            {
                "password_hash": password_hash,
                "user_id": str(user["id"])
            }
        )

    return {
        "ok": True,
        "message": "Password set successfully"
    }


# ============================================================
# CURRENT USER
# ============================================================

@app.get("/api/v1/auth/me")
def me(current_user: dict = Depends(get_current_user)):

    return {
        "id": str(current_user["id"]),
        "phone": current_user["phone"],
        "role": current_user["role_name"],
        "organization_id": (
            str(current_user["organization_id"])
            if current_user["organization_id"]
            else None
        ),
        "status": current_user["status"]
    }


# ============================================================
# LOGOUT
# ============================================================

@app.post("/api/v1/auth/logout")
def logout(current_user: dict = Depends(get_current_user)):

    return {
        "ok": True,
        "message": "Logout acknowledged",
        "user_id": str(current_user["id"])
    }


# ============================================================
# ADMIN TEST
# ============================================================

@app.get("/api/v1/admin/test")
def admin_test(current_user: dict = Depends(get_current_user)):

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

    return {
        "ok": True,
        "message": "Admin API access granted",
        "user_id": str(current_user["id"]),
        "role": current_user["role_name"]
    }


# ============================================================
# EMPLOYEE MANAGEMENT
# ============================================================

@app.post("/api/v1/admin/employees")
def create_employee(
    request: EmployeeCreateRequest,
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

    if not request.phone.strip():
        raise HTTPException(status_code=400, detail="Phone is required")
    
    if not request.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required")

    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM users WHERE phone = :phone"),
            {"phone": request.phone.strip()}
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="User with this phone already exists"
            )

        role_row = conn.execute(
            text("SELECT id FROM roles WHERE name = 'EMPLOYEE'")
        ).fetchone()

        if not role_row:
            raise HTTPException(
                status_code=500,
                detail="EMPLOYEE role not found"
            )

        password_hash = None
        setup_token, setup_token_hash, setup_expires_at = create_password_setup_token()

        user_row = conn.execute(
            text("""
                INSERT INTO users (
                    phone,
                    role_id,
                    organization_id,
                    status,
                    must_set_password,
                    password_setup_token_hash,
                    password_setup_expires_at
                )
                VALUES (
                    :phone,
                    :role_id,
                    :organization_id,
                    'ACTIVE',
                    TRUE,
                    :setup_token_hash,
                    :setup_expires_at
                )
                RETURNING id
            """),
            {
                "phone": request.phone.strip(),
                "role_id": role_row[0],
                "organization_id": current_user["organization_id"],
                "setup_token_hash": setup_token_hash,
                "setup_expires_at": setup_expires_at
            }
        ).fetchone()

        user_id = user_row[0]

        conn.execute(
            text("""
                UPDATE users
                SET password_hash = :password_hash
                WHERE id = :user_id
            """),
            {
                "password_hash": password_hash,
                "user_id": user_id
            }
        )

        conn.execute(
            text("""
                INSERT INTO employee_profiles (
                    user_id,
                    full_name,
                    position,
                    employee_number,
                    department_id,
                    hire_date
                )
                VALUES (
                    :user_id,
                    :full_name,
                    :position,
                    :employee_number,
                    :department_id,
                    :hire_date
                )
            """),
            {
                "user_id": user_id,
                "full_name": request.full_name.strip(),
                "position": request.position,
                "employee_number": request.employee_number,
                "department_id": request.department_id,
                "hire_date": request.hire_date
            }
        )

    return {
        "ok": True,
        "message": "Employee created",
        "user_id": str(user_id),
        "role": "EMPLOYEE",
        "phone": request.phone.strip(),
        "setup_token": setup_token,
        "setup_expires_at": setup_expires_at
    }


# ============================================================
# ROOT
# ============================================================
@app.patch("/api/v1/admin/employees/{user_id}/status")
def update_employee_status(
    user_id: str,
    status: str,
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

    status = status.strip().upper()

    if status not in {"ACTIVE", "INACTIVE"}:
        raise HTTPException(
            status_code=400,
            detail="Status must be ACTIVE or INACTIVE"
        )

    with engine.begin() as conn:
        employee = conn.execute(
            text("""
                SELECT u.id
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = :user_id
                  AND r.name = 'EMPLOYEE'
                  AND u.organization_id = :organization_id
            """),
            {
                "user_id": user_id,
                "organization_id": current_user["organization_id"]
            }
        ).fetchone()

        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Employee not found"
            )

        conn.execute(
            text("""
                UPDATE users
                SET
                    status = :status,
                    deactivated_at = CASE
                        WHEN :status = 'INACTIVE' THEN CURRENT_TIMESTAMP
                        ELSE NULL
                    END
                WHERE id = :user_id
            """),
            {
                "status": status,
                "user_id": user_id
            }
        )

    return {
        "ok": True,
        "message": "Employee status updated",
        "user_id": user_id,
        "status": status
    }
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
              AND u.status = 'ACTIVE'
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
@app.get("/admin/", include_in_schema=False)
def admin_page():
    admin_file = Path(__file__).resolve().parent / "admin" / "index.html"
    return FileResponse(admin_file)
@app.get("/")
def root():

    return {
        "name": "Hunarmand Control API",
        "version": "0.1.0",
        "status": "running"
    }




















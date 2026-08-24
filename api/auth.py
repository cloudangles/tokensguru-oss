"""Simple auth: register / login / logout + API keys.

No RBAC rank system, no org/team/workspace/tenant-slug resolution --
Enterprise's AuthState carries a 7-value role enum plus org/team/tenant/
workspace ids from the start (see docs/OSS_FEATURE_MATRIX.md). OSS auth is
one implicit tenant ("default") per deployment; every logged-in user sees
the same dashboard.

JWT for dashboard sessions, a plain random API key for programmatic/SDK
access -- pyjwt + bcrypt directly (not passlib: its CryptContext runs a
bug-detection self-test at first use that raises ValueError against
bcrypt>=4.0, a known passlib/bcrypt compatibility break -- calling bcrypt
directly avoids that shim entirely).
"""
from __future__ import annotations

import os
import secrets
import time
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator

from db import get_client

router = APIRouter(prefix="/api/auth", tags=["auth"])

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

DEFAULT_TENANT = "default"

if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is not set. Generate one (e.g. `openssl rand -hex 32`) "
        "and set it in your .env file before starting the API."
    )


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _create_access_token(user_id: str, email: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "tenant_id": DEFAULT_TENANT,
        "iat": now,
        "exp": now + JWT_EXPIRE_MINUTES * 60,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _find_user_by_email(email: str) -> Optional[dict]:
    ch = get_client()
    result = ch.query(
        "SELECT toString(user_id) AS user_id, email, password_hash, tenant_id "
        "FROM tokensight.users WHERE email = {email:String} LIMIT 1",
        parameters={"email": email},
    )
    if not result.result_rows:
        return None
    return dict(zip(result.column_names, result.result_rows[0]))


@router.post("/register")
def register(body: RegisterRequest) -> dict:
    if _find_user_by_email(body.email) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    ch = get_client()
    ch.insert(
        "tokensight.users",
        [[body.email, _hash_password(body.password), DEFAULT_TENANT]],
        column_names=["email", "password_hash", "tenant_id"],
    )
    user = _find_user_by_email(body.email)
    api_key = f"tsk_{secrets.token_hex(24)}"
    ch.insert(
        "tokensight.api_keys",
        [[api_key, user["user_id"], DEFAULT_TENANT, "default"]],
        column_names=["api_key", "user_id", "tenant_id", "label"],
    )
    token = _create_access_token(user["user_id"], body.email)
    return {"access_token": token, "api_key": api_key, "email": body.email}


@router.post("/login")
def login(body: LoginRequest) -> dict:
    user = _find_user_by_email(body.email)
    if user is None or not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = _create_access_token(user["user_id"], user["email"])
    return {"access_token": token, "email": user["email"]}


@router.post("/logout")
def logout() -> dict:
    # Stateless JWT -- the client discards the token. Nothing to invalidate
    # server-side in this minimal auth model.
    return {"ok": True}


def _extract_bearer(auth_header: str) -> Optional[str]:
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()


def require_auth(request: Request) -> dict:
    """FastAPI dependency: accept either a dashboard JWT or an API key."""
    auth_header = request.headers.get("authorization", "")
    token = _extract_bearer(auth_header)
    if token:
        try:
            claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return {"user_id": claims["sub"], "tenant_id": claims["tenant_id"]}
        except jwt.PyJWTError:
            pass

    api_key = request.headers.get("x-api-key", "")
    if api_key:
        ch = get_client()
        result = ch.query(
            "SELECT user_id, tenant_id FROM tokensight.api_keys "
            "WHERE api_key = {key:String} AND revoked = 0 LIMIT 1",
            parameters={"key": api_key},
        )
        if result.result_rows:
            user_id, tenant_id = result.result_rows[0]
            return {"user_id": user_id, "tenant_id": tenant_id}

    raise HTTPException(status_code=401, detail="Missing or invalid credentials")

"""Security utilities for authentication and signing links."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    additional_claims: dict | None = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    if additional_claims:
        to_encode.update(additional_claims)

    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Verify a JWT token and return its payload."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def create_signing_token(
    envelope_id: str,
    recipient_id: str,
    recipient_email: str,
) -> str:
    """Create a unique, unguessable signing token for a recipient."""
    expires = datetime.now(timezone.utc) + timedelta(
        hours=settings.signing_link_expiry_hours
    )
    return create_access_token(
        subject=recipient_id,
        expires_delta=timedelta(hours=settings.signing_link_expiry_hours),
        additional_claims={
            "type": "signing",
            "envelope_id": envelope_id,
            "email": recipient_email,
            "exp": expires.timestamp(),
        },
    )


def verify_signing_token(token: str) -> dict | None:
    """Verify a signing token and return its payload."""
    payload = verify_token(token)
    if payload and payload.get("type") == "signing":
        return payload
    return None


def create_magic_link_token(email: str) -> str:
    """Create a magic link token for email authentication."""
    return create_access_token(
        subject=email,
        expires_delta=timedelta(minutes=15),
        additional_claims={"type": "magic_link"},
    )


def verify_magic_link_token(token: str) -> str | None:
    """Verify a magic link token and return the email."""
    payload = verify_token(token)
    if payload and payload.get("type") == "magic_link":
        return payload.get("sub")
    return None


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

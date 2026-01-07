"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_magic_link_token,
    verify_magic_link_token,
    verify_token,
)
from app.models import User, get_db
from app.schemas import AuthRequest, AuthResponse, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


async def get_current_user(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from token."""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user."""
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Create new user
    user = User(
        email=user_data.email,
        name=user_data.name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/magic-link", response_model=dict)
async def request_magic_link(
    auth_data: AuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a magic link for authentication.

    In production, this would send an email.
    For MVP, we return the token directly.
    """
    # Check if user exists, create if not
    result = await db.execute(select(User).where(User.email == auth_data.email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=auth_data.email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Generate magic link token
    token = create_magic_link_token(auth_data.email)

    # In production, we'd send this via email
    # For MVP, return it directly
    return {
        "message": "Magic link generated",
        "token": token,  # Remove in production
        "magic_link": f"/auth/verify?token={token}",
    }


@router.post("/verify", response_model=AuthResponse)
async def verify_magic_link(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Verify magic link and return access token."""
    email = verify_magic_link_token(token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired magic link",
        )

    # Get or create user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Generate access token
    access_token = create_access_token(subject=user.id)

    return AuthResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get current user info."""
    user = await get_current_user(token, db)
    return user

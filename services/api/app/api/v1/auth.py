import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, VerifyOtpRequest
from app.services.auth import create_challenge, create_session, hash_password, verify_challenge, verify_password

router = APIRouter()
SESSION_COOKIE = "documind_session"


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(request: RegisterRequest, session: Annotated[Session, Depends(get_session)], settings: Annotated[Settings, Depends(get_settings)]) -> AuthResponse:
    if session.scalar(select(User).where(User.email == request.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(id=uuid.uuid4(), email=request.email, display_name=request.display_name.strip(), password_hash=hash_password(request.password))
    session.add(user)
    session.flush()
    try:
        challenge = create_challenge(session, user, settings)
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=503, detail="Could not send verification email.")
    return AuthResponse(message="Verification code sent.", challenge_id=str(challenge.id))


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest, session: Annotated[Session, Depends(get_session)], settings: Annotated[Settings, Depends(get_settings)]) -> AuthResponse:
    user = session.scalar(select(User).where(User.email == request.email))
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    try:
        challenge = create_challenge(session, user, settings)
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=503, detail="Could not send verification email.")
    return AuthResponse(message="Verification code sent.", challenge_id=str(challenge.id))


@router.post("/verify", response_model=AuthResponse)
def verify(request: VerifyOtpRequest, response: Response, session: Annotated[Session, Depends(get_session)]) -> AuthResponse:
    user = verify_challenge(session, uuid.UUID(request.challenge_id), request.code)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code.")
    token = create_session(session, user)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", secure=False, max_age=30 * 24 * 60 * 60)
    return AuthResponse(message="Signed in.")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import AuthChallenge, AuthSession
from app.models.user import User
from app.services.email import send_otp_email


logger = logging.getLogger(__name__)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded or not encoded.startswith("scrypt$"):
        return False
    _, salt, digest = encoded.split("$", 2)
    candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1).hex()
    return hmac.compare_digest(candidate, digest)


def create_challenge(session: Session, user: User, settings) -> AuthChallenge:
    code = "000000" if settings.environment == "development" else f"{secrets.randbelow(1_000_000):06d}"
    challenge = AuthChallenge(id=uuid.uuid4(), user_id=user.id, code_hash=_digest(code), expires_at=datetime.now(UTC) + timedelta(minutes=10))
    session.add(challenge)
    session.flush()
    if settings.environment == "development" and not settings.smtp_host:
        logger.info("Development OTP for %s: %s", user.email, code)
    else:
        send_otp_email(settings, user.email, code)
    return challenge


def verify_challenge(session: Session, challenge_id: uuid.UUID, code: str) -> User | None:
    challenge = session.get(AuthChallenge, challenge_id)
    if not challenge or challenge.expires_at < datetime.now(UTC) or not hmac.compare_digest(challenge.code_hash, _digest(code)):
        return None
    user = session.get(User, challenge.user_id)
    session.delete(challenge)
    return user


def create_session(session: Session, user: User) -> str:
    raw = secrets.token_urlsafe(48)
    session.add(AuthSession(id=uuid.uuid4(), token_hash=_digest(raw), user_id=user.id, expires_at=datetime.now(UTC) + timedelta(days=30)))
    session.commit()
    return raw


def user_for_token(session: Session, token: str | None) -> User | None:
    if not token:
        return None
    item = session.scalar(select(AuthSession).where(AuthSession.token_hash == _digest(token)))
    if not item or item.expires_at < datetime.now(UTC):
        return None
    return session.get(User, item.user_id)

# app/utils.py
from passlib.context import CryptContext

# Centralised Argon2 hasher – used everywhere
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password using Argon2."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain, hashed)
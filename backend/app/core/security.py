import hashlib
import hmac
import secrets
from backend.app.core.config import settings

def hash_password(password: str, salt: str = None) -> str:
    """Hash a password using SHA-256 with salt."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    )
    return f"{salt}${key.hex()}"

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verify a stored password hash."""
    if not stored_hash or "$" not in stored_hash:
        return False
    salt, hash_val = stored_hash.split("$", 1)
    test_hash = hash_password(provided_password, salt)
    return hmac.compare_digest(f"{salt}${hash_val}", test_hash)

def generate_unsubscribe_token(subscriber_id: str | int, email: str) -> str:
    """Generate a secure, deterministic or unique token for candidate unsubscribe."""
    raw = f"{subscriber_id}:{email}:{settings.SECRET_KEY}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

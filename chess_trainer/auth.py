"""Password hashing (PBKDF2-HMAC-SHA256, standard library only)."""
import hashlib
import hmac
import secrets

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 600_000


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${salt}${digest.hex()}"


def is_hashed(stored):
    return bool(stored) and stored.startswith(_ALGO + "$")


def verify_password(password, stored):
    """Check a password against a stored hash.

    Databases created by older versions stored plaintext passwords; those are
    still accepted (constant-time comparison) so they can be upgraded on login.
    """
    if not stored:
        return False
    if not is_hashed(stored):
        return hmac.compare_digest(password.encode("utf-8"), stored.encode("utf-8"))
    try:
        _, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), expected)

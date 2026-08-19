import hashlib
import hmac
import json
import re
from datetime import datetime
from pathlib import Path


def safe_user_id(raw_name: str) -> str:
    return (raw_name or "").strip()[:40]


def is_valid_user_id(user_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9\u4e00-\u9fff]{1,40}", user_id))


def load_auth_users(auth_file: Path) -> dict:
    if not auth_file.exists():
        return {}
    try:
        return json.loads(auth_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_auth_users(auth_file: Path, users: dict) -> None:
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    auth_file.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def hash_password(password: str, salt_hex: str) -> str:
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120_000)
    return hashed.hex()


def register_user(
    auth_file: Path,
    user_id: str,
    password: str,
    *,
    now: datetime | None = None,
) -> tuple[bool, str]:
    users = load_auth_users(auth_file)
    if user_id in users:
        return False, "用户名已存在"
    if len(password) < 6:
        return False, "密码至少 6 位"

    current_time = now or datetime.now()
    salt = hashlib.sha256(f"{user_id}-{current_time.isoformat()}".encode("utf-8")).hexdigest()[:32]
    users[user_id] = {
        "salt": salt,
        "password_hash": hash_password(password, salt),
        "created_at": current_time.strftime("%Y-%m-%d"),
    }
    save_auth_users(auth_file, users)
    return True, "注册成功"


def verify_user(auth_file: Path, user_id: str, password: str) -> bool:
    users = load_auth_users(auth_file)
    data = users.get(user_id)
    if not data:
        return False

    salt = str(data.get("salt", ""))
    expected = str(data.get("password_hash", ""))
    if not salt or not expected:
        return False

    current = hash_password(password, salt)
    return hmac.compare_digest(current, expected)

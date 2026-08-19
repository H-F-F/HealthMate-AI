import unittest
from datetime import datetime
from pathlib import Path
import shutil
import uuid

from services.auth_service import is_valid_user_id, load_auth_users, register_user, safe_user_id, verify_user


class AuthServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests/.tmp") / f"auth-{uuid.uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.auth_file = self.temp_dir / "users.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_safe_user_id_trims_and_limits_length(self) -> None:
        raw_name = "  abcdefghijklmnopqrstuvwxyz1234567890more  "
        self.assertEqual(safe_user_id(raw_name), "abcdefghijklmnopqrstuvwxyz1234567890more"[:40])

    def test_is_valid_user_id_accepts_letters_numbers_and_chinese(self) -> None:
        self.assertTrue(is_valid_user_id("alice123"))
        self.assertTrue(is_valid_user_id("健康助手01"))
        self.assertFalse(is_valid_user_id("alice_123"))
        self.assertFalse(is_valid_user_id(""))

    def test_register_and_verify_user(self) -> None:
        ok, msg = register_user(
            self.auth_file,
            "alice",
            "password123",
            now=datetime(2026, 4, 13, 10, 30, 0),
        )
        self.assertTrue(ok)
        self.assertEqual(msg, "注册成功")
        users = load_auth_users(self.auth_file)
        self.assertIn("alice", users)
        self.assertTrue(verify_user(self.auth_file, "alice", "password123"))
        self.assertFalse(verify_user(self.auth_file, "alice", "bad-password"))

    def test_register_rejects_duplicate_and_short_password(self) -> None:
        ok, _ = register_user(self.auth_file, "alice", "password123")
        self.assertTrue(ok)

        duplicate_ok, duplicate_msg = register_user(self.auth_file, "alice", "password123")
        self.assertFalse(duplicate_ok)
        self.assertEqual(duplicate_msg, "用户名已存在")

        short_ok, short_msg = register_user(self.auth_file, "bob", "12345")
        self.assertFalse(short_ok)
        self.assertEqual(short_msg, "密码至少 6 位")

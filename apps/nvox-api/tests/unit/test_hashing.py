from utils.hashing import hash_email, hash_password, verify_password
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestHashEmail:
    def test_hash_email_returns_consistent_hash(self):
        email = "test@example.com"
        hash1 = hash_email(email)
        hash2 = hash_email(email)

        assert hash1 == hash2

    def test_hash_email_returns_64_char_hex(self):
        email = "test@example.com"
        email_hash = hash_email(email)

        assert len(email_hash) == 64
        assert all(c in '0123456789abcdef' for c in email_hash)

    def test_hash_email_different_for_different_emails(self):
        email1 = "test1@example.com"
        email2 = "test2@example.com"

        hash1 = hash_email(email1)
        hash2 = hash_email(email2)

        assert hash1 != hash2

    def test_hash_email_case_sensitive(self):
        email_lower = "test@example.com"
        email_upper = "TEST@EXAMPLE.COM"

        hash_lower = hash_email(email_lower)
        hash_upper = hash_email(email_upper)

        assert hash_lower != hash_upper

    def test_hash_email_handles_special_characters(self):
        email = "test+tag@example.com"
        email_hash = hash_email(email)

        assert len(email_hash) == 64
        assert isinstance(email_hash, str)


class TestHashPassword:
    def test_hash_password_returns_bcrypt_hash(self):
        password = "TestPassword123"
        password_hash = hash_password(password)

        assert password_hash.startswith("$2b$")
        assert len(password_hash) == 60

    def test_hash_password_different_for_same_password(self):
        password = "TestPassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

    def test_hash_password_handles_special_characters(self):
        password = "P@ssw0rd!#$%"
        password_hash = hash_password(password)

        assert password_hash.startswith("$2b$")
        assert len(password_hash) == 60

    def test_hash_password_handles_unicode(self):
        password = "Pässwörd123"
        password_hash = hash_password(password)

        assert password_hash.startswith("$2b$")
        assert len(password_hash) == 60


class TestVerifyPassword:
    def test_verify_password_correct_password(self):
        password = "TestPassword123"
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True

    def test_verify_password_incorrect_password(self):
        password = "TestPassword123"
        wrong_password = "WrongPassword456"
        password_hash = hash_password(password)

        assert verify_password(wrong_password, password_hash) is False

    def test_verify_password_case_sensitive(self):
        password = "TestPassword123"
        wrong_case = "testpassword123"
        password_hash = hash_password(password)

        assert verify_password(wrong_case, password_hash) is False

    def test_verify_password_with_special_characters(self):
        password = "P@ssw0rd!#$%"
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True

    def test_verify_password_empty_string(self):
        password = ""
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True
        assert verify_password("not empty", password_hash) is False


class TestHashingIntegration:
    def test_email_and_password_hashing_together(self):
        email = "user@example.com"
        password = "SecurePass123"

        email_hash = hash_email(email)
        password_hash = hash_password(password)

        assert len(email_hash) == 64
        assert password_hash.startswith("$2b$")

        assert verify_password(password, password_hash) is True

    def test_multiple_users_same_password(self):
        password = "CommonPassword123"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

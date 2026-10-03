from __future__ import annotations

import os
import sys
import unittest
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("JWT_SECRET_KEY", "testing-jwt-secret-key-64-bytes-sample-for-unit-tests")
os.environ.setdefault("ALLOW_SQLITE_FALLBACK", "1")

from main import create_app
from pipeline.db import setup_db
from db.connection import db
from db.models import User


class AuthAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        setup_db(cls.app)
        cls.client = cls.app.test_client()

    def test_registration_and_login_flow(self):
        uid = uuid.uuid4().hex[:8]
        username = f"test_analyst_{uid}"
        password = "SecurePassword123!"

        # Register
        res = self.client.post("/auth/register", json={
            "username": username,
            "password": password,
            "email": f"test_{uid}@analyst.gov",
        })
        self.assertIn(res.status_code, (200, 201))
        data = res.get_json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(data["user"]["username"], username)

        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # Access /auth/me with Bearer token
        me_res = self.client.get("/auth/me", headers={
            "Authorization": f"Bearer {access_token}"
        })
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.get_json()["username"], username)

        # Refresh token rotation
        ref_res = self.client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        self.assertEqual(ref_res.status_code, 200)
        new_data = ref_res.get_json()
        self.assertIn("access_token", new_data)
        self.assertIn("refresh_token", new_data)
        self.assertNotEqual(new_data["refresh_token"], refresh_token)

        # Login with correct credentials
        login_res = self.client.post("/auth/login", json={
            "username": username,
            "password": password,
        })
        self.assertEqual(login_res.status_code, 200)

        # Login with invalid password fails
        bad_res = self.client.post("/auth/login", json={
            "username": username,
            "password": "WrongPassword!",
        })
        self.assertEqual(bad_res.status_code, 401)

    def test_strict_password_hash_verification(self):
        """Verify stored password hash permits login and no bypasses or hardcoded passwords work."""
        uid = uuid.uuid4().hex[:8]
        username = f"analyst_sec_{uid}"
        email = f"sec_{uid}@enterprise.com"
        valid_password = "CorrectComplexPassword123!"

        # Create user with known password
        with self.app.app_context():
            user = User(username=username, email=email, is_admin=True)
            user.set_password(valid_password)
            db.session.add(user)
            db.session.commit()

        # 1. Correct stored password hash permits login (via username, email, identifier)
        for field, ident in [("username", username), ("email", email), ("identifier", username), ("identifier", email)]:
            res = self.client.post("/auth/login", json={field: ident, "password": valid_password})
            self.assertEqual(res.status_code, 200, f"Failed for field {field}={ident}")
            self.assertIn("access_token", res.get_json())

        # 2. Case-insensitive lookup works
        res_caps = self.client.post("/auth/login", json={"identifier": email.upper(), "password": valid_password})
        self.assertEqual(res_caps.status_code, 200)

        # 3. Incorrect password is strictly rejected (HTTP 401)
        res_wrong = self.client.post("/auth/login", json={"identifier": email, "password": "CompletelyWrongPassword!"})
        self.assertEqual(res_wrong.status_code, 401)

        # 4. Common hardcoded / fallback passwords must be rejected
        for bad_attempt in ["admin", "admin123", "password", "root", "12345678", "fallback_admin_pw", "demo_password"]:
            res_bad = self.client.post("/auth/login", json={"identifier": email, "password": bad_attempt})
            self.assertEqual(res_bad.status_code, 401, f"Hardcoded fallback '{bad_attempt}' was not rejected")

        # 5. Environment configuration cannot bypass stored-password verification
        old_env_pw = os.environ.get("ADMIN_PASSWORD")
        try:
            os.environ["ADMIN_PASSWORD"] = "EphemeralEnvBypassAttempt999!"
            res_env_bypass = self.client.post("/auth/login", json={
                "identifier": email,
                "password": "EphemeralEnvBypassAttempt999!",
            })
            self.assertEqual(
                res_env_bypass.status_code,
                401,
                "Environment variable should NOT bypass stored bcrypt password hash verification",
            )
        finally:
            if old_env_pw is not None:
                os.environ["ADMIN_PASSWORD"] = old_env_pw
            else:
                os.environ.pop("ADMIN_PASSWORD", None)


if __name__ == "__main__":
    unittest.main()

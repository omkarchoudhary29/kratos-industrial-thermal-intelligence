"""Provision a dedicated read-only reviewer account for public and recruiter demonstration.

Usage:
    python scripts/setup_demo_user.py [--username demo_reviewer] [--password <pwd>] [--email <email>]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure backend package is in python path
ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import create_app
from db.connection import db
from db.models import User


def setup_demo_user(
    username: str = "demo_reviewer",
    password: str = "KratosDemo2026!",
    email: str = "demo_reviewer@kratos.intelligence",
    is_admin: bool = False,
) -> User:
    """Create or update the designated demo reviewer user account idempotently."""
    app = create_app()

    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user and email:
            user = User.query.filter_by(email=email).first()

        if user:
            print(f"[+] Found existing user '{user.username}' (ID: {user.id}). Updating credentials...")
            user.username = username
            user.email = email
            user.is_admin = is_admin
            user.set_password(password)
        else:
            print(f"[+] Creating new demo user '{username}' ({email})...")
            user = User(
                username=username,
                email=email,
                is_admin=is_admin,
            )
            user.set_password(password)
            db.session.add(user)

        db.session.commit()
        print(f"[✓] Demo reviewer account ready:")
        print(f"    - Username: {username}")
        print(f"    - Email:    {email}")
        print(f"    - Password: {password}")
        print(f"    - Role:     {'Administrator' if is_admin else 'Standard Operational Reviewer'}")
        print(f"    - ID:       {user.id}")
        return user


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision demo reviewer account.")
    parser.add_argument("--username", default=os.getenv("DEMO_USER_NAME", "demo_reviewer"), help="Reviewer username")
    parser.add_argument("--password", default=os.getenv("DEMO_USER_PASSWORD", "KratosDemo2026!"), help="Reviewer password")
    parser.add_argument("--email", default=os.getenv("DEMO_USER_EMAIL", "demo_reviewer@kratos.intelligence"), help="Reviewer email")
    parser.add_argument("--admin", action="store_true", help="Grant admin privileges")

    args = parser.parse_args()
    setup_demo_user(
        username=args.username,
        password=args.password,
        email=args.email,
        is_admin=args.admin,
    )

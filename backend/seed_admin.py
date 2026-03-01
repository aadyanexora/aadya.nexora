#!/usr/bin/env python3
"""Utility script for creating/updating an administrator user.

Usage:
    python backend/seed_admin.py [--email EMAIL] [--password PASSWORD]

Defaults are read from environment variables ADMIN_EMAIL/ADMIN_PASSWORD or
fall back to "admin"/"admin123". The script installs the database tables
(if not already present) and then ensures the specified user exists with
is_admin=True.
"""

import argparse
import os
import sys

# ensure that backend directory (which contains the `app` package) is on the path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

from app.db import session as db_session
from app.models.user import User
from app.core.security import hash_password


def ensure_tables():
    # import models so metadata is populated
    from app.db import base
    import app.models.user
    import app.models.document
    import app.models.chat

    base.Base.metadata.create_all(bind=db_session.engine)


def seed(email: str, password: str):
    db = db_session.SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"Admin user '{email}' already exists; updating password and flagging admin")
            existing.hashed_password = hash_password(password)
            existing.is_admin = True
        else:
            admin = User(
                email=email,
                hashed_password=hash_password(password),
                is_admin=True,
            )
            db.add(admin)
        db.commit()
        print(f"Admin user '{email}' seeded (password {'updated' if existing else 'set'})")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed admin user into database")
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL", "admin@example.com"))
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD", "admin123"))
    args = parser.parse_args()

    ensure_tables()
    seed(args.email, args.password)

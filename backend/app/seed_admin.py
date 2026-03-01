#!/usr/bin/env python3
"""Admin seeder utility contained within the application package.

This version is copied into the Docker image under /app and thus can be run
from the backend container using:

    docker exec <container> python -m app.seed_admin

The script will create database tables if necessary and then ensure that a
user with the configured credentials exists and has `is_admin=True`.
"""

import argparse
import os

from app.db import session as db_session
from app.models.user import User
from app.core.security import hash_password


def ensure_tables():
    # import models so metadata is registered
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


def main():
    parser = argparse.ArgumentParser(description="Seed admin user into database")
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL", "admin@example.com"))
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD", "admin123"))
    args = parser.parse_args()

    ensure_tables()
    seed(args.email, args.password)


if __name__ == "__main__":
    main()

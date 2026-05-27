"""Seed demo login personas for local development and demos.

Usage (from backend/):
    python scripts/seed_demo_users.py

Idempotent: existing emails are skipped.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.config import get_settings
from core.security import hash_password, normalize_email
from services import user_store

DEMO_PERSONAS: list[dict[str, str]] = [
    {
        "persona": "Presales Lead",
        "full_name": "Alex Presales",
        "email": "presales.lead@example.com",
        "password": "DemoPass1",
        "description": "Uploads RFPs, runs the pipeline, and submits clarifications to generate the final draft.",
    },
    {
        "persona": "Solution Architect",
        "full_name": "Sam Architect",
        "email": "solution.architect@example.com",
        "password": "DemoPass1",
        "description": "Reviews requirements, scope, and technical clarifications before proposal finalization.",
    },
    {
        "persona": "Bid Manager",
        "full_name": "Morgan Bid",
        "email": "bid.manager@example.com",
        "password": "DemoPass1",
        "description": "Tracks milestones, submission dates, and deadline reminders across active pursuits.",
    },
]


def seed_demo_users() -> None:
    settings = get_settings()
    created = 0
    skipped = 0
    for persona in DEMO_PERSONAS:
        email = normalize_email(persona["email"])
        if user_store.get_user_by_email(settings, email):
            skipped += 1
            print(f"skip  {persona['persona']:<22} {email}")
            continue
        user_store.create_user(
            settings,
            full_name=persona["full_name"],
            email=email,
            password_hash=hash_password(persona["password"]),
        )
        created += 1
        print(f"added {persona['persona']:<22} {email}")
    print(f"\nDone: {created} created, {skipped} already existed.")


if __name__ == "__main__":
    seed_demo_users()

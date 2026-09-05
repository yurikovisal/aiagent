"""MEZA CLI: create-admin, seed, migrate wrappers used by the Makefile."""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select


async def _create_admin(email: str, password: str, full_name: str) -> None:
    from meza.core.db import session_scope
    from meza.core.rbac import Role
    from meza.core.security import hash_password
    from meza.models import User

    async with session_scope() as db:
        existing = (await db.execute(select(User).where(User.email == email))).scalars().first()
        if existing:
            print(f"User {email} already exists (role={existing.role}).")
            return
        user = User(email=email, full_name=full_name, password_hash=hash_password(password), role=Role.ADMIN.value, is_active=True)
        db.add(user)
    print(f"Created admin user {email}.")


async def _seed_demo(force: bool) -> None:
    from meza.core.db import session_scope
    from meza.models import Order
    from meza.seed.demo_data import seed_demo

    async with session_scope() as db:
        existing = (await db.execute(select(Order).where(Order.is_demo.is_(False)))).scalars().first()
        if existing and not force:
            print("Refusing to seed demo data: non-demo orders already exist. Use --force to override.")
            sys.exit(1)
        summary = await seed_demo(db)
    print("Seeded DEMO DATA:", summary)


async def _create_admin_from_env() -> None:
    from meza.core.config import get_settings

    settings = get_settings()
    await _create_admin(settings.admin_email, settings.admin_password, "ATON+ Admin")


def main() -> None:
    parser = argparse.ArgumentParser(prog="meza")
    sub = parser.add_subparsers(dest="command", required=True)

    p_admin = sub.add_parser("create-admin")
    p_admin.add_argument("--email")
    p_admin.add_argument("--password")
    p_admin.add_argument("--full-name", default="ATON+ Admin")

    p_seed = sub.add_parser("seed")
    p_seed.add_argument("--force", action="store_true")

    sub.add_parser("evaluate-risks")

    args = parser.parse_args()

    if args.command == "create-admin":
        if args.email and args.password:
            asyncio.run(_create_admin(args.email, args.password, args.full_name))
        else:
            asyncio.run(_create_admin_from_env())
    elif args.command == "seed":
        asyncio.run(_seed_demo(args.force))
    elif args.command == "evaluate-risks":
        from meza.core.db import session_scope
        from meza.services.risk_engine import run_all_rules

        async def _run():
            async with session_scope() as db:
                risks = await run_all_rules(db)
            print(f"Evaluated risk rules: {len(risks)} open risks.")

        asyncio.run(_run())


if __name__ == "__main__":
    main()

"""Operational CLI: python -m vulnconsole.platform.cli <command> [options]"""

import argparse
import asyncio
import getpass
import os
import sys

from vulnconsole.contexts.identity.application import service
from vulnconsole.contexts.identity.domain.roles import ROLES
from vulnconsole.shared.db import get_session_factory
from vulnconsole.shared.logging import configure_logging

MIN_PASSWORD_LENGTH = 12


async def _create_user(username: str, role: str, password_env: str, if_not_exists: bool) -> int:
    password = os.environ.get(password_env) or getpass.getpass(f"Password for {username}: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"error: password must be at least {MIN_PASSWORD_LENGTH} characters", file=sys.stderr)
        return 1
    async with get_session_factory()() as session:
        existing = await service.get_user_by_username(session, username)
        if existing is not None:
            if if_not_exists:
                print(f"user {username!r} already exists; skipping")
                return 0
            print(f"error: user {username!r} already exists", file=sys.stderr)
            return 1
        user = await service.create_user(
            session, actor="system:cli", username=username, password=password, role=role
        )
        print(f"created user {user.username!r} with role {user.role!r} (id {user.id})")
    return 0


def main(argv: list[str] | None = None) -> int:
    configure_logging("WARNING")
    parser = argparse.ArgumentParser(prog="vulnconsole", description="Operational commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-user", help="Create a user account")
    create.add_argument("--username", required=True)
    create.add_argument("--role", required=True, choices=ROLES)
    create.add_argument(
        "--password-env",
        default="VULNCONSOLE_USER_PASSWORD",
        help="Environment variable holding the password (prompts if unset)",
    )
    create.add_argument(
        "--if-not-exists",
        action="store_true",
        help="Exit 0 without error when the user already exists",
    )

    args = parser.parse_args(argv)
    if args.command == "create-user":
        return asyncio.run(
            _create_user(args.username, args.role, args.password_env, args.if_not_exists)
        )
    return 2  # pragma: no cover - argparse enforces valid commands


if __name__ == "__main__":
    raise SystemExit(main())

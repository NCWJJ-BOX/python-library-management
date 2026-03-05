from __future__ import annotations

import argparse
from pathlib import Path

from .qt_app import run_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Library Management System (PyQt + SQLite)")
    parser.add_argument(
        "--db",
        default=None,
        help="Path to sqlite database file (default: ./library.db)",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db) if args.db else (Path(__file__).resolve().parent.parent / "library.db")
    return run_app(db_path)


if __name__ == "__main__":
    raise SystemExit(main())

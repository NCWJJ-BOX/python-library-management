# Python Library Management (PyQt + SQLite)

Simple library management app with a PyQt UI and a SQLite database.

## Features

- Books: add/edit/delete, search, status (available/checked out)
- Users: add/edit/delete, search
- Loans: checkout/return, due date, filter open/all and by user
- Tools: export/import CSV (books/users), backup/restore database

## Run

1) Install dependencies

```bash
pip install -r requirements.txt
```

If you are on Debian/Ubuntu with PEP 668 restrictions, use a virtualenv:

```bash
apt install python3-venv
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2) Start the app

```bash
python "library management.py"
```

The default database file is created at `./library.db`.

## Development

Typecheck:

```bash
basedpyright .
```

Syntax check:

```bash
python -m compileall -q .
```

## Git: commit + push

Typical workflow:

```bash
git status
git add <files>
git commit -m "<message>"
git push
```

This repo currently uses simple, plain commit messages (no `feat:` prefixes).

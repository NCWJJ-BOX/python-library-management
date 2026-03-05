# Library Management (PyQt + SQLite)

Desktop library management app with a modern PyQt6 UI and a SQLite database.

## Screenshots

![Books tab](img/books.png)

![Users tab](img/users.png)

![Loans tab](img/loans.png)

![Tools tab](img/tools.png)

## Features

- Books: add/edit/delete, search, status (available / checked out)
- Users: add/edit/delete, search
- Loans: checkout/return, due date, filter open/all and by user
- Tools: export/import CSV (books/users), backup/restore database

## Quick Start

Prerequisites:

- Python 3.10+ (tested with 3.12)

Create a virtual environment and install dependencies.

Windows (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

macOS / Linux:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

Start the app:

```bash
python "library management.py"
```

Default database file is created at `./library.db`.

Optional: choose a database path:

```bash
python "library management.py" --db ./data/library.db
```

## CSV Import/Export

- Books CSV columns: `title,author,isbn`
- Users CSV columns: `name`

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

```bash
git status
git add <files>
git commit -m "<message>"
git push
```

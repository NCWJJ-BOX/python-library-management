from __future__ import annotations

import csv
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, TypedDict

from .errors import ConflictError, NotFoundError, ValidationError


UTC = timezone.utc


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class BookRow:
    id: int
    title: str
    author: str
    isbn: str


@dataclass(frozen=True)
class UserRow:
    id: int
    name: str


@dataclass(frozen=True)
class LoanRow:
    id: int
    user_id: int
    user_name: str
    book_id: int
    book_title: str
    book_author: str
    book_isbn: str
    checkout_at: str
    due_at: str
    return_at: Optional[str]


class BookStatusRow(TypedDict):
    book_id: int
    title: str
    author: str
    isbn: str
    checked_out: bool
    borrower: str | None
    due_at: str | None


class Database:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def migrate(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    isbn TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
                );

                CREATE TABLE IF NOT EXISTS loans (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                    checkout_at TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    return_at TEXT
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_loans_open_book
                    ON loans(book_id) WHERE return_at IS NULL;

                CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
                CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
                CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);
                CREATE INDEX IF NOT EXISTS idx_loans_user_open ON loans(user_id) WHERE return_at IS NULL;
                """
            )

            self._seed_if_empty(conn)

    def _seed_if_empty(self, conn: sqlite3.Connection) -> None:
        cur = conn.execute("SELECT COUNT(*) AS c FROM books")
        if int(cur.fetchone()["c"]) > 0:
            return
        initial_books = [
            ("The Great Gatsby", "F. Scott", "0001"),
            ("To Kill a Mockingbird", "Harper", "0002"),
            ("1984", "George Orwell", "0003"),
            ("Pride and Prejudice", "Jane Austen", "0004"),
            ("The Catcher in the Rye", "J.D.", "0005"),
        ]
        conn.executemany(
            "INSERT INTO books(title, author, isbn) VALUES(?,?,?)",
            initial_books,
        )

    def add_book(self, title: str, author: str, isbn: str) -> int:
        title, author, isbn = title.strip(), author.strip(), isbn.strip()
        if not title or not author or not isbn:
            raise ValidationError("title/author/isbn are required")
        try:
            with self.connect() as conn:
                cur = conn.execute(
                    "INSERT INTO books(title, author, isbn) VALUES(?,?,?)",
                    (title, author, isbn),
                )
                if cur.lastrowid is None:
                    raise RuntimeError("Failed to insert book")
                return int(cur.lastrowid)
        except sqlite3.IntegrityError as e:
            raise ConflictError("ISBN already exists") from e

    def update_book(self, book_id: int, title: str, author: str, isbn: str) -> None:
        title, author, isbn = title.strip(), author.strip(), isbn.strip()
        if not title or not author or not isbn:
            raise ValidationError("title/author/isbn are required")
        try:
            with self.connect() as conn:
                cur = conn.execute(
                    "UPDATE books SET title=?, author=?, isbn=? WHERE id=?",
                    (title, author, isbn, int(book_id)),
                )
                if cur.rowcount == 0:
                    raise NotFoundError("Book not found")
        except sqlite3.IntegrityError as e:
            raise ConflictError("ISBN already exists") from e

    def delete_book(self, book_id: int) -> None:
        with self.connect() as conn:
            open_loan = conn.execute(
                "SELECT 1 FROM loans WHERE book_id=? AND return_at IS NULL",
                (int(book_id),),
            ).fetchone()
            if open_loan is not None:
                raise ConflictError("Cannot delete: book is checked out")
            cur = conn.execute("DELETE FROM books WHERE id=?", (int(book_id),))
            if cur.rowcount == 0:
                raise NotFoundError("Book not found")

    def list_books(self, query: str = "") -> list[BookRow]:
        q = query.strip().lower()
        with self.connect() as conn:
            if not q:
                rows = conn.execute(
                    "SELECT id, title, author, isbn FROM books ORDER BY title"
                ).fetchall()
            else:
                like = f"%{q}%"
                rows = conn.execute(
                    """
                    SELECT id, title, author, isbn
                    FROM books
                    WHERE lower(title) LIKE ? OR lower(author) LIKE ? OR lower(isbn) LIKE ?
                    ORDER BY title
                    """,
                    (like, like, like),
                ).fetchall()
        return [BookRow(int(r["id"]), r["title"], r["author"], r["isbn"]) for r in rows]

    def list_books_with_status(self, query: str = "") -> list[BookStatusRow]:
        q = query.strip().lower()
        with self.connect() as conn:
            params: tuple[object, ...] = ()
            where = ""
            if q:
                like = f"%{q}%"
                where = "WHERE lower(b.title) LIKE ? OR lower(b.author) LIKE ? OR lower(b.isbn) LIKE ?"
                params = (like, like, like)
            rows = conn.execute(
                f"""
                SELECT
                    b.id AS book_id,
                    b.title,
                    b.author,
                    b.isbn,
                    l.id AS loan_id,
                    u.name AS borrower,
                    l.due_at AS due_at
                FROM books b
                LEFT JOIN loans l ON l.book_id = b.id AND l.return_at IS NULL
                LEFT JOIN users u ON u.id = l.user_id
                {where}
                ORDER BY b.title
                """,
                params,
            ).fetchall()

        result: list[BookStatusRow] = []
        for r in rows:
            checked_out = r["loan_id"] is not None
            result.append(
                {
                    "book_id": int(r["book_id"]),
                    "title": r["title"],
                    "author": r["author"],
                    "isbn": r["isbn"],
                    "checked_out": bool(checked_out),
                    "borrower": r["borrower"],
                    "due_at": r["due_at"],
                }
            )
        return result

    def add_user(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValidationError("name is required")
        try:
            with self.connect() as conn:
                cur = conn.execute("INSERT INTO users(name) VALUES(?)", (name,))
                if cur.lastrowid is None:
                    raise RuntimeError("Failed to insert user")
                return int(cur.lastrowid)
        except sqlite3.IntegrityError as e:
            raise ConflictError("User name already exists") from e

    def update_user(self, user_id: int, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValidationError("name is required")
        try:
            with self.connect() as conn:
                cur = conn.execute(
                    "UPDATE users SET name=? WHERE id=?",
                    (name, int(user_id)),
                )
                if cur.rowcount == 0:
                    raise NotFoundError("User not found")
        except sqlite3.IntegrityError as e:
            raise ConflictError("User name already exists") from e

    def delete_user(self, user_id: int) -> None:
        with self.connect() as conn:
            open_loan = conn.execute(
                "SELECT 1 FROM loans WHERE user_id=? AND return_at IS NULL",
                (int(user_id),),
            ).fetchone()
            if open_loan is not None:
                raise ConflictError("Cannot delete: user has checked out books")
            cur = conn.execute("DELETE FROM users WHERE id=?", (int(user_id),))
            if cur.rowcount == 0:
                raise NotFoundError("User not found")

    def list_users(self, query: str = "") -> list[UserRow]:
        q = query.strip().lower()
        with self.connect() as conn:
            if not q:
                rows = conn.execute(
                    "SELECT id, name FROM users ORDER BY name"
                ).fetchall()
            else:
                like = f"%{q}%"
                rows = conn.execute(
                    "SELECT id, name FROM users WHERE lower(name) LIKE ? ORDER BY name",
                    (like,),
                ).fetchall()
        return [UserRow(int(r["id"]), r["name"]) for r in rows]

    def checkout_book(self, user_id: int, book_id: int, loan_days: int = 14) -> int:
        if loan_days <= 0:
            raise ValidationError("loan_days must be > 0")
        checkout_at = utc_now_iso()
        due_at = (
            datetime.fromisoformat(checkout_at)
            .astimezone(UTC)
            .replace(microsecond=0)
            + timedelta(days=int(loan_days))
        ).isoformat()

        try:
            with self.connect() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM users WHERE id=?",
                    (int(user_id),),
                ).fetchone()
                if exists is None:
                    raise NotFoundError("User not found")

                exists = conn.execute(
                    "SELECT 1 FROM books WHERE id=?",
                    (int(book_id),),
                ).fetchone()
                if exists is None:
                    raise NotFoundError("Book not found")

                cur = conn.execute(
                    """
                    INSERT INTO loans(user_id, book_id, checkout_at, due_at, return_at)
                    VALUES(?,?,?,?,NULL)
                    """,
                    (int(user_id), int(book_id), checkout_at, due_at),
                )
                if cur.lastrowid is None:
                    raise RuntimeError("Failed to insert loan")
                return int(cur.lastrowid)
        except sqlite3.IntegrityError as e:
            raise ConflictError("Book is already checked out") from e

    def return_loan(self, loan_id: int) -> None:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE loans SET return_at=? WHERE id=? AND return_at IS NULL",
                (utc_now_iso(), int(loan_id)),
            )
            if cur.rowcount == 0:
                raise NotFoundError("Open loan not found")

    def list_loans(
        self,
        *,
        open_only: bool = False,
        user_id: Optional[int] = None,
    ) -> list[LoanRow]:
        clauses: list[str] = []
        params: list[object] = []
        if open_only:
            clauses.append("l.return_at IS NULL")
        if user_id is not None:
            clauses.append("l.user_id = ?")
            params.append(int(user_id))
        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    l.id AS loan_id,
                    l.user_id,
                    u.name AS user_name,
                    l.book_id,
                    b.title AS book_title,
                    b.author AS book_author,
                    b.isbn AS book_isbn,
                    l.checkout_at,
                    l.due_at,
                    l.return_at
                FROM loans l
                JOIN users u ON u.id = l.user_id
                JOIN books b ON b.id = l.book_id
                {where}
                ORDER BY l.checkout_at DESC
                """,
                tuple(params),
            ).fetchall()

        return [
            LoanRow(
                id=int(r["loan_id"]),
                user_id=int(r["user_id"]),
                user_name=r["user_name"],
                book_id=int(r["book_id"]),
                book_title=r["book_title"],
                book_author=r["book_author"],
                book_isbn=r["book_isbn"],
                checkout_at=r["checkout_at"],
                due_at=r["due_at"],
                return_at=r["return_at"],
            )
            for r in rows
        ]

    def export_books_csv(self, csv_path: Path) -> None:
        books = self.list_books(query="")
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["title", "author", "isbn"])
            for b in books:
                w.writerow([b.title, b.author, b.isbn])

    def export_users_csv(self, csv_path: Path) -> None:
        users = self.list_users(query="")
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name"])
            for u in users:
                w.writerow([u.name])

    def import_books_csv(self, csv_path: Path, *, update_on_isbn: bool = True) -> int:
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise NotFoundError("CSV not found")

        imported = 0
        with csv_path.open("r", newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            expected = {"title", "author", "isbn"}
            if r.fieldnames is None or not expected.issubset(set(r.fieldnames)):
                raise ValidationError("CSV must include title, author, isbn")
            rows = [(row["title"], row["author"], row["isbn"]) for row in r]

        with self.connect() as conn:
            for title, author, isbn in rows:
                title, author, isbn = title.strip(), author.strip(), isbn.strip()
                if not title or not author or not isbn:
                    continue
                try:
                    conn.execute(
                        "INSERT INTO books(title, author, isbn) VALUES(?,?,?)",
                        (title, author, isbn),
                    )
                    imported += 1
                except sqlite3.IntegrityError:
                    if not update_on_isbn:
                        continue
                    conn.execute(
                        "UPDATE books SET title=?, author=? WHERE isbn=?",
                        (title, author, isbn),
                    )
                    imported += 1

        return imported

    def import_users_csv(self, csv_path: Path, *, skip_duplicates: bool = True) -> int:
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise NotFoundError("CSV not found")

        imported = 0
        with csv_path.open("r", newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            if r.fieldnames is None or "name" not in set(r.fieldnames):
                raise ValidationError("CSV must include name")
            names = [row["name"] for row in r]

        with self.connect() as conn:
            for name in names:
                name = (name or "").strip()
                if not name:
                    continue
                try:
                    conn.execute("INSERT INTO users(name) VALUES(?)", (name,))
                    imported += 1
                except sqlite3.IntegrityError:
                    if not skip_duplicates:
                        raise

        return imported

    def backup_to(self, backup_path: Path) -> None:
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            raise NotFoundError("Database file not found")
        shutil.copy2(self.db_path, backup_path)

    def restore_from(self, backup_path: Path) -> None:
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise NotFoundError("Backup file not found")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, self.db_path)

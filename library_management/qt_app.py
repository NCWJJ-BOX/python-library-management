from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import sqlite3

from .db import Database
from .errors import LibraryError

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "PyQt6 is not installed. Install dependencies: pip install -r requirements.txt"
    ) from e


@dataclass(frozen=True)
class BookFormData:
    title: str
    author: str
    isbn: str


@dataclass(frozen=True)
class UserFormData:
    name: str


class BookDialog(QtWidgets.QDialog):
    def __init__(self, *, parent, title: str, data: Optional[BookFormData] = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        self._title = QtWidgets.QLineEdit(self)
        self._author = QtWidgets.QLineEdit(self)
        self._isbn = QtWidgets.QLineEdit(self)

        if data is not None:
            self._title.setText(data.title)
            self._author.setText(data.author)
            self._isbn.setText(data.isbn)

        form = QtWidgets.QFormLayout()
        form.addRow("Title", self._title)
        form.addRow("Author", self._author)
        form.addRow("ISBN", self._isbn)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def value(self) -> BookFormData:
        return BookFormData(
            title=self._title.text().strip(),
            author=self._author.text().strip(),
            isbn=self._isbn.text().strip(),
        )


class UserDialog(QtWidgets.QDialog):
    def __init__(self, *, parent, title: str, data: Optional[UserFormData] = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        self._name = QtWidgets.QLineEdit(self)
        if data is not None:
            self._name.setText(data.name)

        form = QtWidgets.QFormLayout()
        form.addRow("Name", self._name)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def value(self) -> UserFormData:
        return UserFormData(name=self._name.text().strip())


class BooksTab(QtWidgets.QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db

        self.search = QtWidgets.QLineEdit(self)
        self.search.setPlaceholderText("Search by title / author / ISBN")
        self.search.returnPressed.connect(self.refresh)

        self.btn_refresh = QtWidgets.QPushButton("Refresh", self)
        self.btn_add = QtWidgets.QPushButton("Add", self)
        self.btn_edit = QtWidgets.QPushButton("Edit", self)
        self.btn_delete = QtWidgets.QPushButton("Delete", self)
        self.btn_export = QtWidgets.QPushButton("Export CSV", self)
        self.btn_import = QtWidgets.QPushButton("Import CSV", self)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_add.clicked.connect(self.add_book)
        self.btn_edit.clicked.connect(self.edit_book)
        self.btn_delete.clicked.connect(self.delete_book)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_import.clicked.connect(self.import_csv)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Title", "Author", "ISBN", "Status", "Borrower", "Due"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.search, 1)
        for b in (
            self.btn_refresh,
            self.btn_add,
            self.btn_edit,
            self.btn_delete,
            self.btn_export,
            self.btn_import,
        ):
            top.addWidget(b)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)

        self.refresh()

    def _selected_book_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        book_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if book_id is None:
            return None
        return int(book_id)

    def refresh(self) -> None:
        data = self.db.list_books_with_status(query=self.search.text())
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(data))
        for r, b in enumerate(data):
            status = "Checked out" if b["checked_out"] else "Available"
            borrower = b["borrower"] or ""
            due_at = b["due_at"] or ""
            items = [
                QtWidgets.QTableWidgetItem(b["title"]),
                QtWidgets.QTableWidgetItem(b["author"]),
                QtWidgets.QTableWidgetItem(b["isbn"]),
                QtWidgets.QTableWidgetItem(status),
                QtWidgets.QTableWidgetItem(borrower),
                QtWidgets.QTableWidgetItem(due_at),
            ]
            items[0].setData(QtCore.Qt.ItemDataRole.UserRole, b["book_id"])
            for c, it in enumerate(items):
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def add_book(self) -> None:
        dlg = BookDialog(parent=self, title="Add Book")
        if dlg.exec() != int(QtWidgets.QDialog.DialogCode.Accepted):
            return
        v = dlg.value()
        try:
            self.db.add_book(v.title, v.author, v.isbn)
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        self.refresh()

    def edit_book(self) -> None:
        book_id = self._selected_book_id()
        if book_id is None:
            return
        row = self.table.currentRow()
        v = BookFormData(
            title=self.table.item(row, 0).text(),
            author=self.table.item(row, 1).text(),
            isbn=self.table.item(row, 2).text(),
        )
        dlg = BookDialog(parent=self, title="Edit Book", data=v)
        if dlg.exec() != int(QtWidgets.QDialog.DialogCode.Accepted):
            return
        nv = dlg.value()
        try:
            self.db.update_book(book_id, nv.title, nv.author, nv.isbn)
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        self.refresh()

    def delete_book(self) -> None:
        book_id = self._selected_book_id()
        if book_id is None:
            return
        if (
            QtWidgets.QMessageBox.question(self, "Delete", "Delete selected book?")
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self.db.delete_book(book_id)
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        self.refresh()

    def export_csv(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Books", "books.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            self.db.export_books_csv(Path(path))
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        QtWidgets.QMessageBox.information(self, "Export", "Exported books CSV")

    def import_csv(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Books", "", "CSV (*.csv)")
        if not path:
            return
        try:
            n = self.db.import_books_csv(Path(path), update_on_isbn=True)
        except (LibraryError, sqlite3.Error) as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        self.refresh()
        QtWidgets.QMessageBox.information(self, "Import", f"Imported/updated {n} books")


class UsersTab(QtWidgets.QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db

        self.search = QtWidgets.QLineEdit(self)
        self.search.setPlaceholderText("Search user")
        self.search.returnPressed.connect(self.refresh)

        self.btn_refresh = QtWidgets.QPushButton("Refresh", self)
        self.btn_add = QtWidgets.QPushButton("Add", self)
        self.btn_edit = QtWidgets.QPushButton("Edit", self)
        self.btn_delete = QtWidgets.QPushButton("Delete", self)
        self.btn_export = QtWidgets.QPushButton("Export CSV", self)
        self.btn_import = QtWidgets.QPushButton("Import CSV", self)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_add.clicked.connect(self.add_user)
        self.btn_edit.clicked.connect(self.edit_user)
        self.btn_delete.clicked.connect(self.delete_user)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_import.clicked.connect(self.import_csv)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["Name"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.search, 1)
        for b in (
            self.btn_refresh,
            self.btn_add,
            self.btn_edit,
            self.btn_delete,
            self.btn_export,
            self.btn_import,
        ):
            top.addWidget(b)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)

        self.refresh()

    def _selected_user_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        user_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if user_id is None:
            return None
        return int(user_id)

    def refresh(self) -> None:
        users = self.db.list_users(query=self.search.text())
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(users))
        for r, u in enumerate(users):
            it = QtWidgets.QTableWidgetItem(u.name)
            it.setData(QtCore.Qt.ItemDataRole.UserRole, u.id)
            self.table.setItem(r, 0, it)
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def add_user(self) -> None:
        dlg = UserDialog(parent=self, title="Add User")
        if dlg.exec() != int(QtWidgets.QDialog.DialogCode.Accepted):
            return
        v = dlg.value()
        try:
            self.db.add_user(v.name)
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        self.refresh()

    def edit_user(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            return
        row = self.table.currentRow()
        v = UserFormData(name=self.table.item(row, 0).text())
        dlg = UserDialog(parent=self, title="Edit User", data=v)
        if dlg.exec() != int(QtWidgets.QDialog.DialogCode.Accepted):
            return
        nv = dlg.value()
        try:
            self.db.update_user(user_id, nv.name)
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        self.refresh()

    def delete_user(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            return
        if (
            QtWidgets.QMessageBox.question(self, "Delete", "Delete selected user?")
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self.db.delete_user(user_id)
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        self.refresh()

    def export_csv(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Users", "users.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            self.db.export_users_csv(Path(path))
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        QtWidgets.QMessageBox.information(self, "Export", "Exported users CSV")

    def import_csv(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Users", "", "CSV (*.csv)")
        if not path:
            return
        try:
            n = self.db.import_users_csv(Path(path), skip_duplicates=True)
        except (LibraryError, sqlite3.Error) as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        self.refresh()
        QtWidgets.QMessageBox.information(self, "Import", f"Imported {n} users")


class LoansTab(QtWidgets.QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db

        self.user_combo = QtWidgets.QComboBox(self)
        self.user_filter = QtWidgets.QComboBox(self)
        self.open_only = QtWidgets.QCheckBox("Open only", self)

        self.book_combo = QtWidgets.QComboBox(self)
        self.btn_checkout = QtWidgets.QPushButton("Checkout", self)
        self.btn_return = QtWidgets.QPushButton("Return selected", self)
        self.btn_refresh = QtWidgets.QPushButton("Refresh", self)

        self.btn_checkout.clicked.connect(self.checkout)
        self.btn_return.clicked.connect(self.return_selected)
        self.btn_refresh.clicked.connect(self.refresh)
        self.user_filter.currentIndexChanged.connect(self.refresh)
        self.open_only.stateChanged.connect(self.refresh)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "User",
            "Title",
            "ISBN",
            "Checkout",
            "Due",
            "Returned",
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("User:"), 0)
        top.addWidget(self.user_combo, 1)
        top.addWidget(QtWidgets.QLabel("Book:"), 0)
        top.addWidget(self.book_combo, 2)
        top.addWidget(self.btn_checkout)
        top.addWidget(self.btn_return)
        top.addWidget(self.btn_refresh)

        filter_row = QtWidgets.QHBoxLayout()
        filter_row.addWidget(QtWidgets.QLabel("Filter:"), 0)
        filter_row.addWidget(self.user_filter, 1)
        filter_row.addWidget(self.open_only, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(filter_row)
        layout.addWidget(self.table)

        self.refresh()

    def _selected_loan_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        loan_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if loan_id is None:
            return None
        return int(loan_id)

    def refresh(self) -> None:
        users = self.db.list_users(query="")
        self.user_combo.clear()
        for u in users:
            self.user_combo.addItem(u.name, u.id)

        current_filter = self.user_filter.currentData()
        self.user_filter.blockSignals(True)
        self.user_filter.clear()
        self.user_filter.addItem("All users", None)
        for u in users:
            self.user_filter.addItem(u.name, u.id)
        if current_filter is None:
            self.user_filter.setCurrentIndex(0)
        else:
            idx = self.user_filter.findData(current_filter)
            if idx >= 0:
                self.user_filter.setCurrentIndex(idx)
        self.user_filter.blockSignals(False)

        self.book_combo.clear()
        for b in self.db.list_books_with_status(query=""):
            if b["checked_out"]:
                continue
            self.book_combo.addItem(f"{b['title']} ({b['isbn']})", b["book_id"])

        open_only = self.open_only.isChecked()
        user_id = self.user_filter.currentData()
        loans = self.db.list_loans(open_only=open_only, user_id=user_id)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(loans))
        for r, l in enumerate(loans):
            returned = l.return_at or ""
            items = [
                QtWidgets.QTableWidgetItem(l.user_name),
                QtWidgets.QTableWidgetItem(l.book_title),
                QtWidgets.QTableWidgetItem(l.book_isbn),
                QtWidgets.QTableWidgetItem(l.checkout_at),
                QtWidgets.QTableWidgetItem(l.due_at),
                QtWidgets.QTableWidgetItem(returned),
            ]
            items[0].setData(QtCore.Qt.ItemDataRole.UserRole, l.id)
            for c, it in enumerate(items):
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def checkout(self) -> None:
        user_id = self.user_combo.currentData()
        book_id = self.book_combo.currentData()
        if user_id is None or book_id is None:
            return
        try:
            self.db.checkout_book(int(user_id), int(book_id))
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        self.refresh()

    def return_selected(self) -> None:
        loan_id = self._selected_loan_id()
        if loan_id is None:
            return
        try:
            self.db.return_loan(loan_id)
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        self.refresh()


class ToolsTab(QtWidgets.QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db

        self.info = QtWidgets.QLabel(self)
        self.info.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self._refresh_info()

        self.btn_backup = QtWidgets.QPushButton("Backup DB", self)
        self.btn_restore = QtWidgets.QPushButton("Restore DB", self)

        self.btn_backup.clicked.connect(self.backup)
        self.btn_restore.clicked.connect(self.restore)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.info)
        layout.addWidget(self.btn_backup)
        layout.addWidget(self.btn_restore)
        layout.addStretch(1)

    def _refresh_info(self) -> None:
        self.info.setText(f"Database: {self.db.db_path}")

    def backup(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Backup Database", "library.backup.db", "DB (*.db)")
        if not path:
            return
        try:
            self.db.backup_to(Path(path))
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        QtWidgets.QMessageBox.information(self, "Backup", "Backup created")

    def restore(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Restore Database", "", "DB (*.db)")
        if not path:
            return
        if (
            QtWidgets.QMessageBox.question(self, "Restore", "Restore will overwrite current database. Continue?")
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self.db.restore_from(Path(path))
            self.db.migrate()
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        self._refresh_info()
        QtWidgets.QMessageBox.information(self, "Restore", "Database restored")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.setWindowTitle("Library Management System")
        self.resize(1100, 650)

        tabs = QtWidgets.QTabWidget(self)
        self.books_tab = BooksTab(db, parent=tabs)
        self.users_tab = UsersTab(db, parent=tabs)
        self.loans_tab = LoansTab(db, parent=tabs)
        self.tools_tab = ToolsTab(db, parent=tabs)

        tabs.addTab(self.books_tab, "Books")
        tabs.addTab(self.users_tab, "Users")
        tabs.addTab(self.loans_tab, "Loans")
        tabs.addTab(self.tools_tab, "Tools")

        tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(tabs)

    def _on_tab_changed(self, _index: int) -> None:
        self.books_tab.refresh()
        self.users_tab.refresh()
        self.loans_tab.refresh()


def run_app(db_path: Path) -> int:
    db = Database(db_path)
    db.migrate()

    app = QtWidgets.QApplication([])
    app.setApplicationName("Library Management")

    win = MainWindow(db)
    win.show()
    return int(app.exec())

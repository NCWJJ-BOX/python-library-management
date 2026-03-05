from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, cast

import sqlite3

from .db import Database
from .errors import LibraryError

try:
    if TYPE_CHECKING:
        QtCore = cast(Any, object())
        QtGui = cast(Any, object())
        QtWidgets = cast(Any, object())
    else:
        from PyQt6 import QtCore as QtCore
        from PyQt6 import QtGui as QtGui
        from PyQt6 import QtWidgets as QtWidgets
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "PyQt6 is not installed. Install dependencies: pip install -r requirements.txt"
    ) from e


def apply_theme(app) -> None:
    app.setStyle("Fusion")

    font = QtGui.QFont("Segoe UI", 10)
    font.setStyleHint(QtGui.QFont.StyleHint.SansSerif)
    app.setFont(font)

    pal = QtGui.QPalette()
    pal.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#f6f7fb"))
    pal.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#ffffff"))
    pal.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#f3f6fb"))
    pal.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("#0f172a"))
    pal.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("#0f172a"))
    pal.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#ffffff"))
    pal.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#0f172a"))
    pal.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#dbeafe"))
    pal.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor("#0f172a"))
    app.setPalette(pal)

    app.setStyleSheet(
        """
        QWidget {
            color: #0f172a;
        }

        QLabel[role='muted'] {
            color: #425466;
        }

        QWidget#HeaderBar {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #ffffff,
                stop:1 #eef2ff);
            border: 1px solid #d7dde7;
            border-radius: 16px;
        }

        QLabel#AppTitle {
            font-size: 20px;
            font-weight: 700;
            color: #0f172a;
        }

        QLineEdit, QComboBox {
            background: #ffffff;
            border: 1px solid #d7dde7;
            border-radius: 10px;
            padding: 7px 10px;
        }

        QLineEdit:focus, QComboBox:focus {
            border-color: #2563eb;
        }

        QPushButton {
            background: #ffffff;
            border: 1px solid #d7dde7;
            border-radius: 10px;
            padding: 7px 12px;
        }

        QPushButton:hover {
            background: #f3f6fb;
            border-color: #c7d0df;
        }

        QPushButton:pressed {
            background: #e9eef7;
        }

        QPushButton[variant='primary'] {
            background: #2563eb;
            color: #ffffff;
            border: 1px solid #1d4ed8;
        }

        QPushButton[variant='primary']:hover {
            background: #1d4ed8;
        }

        QPushButton[variant='danger'] {
            background: #ef4444;
            color: #ffffff;
            border: 1px solid #dc2626;
        }

        QPushButton[variant='danger']:hover {
            background: #dc2626;
        }

        QTabWidget::pane {
            border: 0px;
        }

        QTabBar::tab {
            background: transparent;
            border: 1px solid transparent;
            padding: 10px 14px;
            margin-right: 6px;
            border-radius: 10px;
        }

        QTabBar::tab:selected {
            background: #ffffff;
            border-color: #d7dde7;
        }

        QTableWidget {
            background: #ffffff;
            border: 1px solid #d7dde7;
            border-radius: 12px;
            gridline-color: #e6ebf2;
            selection-background-color: #dbeafe;
            selection-color: #0f172a;
        }

        QHeaderView::section {
            background: #f3f6fb;
            border: 0px;
            border-bottom: 1px solid #e6ebf2;
            padding: 8px 10px;
            font-weight: 600;
        }

        QTableWidget::item {
            padding: 6px;
            border-bottom: 1px solid #eef2f7;
        }

        QStatusBar {
            color: #425466;
        }
        """
    )


def _style_table(table) -> None:
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().setVisible(False)
    table.setWordWrap(False)
    table.setCornerButtonEnabled(False)
    table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    header = table.horizontalHeader()
    header.setHighlightSections(False)
    header.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)


def _set_btn_variant(btn, variant: str) -> None:
    btn.setProperty("variant", variant)
    btn.style().unpolish(btn)
    btn.style().polish(btn)


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
        self.setMinimumWidth(420)

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
        self.setMinimumWidth(420)

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
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self.refresh)

        self.btn_refresh = QtWidgets.QPushButton("Refresh", self)
        self.btn_add = QtWidgets.QPushButton("Add", self)
        self.btn_edit = QtWidgets.QPushButton("Edit", self)
        self.btn_delete = QtWidgets.QPushButton("Delete", self)
        self.btn_export = QtWidgets.QPushButton("Export CSV", self)
        self.btn_import = QtWidgets.QPushButton("Import CSV", self)

        _set_btn_variant(self.btn_add, "primary")
        _set_btn_variant(self.btn_delete, "danger")

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_add.clicked.connect(self.add_book)
        self.btn_edit.clicked.connect(self.edit_book)
        self.btn_delete.clicked.connect(self.delete_book)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_import.clicked.connect(self.import_csv)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Title", "Author", "ISBN", "Status", "Borrower", "Due"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        _style_table(self.table)

        self.footer = QtWidgets.QLabel(self)
        self.footer.setProperty("role", "muted")

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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(self.footer)

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
        self.footer.setText(f"{len(data)} books")

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
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self.refresh)

        self.btn_refresh = QtWidgets.QPushButton("Refresh", self)
        self.btn_add = QtWidgets.QPushButton("Add", self)
        self.btn_edit = QtWidgets.QPushButton("Edit", self)
        self.btn_delete = QtWidgets.QPushButton("Delete", self)
        self.btn_export = QtWidgets.QPushButton("Export CSV", self)
        self.btn_import = QtWidgets.QPushButton("Import CSV", self)

        _set_btn_variant(self.btn_add, "primary")
        _set_btn_variant(self.btn_delete, "danger")

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_add.clicked.connect(self.add_user)
        self.btn_edit.clicked.connect(self.edit_user)
        self.btn_delete.clicked.connect(self.delete_user)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_import.clicked.connect(self.import_csv)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["Name"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        _style_table(self.table)

        self.footer = QtWidgets.QLabel(self)
        self.footer.setProperty("role", "muted")

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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(self.footer)

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
        self.footer.setText(f"{len(users)} users")

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

        _set_btn_variant(self.btn_checkout, "primary")

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
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        _style_table(self.table)

        self.footer = QtWidgets.QLabel(self)
        self.footer.setProperty("role", "muted")

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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(top)
        layout.addLayout(filter_row)
        layout.addWidget(self.table)
        layout.addWidget(self.footer)

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
        open_label = "open" if open_only else "all"
        who = "all users" if user_id is None else str(self.user_filter.currentText())
        self.footer.setText(f"{len(loans)} loans ({open_label}, {who})")

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

        _set_btn_variant(self.btn_backup, "primary")
        _set_btn_variant(self.btn_restore, "danger")

        self.btn_backup.clicked.connect(self.backup)
        self.btn_restore.clicked.connect(self.restore)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self.info)
        layout.addWidget(self.btn_backup)
        layout.addWidget(self.btn_restore)
        layout.addStretch(1)

    def _refresh_info(self) -> None:
        self.info.setText(f"Database: {self.db.db_path}")

    def backup(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Backup Database",
            "library.backup.db",
            "DB (*.db)",
        )
        if not path:
            return
        try:
            self.db.backup_to(Path(path))
        except LibraryError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return
        QtWidgets.QMessageBox.information(self, "Backup", "Backup created")

    def restore(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Restore Database",
            "",
            "DB (*.db)",
        )
        if not path:
            return
        if (
            QtWidgets.QMessageBox.question(
                self,
                "Restore",
                "Restore will overwrite current database. Continue?",
            )
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


class HeaderBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBar")

        title = QtWidgets.QLabel("Library Management", self)
        title.setObjectName("AppTitle")

        subtitle = QtWidgets.QLabel("Books, users, loans, and database tools", self)
        subtitle.setProperty("role", "muted")

        text_col = QtWidgets.QVBoxLayout()
        text_col.setSpacing(2)
        text_col.addWidget(title)
        text_col.addWidget(subtitle)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addLayout(text_col, 1)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.setWindowTitle("Library Management System")
        self.resize(1100, 650)

        self.statusBar().showMessage("Ready")

        wrapper = QtWidgets.QWidget(self)
        outer = QtWidgets.QVBoxLayout(wrapper)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        outer.addWidget(HeaderBar(parent=wrapper))

        tabs = QtWidgets.QTabWidget(wrapper)
        self.books_tab = BooksTab(db, parent=tabs)
        self.users_tab = UsersTab(db, parent=tabs)
        self.loans_tab = LoansTab(db, parent=tabs)
        self.tools_tab = ToolsTab(db, parent=tabs)

        tabs.addTab(self.books_tab, "Books")
        tabs.addTab(self.users_tab, "Users")
        tabs.addTab(self.loans_tab, "Loans")
        tabs.addTab(self.tools_tab, "Tools")

        tabs.currentChanged.connect(self._on_tab_changed)
        outer.addWidget(tabs, 1)
        self.setCentralWidget(wrapper)

    def _on_tab_changed(self, _index: int) -> None:
        self.books_tab.refresh()
        self.users_tab.refresh()
        self.loans_tab.refresh()


def run_app(db_path: Path) -> int:
    db = Database(db_path)
    db.migrate()

    app = QtWidgets.QApplication([])
    app.setApplicationName("Library Management")
    apply_theme(app)

    win = MainWindow(db)
    win.show()
    return int(app.exec())

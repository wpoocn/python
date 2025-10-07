"""MD5 modification utility with PySide6 GUI.
"""
from __future__ import annotations

import random
import string
from pathlib import Path
from typing import Dict, Iterable, List

from PySide6.QtCore import (Qt, QRunnable, QThreadPool, Signal, Slot,
                            QObject)
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


CHUNK_SIZE = 1024 * 1024


def compute_md5(path: Path) -> str:
    """Compute the MD5 hash of a file."""
    import hashlib

    md5 = hashlib.md5()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


def mutate_file(path: Path) -> None:
    """Mutate a file slightly so that its MD5 changes."""
    # Append a random marker to avoid collisions and keep modification minimal.
    token = "\n#" + "".join(random.choices(string.ascii_letters + string.digits, k=16)) + "\n"
    with path.open("ab") as handle:
        handle.write(token.encode("utf-8"))


class WorkerSignals(QObject):
    file_processed = Signal(str, str)
    finished = Signal()


class Md5Loader(QRunnable):
    def __init__(self, paths: Iterable[Path]):
        super().__init__()
        self._paths = list(paths)
        self.signals = WorkerSignals()

    def run(self) -> None:
        for path in self._paths:
            if not path.is_file():
                continue
            try:
                digest = compute_md5(path)
            except OSError as exc:
                digest = f"读取失败: {exc}"
            self.signals.file_processed.emit(str(path), digest)
        self.signals.finished.emit()


class Md5Modifier(QRunnable):
    def __init__(self, paths: Iterable[Path]):
        super().__init__()
        self._paths = list(paths)
        self.signals = WorkerSignals()

    def run(self) -> None:
        for path in self._paths:
            if not path.is_file():
                continue
            try:
                mutate_file(path)
                digest = compute_md5(path)
            except OSError as exc:
                digest = f"修改失败: {exc}"
            self.signals.file_processed.emit(str(path), digest)
        self.signals.finished.emit()


class FileTableWidget(QTableWidget):
    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, 3, parent)
        self.setHorizontalHeaderLabels(["文件路径", "原始 MD5", "修改后 MD5"])
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTableWidget.DropOnly)
        self.setEditTriggers(QTableWidget.NoEditTriggers)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MD5 修改工具")
        self.resize(900, 600)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        # Path selector
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("请选择需要加载的文件夹")
        self.path_edit.setReadOnly(True)

        self.choose_button = QPushButton("选择文件夹")
        self.choose_button.clicked.connect(self.select_folder)

        self.load_button = QPushButton("读入文件")
        self.load_button.clicked.connect(self.load_files)

        path_layout.addWidget(QLabel("目标目录:"))
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(self.choose_button)
        path_layout.addWidget(self.load_button)

        layout.addLayout(path_layout)

        # Table
        self.table = FileTableWidget()
        layout.addWidget(self.table, 1)

        # Buttons
        button_layout = QHBoxLayout()
        self.modify_button = QPushButton("批量修改 MD5")
        self.modify_button.clicked.connect(self.modify_md5)
        self.clear_button = QPushButton("清空表格")
        self.clear_button.clicked.connect(self.clear_table)

        button_layout.addStretch(1)
        button_layout.addWidget(self.modify_button)
        button_layout.addWidget(self.clear_button)

        layout.addLayout(button_layout)

        self.setCentralWidget(central_widget)

        self.thread_pool = QThreadPool.globalInstance()
        self._rows: Dict[str, int] = {}

        self.table.files_dropped.connect(self.add_files)
        self.apply_styles()

    def apply_styles(self) -> None:
        self.clear_button.setObjectName("clearButton")

        palette = """
        QWidget {
            background-color: #1f1f24;
            color: #f0f0f3;
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            font-size: 15px;
        }
        QLineEdit {
            background-color: #2a2a32;
            border: 1px solid #3d3d47;
            border-radius: 6px;
            padding: 6px;
            selection-background-color: #4f5bd5;
            selection-color: white;
        }
        QLabel {
            font-weight: bold;
        }
        QPushButton {
            background-color: #4f5bd5;
            border: none;
            border-radius: 6px;
            padding: 8px 18px;
            color: white;
        }
        QPushButton:hover {
            background-color: #5f6be5;
        }
        QPushButton:pressed {
            background-color: #3f4bb5;
        }
        QPushButton#clearButton {
            background-color: #e05656;
        }
        QPushButton#clearButton:hover {
            background-color: #ef6a6a;
        }
        QPushButton#clearButton:pressed {
            background-color: #c64f4f;
        }
        QTableWidget {
            background-color: #262631;
            alternate-background-color: #2f2f3c;
            gridline-color: #3c3c4a;
            border: 1px solid #383848;
            border-radius: 8px;
        }
        QHeaderView::section {
            background-color: #343447;
            color: #f5f5f7;
            padding: 6px;
            border: none;
        }
        QTableWidget::item {
            padding: 6px;
        }
        """
        self.setStyleSheet(palette)

    @Slot()
    def select_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if directory:
            self.path_edit.setText(directory)
            self.load_files()

    @Slot()
    def load_files(self) -> None:
        directory = self.path_edit.text()
        if not directory:
            QMessageBox.information(self, "提示", "请先选择一个文件夹。")
            return

        folder = Path(directory)
        if not folder.exists():
            QMessageBox.warning(self, "错误", "所选目录不存在。")
            return

        files = [p for p in folder.rglob("*") if p.is_file()]
        if not files:
            QMessageBox.information(self, "提示", "该目录下没有文件。")
            return

        self.add_files([str(path) for path in files])

    @Slot()
    def modify_md5(self) -> None:
        if not self._rows:
            QMessageBox.information(self, "提示", "请先添加文件。")
            return

        paths = [Path(path) for path in self._rows.keys()]
        job = Md5Modifier(paths)
        job.signals.file_processed.connect(self.update_modified_digest)
        job.signals.finished.connect(lambda: QMessageBox.information(self, "完成", "MD5 修改完成。"))
        self.modify_button.setEnabled(False)
        job.signals.finished.connect(lambda: self.modify_button.setEnabled(True))
        self.thread_pool.start(job)

    @Slot()
    def clear_table(self) -> None:
        self.table.setRowCount(0)
        self._rows.clear()

    @Slot(list)
    def add_files(self, paths: List[str]) -> None:
        unique_paths = []
        for raw_path in paths:
            path = Path(raw_path).resolve()
            if not path.is_file():
                continue
            if str(path) in self._rows:
                continue
            unique_paths.append(path)

        if not unique_paths:
            return

        for path in unique_paths:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._rows[str(path)] = row
            self.set_table_item(row, 0, str(path))
            self.set_table_item(row, 1, "计算中…")
            self.set_table_item(row, 2, "-")

        job = Md5Loader(unique_paths)
        job.signals.file_processed.connect(self.update_original_digest)
        self.thread_pool.start(job)

    def set_table_item(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, column, item)

    @Slot(str, str)
    def update_original_digest(self, path: str, digest: str) -> None:
        row = self._rows.get(path)
        if row is None:
            return
        self.set_table_item(row, 1, digest)

    @Slot(str, str)
    def update_modified_digest(self, path: str, digest: str) -> None:
        row = self._rows.get(path)
        if row is None:
            return
        self.set_table_item(row, 2, digest)


def main() -> None:
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

# coding: utf-8
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout


class FileDropArea(QFrame):
    filesChanged = Signal(list)

    def __init__(
        self,
        accepted_suffixes: tuple[str, ...],
        hint_text: str,
        parent=None,
    ):
        super().__init__(parent)
        self.accepted_suffixes = {suffix.lower() for suffix in accepted_suffixes}
        self.paths: list[str] = []

        self.setObjectName("dropCard")
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("素材导入", self)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        hint = QLabel(hint_text, self)
        hint.setObjectName("sectionDescription")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.add_button = QPushButton("选择文件", self)
        self.add_button.clicked.connect(self.choose_files)
        button_row.addWidget(self.add_button)

        self.clear_button = QPushButton("清空列表", self)
        self.clear_button.clicked.connect(self.clear_files)
        button_row.addWidget(self.clear_button)

        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.tip_label = QLabel(self._build_drop_tip(), self)
        self.tip_label.setObjectName("dropTip")
        self.tip_label.setAlignment(Qt.AlignCenter)
        self.tip_label.setMinimumHeight(88)
        layout.addWidget(self.tip_label)

        self.file_list = QListWidget(self)
        self.file_list.setObjectName("fileList")
        self.file_list.setMinimumHeight(150)
        layout.addWidget(self.file_list)

        self._refresh_list()

    def _build_drop_tip(self) -> str:
        suffix_text = "、".join(sorted(self.accepted_suffixes))
        return f"将文件拖到这里，或点击上方按钮选择\n支持类型：{suffix_text}"

    def _is_supported(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.accepted_suffixes

    def _refresh_list(self) -> None:
        self.file_list.clear()
        if self.paths:
            self.file_list.addItems(self.paths)
            return
        self.file_list.addItem("暂无已选择文件")

    def _append_files(self, file_paths: list[str]) -> None:
        new_files = [path for path in file_paths if self._is_supported(path)]
        for path in new_files:
            if path not in self.paths:
                self.paths.append(path)

        self._refresh_list()
        self.filesChanged.emit(self.paths.copy())

    def choose_files(self) -> None:
        patterns = " ".join(f"*{suffix}" for suffix in sorted(self.accepted_suffixes))
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择素材文件",
            "",
            f"支持文件 ({patterns});;所有文件 (*.*)",
        )
        if file_paths:
            self._append_files(file_paths)

    def clear_files(self) -> None:
        self.paths.clear()
        self._refresh_list()
        self.filesChanged.emit([])

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self._append_files(paths)
        event.acceptProposedAction()

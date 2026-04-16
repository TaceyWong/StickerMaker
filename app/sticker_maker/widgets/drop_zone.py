# coding: utf-8
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


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

        title = QLabel("素材", self)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.hint = QLabel(hint_text, self)
        self.hint.setObjectName("sectionDescription")
        self.hint.setWordWrap(True)
        self.hint.setAcceptDrops(False)
        layout.addWidget(self.hint)

        self.clear_button = QPushButton("清空", self)
        self.clear_button.clicked.connect(self.clear_files)
        layout.addWidget(self.clear_button, 0, Qt.AlignRight)

        self.tip_label = QLabel(self._build_drop_tip(), self)
        self.tip_label.setObjectName("dropTip")
        self.tip_label.setAlignment(Qt.AlignCenter)
        self.tip_label.setMinimumHeight(88)
        self.tip_label.setCursor(Qt.PointingHandCursor)
        self.tip_label.setAcceptDrops(False)
        layout.addWidget(self.tip_label)

        self.file_list = QListWidget(self)
        self.file_list.setObjectName("fileList")
        self.file_list.setMinimumHeight(150)
        self.file_list.setAcceptDrops(False)
        self.file_list.viewport().setAcceptDrops(False)
        self.file_list.itemDoubleClicked.connect(self._preview_selected_item)
        layout.addWidget(self.file_list)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.preview_button = QPushButton("预览", self)
        self.preview_button.clicked.connect(self.preview_selected)
        action_row.addWidget(self.preview_button)

        self.up_button = QPushButton("上移", self)
        self.up_button.clicked.connect(self.move_selected_up)
        action_row.addWidget(self.up_button)

        self.down_button = QPushButton("下移", self)
        self.down_button.clicked.connect(self.move_selected_down)
        action_row.addWidget(self.down_button)

        self.remove_button = QPushButton("删除选中", self)
        self.remove_button.clicked.connect(self.remove_selected)
        action_row.addWidget(self.remove_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self._refresh_list()

    def _build_drop_tip(self) -> str:
        suffix_text = "、".join(sorted(self.accepted_suffixes))
        return f"拖入文件到此处，或点击此区域选择\n支持类型：{suffix_text}"

    def _is_supported(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.accepted_suffixes

    def _refresh_list(self) -> None:
        self.file_list.clear()
        if self.paths:
            self.file_list.addItems(self.paths)
            self._sync_action_buttons(True)
            return
        self.file_list.addItem("暂无文件")
        self._sync_action_buttons(False)

    def _sync_action_buttons(self, enabled: bool) -> None:
        self.preview_button.setEnabled(enabled)
        self.up_button.setEnabled(enabled)
        self.down_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)

    def _append_files(self, file_paths: list[str]) -> None:
        new_files = [path for path in file_paths if self._is_supported(path)]
        for path in new_files:
            if path not in self.paths:
                self.paths.append(path)

        self._refresh_list()
        self.filesChanged.emit(self.paths.copy())

    def _extract_supported_local_paths(self, event: QDropEvent | QDragEnterEvent | QDragMoveEvent) -> list[str]:
        if not event.mimeData().hasUrls():
            return []
        local_paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        return [path for path in local_paths if self._is_supported(path)]

    def _set_drag_state(self, active: bool) -> None:
        self.setProperty("dragOver", active)
        self.tip_label.setProperty("dragOver", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.tip_label.style().unpolish(self.tip_label)
        self.tip_label.style().polish(self.tip_label)

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

    def _selected_index(self) -> int:
        if not self.paths:
            return -1
        return self.file_list.currentRow()

    def _preview_selected_item(self, _item: QListWidgetItem | None = None) -> None:
        self.preview_selected()

    def preview_selected(self) -> None:
        idx = self._selected_index()
        if idx < 0 or idx >= len(self.paths):
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.paths[idx]))

    def remove_selected(self) -> None:
        idx = self._selected_index()
        if idx < 0 or idx >= len(self.paths):
            return
        self.paths.pop(idx)
        self._refresh_list()
        if self.paths:
            self.file_list.setCurrentRow(min(idx, len(self.paths) - 1))
        self.filesChanged.emit(self.paths.copy())

    def move_selected_up(self) -> None:
        idx = self._selected_index()
        if idx <= 0 or idx >= len(self.paths):
            return
        self.paths[idx - 1], self.paths[idx] = self.paths[idx], self.paths[idx - 1]
        self._refresh_list()
        self.file_list.setCurrentRow(idx - 1)
        self.filesChanged.emit(self.paths.copy())

    def move_selected_down(self) -> None:
        idx = self._selected_index()
        if idx < 0 or idx >= len(self.paths) - 1:
            return
        self.paths[idx + 1], self.paths[idx] = self.paths[idx], self.paths[idx + 1]
        self._refresh_list()
        self.file_list.setCurrentRow(idx + 1)
        self.filesChanged.emit(self.paths.copy())

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._extract_supported_local_paths(event):
            self._set_drag_state(True)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: N802
        if self._extract_supported_local_paths(event):
            self._set_drag_state(True)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # noqa: N802
        self._set_drag_state(False)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self._set_drag_state(False)
        paths = self._extract_supported_local_paths(event)
        self._append_files(paths)
        if paths:
            event.acceptProposedAction()
            return
        event.ignore()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.tip_label.geometry().contains(event.pos()):
            self.choose_files()
            event.accept()
            return
        super().mousePressEvent(event)

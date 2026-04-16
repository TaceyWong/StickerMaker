# coding: utf-8
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QMouseEvent, QPixmap
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

        self.file_list = QListWidget(self)
        self.file_list.setObjectName("fileList")
        self.file_list.setMinimumHeight(150)
        self.file_list.setAcceptDrops(False)
        self.file_list.viewport().setAcceptDrops(False)
        self.file_list.itemDoubleClicked.connect(self._preview_selected_item)
        self.file_list.currentRowChanged.connect(self._update_preview_from_selection)

        preview_frame = QFrame(self)
        preview_frame.setObjectName("previewFrame")
        preview_frame.setFixedWidth(240)

        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(10)

        preview_title = QLabel("预览", preview_frame)
        preview_title.setObjectName("previewTitle")
        preview_title.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(preview_title)

        self.preview_label = QLabel("无预览", preview_frame)
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(160)
        self.preview_label.setCursor(Qt.PointingHandCursor)
        self.preview_label.installEventFilter(self)
        preview_layout.addWidget(self.preview_label)

        list_and_preview = QHBoxLayout()
        list_and_preview.setSpacing(12)
        list_and_preview.addWidget(self.file_list, 1)
        list_and_preview.addWidget(preview_frame, 0)
        layout.addLayout(list_and_preview)

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

        self.clear_button = QPushButton("清空", self)
        self.clear_button.clicked.connect(self.clear_files)
        action_row.addWidget(self.clear_button)

        self.add_button = QPushButton("添加", self)
        self.add_button.clicked.connect(self.choose_files)
        action_row.addWidget(self.add_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self._refresh_list()

    def _build_drop_tip(self) -> str:
        # 保留方法接口，当前未使用（历史虚线提示位）。
        suffix_text = "、".join(sorted(self.accepted_suffixes))
        return f"支持类型：{suffix_text}"

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
        self.style().unpolish(self)
        self.style().polish(self)

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

    def _update_preview_from_selection(self, _row: int) -> None:
        idx = self._selected_index()
        if idx < 0 or idx >= len(self.paths):
            self.preview_label.setText("无预览")
            self.preview_label.setPixmap(QPixmap())
            return

        path = self.paths[idx]
        suffix = Path(path).suffix.lower()
        img_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
        if suffix not in img_suffixes:
            self.preview_label.setText(f"不支持预览\n{suffix or '文件'}")
            self.preview_label.setPixmap(QPixmap())
            return

        pix = QPixmap(path)
        if pix.isNull():
            self.preview_label.setText("加载失败")
            self.preview_label.setPixmap(QPixmap())
            return

        target = self.preview_label.size()
        if target.width() <= 0 or target.height() <= 0:
            target = self.preview_label.minimumSize()

        scaled = pix.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setText("")
        self.preview_label.setPixmap(scaled)

    def eventFilter(self, watched, event) -> bool:  # noqa: ANN001
        if watched is self.preview_label and event.type() == QEvent.MouseButtonPress:
            self.preview_selected()
            return True
        return super().eventFilter(watched, event)

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
        super().mousePressEvent(event)

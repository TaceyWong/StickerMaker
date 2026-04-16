# coding: utf-8
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout


class OutputPreviewDialog(QDialog):
    def __init__(self, files: list[Path], parent=None):
        super().__init__(parent)
        self._files = files
        self._movie: QMovie | None = None

        self.setWindowTitle("输出预览")
        self.resize(980, 640)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        main = QHBoxLayout()
        main.setSpacing(12)
        root.addLayout(main, 1)

        self.file_list = QListWidget(self)
        self.file_list.setMinimumWidth(320)
        for path in self._files:
            self.file_list.addItem(path.name)
        self.file_list.currentRowChanged.connect(self._on_selected)
        main.addWidget(self.file_list, 0)

        right = QVBoxLayout()
        right.setSpacing(8)
        main.addLayout(right, 1)

        self.path_label = QLabel("未选择文件", self)
        self.path_label.setWordWrap(True)
        right.addWidget(self.path_label)

        self.preview_label = QLabel("无预览", self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(520)
        self.preview_label.setStyleSheet(
            "background:#f8f9fc;border:1px dashed #c3ccdb;border-radius:10px;color:#506176;"
        )
        right.addWidget(self.preview_label, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        close_btn = QPushButton("关闭", self)
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)
        root.addLayout(actions)

        if self._files:
            self.file_list.setCurrentRow(0)

    def _clear_movie(self) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None

    def _on_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._files):
            self.path_label.setText("未选择文件")
            self.preview_label.setText("无预览")
            self.preview_label.setPixmap(QPixmap())
            self._clear_movie()
            return

        path = self._files[row]
        self.path_label.setText(str(path))
        suffix = path.suffix.lower()

        if suffix == ".gif":
            self._clear_movie()
            movie = QMovie(str(path))
            if not movie.isValid():
                self.preview_label.setText("GIF 加载失败")
                self.preview_label.setPixmap(QPixmap())
                return
            movie.setScaledSize(self.preview_label.size() * 0.95)
            self.preview_label.setMovie(movie)
            movie.start()
            self._movie = movie
            return

        self._clear_movie()
        pix = QPixmap(str(path))
        if pix.isNull():
            self.preview_label.setText("图片加载失败")
            self.preview_label.setPixmap(QPixmap())
            return
        scaled = pix.scaled(
            self.preview_label.size() * 0.95,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview_label.setText("")
        self.preview_label.setPixmap(scaled)

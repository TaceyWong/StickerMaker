# coding: utf-8
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


class OutputPreviewDialog(QDialog):
    def __init__(self, files: list[Path], parent=None):
        super().__init__(parent)
        self._png_files = sorted([p for p in files if p.suffix.lower() == ".png"], key=lambda x: x.name)
        self._gif_files = sorted([p for p in files if p.suffix.lower() == ".gif"], key=lambda x: x.name)
        self._movie: QMovie | None = None

        self.setWindowTitle("输出预览")
        self.resize(1080, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        main = QHBoxLayout()
        main.setSpacing(12)
        root.addLayout(main, 1)

        # 左侧：可折叠树形文件列表（分 PNG/GIF）
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(320)
        main.addWidget(self.tree, 0)

        self._png_root = QTreeWidgetItem(self.tree, ["PNG"])
        self._gif_root = QTreeWidgetItem(self.tree, ["GIF"])
        self._png_root.setExpanded(True)
        self._gif_root.setExpanded(True)

        for p in self._png_files:
            item = QTreeWidgetItem(self._png_root, [p.name])
            item.setData(0, Qt.UserRole, str(p))

        for p in self._gif_files:
            item = QTreeWidgetItem(self._gif_root, [p.name])
            item.setData(0, Qt.UserRole, str(p))

        self.tree.expandAll()
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)

        right = QVBoxLayout()
        right.setSpacing(8)
        main.addLayout(right, 1)

        self.path_label = QLabel("未选择文件", self)
        self.path_label.setWordWrap(True)
        right.addWidget(self.path_label)

        # 右侧：原尺寸展示（不缩放），配合滚动条浏览大图/长动图
        self.preview_scroll = QScrollArea(self)
        # 固定使用原图/原 gif 尺寸展示：让滚动条负责浏览
        self.preview_scroll.setWidgetResizable(False)
        self.preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.preview_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right.addWidget(self.preview_scroll, 1)

        self.preview_container = QLabel("无预览", self)
        self.preview_container.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.preview_container.setStyleSheet(
            "background:#f8f9fc;border:1px dashed #c3ccdb;border-radius:10px;color:#506176;"
        )
        self.preview_scroll.setWidget(self.preview_container)

        actions = QHBoxLayout()
        actions.addStretch(1)
        close_btn = QPushButton("关闭", self)
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)
        root.addLayout(actions)

        # 自动选中第一项
        if self._png_files:
            self.tree.setCurrentItem(self._png_root.child(0))
        elif self._gif_files:
            self.tree.setCurrentItem(self._gif_root.child(0))

    def _clear_movie(self) -> None:
        if self._movie is None:
            self.preview_container.clear()
            return
        self._movie.stop()
        self._movie.deleteLater()
        self._movie = None
        self.preview_container.setMovie(None)
        self.preview_container.clear()

    def _show_pixmap_original(self, path: Path) -> None:
        self._clear_movie()
        pix = QPixmap(str(path))
        if pix.isNull():
            self.preview_container.setText("图片加载失败")
            return

        # 原尺寸：不对 pixmap 做 scaled()；用滚动条来浏览
        self.preview_container.setText("")
        self.preview_container.setPixmap(pix)
        self.preview_container.setFixedSize(pix.size())

    def _show_gif_original(self, path: Path) -> None:
        self._clear_movie()
        movie = QMovie(str(path))
        if not movie.isValid():
            self.preview_container.setText("GIF 加载失败")
            return

        # 原尺寸：不调用 setScaledSize
        movie.jumpToFrame(0)
        frame_size = movie.frameRect().size()
        if frame_size.width() > 0 and frame_size.height() > 0:
            self.preview_container.setFixedSize(frame_size)

        self.preview_container.setText("")
        self.preview_container.setMovie(movie)
        self._movie = movie
        movie.start()

    def _on_tree_selection_changed(self) -> None:
        items = self.tree.selectedItems()
        if not items:
            self.path_label.setText("未选择文件")
            self._clear_movie()
            self.preview_container.setText("无预览")
            return

        item = items[0]
        path_str = item.data(0, Qt.UserRole)
        if not path_str:
            self._clear_movie()
            self.preview_container.setText("无预览")
            return

        path = Path(path_str)
        self.path_label.setText(str(path))

        if path.suffix.lower() == ".gif":
            self._show_gif_original(path)
        else:
            self._show_pixmap_original(path)

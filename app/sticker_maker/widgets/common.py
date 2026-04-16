# coding: utf-8
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ScrollPage(QFrame):
    """A scrollable page used as a sub interface in the Fluent window."""

    def __init__(self, route_key: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName(route_key)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root_layout.addWidget(self.scroll_area)

        self.container = QWidget(self.scroll_area)
        self.container.setObjectName("pageContainer")
        self.scroll_area.setWidget(self.container)

        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(18)


class TagChip(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("tagChip")


class SectionCard(QFrame):
    """Simple card with title, optional subtitle, and a body layout."""

    def __init__(
        self,
        title: str,
        description: str = "",
        parent: QWidget | None = None,
        object_name: str = "sectionCard",
    ):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(14)

        title_label = QLabel(title, self)
        title_label.setObjectName("sectionTitle")
        self._layout.addWidget(title_label)

        if description:
            description_label = QLabel(description, self)
            description_label.setObjectName("sectionDescription")
            description_label.setWordWrap(True)
            self._layout.addWidget(description_label)

        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(12)
        self._layout.addLayout(self.body_layout)


class HeroCard(SectionCard):
    def __init__(
        self,
        title: str,
        description: str,
        tags: tuple[str, ...],
        parent: QWidget | None = None,
    ):
        super().__init__(title, description, parent=parent, object_name="heroCard")

        tag_row = QHBoxLayout()
        tag_row.setSpacing(8)
        tag_row.setContentsMargins(0, 0, 0, 0)

        for tag in tags:
            tag_row.addWidget(TagChip(tag, self))

        tag_row.addStretch(1)
        self.body_layout.addLayout(tag_row)


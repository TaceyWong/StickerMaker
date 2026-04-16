# coding: utf-8
import sys

from PySide6.QtWidgets import QApplication

from sticker_maker.main_window import StickerMakerWindow


def main() -> int:
    """Start the desktop application."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("StickerMaker · 表情包制作")

    window = StickerMakerWindow()
    window.show()
    return app.exec()

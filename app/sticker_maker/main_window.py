# coding: utf-8
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, NavigationItemPosition
from qfluentwidgets import FluentIcon as FIF

from sticker_maker.data.modes import DYNAMIC_MODE, STATIC_MODE, VIDEO_MODE
from sticker_maker.views.mode_workspace_view import ModeWorkspaceView
from sticker_maker.views.settings_view import SettingsView


class StickerMakerWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        self.static_view = ModeWorkspaceView(STATIC_MODE, self)
        self.dynamic_view = ModeWorkspaceView(DYNAMIC_MODE, self)
        self.video_view = ModeWorkspaceView(VIDEO_MODE, self)
        self.settings_view = SettingsView(self)

        self._init_navigation()
        self._init_window()
        self._apply_style()

    def _init_navigation(self) -> None:
        self.addSubInterface(self.static_view, FIF.ALBUM, "成套静态")
        self.addSubInterface(self.dynamic_view, FIF.VIDEO, "单个动态")
        self.addSubInterface(self.video_view, FIF.FOLDER, "视频成套动态")
        self.addSubInterface(self.settings_view, FIF.SETTING, "设置", NavigationItemPosition.BOTTOM)

    def _init_window(self) -> None:
        self.resize(1280, 860)
        self.setMinimumWidth(1080)
        self.setWindowTitle("StickerMaker")
        self.setWindowIcon(QIcon("resource/shoko.png"))

        desktop = QApplication.screens()[0].availableGeometry()
        self.move(
            desktop.width() // 2 - self.width() // 2,
            desktop.height() // 2 - self.height() // 2,
        )

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget#pageContainer {
                background: #f4f6fa;
            }
            QFrame#sectionCard, QFrame#dropCard, QFrame#workflowStep {
                background: #ffffff;
                border: 1px solid #e1e6ef;
                border-radius: 14px;
            }
            QLabel#sectionTitle {
                color: #10243d;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#sectionDescription, QLabel#fieldDescription, QLabel#stepDescription, QLabel#stepDetail {
                color: #506176;
                font-size: 12px;
            }
            QLabel#dropTip {
                color: #506176;
                background: #f8f9fc;
                border: 1px dashed #c3ccdb;
                border-radius: 12px;
                font-size: 12px;
            }
            QListWidget#fileList, QTextEdit {
                background: #f8f9fc;
                border: 1px solid #d8dfec;
                border-radius: 12px;
                padding: 8px;
            }
            QLineEdit, QComboBox {
                min-height: 34px;
                border: 1px solid #d8dfec;
                border-radius: 8px;
                padding: 0 10px;
                background: #ffffff;
            }
            QPushButton {
                min-height: 34px;
                border: 1px solid #ccd6e6;
                border-radius: 8px;
                padding: 0 14px;
                background: #f7f9fc;
                color: #213650;
            }
            QPushButton:hover {
                background: #ecf1f8;
            }
            QPushButton#primaryButton {
                background: #2f6fed;
                border: 1px solid #2f6fed;
                color: #ffffff;
                font-weight: 600;
            }
            QPushButton#primaryButton:hover {
                background: #255ed0;
            }
            QCheckBox {
                color: #10243d;
                min-height: 28px;
            }
            QLabel#statusLabel {
                color: #2f4e72;
                font-size: 12px;
            }
            """
        )

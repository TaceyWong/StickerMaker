# coding: utf-8
import os

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from sticker_maker.data.modes import REMBG_MODEL_CHOICES, TECH_STACK
from sticker_maker.widgets.common import ScrollPage, SectionCard


class SettingsView(ScrollPage):
    def __init__(self, parent=None):
        super().__init__("settings", parent)

        about = SectionCard(
            "关于",
            "功能与流程说明见项目根目录下的 README。",
            self.container,
        )
        for line in (
            "三种模式对应 README 中的模式一～三：成套静态、单张动态 GIF、视频成套动态。",
            "去水印能力尚在开发；勾选相关选项时会在日志中提示。",
            "去背景使用 rembg；权重文件放在 app/resource/models（处理任务开始时会设置 U2NET_HOME，缺失时首次需联网下载）。",
            "视频模式依赖本机已安装 ffmpeg，且可在命令行中直接调用。",
        ):
            label = QLabel(line, about)
            label.setObjectName("sectionDescription")
            label.setWordWrap(True)
            about.body_layout.addWidget(label)

        self.content_layout.addWidget(about)

        rembg = SectionCard(
            "去背景模型",
            "工作区不再提供模型选择，这里统一配置；默认 BRIA RMBG 2.0。",
            self.container,
        )
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.model_combo = QComboBox(rembg)
        for choice in REMBG_MODEL_CHOICES:
            self.model_combo.addItem(choice.label, choice.value)
        default_model = os.getenv("STICKERMAKER_RMBG_MODEL", "bria-rmbg")
        idx = self.model_combo.findData(default_model)
        self.model_combo.setCurrentIndex(max(idx, 0))
        row.addWidget(self.model_combo)

        save_btn = QPushButton("应用", rembg)
        save_btn.clicked.connect(self._apply_model_setting)
        row.addWidget(save_btn)
        row.addStretch(1)
        box = QWidget(rembg)
        box.setLayout(row)
        rembg.body_layout.addWidget(box)
        self.content_layout.addWidget(rembg)

        deps = SectionCard(
            "依赖与技术",
            "与 README「技术栈」一致，便于排查环境。",
            self.container,
        )
        for item in TECH_STACK:
            label = QLabel(f"· {item}", deps)
            label.setObjectName("sectionDescription")
            label.setWordWrap(True)
            deps.body_layout.addWidget(label)

        self.content_layout.addWidget(deps)
        self.content_layout.addStretch(1)

    def _apply_model_setting(self) -> None:
        os.environ["STICKERMAKER_RMBG_MODEL"] = str(self.model_combo.currentData())

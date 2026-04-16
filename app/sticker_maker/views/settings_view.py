# coding: utf-8
import os

from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

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

        ai = SectionCard(
            "AI 生成配置",
            "AI 弹窗内不再填写连接参数；统一在这里维护。",
            self.container,
        )
        ai_grid = QGridLayout()
        ai_grid.setContentsMargins(0, 0, 0, 0)
        ai_grid.setHorizontalSpacing(10)
        ai_grid.setVerticalSpacing(8)

        # OpenAI 兼容
        self.ai_openai_base = QLineEdit(ai)
        self.ai_openai_base.setText(os.getenv("STICKERMAKER_AI_OPENAI_BASE_URL", "https://api.openai.com/v1"))
        self.ai_openai_model = QLineEdit(ai)
        self.ai_openai_model.setText(os.getenv("STICKERMAKER_AI_OPENAI_MODEL", "gpt-image-1"))
        self.ai_openai_key = QLineEdit(ai)
        self.ai_openai_key.setText(os.getenv("STICKERMAKER_AI_OPENAI_API_KEY", ""))
        self.ai_openai_key.setEchoMode(QLineEdit.Password)

        # 千问（用户名/密码）
        self.ai_qwen_base = QLineEdit(ai)
        self.ai_qwen_base.setText(os.getenv("STICKERMAKER_AI_QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
        self.ai_qwen_model = QLineEdit(ai)
        self.ai_qwen_model.setText(os.getenv("STICKERMAKER_AI_QWEN_MODEL", "qwen-image"))
        self.ai_qwen_user = QLineEdit(ai)
        self.ai_qwen_user.setText(os.getenv("STICKERMAKER_AI_QWEN_USERNAME", ""))
        self.ai_qwen_pwd = QLineEdit(ai)
        self.ai_qwen_pwd.setText(os.getenv("STICKERMAKER_AI_QWEN_PASSWORD", ""))
        self.ai_qwen_pwd.setEchoMode(QLineEdit.Password)

        # Banana
        self.ai_banana_base = QLineEdit(ai)
        self.ai_banana_base.setText(os.getenv("STICKERMAKER_AI_BANANA_BASE_URL", ""))
        self.ai_banana_model = QLineEdit(ai)
        self.ai_banana_model.setText(os.getenv("STICKERMAKER_AI_BANANA_MODEL", ""))
        self.ai_banana_key = QLineEdit(ai)
        self.ai_banana_key.setText(os.getenv("STICKERMAKER_AI_BANANA_API_KEY", ""))
        self.ai_banana_key.setEchoMode(QLineEdit.Password)

        r = 0
        ai_grid.addWidget(QLabel("OpenAI Base URL", ai), r, 0)
        ai_grid.addWidget(self.ai_openai_base, r, 1)
        ai_grid.addWidget(QLabel("OpenAI Model", ai), r, 2)
        ai_grid.addWidget(self.ai_openai_model, r, 3)
        r += 1
        ai_grid.addWidget(QLabel("OpenAI API Key", ai), r, 0)
        ai_grid.addWidget(self.ai_openai_key, r, 1, 1, 3)
        r += 1
        ai_grid.addWidget(QLabel("千问 Base URL", ai), r, 0)
        ai_grid.addWidget(self.ai_qwen_base, r, 1)
        ai_grid.addWidget(QLabel("千问 Model", ai), r, 2)
        ai_grid.addWidget(self.ai_qwen_model, r, 3)
        r += 1
        ai_grid.addWidget(QLabel("千问用户名", ai), r, 0)
        ai_grid.addWidget(self.ai_qwen_user, r, 1)
        ai_grid.addWidget(QLabel("千问密码", ai), r, 2)
        ai_grid.addWidget(self.ai_qwen_pwd, r, 3)
        r += 1
        ai_grid.addWidget(QLabel("Banana Base URL", ai), r, 0)
        ai_grid.addWidget(self.ai_banana_base, r, 1)
        ai_grid.addWidget(QLabel("Banana Model", ai), r, 2)
        ai_grid.addWidget(self.ai_banana_model, r, 3)
        r += 1
        ai_grid.addWidget(QLabel("Banana API Key", ai), r, 0)
        ai_grid.addWidget(self.ai_banana_key, r, 1, 1, 3)
        r += 1

        ai_box = QWidget(ai)
        ai_box.setLayout(ai_grid)
        ai.body_layout.addWidget(ai_box)

        ai_hint = QLabel("本地豆包使用本地浏览器 RPA，不需要配置；在 AI 弹窗直接选择即可。", ai)
        ai_hint.setObjectName("sectionDescription")
        ai_hint.setWordWrap(True)
        ai.body_layout.addWidget(ai_hint)

        ai_btn_row = QHBoxLayout()
        ai_btn_row.setContentsMargins(0, 0, 0, 0)
        ai_btn_row.setSpacing(8)
        ai_apply_btn = QPushButton("应用 AI 配置", ai)
        ai_apply_btn.clicked.connect(self._apply_ai_settings)
        ai_btn_row.addWidget(ai_apply_btn)
        ai_btn_row.addStretch(1)
        ai_btn_box = QWidget(ai)
        ai_btn_box.setLayout(ai_btn_row)
        ai.body_layout.addWidget(ai_btn_box)
        self.content_layout.addWidget(ai)

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

    def _apply_ai_settings(self) -> None:
        os.environ["STICKERMAKER_AI_OPENAI_BASE_URL"] = self.ai_openai_base.text().strip()
        os.environ["STICKERMAKER_AI_OPENAI_MODEL"] = self.ai_openai_model.text().strip()
        os.environ["STICKERMAKER_AI_OPENAI_API_KEY"] = self.ai_openai_key.text().strip()
        os.environ["STICKERMAKER_AI_QWEN_BASE_URL"] = self.ai_qwen_base.text().strip()
        os.environ["STICKERMAKER_AI_QWEN_MODEL"] = self.ai_qwen_model.text().strip()
        os.environ["STICKERMAKER_AI_QWEN_USERNAME"] = self.ai_qwen_user.text().strip()
        os.environ["STICKERMAKER_AI_QWEN_PASSWORD"] = self.ai_qwen_pwd.text()
        os.environ["STICKERMAKER_AI_BANANA_BASE_URL"] = self.ai_banana_base.text().strip()
        os.environ["STICKERMAKER_AI_BANANA_MODEL"] = self.ai_banana_model.text().strip()
        os.environ["STICKERMAKER_AI_BANANA_API_KEY"] = self.ai_banana_key.text().strip()

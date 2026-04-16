# coding: utf-8
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import MessageBox

from sticker_maker.workers.ai_generate_worker import AIGenerateWorker


class AIGenerateDialog(QDialog):
    def __init__(self, on_generated: Callable[[list[str]], None], parent=None):
        super().__init__(parent)
        self._on_generated = on_generated
        self._worker: AIGenerateWorker | None = None

        self.setWindowTitle("AI 生成素材")
        self.resize(820, 640)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 0)

        tab_local = QWidget(self)
        tab_openai = QWidget(self)
        self.tabs.addTab(tab_local, "本地豆包模式")
        self.tabs.addTab(tab_openai, "OpenAI 兼容 API")

        # ---------- 本地豆包 ----------
        local_layout = QVBoxLayout(tab_local)
        local_layout.setContentsMargins(12, 12, 12, 12)

        self.local_base_url = QLineEdit(tab_local)
        self.local_base_url.setText("http://127.0.0.1:8000/v1")
        self.local_base_url.setPlaceholderText("例如：http://127.0.0.1:8000/v1")
        local_layout.addWidget(_labeled("Base URL", self.local_base_url))

        self.local_api_key = QLineEdit(tab_local)
        self.local_api_key.setPlaceholderText("如需鉴权可填写；留空则不带 Bearer")
        local_layout.addWidget(_labeled("API Key（可选）", self.local_api_key))

        self.local_model = QLineEdit(tab_local)
        self.local_model.setText("doubao-image")
        self.local_model.setPlaceholderText("图像模型名")
        local_layout.addWidget(_labeled("Model", self.local_model))

        local_layout.addStretch(1)

        # ---------- OpenAI 兼容 ----------
        openai_layout = QVBoxLayout(tab_openai)
        openai_layout.setContentsMargins(12, 12, 12, 12)

        self.openai_base_url = QLineEdit(tab_openai)
        self.openai_base_url.setText("https://api.openai.com/v1")
        self.openai_base_url.setPlaceholderText("例如：https://api.openai.com/v1")
        openai_layout.addWidget(_labeled("Base URL", self.openai_base_url))

        # 兼容老版本 PySide6：没有 QPasswordLineEdit 时用 QLineEdit + 密码回显模式实现
        self.openai_api_key = QLineEdit(tab_openai)
        self.openai_api_key.setPlaceholderText("OpenAI API Key")
        self.openai_api_key.setEchoMode(QLineEdit.Password)
        openai_layout.addWidget(_labeled("API Key", self.openai_api_key))

        self.openai_model = QLineEdit(tab_openai)
        self.openai_model.setText("gpt-image-1")
        self.openai_model.setPlaceholderText("图像模型名")
        openai_layout.addWidget(_labeled("Model", self.openai_model))

        openai_layout.addStretch(1)

        # ---------- Prompt ----------
        prompt_card = QWidget(self)
        prompt_layout = QVBoxLayout(prompt_card)
        prompt_layout.setContentsMargins(0, 0, 0, 0)
        prompt_layout.setSpacing(8)
        root.addWidget(prompt_card, 1)

        tpl_row = QHBoxLayout()
        tpl_row.setSpacing(10)
        prompt_layout.addLayout(tpl_row)

        tpl_row.addWidget(QLabel("提示词模板：", prompt_card))
        self.template_combo = QComboBox(prompt_card)
        self.template_combo.addItem("自定义（不套模板）", "")
        self.template_combo.addItem("二次元表情包风格（默认）", "二次元表情包风格：{prompt}")
        self.template_combo.addItem("写实人像表情包风格", "写实人像表情包风格：{prompt}")
        self.template_combo.addItem("萌系可爱贴纸风格", "萌系可爱贴纸风格：{prompt}")
        self.template_combo.setCurrentIndex(1)
        tpl_row.addWidget(self.template_combo, 1)

        self.prompt_edit = QPlainTextEdit(prompt_card)
        self.prompt_edit.setPlaceholderText("在这里输入完整提示词（如：生成一张透明底的 3x3 宫格拼版图，每格一个表情）")
        prompt_layout.addWidget(self.prompt_edit, 1)

        size_row = QHBoxLayout()
        size_row.setSpacing(10)
        prompt_layout.addLayout(size_row)

        size_row.addWidget(QLabel("生成尺寸：", prompt_card))
        self.size_combo = QComboBox(prompt_card)
        self.size_combo.addItems(["512x512", "1024x1024"])
        self.size_combo.setCurrentText("1024x1024")
        size_row.addWidget(self.size_combo, 1)

        size_row.addWidget(QLabel("生成张数：", prompt_card))
        self.count_spin = QSpinBox(prompt_card)
        self.count_spin.setRange(1, 4)
        self.count_spin.setValue(1)
        size_row.addWidget(self.count_spin, 1)

        # ---------- Progress ----------
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        root.addLayout(progress_row)

        self.progress_label = QLabel("就绪", self)
        progress_row.addWidget(self.progress_label, 0)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        progress_row.addWidget(self.progress_bar, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        root.addLayout(btn_row)

        self.generate_btn = QPushButton("生成", self)
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        btn_row.addWidget(self.generate_btn)

        self.cancel_btn = QPushButton("取消", self)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch(1)

        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        self._on_template_changed()  # 初始化 prompt

    def _on_template_changed(self) -> None:
        tpl = self.template_combo.currentData()
        # 只有在用户仍在“自动生成模板”状态时才覆盖内容；避免打断手动编辑。
        # 这里用一个简单策略：如果编辑框为空或仍等于上次模板生成结果，则覆盖。
        current = self.prompt_edit.toPlainText().strip()
        if tpl is None or tpl == "":
            return
        # 只在用户还没输入任何内容时用模板填充；否则不硬覆盖。
        if current:
            return
        self.prompt_edit.setPlainText(tpl.format(prompt="生成一张透明底的宫格拼版图，每格一个表情。"))

    def _set_busy(self, busy: bool) -> None:
        self.generate_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(not busy)
        self.tabs.setEnabled(not busy)
        self.prompt_edit.setEnabled(not busy)
        self.size_combo.setEnabled(not busy)
        self.count_spin.setEnabled(not busy)

    def _on_generate_clicked(self) -> None:
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            dialog = MessageBox("提示", "请先填写提示词。", self)
            dialog.yesButton.setText("好的")
            dialog.cancelButton.hide()
            dialog.exec()
            return

        if self.tabs.currentIndex() == 0:
            base_url = self.local_base_url.text().strip()
            api_key = self.local_api_key.text().strip()
            model = self.local_model.text().strip()
        else:
            base_url = self.openai_base_url.text().strip()
            api_key = self.openai_api_key.text().strip()
            model = self.openai_model.text().strip()
            if not api_key:
                dialog = MessageBox("提示", "OpenAI 模式下 API Key 不能为空。", self)
                dialog.yesButton.setText("好的")
                dialog.cancelButton.hide()
                dialog.exec()
                return

        if not base_url or not model:
            dialog = MessageBox("提示", "Base URL 和 Model 都不能为空。", self)
            dialog.yesButton.setText("好的")
            dialog.cancelButton.hide()
            dialog.exec()
            return

        count = int(self.count_spin.value())
        size = str(self.size_combo.currentText())

        repo_root = Path(__file__).resolve().parents[3]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = repo_root / "output" / "ai_generated" / ts

        self.progress_bar.setRange(0, count)
        self.progress_bar.setValue(0)
        self.progress_label.setText("开始生成…")

        self._set_busy(True)
        self._worker = AIGenerateWorker(
            service_base_url=base_url,
            service_api_key=api_key,
            service_model=model,
            prompt=prompt,
            size=size,
            count=count,
            output_dir=output_dir,
            parent=self,
        )
        self._worker.logMessage.connect(self._on_worker_log)
        self._worker.progressValue.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.start()

    def _on_worker_log(self, message: str) -> None:
        self.progress_label.setText(message)

    def _on_worker_progress(self, done: int) -> None:
        self.progress_bar.setValue(done)

    def _on_worker_finished(self, paths_obj: object) -> None:
        self._set_busy(False)
        try:
            paths = paths_obj if isinstance(paths_obj, list) else list(paths_obj)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            paths = []

        if not paths:
            dialog = MessageBox("提示", "生成完成，但没有得到任何图片。", self)
            dialog.yesButton.setText("好的")
            dialog.cancelButton.hide()
            dialog.exec()
            return

        self.progress_label.setText("生成完成，已加入素材列表。")
        if callable(self._on_generated):
            self._on_generated(paths)  # type: ignore[misc]
        self.accept()

    def _on_worker_failed(self, error_message: str) -> None:
        self._set_busy(False)
        dialog = MessageBox("生成失败", error_message, self)
        dialog.yesButton.setText("好的")
        dialog.cancelButton.hide()
        dialog.exec()


def _labeled(label: str, widget: QWidget) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    layout.addWidget(QLabel(label))
    layout.addWidget(widget, 1)
    return row


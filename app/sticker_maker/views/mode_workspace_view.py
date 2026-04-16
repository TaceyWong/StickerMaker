# coding: utf-8
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget
from qfluentwidgets import MessageBox

from sticker_maker.data.modes import ModeConfig
from sticker_maker.services.processing import ProcessingResult
from sticker_maker.services.workspace_service import build_task_summary
from sticker_maker.widgets.common import HeroCard, ScrollPage, SectionCard, WorkflowStepCard
from sticker_maker.widgets.drop_zone import FileDropArea
from sticker_maker.widgets.option_panel import OptionPanel
from sticker_maker.workers.processing_worker import ProcessingWorker


class ModeWorkspaceView(ScrollPage):
    def __init__(self, config: ModeConfig, parent=None):
        super().__init__(config.route, parent)
        self.config = config
        self.worker: ProcessingWorker | None = None
        self.last_result: ProcessingResult | None = None

        hero = HeroCard(
            config.title,
            config.description,
            config.shared_capabilities,
            self.container,
        )
        self.content_layout.addWidget(hero)

        columns = QHBoxLayout()
        columns.setSpacing(18)

        left_column = QVBoxLayout()
        left_column.setSpacing(18)

        accepted_suffixes = self._parse_suffixes(config.accepted_inputs)
        self.drop_area = FileDropArea(accepted_suffixes, config.drop_hint, self.container)
        self.drop_area.filesChanged.connect(self._refresh_summary)
        left_column.addWidget(self.drop_area)

        self.option_panel = OptionPanel(config.option_specs, self.container)
        self.option_panel.optionsChanged.connect(self._refresh_summary)
        left_column.addWidget(self.option_panel)

        workflow_card = SectionCard(
            "处理步骤",
            "以下步骤完全对应 README 的工作流，并把共享能力沉淀成可复用视图。",
            self.container,
        )
        for index, step in enumerate(config.workflow_steps, start=1):
            workflow_card.body_layout.addWidget(
                WorkflowStepCard(index, step.title, step.description, step.detail, workflow_card)
            )
        left_column.addWidget(workflow_card)

        right_column = QVBoxLayout()
        right_column.setSpacing(18)

        action_card = SectionCard(
            "执行任务",
            "处理会在后台线程执行，生成结果后会把日志和输出目录回填到右侧。",
            self.container,
        )
        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.process_button = QPushButton("开始处理", action_card)
        self.process_button.clicked.connect(self._start_processing)
        button_row.addWidget(self.process_button)

        self.open_output_button = QPushButton("打开输出目录", action_card)
        self.open_output_button.setEnabled(False)
        self.open_output_button.clicked.connect(self._open_output_dir)
        button_row.addWidget(self.open_output_button)
        button_row.addStretch(1)
        action_card.body_layout.addLayout(button_row)

        self.status_label = QLabel("状态：等待选择素材", action_card)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        action_card.body_layout.addWidget(self.status_label)
        right_column.addWidget(action_card)

        summary_card = SectionCard(
            "任务摘要",
            "右侧工作区会根据输入文件与参数实时生成处理摘要，方便后续直接串接服务层。",
            self.container,
        )
        self.summary_text = QTextEdit(summary_card)
        self.summary_text.setReadOnly(True)
        self.summary_text.setMinimumHeight(280)
        summary_card.body_layout.addWidget(self.summary_text)
        right_column.addWidget(summary_card)

        log_card = SectionCard(
            "执行日志",
            "这里会显示本次处理的进度、警告和输出目录。",
            self.container,
        )
        self.log_text = QTextEdit(log_card)
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(220)
        log_card.body_layout.addWidget(self.log_text)
        right_column.addWidget(log_card)

        output_card = SectionCard(
            "交付产物",
            "这里展示当前模式的目标输出，帮助后续实现时统一目录和命名规则。",
            self.container,
        )
        for item in config.expected_outputs:
            label = QLabel(f"• {item}", output_card)
            label.setObjectName("sectionDescription")
            label.setWordWrap(True)
            output_card.body_layout.addWidget(label)
        right_column.addWidget(output_card)
        right_column.addStretch(1)

        left_widget = QWidget(self.container)
        left_widget.setLayout(left_column)
        right_widget = QWidget(self.container)
        right_widget.setLayout(right_column)

        columns.addWidget(left_widget, 3)
        columns.addWidget(right_widget, 2)

        columns_widget = QWidget(self.container)
        columns_widget.setLayout(columns)
        self.content_layout.addWidget(columns_widget)
        self.content_layout.addStretch(1)

        self._refresh_summary()

    @staticmethod
    def _parse_suffixes(description: str) -> tuple[str, ...]:
        suffixes = []
        for part in description.replace("支持", "").replace("、", " ").split():
            text = part.strip().strip("，,")
            if not text or text.startswith("类型"):
                continue
            suffixes.append(f".{text.lower()}")
        return tuple(suffixes)

    def _refresh_summary(self, *_args) -> None:
        summary = build_task_summary(
            self.config,
            self.option_panel.values(),
            self.drop_area.paths,
        )
        self.summary_text.setPlainText(summary)
        if not self.drop_area.paths and self.worker is None:
            self.status_label.setText("状态：等待选择素材")

    def _start_processing(self) -> None:
        if self.worker is not None:
            return

        source_paths = self.drop_area.paths.copy()
        if not source_paths:
            dialog = MessageBox("无法开始处理", "请先拖入或选择至少一个素材文件。", self)
            dialog.yesButton.setText("知道了")
            dialog.cancelButton.hide()
            dialog.exec()
            return

        self.log_text.clear()
        self.last_result = None
        self.open_output_button.setEnabled(False)
        self.process_button.setEnabled(False)
        self.status_label.setText("状态：处理中，请稍候…")

        self.worker = ProcessingWorker(
            mode_key=self.config.key,
            source_paths=source_paths,
            options=self.option_panel.values(),
            base_dir=Path(__file__).resolve().parents[2],
            parent=self,
        )
        self.worker.logMessage.connect(self._append_log)
        self.worker.succeeded.connect(self._handle_success)
        self.worker.failed.connect(self._handle_failure)
        self.worker.finished.connect(self._handle_finished)
        self.worker.start()

    def _append_log(self, message: str) -> None:
        current = self.log_text.toPlainText().strip()
        updated = f"{current}\n{message}".strip() if current else message
        self.log_text.setPlainText(updated)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def _handle_success(self, result: ProcessingResult) -> None:
        self.last_result = result
        self.open_output_button.setEnabled(True)
        warning_text = f"，警告 {len(result.warnings)} 条" if result.warnings else ""
        self.status_label.setText(
            f"状态：处理完成，生成 {len(result.generated_files)} 个文件{warning_text}"
        )

    def _handle_failure(self, error_message: str) -> None:
        self.status_label.setText(f"状态：处理失败，{error_message}")
        self._append_log(f"错误：{error_message}")

    def _handle_finished(self) -> None:
        self.process_button.setEnabled(True)
        self.worker = None

    def _open_output_dir(self) -> None:
        if self.last_result is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_result.output_dir)))

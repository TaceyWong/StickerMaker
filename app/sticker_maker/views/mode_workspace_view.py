# coding: utf-8
from pathlib import Path
import weakref

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition, MessageBox

from sticker_maker.data.modes import ModeConfig
from sticker_maker.services.processing import ProcessingResult
from sticker_maker.widgets.common import ScrollPage, SectionCard
from sticker_maker.widgets.drop_zone import FileDropArea
from sticker_maker.widgets.option_panel import OptionPanel
from sticker_maker.widgets.output_preview_dialog import OutputPreviewDialog
from sticker_maker.workers.processing_worker import ProcessingWorker
from sticker_maker.workers.rembg_preload_worker import RembgPreloadWorker


class ModeWorkspaceView(ScrollPage):
    _view_refs: "weakref.WeakSet[ModeWorkspaceView]" = weakref.WeakSet()
    _global_rembg_ready = False
    _global_rembg_preloading = False
    _global_rembg_preload_error = ""
    _global_loading_tip_shown = False
    _global_ready_tip_shown = False
    _global_error_tip_shown = False
    _global_loading_tip_bar = None

    def __init__(self, config: ModeConfig, parent=None):
        super().__init__(config.route, parent)
        ModeWorkspaceView._view_refs.add(self)
        self.config = config
        self.worker: ProcessingWorker | None = None
        self.preload_worker: RembgPreloadWorker | None = None
        self.last_result: ProcessingResult | None = None

        header = QLabel(f"{config.title.upper()}  ·  {config.subtitle.lower()}", self.container)
        header.setObjectName("sectionTitle")
        header.setWordWrap(False)
        self.content_layout.addWidget(header)

        columns = QHBoxLayout()
        columns.setSpacing(18)

        left_column = QVBoxLayout()
        left_column.setSpacing(18)

        accepted_suffixes = self._parse_suffixes(config.accepted_inputs)
        self.drop_area = FileDropArea(accepted_suffixes, config.drop_hint, self.container)
        left_column.addWidget(self.drop_area)

        self.option_panel = OptionPanel(config.option_specs, self.container)
        self.option_panel.optionsChanged.connect(self._on_options_changed)
        left_column.addWidget(self.option_panel)

        right_column = QVBoxLayout()
        right_column.setSpacing(18)

        run_card = SectionCard(
            "处理",
            "后台执行，完成后可打开输出目录查看结果。",
            self.container,
        )
        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.process_button = QPushButton("开始处理", run_card)
        self.process_button.setObjectName("primaryButton")
        self.process_button.clicked.connect(self._start_processing)
        button_row.addWidget(self.process_button)

        self.open_output_button = QPushButton("打开输出目录", run_card)
        self.open_output_button.setEnabled(False)
        self.open_output_button.clicked.connect(self._open_output_dir)
        button_row.addWidget(self.open_output_button)

        self.preview_output_button = QPushButton("预览", run_card)
        self.preview_output_button.setEnabled(False)
        self.preview_output_button.clicked.connect(self._open_preview_dialog)
        button_row.addWidget(self.preview_output_button)
        button_row.addStretch(1)
        run_card.body_layout.addLayout(button_row)

        self.status_label = QLabel("就绪。请先添加素材文件。", run_card)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        run_card.body_layout.addWidget(self.status_label)

        self.rembg_hint_label = QLabel("", run_card)
        self.rembg_hint_label.setObjectName("statusLabel")
        self.rembg_hint_label.setWordWrap(True)
        run_card.body_layout.addWidget(self.rembg_hint_label)
        right_column.addWidget(run_card)

        output_card = SectionCard("运行日志", "处理过程中的输出将显示在这里。", self.container)
        self.log_text = QTextEdit(output_card)
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(360)
        self.log_text.setPlaceholderText("运行日志…")
        output_card.body_layout.addWidget(self.log_text)
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
        self._refresh_rembg_hint()
        # 延迟到事件循环启动后再触发，避免首屏构建阶段卡顿。
        QTimer.singleShot(300, self._start_rembg_preload_if_needed)

    @staticmethod
    def _parse_suffixes(description: str) -> tuple[str, ...]:
        cleaned = description.replace("、", " ").replace("，", " ").replace("支持", "")
        suffixes: list[str] = []
        for part in cleaned.split():
            ext = part.strip().lower().strip(".，,")
            if ext and ext.isalnum():
                suffixes.append(f".{ext}")
        return tuple(suffixes)

    def _start_processing(self) -> None:
        if self.worker is not None:
            return

        source_paths = self.drop_area.paths.copy()
        if not source_paths:
            dialog = MessageBox("无法开始", "请先添加至少一个素材文件。", self)
            dialog.yesButton.setText("好的")
            dialog.cancelButton.hide()
            dialog.exec()
            return

        self.log_text.clear()
        self.last_result = None
        self.open_output_button.setEnabled(False)
        self.preview_output_button.setEnabled(False)
        self.process_button.setEnabled(False)
        self.status_label.setText("处理中，请稍候…")

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

    def _supports_background_removal(self) -> bool:
        return any(spec.key == "remove_background" for spec in self.config.option_specs)

    def _is_remove_background_enabled(self) -> bool:
        if not self._supports_background_removal():
            return False
        return bool(self.option_panel.values().get("remove_background"))

    def _start_rembg_preload_if_needed(self) -> None:
        if not self._supports_background_removal():
            return
        if (
            ModeWorkspaceView._global_rembg_ready
            or ModeWorkspaceView._global_rembg_preloading
            or self.preload_worker is not None
        ):
            return
        ModeWorkspaceView._global_rembg_preloading = True
        ModeWorkspaceView._global_rembg_preload_error = ""
        self._show_top_rembg_loading_tip_once()
        self._refresh_rembg_hint()
        self.preload_worker = RembgPreloadWorker(
            base_dir=Path(__file__).resolve().parents[2],
            parent=self,
        )
        self.preload_worker.succeeded.connect(self._handle_preload_success)
        self.preload_worker.failed.connect(self._handle_preload_failed)
        self.preload_worker.finished.connect(self._handle_preload_finished)
        self.preload_worker.start()

    def _handle_preload_success(self) -> None:
        ModeWorkspaceView._global_rembg_ready = True
        ModeWorkspaceView._global_rembg_preload_error = ""
        self._close_top_rembg_loading_tip()
        self._show_top_rembg_ready_tip_once()
        self._refresh_all_rembg_hints()

    def _handle_preload_failed(self, message: str) -> None:
        ModeWorkspaceView._global_rembg_ready = False
        ModeWorkspaceView._global_rembg_preload_error = message
        self._close_top_rembg_loading_tip()
        self._show_top_rembg_error_tip_once(message)
        self._refresh_all_rembg_hints()

    def _handle_preload_finished(self) -> None:
        ModeWorkspaceView._global_rembg_preloading = False
        self.preload_worker = None
        self._refresh_all_rembg_hints()

    def _on_options_changed(self, _values: dict[str, object]) -> None:
        if self._is_remove_background_enabled():
            self._start_rembg_preload_if_needed()
        self._refresh_rembg_hint()

    def _refresh_rembg_hint(self) -> None:
        if not self._supports_background_removal():
            self.rembg_hint_label.setText("")
            self.rembg_hint_label.setVisible(False)
            return
        if not self._is_remove_background_enabled():
            self.rembg_hint_label.setText("去背景已关闭。")
            self.rembg_hint_label.setVisible(True)
            return
        self.rembg_hint_label.setVisible(True)
        if ModeWorkspaceView._global_rembg_ready:
            self.rembg_hint_label.setText("去背景模型已就绪。")
            return
        if ModeWorkspaceView._global_rembg_preloading:
            self.rembg_hint_label.setText("去背景模型正在后台加载，可继续操作界面。")
            return
        if ModeWorkspaceView._global_rembg_preload_error:
            self.rembg_hint_label.setText(
                f"去背景模型加载失败：{ModeWorkspaceView._global_rembg_preload_error}"
            )
            return
        self.rembg_hint_label.setText("去背景模型等待加载。")

    @classmethod
    def _refresh_all_rembg_hints(cls) -> None:
        for view in list(cls._view_refs):
            view._refresh_rembg_hint()

    def _show_top_rembg_loading_tip_once(self) -> None:
        if ModeWorkspaceView._global_loading_tip_shown:
            return
        ModeWorkspaceView._global_loading_tip_shown = True
        ModeWorkspaceView._global_loading_tip_bar = InfoBar.warning(
            title="去背景模型加载中",
            content="首次启动会在后台预热模型，期间可继续操作界面。",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=-1,
            parent=self.window(),
        )

    def _close_top_rembg_loading_tip(self) -> None:
        bar = ModeWorkspaceView._global_loading_tip_bar
        if bar is None:
            return
        try:
            bar.close()
        finally:
            ModeWorkspaceView._global_loading_tip_bar = None

    def _show_top_rembg_ready_tip_once(self) -> None:
        if ModeWorkspaceView._global_ready_tip_shown:
            return
        ModeWorkspaceView._global_ready_tip_shown = True
        InfoBar.success(
            title="去背景模型已就绪",
            content="后续去背景处理将直接复用缓存会话。",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2500,
            parent=self.window(),
        )

    def _show_top_rembg_error_tip_once(self, message: str) -> None:
        if ModeWorkspaceView._global_error_tip_shown:
            return
        ModeWorkspaceView._global_error_tip_shown = True
        InfoBar.error(
            title="去背景模型加载失败",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=6000,
            parent=self.window(),
        )

    def _append_log(self, message: str) -> None:
        current = self.log_text.toPlainText().strip()
        updated = f"{current}\n{message}".strip() if current else message
        self.log_text.setPlainText(updated)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def _handle_success(self, result: ProcessingResult) -> None:
        self.last_result = result
        self.open_output_button.setEnabled(True)
        self.preview_output_button.setEnabled(bool(self._collect_preview_files(result)))
        warning_text = f"（{len(result.warnings)} 条提示）" if result.warnings else ""
        self.status_label.setText(
            f"完成。已生成 {len(result.generated_files)} 个文件{warning_text}。"
        )

    def _handle_failure(self, error_message: str) -> None:
        self.status_label.setText(f"失败：{error_message}")
        self._append_log(f"错误：{error_message}")

    def _handle_finished(self) -> None:
        self.process_button.setEnabled(True)
        self.worker = None

    def _open_output_dir(self) -> None:
        if self.last_result is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_result.output_dir)))

    @staticmethod
    def _collect_preview_files(result: ProcessingResult) -> list[Path]:
        exts = {".png", ".gif"}
        return [path for path in result.generated_files if path.suffix.lower() in exts and path.exists()]

    def _open_preview_dialog(self) -> None:
        if self.last_result is None:
            return
        files = self._collect_preview_files(self.last_result)
        if not files:
            dialog = MessageBox("无可预览文件", "当前任务没有生成 PNG 或 GIF。", self)
            dialog.yesButton.setText("知道了")
            dialog.cancelButton.hide()
            dialog.exec()
            return
        preview = OutputPreviewDialog(files, self)
        preview.exec()

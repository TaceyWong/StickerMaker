# coding: utf-8
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from sticker_maker.services.processing import ProcessingError, ProcessingResult, process_sticker_job


class ProcessingWorker(QThread):
    logMessage = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        mode_key: str,
        source_paths: list[str],
        options: dict[str, object],
        base_dir: Path,
        parent=None,
    ):
        super().__init__(parent)
        self.mode_key = mode_key
        self.source_paths = source_paths
        self.options = options
        self.base_dir = base_dir

    def run(self) -> None:
        try:
            result: ProcessingResult = process_sticker_job(
                self.mode_key,
                self.source_paths,
                self.options,
                self.base_dir,
                logger=self.logMessage.emit,
            )
        except ProcessingError as error:
            self.failed.emit(str(error))
            return
        except Exception as error:  # noqa: BLE001
            self.failed.emit(f"处理过程中发生未预期错误：{error}")
            return

        self.succeeded.emit(result)

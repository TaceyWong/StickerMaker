# coding: utf-8
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from sticker_maker.services.processing import (
    ProcessingError,
    REMBG_DEFAULT_MODEL,
    REMBG_MODEL_IDS,
    configure_rembg_models_dir,
)


class RembgPreloadWorker(QThread):
    succeeded = Signal()
    failed = Signal(str)

    def __init__(self, base_dir: Path, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir

    def _resolve_model_name(self) -> str:
        raw = str(os.getenv("STICKERMAKER_RMBG_MODEL", "")).strip()
        if raw in REMBG_MODEL_IDS:
            return raw
        return REMBG_DEFAULT_MODEL

    def run(self) -> None:
        model_name = self._resolve_model_name()
        models_dir = configure_rembg_models_dir(self.base_dir)
        env = os.environ.copy()
        env["U2NET_HOME"] = str(models_dir)
        preload_script = (
            "from rembg import new_session\n"
            f"new_session({model_name!r})\n"
            "print('ok')\n"
        )
        try:
            completed = subprocess.run(
                [sys.executable, "-c", preload_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                cwd=str(self.base_dir),
            )
            if completed.returncode != 0:
                output = (completed.stderr or completed.stdout).strip()
                if "No module named 'rembg'" in output:
                    raise ProcessingError(
                        '未安装 rembg，请在当前 Python 环境中执行：pip install "rembg[cpu]"'
                    )
                raise ProcessingError(output or "去背景模型预加载失败。")
        except ProcessingError as error:
            self.failed.emit(str(error))
            return
        except Exception as error:  # noqa: BLE001
            self.failed.emit(f"去背景模型预加载失败：{error}")
            return
        self.succeeded.emit()

# coding: utf-8
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from sticker_maker.services.ai_image_service import (
    OpenAICompatibleImageRequest,
    generate_local_doubao_images_via_rpa,
    generate_openai_compatible_images,
)


class AIGenerateWorker(QThread):
    logMessage = Signal(str)
    progressValue = Signal(int)  # 已完成数
    finished = Signal(object)  # list[str]
    failed = Signal(str)

    def __init__(
        self,
        *,
        provider: str,
        service_base_url: str = "",
        service_api_key: str = "",
        service_model: str = "",
        service_username: str = "",
        service_password: str = "",
        prompt: str,
        size: str,
        count: int,
        output_dir: Path,
        parent=None,
    ):
        super().__init__(parent)
        self.provider = provider
        self.service_base_url = service_base_url
        self.service_api_key = service_api_key
        self.service_model = service_model
        self.service_username = service_username
        self.service_password = service_password
        self.prompt = prompt
        self.size = size
        self.count = count
        self.output_dir = output_dir

    def run(self) -> None:
        results: list[Path] = []
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            if self.provider == "local_doubao":
                self.logMessage.emit("正在调用本地豆包（浏览器 RPA）…")
                paths = generate_local_doubao_images_via_rpa(self.prompt, self.count, self.output_dir)
                results.extend(paths)
                self.progressValue.emit(self.count)
                self.finished.emit([str(p) for p in results])
                return

            for i in range(self.count):
                self.logMessage.emit(f"AI 生成中：{i+1}/{self.count}…")
                req = OpenAICompatibleImageRequest(
                    base_url=self.service_base_url,
                    api_key=self.service_api_key,
                    model=self.service_model,
                    prompt=self.prompt,
                    size=self.size,
                    n=1,
                    username=self.service_username,
                    password=self.service_password,
                )
                paths = generate_openai_compatible_images(req, self.output_dir)
                results.extend(paths)
                self.progressValue.emit(i + 1)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
            return

        self.finished.emit([str(p) for p in results])


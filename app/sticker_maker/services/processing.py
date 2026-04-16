# coding: utf-8
from __future__ import annotations

import math
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter


LogCallback = Callable[[str], None]


class ProcessingError(RuntimeError):
    """Raised when a processing task cannot continue."""


@dataclass
class ProcessingResult:
    mode_key: str
    output_dir: Path
    generated_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)


GRID_LAYOUTS = {
    "3x3": (3, 3),
    "3x4": (3, 4),
    "4x3": (4, 3),
}

REMBG_MODEL_IDS = frozenset(
    {"isnet-anime", "birefnet-portrait", "u2net_human_seg", "isnet-general-use"}
)
REMBG_DEFAULT_MODEL = "isnet-anime"


def process_sticker_job(
    mode_key: str,
    source_paths: list[str],
    options: dict[str, object],
    base_dir: Path,
    logger: LogCallback | None = None,
) -> ProcessingResult:
    if not source_paths:
        raise ProcessingError("请先选择要处理的文件。")

    output_root = resolve_output_root(base_dir, str(options.get("output_dir", "")).strip())
    job_dir = create_job_dir(output_root, mode_key)
    result = ProcessingResult(mode_key=mode_key, output_dir=job_dir)

    def emit(message: str) -> None:
        result.logs.append(message)
        if logger is not None:
            logger(message)

    emit(f"输出目录：{job_dir}")
    append_feature_warnings(options, result, emit)

    if mode_key == "static":
        process_static_images(source_paths, options, job_dir, result, emit)
    elif mode_key == "dynamic":
        process_dynamic_images(source_paths, options, job_dir, result, emit)
    elif mode_key == "video":
        process_video_sources(source_paths, options, job_dir, result, emit)
    else:
        raise ProcessingError(f"暂不支持的模式：{mode_key}")

    emit(f"处理完成，共生成 {len(result.generated_files)} 个文件。")
    return result


def resolve_output_root(base_dir: Path, output_value: str) -> Path:
    output_value = output_value or "../output"
    output_path = Path(output_value)
    if not output_path.is_absolute():
        output_path = (base_dir / output_path).resolve()
    return output_path


def create_job_dir(output_root: Path, mode_key: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_dir = output_root / f"{mode_key}_{stamp}"
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def append_feature_warnings(
    options: dict[str, object],
    result: ProcessingResult,
    emit: LogCallback,
) -> None:
    if options.get("remove_watermark"):
        warning = "当前版本尚未接入自动去水印，已保留处理开关并暂时跳过此步骤。"
        result.warnings.append(warning)
        emit(f"提示：{warning}")


def process_static_images(
    source_paths: list[str],
    options: dict[str, object],
    job_dir: Path,
    result: ProcessingResult,
    emit: LogCallback,
) -> None:
    rows, cols = parse_grid_layout(str(options.get("grid_layout", "3x3")))
    output_dir = job_dir / "png"
    output_dir.mkdir(parents=True, exist_ok=True)

    rembg_session = _create_rembg_session_if_enabled(options)
    if rembg_session is not None:
        emit(f"去背景模型：{_resolve_rembg_model_name(options)}")

    counter = 1
    for source_path in source_paths:
        emit(f"切分图片：{source_path}")
        image = load_image(Path(source_path))
        if rembg_session is not None:
            emit(f"去除背景：{source_path}")
            image = _remove_background_with_rembg(image, rembg_session)
        for cell in split_grid(image, rows, cols):
            normalized = normalize_cell(cell)
            output_path = output_dir / f"{counter:04d}.png"
            save_png(normalized, output_path)
            result.generated_files.append(output_path)
            counter += 1


def process_dynamic_images(
    source_paths: list[str],
    options: dict[str, object],
    job_dir: Path,
    result: ProcessingResult,
    emit: LogCallback,
) -> None:
    process_static_images(source_paths, options, job_dir, result, emit)

    frame_dir = job_dir / "png"
    gif_path = job_dir / "output.gif"
    interval = parse_positive_int(options.get("gif_interval"), default=120)
    build_gif_from_sequence(frame_dir, gif_path, interval, emit)
    result.generated_files.append(gif_path)


def process_video_sources(
    source_paths: list[str],
    options: dict[str, object],
    job_dir: Path,
    result: ProcessingResult,
    emit: LogCallback,
) -> None:
    if len(source_paths) != 1:
        raise ProcessingError("视频模式当前仅支持一次处理一个视频文件。")

    rows, cols = parse_grid_layout(str(options.get("grid_layout", "3x3")))
    frame_strategy = str(options.get("frame_strategy", "keyframe"))
    interval = parse_positive_int(options.get("gif_interval"), default=100)

    extracted_dir = job_dir / "extracted_frames"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    source_path = Path(source_paths[0])

    emit(f"抽帧视频：{source_path}")
    extract_video_frames(source_path, extracted_dir, frame_strategy, interval)

    frame_paths = sorted(extracted_dir.glob("*.png"))
    if not frame_paths:
        raise ProcessingError("没有从视频中提取到可用帧，请检查输入视频或抽帧策略。")

    emit(f"已提取 {len(frame_paths)} 帧，开始按宫格切分。")
    cell_root = job_dir / "cells"
    gif_root = job_dir / "gifs"
    gif_root.mkdir(parents=True, exist_ok=True)

    rembg_session = _create_rembg_session_if_enabled(options)
    if rembg_session is not None:
        emit(
            f"去背景模型：{_resolve_rembg_model_name(options)}"
            "（逐帧处理，CPU 模式下可能较慢）。"
        )

    for frame_index, frame_path in enumerate(frame_paths, start=1):
        image = load_image(frame_path)
        if rembg_session is not None:
            image = _remove_background_with_rembg(image, rembg_session)
        cells = split_grid(image, rows, cols)
        for cell_index, cell in enumerate(cells):
            row = cell_index // cols + 1
            col = cell_index % cols + 1
            cell_dir = cell_root / f"r{row}_c{col}"
            cell_dir.mkdir(parents=True, exist_ok=True)

            normalized = normalize_cell(cell)
            output_path = cell_dir / f"{frame_index:04d}.png"
            save_png(normalized, output_path)
            result.generated_files.append(output_path)

    emit("开始按格位合成 GIF。")
    for cell_dir in sorted(path for path in cell_root.iterdir() if path.is_dir()):
        gif_path = gif_root / f"{cell_dir.name}.gif"
        build_gif_from_sequence(cell_dir, gif_path, interval, emit)
        result.generated_files.append(gif_path)


def parse_grid_layout(layout: str) -> tuple[int, int]:
    try:
        return GRID_LAYOUTS[layout]
    except KeyError as error:
        raise ProcessingError(f"无效的宫格布局：{layout}") from error


def parse_positive_int(value: object, default: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _resolve_rembg_model_name(options: dict[str, object]) -> str:
    raw = str(options.get("rembg_model", "") or "").strip()
    if raw in REMBG_MODEL_IDS:
        return raw
    return REMBG_DEFAULT_MODEL


def _create_rembg_session_if_enabled(options: dict[str, object]) -> object | None:
    if not options.get("remove_background"):
        return None
    try:
        from rembg import new_session
    except ImportError as error:
        raise ProcessingError(
            '未安装 rembg，请在当前 Python 环境中执行：pip install "rembg[cpu]"'
        ) from error
    model_name = _resolve_rembg_model_name(options)
    return new_session(model_name)


def _qimage_to_png_bytes(image: QImage) -> bytes:
    buffer = QByteArray()
    io_buffer = QBuffer(buffer)
    io_buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(io_buffer, "PNG"):
        raise ProcessingError("无法将图像编码为 PNG（去背景前）。")
    return bytes(buffer)


def _remove_background_with_rembg(image: QImage, session: object) -> QImage:
    from rembg import remove

    png_bytes = _qimage_to_png_bytes(image)
    output_bytes = remove(png_bytes, session=session)
    result = QImage.fromData(output_bytes)
    if result.isNull():
        raise ProcessingError("去背景失败：无法将 rembg 输出解码为图像。")
    return result.convertToFormat(QImage.Format_RGBA8888)


def load_image(source_path: Path) -> QImage:
    image = QImage(str(source_path))
    if image.isNull():
        raise ProcessingError(f"无法读取图片文件：{source_path}")
    return image.convertToFormat(QImage.Format_RGBA8888)


def split_grid(image: QImage, rows: int, cols: int) -> list[QImage]:
    x_edges = [round(index * image.width() / cols) for index in range(cols + 1)]
    y_edges = [round(index * image.height() / rows) for index in range(rows + 1)]

    cells: list[QImage] = []
    for row in range(rows):
        for col in range(cols):
            rect = QRect(
                x_edges[col],
                y_edges[row],
                x_edges[col + 1] - x_edges[col],
                y_edges[row + 1] - y_edges[row],
            )
            cells.append(image.copy(rect))
    return cells


def normalize_cell(cell: QImage, padding: int = 5, size: int = 240) -> QImage:
    bounds = find_content_bounds(cell)
    if bounds is None:
        cropped = cell
    else:
        left, top, right, bottom = bounds
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(cell.width() - 1, right + padding)
        bottom = min(cell.height() - 1, bottom + padding)
        cropped = cell.copy(QRect(left, top, right - left + 1, bottom - top + 1))

    square_size = max(cropped.width(), cropped.height(), 1)
    canvas = QImage(square_size, square_size, QImage.Format_RGBA8888)
    canvas.fill(Qt.transparent)

    painter = QPainter(canvas)
    painter.drawImage(
        (square_size - cropped.width()) // 2,
        (square_size - cropped.height()) // 2,
        cropped,
    )
    painter.end()

    return canvas.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def find_content_bounds(image: QImage) -> tuple[int, int, int, int] | None:
    width = image.width()
    height = image.height()

    left = 0
    while left < width and column_is_transparent(image, left):
        left += 1
    if left >= width:
        return None

    right = width - 1
    while right >= 0 and column_is_transparent(image, right):
        right -= 1

    top = 0
    while top < height and row_is_transparent(image, top):
        top += 1

    bottom = height - 1
    while bottom >= 0 and row_is_transparent(image, bottom):
        bottom -= 1

    return left, top, right, bottom


def column_is_transparent(image: QImage, x: int) -> bool:
    for y in range(image.height()):
        if QColor(image.pixelColor(x, y)).alpha() > 0:
            return False
    return True


def row_is_transparent(image: QImage, y: int) -> bool:
    for x in range(image.width()):
        if QColor(image.pixelColor(x, y)).alpha() > 0:
            return False
    return True


def save_png(image: QImage, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(target_path), "PNG"):
        raise ProcessingError(f"保存 PNG 失败：{target_path}")


def build_gif_from_sequence(
    frame_dir: Path,
    gif_path: Path,
    interval_ms: int,
    emit: LogCallback,
) -> None:
    frame_files = sorted(frame_dir.glob("*.png"))
    if not frame_files:
        raise ProcessingError(f"目录中没有可用于合成 GIF 的 PNG：{frame_dir}")

    fps = max(1.0, 1000.0 / interval_ms)
    palette_path = frame_dir / "palette.png"
    sequence_pattern = str(frame_dir / "%04d.png")

    emit(f"合成 GIF：{gif_path.name}")
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            f"{fps:.4f}",
            "-start_number",
            "1",
            "-i",
            sequence_pattern,
            "-vf",
            "palettegen=reserve_transparent=on",
            str(palette_path),
        ],
        cwd=frame_dir,
    )
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            f"{fps:.4f}",
            "-start_number",
            "1",
            "-i",
            sequence_pattern,
            "-i",
            str(palette_path),
            "-lavfi",
            "paletteuse=alpha_threshold=128",
            "-loop",
            "0",
            str(gif_path),
        ],
        cwd=frame_dir,
    )

    if palette_path.exists():
        palette_path.unlink()


def extract_video_frames(
    source_path: Path,
    output_dir: Path,
    strategy: str,
    interval_ms: int,
) -> None:
    pattern = str(output_dir / "%04d.png")

    if strategy == "keyframe":
        args = [
            "ffmpeg",
            "-y",
            "-skip_frame",
            "nokey",
            "-i",
            str(source_path),
            "-vsync",
            "vfr",
            pattern,
        ]
    else:
        fps = max(1, math.ceil(1000 / interval_ms))
        args = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-vf",
            f"fps={fps}",
            pattern,
        ]

    run_ffmpeg(args, cwd=output_dir)


def run_ffmpeg(args: list[str], cwd: Path) -> None:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise ProcessingError("未找到 ffmpeg，请先安装并确保 ffmpeg 在 PATH 中可用。")

    command = args.copy()
    command[0] = ffmpeg_path

    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "未知 ffmpeg 错误"
        raise ProcessingError(message)

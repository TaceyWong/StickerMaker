# coding: utf-8
from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable

from PIL import Image
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
    {
        "isnet-anime",
        "bria-rmbg",
        "birefnet-portrait",
        "u2net_human_seg",
        "isnet-general-use",
    }
)
REMBG_DEFAULT_MODEL = "isnet-anime"


def configure_rembg_models_dir(base_dir: Path) -> Path:
    """将 rembg 的 U2NET_HOME 指向项目内 resource/models（与 README 中「模型放项目内」一致）。"""
    models_dir = (base_dir / "resource" / "models").resolve()
    models_dir.mkdir(parents=True, exist_ok=True)
    os.environ["U2NET_HOME"] = str(models_dir)
    return models_dir


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
    models_dir = configure_rembg_models_dir(base_dir)
    emit(f"rembg 模型目录：{models_dir}")
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
    rembg_session = _create_rembg_session_if_enabled(options)
    if rembg_session is not None:
        emit(f"去背景模型：{_resolve_rembg_model_name(options)}")

    sources_root = job_dir / "sources"
    sources_root.mkdir(parents=True, exist_ok=True)
    for source_index, source_path in enumerate(source_paths, start=1):
        emit(f"读取素材：{source_path}")
        source = Path(source_path)
        source_dir = _build_source_dir(sources_root, source_index, source)
        generated_cells = process_single_source_images(
            source_path=source,
            source_dir=source_dir,
            rows=rows,
            cols=cols,
            remove_watermark=bool(options.get("remove_watermark")),
            rembg_session=rembg_session,
            result=result,
            emit=emit,
        )
        emit(f"完成素材：{source.name}，切出 {len(generated_cells)} 张。")


def process_dynamic_images(
    source_paths: list[str],
    options: dict[str, object],
    job_dir: Path,
    result: ProcessingResult,
    emit: LogCallback,
) -> None:
    rows, cols = parse_grid_layout(str(options.get("grid_layout", "3x3")))
    interval = parse_positive_int(options.get("gif_interval"), default=120)
    rembg_session = _create_rembg_session_if_enabled(options)
    if rembg_session is not None:
        emit(f"去背景模型：{_resolve_rembg_model_name(options)}")

    sources_root = job_dir / "sources"
    sources_root.mkdir(parents=True, exist_ok=True)
    for source_index, source_path in enumerate(source_paths, start=1):
        source = Path(source_path)
        source_dir = _build_source_dir(sources_root, source_index, source)
        generated_cells = process_single_source_images(
            source_path=source,
            source_dir=source_dir,
            rows=rows,
            cols=cols,
            remove_watermark=bool(options.get("remove_watermark")),
            rembg_session=rembg_session,
            result=result,
            emit=emit,
        )
        if not generated_cells:
            continue
        gif_path = source_dir / "output.gif"
        build_gif_from_sequence(source_dir / "cells", gif_path, interval, emit)
        result.generated_files.append(gif_path)
        emit(f"完成动态素材：{source.name} -> {gif_path.name}")


def _build_source_dir(sources_root: Path, source_index: int, source: Path) -> Path:
    safe_name = re.sub(r"[^0-9A-Za-z_\u4e00-\u9fa5-]+", "_", source.stem).strip("_")
    if not safe_name:
        safe_name = f"source_{source_index:02d}"
    source_dir = sources_root / f"{source_index:02d}_{safe_name}"
    source_dir.mkdir(parents=True, exist_ok=True)
    return source_dir


def process_single_source_images(
    source_path: Path,
    source_dir: Path,
    rows: int,
    cols: int,
    remove_watermark: bool,
    rembg_session: object | None,
    result: ProcessingResult,
    emit: LogCallback,
) -> list[Path]:
    image = load_image(source_path)
    original_path = source_dir / "original.png"
    save_png(image, original_path)
    result.generated_files.append(original_path)

    if remove_watermark:
        # 当前去水印能力尚未接入，先保留占位结果，保证全链路可追踪。
        watermark_path = source_dir / "watermark_removed.png"
        save_png(image, watermark_path)
        result.generated_files.append(watermark_path)

    if rembg_session is not None:
        emit(f"去除背景：{source_path}")
        image = _remove_background_with_rembg(image, rembg_session)
        image = _cleanup_edge_black_fringe(image)
        bg_removed_path = source_dir / "background_removed.png"
        save_png(image, bg_removed_path)
        result.generated_files.append(bg_removed_path)

    emit(f"切分宫格：{source_path}")
    cells_dir = source_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    generated_cells: list[Path] = []
    counter = 1
    for cell in split_grid(image, rows, cols):
        normalized = normalize_cell(cell)
        output_path = cells_dir / f"{counter:04d}.png"
        save_png(normalized, output_path)
        result.generated_files.append(output_path)
        generated_cells.append(output_path)
        counter += 1
    return generated_cells


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

    source_path = Path(source_paths[0])
    sources_root = job_dir / "sources"
    sources_root.mkdir(parents=True, exist_ok=True)
    source_dir = _build_source_dir(sources_root, 1, source_path)

    extracted_dir = source_dir / "extracted_frames"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    emit(f"抽帧视频：{source_path}")
    extract_video_frames(source_path, extracted_dir, frame_strategy, interval)

    frame_paths = sorted(extracted_dir.glob("*.png"))
    if not frame_paths:
        raise ProcessingError("没有从视频中提取到可用帧，请检查输入视频或抽帧策略。")

    emit(f"已提取 {len(frame_paths)} 帧，开始按宫格切分。")
    original_dir = source_dir / "original_frames"
    original_dir.mkdir(parents=True, exist_ok=True)
    watermark_dir = source_dir / "watermark_removed_frames"
    if options.get("remove_watermark"):
        watermark_dir.mkdir(parents=True, exist_ok=True)
    bg_removed_dir = source_dir / "background_removed_frames"

    cell_root = source_dir / "cells"
    gif_root = source_dir / "gifs"
    gif_root.mkdir(parents=True, exist_ok=True)

    rembg_session = _create_rembg_session_if_enabled(options)
    if rembg_session is not None:
        bg_removed_dir.mkdir(parents=True, exist_ok=True)
        emit(
            f"去背景模型：{_resolve_rembg_model_name(options)}"
            "（逐帧处理，CPU 模式下可能较慢）。"
        )

    for frame_index, frame_path in enumerate(frame_paths, start=1):
        image = load_image(frame_path)
        original_path = original_dir / f"{frame_index:04d}.png"
        save_png(image, original_path)
        result.generated_files.append(original_path)

        if options.get("remove_watermark"):
            watermark_path = watermark_dir / f"{frame_index:04d}.png"
            save_png(image, watermark_path)
            result.generated_files.append(watermark_path)
        if rembg_session is not None:
            image = _remove_background_with_rembg(image, rembg_session)
            image = _cleanup_edge_black_fringe(image)
            bg_removed_path = bg_removed_dir / f"{frame_index:04d}.png"
            save_png(image, bg_removed_path)
            result.generated_files.append(bg_removed_path)
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
    for cell_dir in _sort_cell_position_dirs(cell_root):
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


def _cleanup_edge_black_fringe(image: QImage) -> QImage:
    """清理去背景后半透明边缘的黑色污染。"""
    try:
        import numpy as np
    except ImportError as error:
        raise ProcessingError("边缘去黑需要 numpy，请先安装。") from error

    png_bytes = _qimage_to_png_bytes(image)
    try:
        rgba = Image.open(BytesIO(png_bytes)).convert("RGBA")
    except OSError as error:
        raise ProcessingError(f"边缘去黑失败：{error}") from error

    arr = np.array(rgba, dtype=np.uint8)
    alpha = arr[:, :, 3].astype(np.uint16)

    # 完全透明像素清零 RGB，避免量化时把脏色带出来。
    fully_transparent = alpha <= 2
    arr[fully_transparent, 0:3] = 0

    # 半透明边缘按 alpha 拉亮，减轻黑边。
    edge_band = (alpha > 2) & (alpha < 112)
    if edge_band.any():
        a = alpha[edge_band].astype(np.float32)
        # 反预乘近似，限制放大倍率，避免噪声爆亮。
        boost = np.clip(255.0 / np.maximum(a, 1.0), 1.0, 2.8).reshape(-1, 1)
        rgb = arr[edge_band, 0:3].astype(np.float32) * boost
        arr[edge_band, 0:3] = np.clip(rgb, 0, 255).astype(np.uint8)

    cleaned = Image.fromarray(arr, mode="RGBA")
    output = BytesIO()
    cleaned.save(output, format="PNG")
    result = QImage.fromData(output.getvalue())
    if result.isNull():
        raise ProcessingError("边缘去黑失败：无法解码输出图像。")
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


def _scan_numbered_png_frames(frame_dir: Path) -> list[Path]:
    """只认 0001.png 形式的帧，排除 palette.png 等杂文件。"""
    frames: list[Path] = []
    for path in frame_dir.iterdir():
        if path.suffix.lower() != ".png":
            continue
        stem = path.stem
        if len(stem) == 4 and stem.isdigit():
            frames.append(path)
    frames.sort(key=lambda p: p.stem)
    return frames


def _sort_cell_position_dirs(cell_root: Path) -> list[Path]:
    """按行、列数值排序（避免 r1_c10 排在 r1_c2 前的字典序问题）。"""

    def row_col_key(path: Path) -> tuple[int, int, str]:
        match = re.fullmatch(r"r(\d+)_c(\d+)", path.name)
        if match:
            return int(match.group(1)), int(match.group(2)), path.name
        return (9999, 9999, path.name)

    return sorted((p for p in cell_root.iterdir() if p.is_dir()), key=row_col_key)


def build_gif_from_sequence(
    frame_dir: Path,
    gif_path: Path,
    interval_ms: int,
    emit: LogCallback,
) -> None:
    frames = _scan_numbered_png_frames(frame_dir)
    if not frames:
        raise ProcessingError(
            f"目录中没有可用于合成 GIF 的编号 PNG（需为 0001.png、0002.png…）：{frame_dir}"
        )

    gif_out = gif_path.resolve()
    gif_out.parent.mkdir(parents=True, exist_ok=True)
    emit(f"合成 GIF：{gif_out.name}（{len(frames)} 帧，{interval_ms} ms/帧）")

    magick_path = _resolve_magick_executable()
    delay_cs = max(1, round(interval_ms / 10))  # ImageMagick delay unit = 1/100s
    command = [
        str(magick_path),
        "-delay",
        str(delay_cs),
        "-dispose","background",
        *[str(path.resolve()) for path in frames],
        "-alpha",
        "set",
        "-dispose",
        "previous",
        "-loop",
        "0",
        "-layers",
        "OptimizeTransparency",
        str(gif_out),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "未知 ImageMagick 错误"
        raise ProcessingError(f"ImageMagick 合成 GIF 失败：{message}")


def _resolve_magick_executable() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    local_magick = repo_root / "gif" / "magick.exe"
    if local_magick.is_file():
        return local_magick

    path_magick = shutil.which("magick")
    if path_magick:
        return Path(path_magick)

    raise ProcessingError("未找到 ImageMagick，可执行文件应位于 gif/magick.exe 或 PATH 中的 magick。")


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

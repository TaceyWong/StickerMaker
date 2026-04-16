# coding: utf-8
from __future__ import annotations

import base64
import json
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class OpenAICompatibleImageRequest:
    base_url: str
    api_key: str
    model: str
    prompt: str
    size: str = "1024x1024"
    n: int = 1


def _json_post(url: str, payload: dict[str, Any], headers: dict[str, str], timeout_s: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=headers, method="POST")

    # 本地接口可能是自签证书：兼容；不影响生产接口。
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urlopen(req, timeout=timeout_s, context=ctx) as resp:  # noqa: S310
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


def _http_get_bytes(url: str, timeout_s: int) -> bytes:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urlopen(url, timeout=timeout_s, context=ctx) as resp:  # noqa: S310
        return resp.read()


def _save_png_bytes(dst: Path, png_bytes: bytes) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(png_bytes)
    return dst


def generate_openai_compatible_images(
    req: OpenAICompatibleImageRequest,
    output_dir: Path,
    *,
    timeout_s: int = 180,
) -> list[Path]:
    """
    兼容 OpenAI images/generations 的接口：
    - 返回 data[i].b64_json 或 data[i].url
    - 将结果保存为 png 文件，返回本地路径列表
    """

    base_url = req.base_url.strip().rstrip("/")
    if not base_url:
        raise ValueError("base_url 不能为空")
    if not req.model:
        raise ValueError("model 不能为空")
    if not req.prompt.strip():
        raise ValueError("prompt 不能为空")
    if req.n < 1:
        raise ValueError("n 必须 >= 1")

    url = f"{base_url}/images/generations"
    headers = {"Content-Type": "application/json"}
    if req.api_key.strip():
        headers["Authorization"] = f"Bearer {req.api_key.strip()}"

    payload = {
        "model": req.model,
        "prompt": req.prompt,
        "n": req.n,
        "size": req.size,
    }

    try:
        resp = _json_post(url, payload, headers=headers, timeout_s=timeout_s)
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"请求失败：HTTP {e.code} {e.reason}\n{detail}".strip()) from e
    except URLError as e:
        raise RuntimeError(f"请求失败：{e.reason}".strip()) from e

    data = resp.get("data") or []
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"响应格式异常：未找到 data 字段\n响应：{resp}")

    saved: list[Path] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        b64 = item.get("b64_json")
        url_item = item.get("url")

        if isinstance(b64, str) and b64.strip():
            png_bytes = base64.b64decode(b64)
            saved.append(_save_png_bytes(output_dir / f"generated_{idx+1:04d}.png", png_bytes))
            continue

        if isinstance(url_item, str) and url_item.strip():
            png_bytes = _http_get_bytes(url_item.strip(), timeout_s=timeout_s)
            saved.append(_save_png_bytes(output_dir / f"generated_{idx+1:04d}.png", png_bytes))
            continue

    if not saved:
        raise RuntimeError(f"响应中未包含可用图片数据（b64_json/url）\n响应：{resp}")
    return saved


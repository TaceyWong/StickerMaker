# coding: utf-8
from collections.abc import Mapping, Sequence

from sticker_maker.data.modes import ModeConfig, OptionSpec


def resolve_choice_label(spec: OptionSpec, value: object) -> str:
    for choice in spec.choices:
        if choice.value == value:
            return choice.label
    return str(value or "—")


def format_option_value(spec: OptionSpec, value: object) -> str:
    if spec.kind == "boolean":
        return "是" if bool(value) else "否"
    if spec.kind in {"choice", "grid_checkbox"}:
        return resolve_choice_label(spec, value)
    text = str(value).strip()
    return text or "—"


def summarize_sources(paths: Sequence[str]) -> str:
    if not paths:
        return "尚未添加文件"
    if len(paths) == 1:
        return paths[0]

    preview = "、".join(paths[:2])
    if len(paths) > 2:
        preview = f"{preview} 等共 {len(paths)} 个"
    return preview


def build_task_summary(
    config: ModeConfig,
    option_values: Mapping[str, object],
    sources: Sequence[str],
) -> str:
    lines = [
        f"{config.title}",
        f"{config.subtitle}",
        "",
        "【输入】",
        f"文件：{summarize_sources(sources)}",
        f"格式：{config.accepted_inputs}",
        "",
        "【当前参数】",
    ]

    for spec in config.option_specs:
        value = option_values.get(spec.key, spec.default)
        lines.append(f"{spec.label}：{format_option_value(spec, value)}")

    lines.extend(
        [
            "",
            "【将产出】",
            *[f"· {item}" for item in config.expected_outputs],
        ]
    )
    return "\n".join(lines)

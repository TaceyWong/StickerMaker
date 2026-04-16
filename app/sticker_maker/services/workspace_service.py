# coding: utf-8
from collections.abc import Mapping, Sequence

from sticker_maker.data.modes import ModeConfig, OptionSpec


def resolve_choice_label(spec: OptionSpec, value: object) -> str:
    for choice in spec.choices:
        if choice.value == value:
            return choice.label
    return str(value or "未设置")


def format_option_value(spec: OptionSpec, value: object) -> str:
    if spec.kind == "boolean":
        return "开启" if bool(value) else "关闭"
    if spec.kind == "choice":
        return resolve_choice_label(spec, value)
    text = str(value).strip()
    return text or "未填写"


def summarize_sources(paths: Sequence[str]) -> str:
    if not paths:
        return "等待拖入或选择文件"
    if len(paths) == 1:
        return paths[0]

    preview = "、".join(paths[:2])
    if len(paths) > 2:
        preview = f"{preview} 等 {len(paths)} 个文件"
    return preview


def build_task_summary(
    config: ModeConfig,
    option_values: Mapping[str, object],
    sources: Sequence[str],
) -> str:
    lines = [
        f"当前模式：{config.title}",
        f"模式说明：{config.subtitle}",
        "",
        "输入状态",
        f"- 已选择文件：{len(sources)} 个",
        f"- 当前素材：{summarize_sources(sources)}",
        f"- 支持类型：{config.accepted_inputs}",
        "",
        "参数摘要",
    ]

    for spec in config.option_specs:
        value = option_values.get(spec.key, spec.default)
        lines.append(f"- {spec.label}：{format_option_value(spec, value)}")

    lines.extend(
        [
            "",
            "预计输出",
            *[f"- {item}" for item in config.expected_outputs],
            "",
            "处理链路",
            *[
                f"- {index}. {step.title}：{step.description}"
                for index, step in enumerate(config.workflow_steps, start=1)
            ],
        ]
    )
    return "\n".join(lines)

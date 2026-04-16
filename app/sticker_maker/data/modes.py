# coding: utf-8
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OptionChoice:
    value: str
    label: str


@dataclass(frozen=True)
class OptionSpec:
    key: str
    label: str
    description: str
    kind: str
    default: str | bool
    choices: tuple[OptionChoice, ...] = field(default_factory=tuple)
    placeholder: str = ""


@dataclass(frozen=True)
class WorkflowStep:
    title: str
    description: str
    detail: str = ""


@dataclass(frozen=True)
class ModeConfig:
    key: str
    route: str
    title: str
    subtitle: str
    description: str
    accepted_inputs: str
    drop_hint: str
    shared_capabilities: tuple[str, ...]
    workflow_steps: tuple[WorkflowStep, ...]
    option_specs: tuple[OptionSpec, ...]
    expected_outputs: tuple[str, ...]


GRID_CHOICES = (
    OptionChoice("3x3", "3 x 3 九宫格"),
    OptionChoice("3x4", "3 x 4 十二宫格"),
    OptionChoice("4x3", "4 x 3 十二宫格"),
)

SOURCE_CHOICES = (
    OptionChoice("upload", "直接拖入拼版图片"),
    OptionChoice("multi-upload", "拖入多张拼版图片"),
    OptionChoice("reference", "拖入参考图生成（预留）"),
)

VIDEO_FRAME_CHOICES = (
    OptionChoice("keyframe", "优先提取关键帧"),
    OptionChoice("fixed-fps", "固定帧率抽帧"),
    OptionChoice("manual", "后续扩展手动抽帧"),
)

REMBG_MODEL_CHOICES = (
    OptionChoice("isnet-anime", "动漫 / 二次元（isnet-anime）"),
    OptionChoice("birefnet-portrait", "真人肖像（birefnet-portrait）"),
    OptionChoice("u2net_human_seg", "人体分割（u2net_human_seg）"),
    OptionChoice("isnet-general-use", "通用（isnet-general-use）"),
)

COMMON_CAPABILITIES = (
    "拖拽导入",
    "去右下角水印",
    "透明背景",
    "自动切图编号",
    "240 x 240 PNG 输出",
)

COMMON_IMAGE_OPTIONS = (
    OptionSpec(
        key="source_kind",
        label="素材来源",
        description="静态图与单个动态模式共用同一套导入入口，后续接入生成能力时可复用。",
        kind="choice",
        default="upload",
        choices=SOURCE_CHOICES,
    ),
    OptionSpec(
        key="grid_layout",
        label="宫格布局",
        description="README 中的三种拼版尺寸统一用配置驱动，避免后面在各视图里重复判断。",
        kind="choice",
        default="3x3",
        choices=GRID_CHOICES,
    ),
    OptionSpec(
        key="remove_watermark",
        label="去除右下角文字水印",
        description="可选步骤，对齐 README 的处理链路。",
        kind="boolean",
        default=True,
    ),
    OptionSpec(
        key="remove_background",
        label="去除背景并转透明",
        description="静态与动态流程共用的透明底输出开关。",
        kind="boolean",
        default=True,
    ),
    OptionSpec(
        key="rembg_model",
        label="去背景模型",
        description="二次元贴纸优先 isnet-anime；真人照片可换 birefnet-portrait 或 u2net_human_seg。",
        kind="choice",
        default="isnet-anime",
        choices=REMBG_MODEL_CHOICES,
    ),
)

STATIC_MODE = ModeConfig(
    key="static",
    route="mode-static",
    title="成套静态表情包",
    subtitle="从拼版图片切出一套标准尺寸的透明 PNG 表情。",
    description="适合处理九宫格或十二宫格素材，完成去水印、去背景、切割、裁边与标准化保存。",
    accepted_inputs="支持 PNG、JPG、JPEG、WEBP、BMP",
    drop_hint="拖入单张或多张 3 x 3、3 x 4、4 x 3 拼版图，或拖入参考图预留后续生成入口。",
    shared_capabilities=COMMON_CAPABILITIES,
    workflow_steps=(
        WorkflowStep("导入素材", "接收单张、多张拼版图片，或预留参考图生成入口。"),
        WorkflowStep("可选去水印", "针对图片右下角文字区域执行清理流程。"),
        WorkflowStep("透明背景", "执行背景去除并统一输出透明底图像。"),
        WorkflowStep("自动切图", "根据宫格布局逐行逐列切割并编号。"),
        WorkflowStep(
            "标准化输出",
            "扫描非透明边界、回退 5px、补齐正方形，再缩放为 240 x 240 PNG。",
            "输出尺寸与命名规范可复用于另外两种模式。",
        ),
    ),
    option_specs=COMMON_IMAGE_OPTIONS
    + (
        OptionSpec(
            key="output_dir",
            label="输出目录",
            description="用于后续真实处理任务的保存位置，当前模板会实时反映到摘要中。",
            kind="text",
            default="../output/static",
            placeholder="例如 ../output/static",
        ),
    ),
    expected_outputs=(
        "按行列顺序编号的透明 PNG 文件",
        "每张图片裁边后补齐为正方形",
        "统一缩放到 240 x 240",
    ),
)

DYNAMIC_MODE = ModeConfig(
    key="dynamic",
    route="mode-dynamic",
    title="单个动态表情包",
    subtitle="从静态拼版切出序列帧，并合成为单个循环 GIF。",
    description="复用静态模式的图像处理流程，在收尾阶段增加 GIF 序列合成。",
    accepted_inputs="支持 PNG、JPG、JPEG、WEBP、BMP",
    drop_hint="拖入单张或多张拼版图片，先完成切图和标准化，再按编号生成循环 GIF。",
    shared_capabilities=COMMON_CAPABILITIES + ("循环 GIF 合成",),
    workflow_steps=(
        WorkflowStep("导入素材", "拖入拼版图片或参考图，保留后续生成型工作流接入口。"),
        WorkflowStep("去水印", "可选移除右下角文字水印。"),
        WorkflowStep("透明背景", "统一转为透明底 PNG。"),
        WorkflowStep("自动切图", "根据宫格布局逐个切图并编号。"),
        WorkflowStep("标准化输出", "裁边、透明填充、缩放为 240 x 240 PNG。"),
        WorkflowStep("GIF 合成", "按照编号顺序合并为可无限循环的 GIF。"),
    ),
    option_specs=COMMON_IMAGE_OPTIONS
    + (
        OptionSpec(
            key="gif_interval",
            label="GIF 帧间隔(ms)",
            description="动态模式的独有参数，后续接 pillow 时可直接复用。",
            kind="text",
            default="120",
            placeholder="例如 120",
        ),
        OptionSpec(
            key="output_dir",
            label="输出目录",
            description="同时保存中间 PNG 与最终 GIF。",
            kind="text",
            default="../output/dynamic",
            placeholder="例如 ../output/dynamic",
        ),
    ),
    expected_outputs=(
        "按编号保存的透明 PNG 序列",
        "一个可无限循环播放的 GIF",
        "可复用的中间帧目录，便于后续调试",
    ),
)

VIDEO_MODE = ModeConfig(
    key="video",
    route="mode-video",
    title="通过视频成套动态表情包",
    subtitle="从单个拼版布局视频中抽帧，批量切出多套动态表情。",
    description="流程会先从视频获取 PNG 序列，再按 图片序列编号_行_列 的方式切分和聚合。",
    accepted_inputs="支持 MP4、MOV、AVI、MKV、WEBM",
    drop_hint="拖入一个包含 3 x 3、3 x 4 或 4 x 3 布局的视频文件，先抽关键帧，再进入图片工作流。",
    shared_capabilities=(
        "视频导入",
        "PNG 抽帧",
        "去水印",
        "透明背景",
        "批量切图编号",
        "分组 GIF 合成",
    ),
    workflow_steps=(
        WorkflowStep("导入视频", "拖入单个宫格布局视频并指定布局。"),
        WorkflowStep("抽取 PNG 序列", "调用 ffmpeg 提取关键帧或固定帧率序列。"),
        WorkflowStep("去水印", "可选移除右下角文字水印。"),
        WorkflowStep("透明背景", "统一将帧图转换为透明背景。"),
        WorkflowStep("切图与编号", "按 图片序列编号_行_列 规则切割每帧。"),
        WorkflowStep("分组 GIF 合成", "将相同图片序列编号的帧合成为无限循环 GIF。"),
    ),
    option_specs=(
        OptionSpec(
            key="grid_layout",
            label="宫格布局",
            description="视频模式也复用同一组布局配置。",
            kind="choice",
            default="3x3",
            choices=GRID_CHOICES,
        ),
        OptionSpec(
            key="frame_strategy",
            label="抽帧策略",
            description="对齐 README 中的关键帧提取能力，并为未来扩展预留入口。",
            kind="choice",
            default="keyframe",
            choices=VIDEO_FRAME_CHOICES,
        ),
        OptionSpec(
            key="remove_watermark",
            label="去除右下角文字水印",
            description="抽帧后可复用图片清理能力。",
            kind="boolean",
            default=True,
        ),
        OptionSpec(
            key="remove_background",
            label="去除背景并转透明",
            description="视频模式最终仍以透明底 PNG 与 GIF 输出。",
            kind="boolean",
            default=True,
        ),
        OptionSpec(
            key="rembg_model",
            label="去背景模型",
            description="与静态图相同：动漫用 isnet-anime，真人肖像用 birefnet-portrait。",
            kind="choice",
            default="isnet-anime",
            choices=REMBG_MODEL_CHOICES,
        ),
        OptionSpec(
            key="gif_interval",
            label="GIF 帧间隔(ms)",
            description="控制每组 GIF 的播放节奏。",
            kind="text",
            default="100",
            placeholder="例如 100",
        ),
        OptionSpec(
            key="output_dir",
            label="输出目录",
            description="保存抽帧 PNG、中间切图与分组合成的 GIF。",
            kind="text",
            default="../output/video",
            placeholder="例如 ../output/video",
        ),
    ),
    expected_outputs=(
        "按序号命名的抽帧 PNG 序列",
        "按 图片序列编号_行_列 命名的切图结果",
        "每个序列编号对应一张无限循环 GIF",
    ),
)

MODE_CONFIGS = (STATIC_MODE, DYNAMIC_MODE, VIDEO_MODE)

TECH_STACK = (
    "GUI：qfluentwidgets + PySide6",
    "打包：PyInstaller",
    "背景去除：rembg",
    "水印去除：LaMa",
    "视频关键帧：ffmpeg.exe",
    "图片处理：Pillow",
)

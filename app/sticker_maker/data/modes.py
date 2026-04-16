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
    OptionChoice("1x1", "1×1"),
    OptionChoice("2x2", "2×2"),
    OptionChoice("3x3", "3×3 九宫格"),
    OptionChoice("3x4", "3×4 十二宫格"),
    OptionChoice("4x3", "4×3 十二宫格"),
)

VIDEO_FRAME_CHOICES = (
    OptionChoice("keyframe", "关键帧（推荐）"),
    OptionChoice("fixed-fps", "固定帧率"),
)

REMBG_MODEL_CHOICES = (
    OptionChoice("isnet-anime", "动漫 / 二次元"),
    OptionChoice("bria-rmbg", "BRIA RMBG 2.0"),
    OptionChoice("birefnet-portrait", "真人肖像"),
    OptionChoice("u2net_human_seg", "人体分割"),
    OptionChoice("isnet-general-use", "通用场景（IS-Net）"),
)

COMMON_CAPABILITIES = (
    "宫格切图与编号",
    "透明底 240×240",
    "rembg 去背景",
    "裁边与正方形填充",
)

COMMON_IMAGE_OPTIONS = (
    OptionSpec(
        key="grid_layout",
        label="宫格布局",
        description="勾选一个与拼版图一致的布局。",
        kind="grid_checkbox",
        default="3x3",
        choices=GRID_CHOICES,
    ),
    OptionSpec(
        key="remove_watermark",
        label="去除右下角文字水印",
        description="当前版本尚未接入，勾选无效，仅保留开关。",
        kind="boolean",
        default=False,
    ),
    OptionSpec(
        key="remove_background",
        label="去除背景（透明）",
        description="开=使用默认 BRIA RMBG 2.0；关=跳过去背景。",
        kind="boolean",
        default=True,
    ),
)

STATIC_MODE = ModeConfig(
    key="static",
    route="mode-static",
    title="模式一 · 成套静态表情",
    subtitle="从拼版图切出一套 240×240 透明 PNG。",
    description="拖入与布局一致的宫格拼版图，按行列编号导出多张表情。",
    accepted_inputs="PNG、JPG、JPEG、WEBP、BMP",
    drop_hint="拖入一张或多张宫格拼版图；支持多文件批量处理。",
    shared_capabilities=COMMON_CAPABILITIES,
    workflow_steps=(
        WorkflowStep("导入", "选择拼版图片（大模型生成入口将后续补充）。"),
        WorkflowStep("可选去水印", "清理右下角文字（开发中）。"),
        WorkflowStep("去背景", "转为透明底（可关）。"),
        WorkflowStep("切图", "按所选宫格逐格切割并编号。"),
        WorkflowStep(
            "标准化",
            "沿非透明区域裁切、外扩 5px、置于正方形画布，再缩放到 240×240。",
        ),
    ),
    option_specs=COMMON_IMAGE_OPTIONS
    + (
        OptionSpec(
            key="output_dir",
            label="输出目录",
            description="相对应用目录的路径；任务会在其下按时间戳建子文件夹。",
            kind="text",
            default="../output/static",
            placeholder="../output/static",
        ),
    ),
    expected_outputs=(
        "png/ 下按 0001、0002… 编号的透明 PNG",
        "每格裁边后为正方形，边长 240px",
    ),
)

DYNAMIC_MODE = ModeConfig(
    key="dynamic",
    route="mode-dynamic",
    title="模式二 · 单个动态表情",
    subtitle="切图后按帧序合成一个循环 GIF。",
    description="流程与静态相同，最后将切出的 PNG 序列合并为一张无限循环 GIF。",
    accepted_inputs="PNG、JPG、JPEG、WEBP、BMP",
    drop_hint="拖入一张或多张拼版图；多图时按文件名顺序参与编号与合成。",
    shared_capabilities=COMMON_CAPABILITIES + ("循环 GIF",),
    workflow_steps=(
        WorkflowStep("导入", "选择拼版图片。"),
        WorkflowStep("可选去水印", "清理右下角文字（开发中）。"),
        WorkflowStep("去背景", "透明底处理。"),
        WorkflowStep("切图与标准化", "同静态模式。"),
        WorkflowStep("合成 GIF", "按编号顺序合并为循环 GIF（output.gif）。"),
    ),
    option_specs=COMMON_IMAGE_OPTIONS
    + (
        OptionSpec(
            key="gif_interval",
            label="GIF 帧间隔（毫秒）",
            description="数值越小动画越快。",
            kind="text",
            default="120",
            placeholder="120",
        ),
        OptionSpec(
            key="output_dir",
            label="输出目录",
            description="包含 png/ 序列与同目录下的 output.gif。",
            kind="text",
            default="../output/dynamic",
            placeholder="../output/dynamic",
        ),
    ),
    expected_outputs=(
        "png/ 下切图序列",
        "同目录 output.gif（循环播放）",
    ),
)

VIDEO_MODE = ModeConfig(
    key="video",
    route="mode-video",
    title="模式三 · 视频成套动态表情",
    subtitle="从宫格布局视频中抽帧，按格位输出多组 GIF。",
    description="对每一帧做切图与标准化，再按「行_列」分组，每组合成一条循环 GIF。",
    accepted_inputs="MP4、MOV、AVI、MKV、WEBM",
    drop_hint="拖入一个视频文件；画面需为稳定的宫格拼版布局。",
    shared_capabilities=(
        "ffmpeg 抽帧",
        "宫格切图",
        "透明底 240×240",
        "按格位 GIF",
    ),
    workflow_steps=(
        WorkflowStep("导入视频", "单个文件，并选择与画面一致的宫格。"),
        WorkflowStep("抽帧", "关键帧或固定帧率，得到有序 PNG 序列。"),
        WorkflowStep("可选去水印", "右下角文字（开发中）。"),
        WorkflowStep("去背景", "每帧单独处理。"),
        WorkflowStep("切图", "每帧按行列切格，路径含帧序号与格位。"),
        WorkflowStep("合成 GIF", "同一格位上的帧合成一条循环 GIF。"),
    ),
    option_specs=(
        OptionSpec(
            key="grid_layout",
            label="宫格布局",
            description="与视频画面中的格子划分一致。",
            kind="choice",
            default="3x3",
            choices=GRID_CHOICES,
        ),
        OptionSpec(
            key="frame_strategy",
            label="抽帧方式",
            description="关键帧适合变化少的画面；固定帧率按间隔均匀取帧。",
            kind="choice",
            default="keyframe",
            choices=VIDEO_FRAME_CHOICES,
        ),
        OptionSpec(
            key="remove_watermark",
            label="去除右下角文字水印",
            description="当前版本尚未接入，勾选无效。",
            kind="boolean",
            default=False,
        ),
        OptionSpec(
            key="remove_background",
            label="去除背景（透明）",
            description="对每一视频帧去背景；CPU 下可能较慢。",
            kind="boolean",
            default=True,
        ),
        OptionSpec(
            key="gif_interval",
            label="GIF 帧间隔（毫秒）",
            description="控制每条格位 GIF 的播放速度。",
            kind="text",
            default="100",
            placeholder="100",
        ),
        OptionSpec(
            key="output_dir",
            label="输出目录",
            description="含 extracted_frames、cells、gifs 等子目录。",
            kind="text",
            default="../output/video",
            placeholder="../output/video",
        ),
    ),
    expected_outputs=(
        "抽帧 PNG 序列",
        "按格位目录保存的切图",
        "gifs/ 下每条格位一条循环 GIF",
    ),
)

MODE_CONFIGS = (STATIC_MODE, DYNAMIC_MODE, VIDEO_MODE)

TECH_STACK = (
    "界面：qfluentwidgets（Fluent Design）",
    "去背景：rembg（模型位于 app/resource/models，见 U2NET_HOME）",
    "去水印：LaMa（计划中）",
    "视频：ffmpeg（需在系统 PATH 中可用）",
    "图像：Pillow / Qt 图像管线",
)

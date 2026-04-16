# coding: utf-8
from PySide6.QtWidgets import QLabel

from sticker_maker.data.modes import TECH_STACK
from sticker_maker.widgets.common import ScrollPage, SectionCard


class SettingsView(ScrollPage):
    def __init__(self, parent=None):
        super().__init__("settings", parent)

        guidance = SectionCard(
            "项目约定",
            "这里集中展示当前模板的实现边界和后续扩展方向，方便继续开发时保持结构一致。",
            self.container,
        )
        for line in (
            "代码按入口、主窗口、视图、组件、服务、静态数据拆分。",
            "三种模式共用同一套工作区页面，通过配置数据描述差异。",
            "文件读写统一使用 UTF-8，不写入 BOM。",
            "真实处理能力建议从 services 层继续向下拆到 image/video 子模块。",
        ):
            label = QLabel(f"• {line}", guidance)
            label.setObjectName("sectionDescription")
            label.setWordWrap(True)
            guidance.body_layout.addWidget(label)

        self.content_layout.addWidget(guidance)

        stack = SectionCard(
            "技术栈映射",
            "README 中的关键依赖已经整理到这里，便于逐项接入。",
            self.container,
        )
        for item in TECH_STACK:
            label = QLabel(f"• {item}", stack)
            label.setObjectName("sectionDescription")
            label.setWordWrap(True)
            stack.body_layout.addWidget(label)

        self.content_layout.addWidget(stack)
        self.content_layout.addStretch(1)

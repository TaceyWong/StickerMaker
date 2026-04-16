# coding: utf-8
from PySide6.QtWidgets import QGridLayout, QLabel

from sticker_maker.data.modes import MODE_CONFIGS, TECH_STACK
from sticker_maker.widgets.common import HeroCard, ScrollPage, SectionCard, TagChip


class OverviewView(ScrollPage):
    def __init__(self, parent=None):
        super().__init__("overview", parent)

        hero = HeroCard(
            "StickerMaker",
            "围绕 README 的三条核心工作流构建桌面端骨架：左侧导航切换模式，右侧工作区负责素材、参数、流程与输出摘要。",
            ("模块化结构", "流程复用", "后续可接入图片处理引擎"),
            self.container,
        )
        self.content_layout.addWidget(hero)

        mode_section = SectionCard(
            "三种模式",
            "三张模式卡片使用同一份配置数据渲染，后续只要补服务层即可接入真实处理逻辑。",
            self.container,
        )
        mode_grid = QGridLayout()
        mode_grid.setSpacing(12)

        for index, config in enumerate(MODE_CONFIGS):
            card = SectionCard(config.title, config.subtitle, mode_section)

            description = QLabel(config.description, card)
            description.setWordWrap(True)
            description.setObjectName("sectionDescription")
            card.body_layout.addWidget(description)

            for tag in config.shared_capabilities[:3]:
                card.body_layout.addWidget(TagChip(tag, card))

            mode_grid.addWidget(card, index // 2, index % 2)

        mode_section.body_layout.addLayout(mode_grid)
        self.content_layout.addWidget(mode_section)

        stack_section = SectionCard(
            "技术栈与规划",
            "README 中的关键依赖和处理链路已经映射到当前 UI，便于后续逐步落地。",
            self.container,
        )
        for item in TECH_STACK:
            label = QLabel(f"• {item}", stack_section)
            label.setObjectName("sectionDescription")
            label.setWordWrap(True)
            stack_section.body_layout.addWidget(label)

        self.content_layout.addWidget(stack_section)
        self.content_layout.addStretch(1)

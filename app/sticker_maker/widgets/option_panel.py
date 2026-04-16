# coding: utf-8
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QFrame, QLabel, QLineEdit, QVBoxLayout, QWidget

from sticker_maker.data.modes import OptionSpec


class OptionPanel(QFrame):
    optionsChanged = Signal(dict)

    def __init__(self, option_specs: tuple[OptionSpec, ...], parent: QWidget | None = None):
        super().__init__(parent)
        self.option_specs = option_specs
        self.controls: dict[str, QWidget] = {}
        self.setObjectName("sectionCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("参数", self)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addLayout(form_layout)

        for spec in self.option_specs:
            description = QLabel(spec.description, self)
            description.setObjectName("fieldDescription")
            description.setWordWrap(True)

            field_layout = QVBoxLayout()
            field_layout.setSpacing(6)
            field_layout.addWidget(description)

            editor = self._create_editor(spec)
            self.controls[spec.key] = editor
            field_layout.addWidget(editor)

            field_container = QWidget(self)
            field_container.setLayout(field_layout)
            form_layout.addRow(spec.label, field_container)

        layout.addStretch(1)

    def _create_editor(self, spec: OptionSpec) -> QWidget:
        if spec.kind == "choice":
            editor = QComboBox(self)
            for choice in spec.choices:
                editor.addItem(choice.label, choice.value)
            index = editor.findData(spec.default)
            editor.setCurrentIndex(max(index, 0))
            editor.currentIndexChanged.connect(self._emit_options_changed)
            return editor

        if spec.kind == "boolean":
            editor = QCheckBox(self)
            editor.setChecked(bool(spec.default))
            editor.stateChanged.connect(self._emit_options_changed)
            return editor

        editor = QLineEdit(self)
        editor.setPlaceholderText(spec.placeholder)
        editor.setText(str(spec.default))
        editor.textChanged.connect(self._emit_options_changed)
        return editor

    def values(self) -> dict[str, object]:
        values: dict[str, object] = {}
        for spec in self.option_specs:
            editor = self.controls[spec.key]
            if isinstance(editor, QComboBox):
                values[spec.key] = editor.currentData()
            elif isinstance(editor, QCheckBox):
                values[spec.key] = editor.isChecked()
            elif isinstance(editor, QLineEdit):
                values[spec.key] = editor.text().strip()
        return values

    def _emit_options_changed(self) -> None:
        self.optionsChanged.emit(self.values())

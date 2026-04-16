# coding: utf-8
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from sticker_maker.data.modes import OptionSpec


class OptionPanel(QFrame):
    optionsChanged = Signal(dict)

    def __init__(self, option_specs: tuple[OptionSpec, ...], parent: QWidget | None = None):
        super().__init__(parent)
        self.option_specs = option_specs
        self.controls: dict[str, QWidget] = {}
        self.grid_groups: dict[str, list[QCheckBox]] = {}
        self.labels: dict[str, QLabel] = {}
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
            label = QLabel(spec.label, self)
            label.setToolTip(spec.description)
            editor = self._create_editor(spec)
            editor.setToolTip(spec.description)
            self.labels[spec.key] = label
            self.controls[spec.key] = editor
            form_layout.addRow(label, editor)

        self._apply_conditional_visibility()
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

        if spec.kind == "grid_checkbox":
            container = QWidget(self)
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(10)
            checkboxes: list[QCheckBox] = []
            for choice in spec.choices:
                cb = QCheckBox(choice.label, container)
                cb.setProperty("value", choice.value)
                cb.setChecked(choice.value == spec.default)
                cb.toggled.connect(lambda checked, s=spec, c=cb: self._on_grid_toggled(s.key, c, checked))
                row.addWidget(cb)
                checkboxes.append(cb)
            row.addStretch(1)
            self.grid_groups[spec.key] = checkboxes
            return container

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
            elif spec.kind == "grid_checkbox":
                selected = spec.default
                for cb in self.grid_groups.get(spec.key, []):
                    if cb.isChecked():
                        selected = str(cb.property("value"))
                        break
                values[spec.key] = selected
        return values

    def _on_grid_toggled(self, key: str, target: QCheckBox, checked: bool) -> None:
        if not checked:
            if not any(cb.isChecked() for cb in self.grid_groups.get(key, [])):
                target.setChecked(True)
            return
        for cb in self.grid_groups.get(key, []):
            if cb is not target:
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
        self._apply_conditional_visibility()
        self._emit_options_changed()

    def _emit_options_changed(self) -> None:
        self._apply_conditional_visibility()
        self.optionsChanged.emit(self.values())

    def _selected_grid_layout(self) -> str:
        grid_spec = next((spec for spec in self.option_specs if spec.kind == "grid_checkbox"), None)
        if grid_spec is None:
            return ""
        for cb in self.grid_groups.get(grid_spec.key, []):
            if cb.isChecked():
                return str(cb.property("value"))
        return str(grid_spec.default)

    def _apply_conditional_visibility(self) -> None:
        selected_grid = self._selected_grid_layout()
        show_one_by_one_options = selected_grid == "1x1"
        for key in ("output_width", "output_height", "keep_aspect_ratio"):
            label = self.labels.get(key)
            editor = self.controls.get(key)
            if label is not None:
                label.setVisible(show_one_by_one_options)
            if editor is not None:
                editor.setVisible(show_one_by_one_options)

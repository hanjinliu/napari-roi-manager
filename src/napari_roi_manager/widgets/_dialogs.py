from __future__ import annotations

from textwrap import wrap
from typing import TYPE_CHECKING

from qtpy import QtCore, QtGui
from qtpy import QtWidgets as QtW

if TYPE_CHECKING:
    from napari_roi_manager.layers import RoiManagerLayer


class QCustomDialog(QtW.QDialog):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)

        layout = QtW.QVBoxLayout(self)
        self._message = QtW.QLabel(self)
        layout.addWidget(self._message)

        self._buttons = QtW.QWidget(self)
        _btn_layout = QtW.QHBoxLayout(self._buttons)
        _btn_layout.setContentsMargins(0, 0, 0, 0)
        _btn_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._buttons)
        self._last_clicked = None

    def exec_dialog(self) -> str | None:
        if self.exec():
            return self._last_clicked
        else:
            return None

    @classmethod
    def construct(
        cls,
        title: str,
        message: str,
        choices: list[str],
        parent: QtW.QWidget | None = None,
    ) -> QCustomDialog:
        self = cls(parent)
        self.setWindowTitle(title)
        self._message.setText("\n".join(wrap(message)))
        for choice in choices:
            btn = QtW.QPushButton(choice, self._buttons)
            self._buttons.layout().addWidget(btn)
            btn.clicked.connect(self._make_callback(choice))
        return self

    def _make_callback(self, choice: str):
        def callback():
            self._last_clicked = choice
            self.accept()

        return callback


def _labeled(text: str, widget: QtW.QWidget) -> QtW.QWidget:
    out = QtW.QWidget()
    layout = QtW.QHBoxLayout()
    layout.addWidget(QtW.QLabel(text))
    layout.addWidget(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    out.setLayout(layout)
    return out


class QSpecifyDialog(QtW.QDialog):
    def __init__(self, layer: RoiManagerLayer, parent: QtW.QWidget | None = None):
        super().__init__(parent)

        self.layer = layer
        layout = QtW.QVBoxLayout(self)
        self.width_input = QtW.QLineEdit("256", self)
        self.width_input.setValidator(QtGui.QDoubleValidator())
        self.height_input = QtW.QLineEdit("256", self)
        self.height_input.setValidator(QtGui.QDoubleValidator())
        self.x_input = QtW.QLineEdit("128", self)
        self.x_input.setValidator(QtGui.QDoubleValidator())
        self.y_input = QtW.QLineEdit("128", self)
        self.y_input.setValidator(QtGui.QDoubleValidator())
        self.multiply_by_scale = QtW.QCheckBox("Multiply by scale", self)
        self.run_button = QtW.QPushButton("OK", self)

        layout.addWidget(_labeled("Width", self.width_input))
        layout.addWidget(_labeled("Height", self.height_input))
        layout.addWidget(_labeled("X coordinate", self.x_input))
        layout.addWidget(_labeled("Y coordinate", self.y_input))
        layout.addWidget(self.multiply_by_scale)
        layout.addWidget(self.run_button)

        self.width_input.textChanged.connect(self._on_value_changed)
        self.height_input.textChanged.connect(self._on_value_changed)
        self.x_input.textChanged.connect(self._on_value_changed)
        self.y_input.textChanged.connect(self._on_value_changed)
        self.multiply_by_scale.stateChanged.connect(self._on_value_changed)

        self.run_button.clicked.connect(self.accept)

        if layer.mode != "add_rectangle":
            layer.mode = "add_rectangle"

        self._on_value_changed()

    def _on_value_changed(self):
        yscale, xscale = (
            self.layer.scale[-2:] if self.multiply_by_scale.isChecked() else (1, 1)
        )
        width = float(self.width_input.text()) * xscale
        height = float(self.height_input.text()) * yscale
        x = float(self.x_input.text()) * xscale
        y = float(self.y_input.text()) * yscale
        new_data = [[y, x], [y + height, x], [y + height, x + width], [y, x + width]]
        if (ci := self.layer._current_item) is None:
            self.layer.add(new_data, shape_type="rectangle")
        else:
            self.layer.data = (
                self.layer.data[:ci] + new_data + self.layer.data[ci + 1 :]
            )

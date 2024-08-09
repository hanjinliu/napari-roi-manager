from __future__ import annotations

from textwrap import wrap

from qtpy import QtCore
from qtpy import QtWidgets as QtW


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

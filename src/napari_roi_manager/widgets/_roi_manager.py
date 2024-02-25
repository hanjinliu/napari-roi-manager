import napari
from qtpy import QtCore
from qtpy import QtWidgets as QtW

from napari_roi_manager.layers import RoiManagerLayer


class QRoiManagerButtons(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtW.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        self._add_roi_btn = QtW.QPushButton("Add", self)
        self._remove_roi_btn = QtW.QPushButton("Remove", self)
        self._to_shapes_btn = QtW.QPushButton("To Shapes", self)
        self._show_all_checkbox = QtW.QCheckBox("Show All", self)
        self._show_all_checkbox.setChecked(True)
        layout.addWidget(self._add_roi_btn)
        layout.addWidget(self._remove_roi_btn)
        layout.addWidget(self._to_shapes_btn)
        layout.addWidget(self._show_all_checkbox)

        self.setFixedWidth(95)


class QRoiListWidget(QtW.QTableWidget):
    selected = QtCore.Signal(set)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["name", "type"])
        self.setColumnWidth(0, 80)
        self.setColumnWidth(1, 65)
        self.horizontalHeader().setFixedHeight(18)
        self.setMaximumWidth(180)
        self.verticalHeader().setSectionResizeMode(
            QtW.QHeaderView.ResizeMode.Fixed
        )
        self.itemSelectionChanged.connect(self._selection_changed)

    def addRow(self, text: str, shape_type: str):
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, QtW.QTableWidgetItem(text))
        item = QtW.QTableWidgetItem(shape_type)
        # set read only
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 1, item)
        self.setRowHeight(row, 18)

    def _selection_changed(self):
        indices = {idx.row() for idx in self.selectedIndexes()}
        self.selected.emit(indices)


class QRoiManager(QtW.QWidget):
    def __init__(self, viewer: napari.Viewer):
        self._viewer = viewer
        super().__init__()

        layout = QtW.QHBoxLayout()
        self.setLayout(layout)

        layer = RoiManagerLayer(name="ROIs")
        viewer.add_layer(layer)

        self._btns = QRoiManagerButtons(self)
        self._btns.setSizePolicy(
            QtW.QSizePolicy.Policy.Fixed, QtW.QSizePolicy.Policy.Expanding
        )
        self._roilist = QRoiListWidget(self)
        self._roilist.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        layout.addWidget(
            self._roilist,
            2,
            QtCore.Qt.AlignmentFlag.AlignTop
            | QtCore.Qt.AlignmentFlag.AlignLeft,
        )
        layout.addWidget(
            self._btns,
            1,
            QtCore.Qt.AlignmentFlag.AlignTop
            | QtCore.Qt.AlignmentFlag.AlignRight,
        )
        self.connect_layer(layer)
        self._layer = layer

    def connect_layer(self, layer: RoiManagerLayer):
        btns = self._btns
        roilist = self._roilist
        btns._add_roi_btn.clicked.connect(layer.register_roi)
        btns._remove_roi_btn.clicked.connect(layer.remove_selected)

        btns._to_shapes_btn.clicked.connect(self.as_shapes_layer)

        @btns._show_all_checkbox.stateChanged.connect
        def _show_all_changed(val):
            layer.show_all = val == QtCore.Qt.CheckState.Checked

        @layer.events.roi_added.connect
        def _roi_added(event):
            tp = event.shape_type
            nr = roilist.rowCount()
            roilist.addRow(f"ROI-{nr:>04}", tp)

        @layer.events.roi_removed.connect
        def _roi_removed(event):
            indices = sorted(event.indices)
            for idx in reversed(indices):
                roilist.removeRow(idx)

        @roilist.selected.connect
        def _roi_selected(indices):
            layer._remove_current()
            if layer.show_all:
                layer.selected_data = set(indices)

    def add(self, data, shape_type: str = "rectangle"):
        return self._layer.add(data, shape_type=shape_type)

    def register(self):
        self._layer.register_roi()

    def select(self, indices=()):
        if not hasattr(indices, "__iter__"):
            indices = {indices}
        self._layer.selected_data = set(indices)

    def remove(self, indices=None):
        if indices is not None:
            self._layer.selected_data = set(indices)
        self._layer.remove_selected()

    def set_show_all(self, show_all: bool):
        self._btns._show_all_checkbox.setChecked(show_all)

    def as_shapes_layer(self):
        shapes = self._layer.as_shapes_layer()
        self._viewer.add_layer(shapes)

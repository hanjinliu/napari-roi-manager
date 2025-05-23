from collections.abc import Iterable
from pathlib import Path

import napari
import numpy as np
from qtpy import QtCore
from qtpy import QtWidgets as QtW
from roifile import roiread, roiwrite

from napari_roi_manager.ij._convert import roi_to_shape, shape_to_roi
from napari_roi_manager.layers import RoiManagerLayer
from napari_roi_manager.widgets._dialogs import QCustomDialog


class QRoiManagerButtons(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtW.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        # button widgets
        self._add_roi_btn = QtW.QPushButton("Add", self)
        self._add_roi_btn.setToolTip("Add the current ROI to the manager.")
        self._remove_roi_btn = QtW.QPushButton("Remove", self)
        self._add_roi_btn.setToolTip("Remove selected ROI from the manager.")
        self._specify_btn = QtW.QPushButton("Specify", self)
        self._specify_btn.setToolTip("Specify the shape/position of the ROI.")
        self._load_roiset_btn = QtW.QPushButton("Load", self)
        self._load_roiset_btn.setToolTip("Load ROIs from a file.")
        self._save_roiset_btn = QtW.QPushButton("Save", self)
        self._save_roiset_btn.setToolTip("Save ROIs to a file.")
        self._to_shapes_btn = QtW.QPushButton("To Shapes", self)
        self._to_shapes_btn.setToolTip("Convert ROIs to the builtin shapes layer.")

        # text related
        self._text_group = QtW.QGroupBox("ROI Text")
        _text_group_layout = QtW.QVBoxLayout(self._text_group)
        _text_group_layout.setContentsMargins(2, 8, 2, 4)
        self._text_feature_name = QtW.QComboBox()
        self._text_feature_name.addItems(["ID", "Name"])
        self._text_font_size = QtW.QSpinBox()
        self._text_font_size.setRange(4, 64)
        self._text_font_size.setValue(9)
        self._text_font_size.setToolTip("Font size for the ROI text.")
        self._text_font_size.setSuffix(" pt")
        _text_group_layout.addWidget(self._text_feature_name)
        _text_group_layout.addWidget(self._text_font_size)

        self._show_all_checkbox = QtW.QCheckBox("Show All", self)
        self._show_all_checkbox.setChecked(True)

        # add all the widgets
        layout.addWidget(self._add_roi_btn)
        layout.addWidget(self._remove_roi_btn)
        layout.addWidget(self._specify_btn)
        layout.addWidget(self._load_roiset_btn)
        layout.addWidget(self._save_roiset_btn)
        layout.addWidget(self._to_shapes_btn)
        layout.addWidget(self._text_group)
        layout.addWidget(self._show_all_checkbox)

        self.setFixedWidth(115)


class QRoiListWidget(QtW.QTableWidget):
    selected = QtCore.Signal(set)
    renamed = QtCore.Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["name", "type"])
        self.setColumnWidth(0, 80)
        self.setColumnWidth(1, 65)
        self.horizontalHeader().setFixedHeight(18)
        self.setMaximumWidth(180)
        self.verticalHeader().setSectionResizeMode(QtW.QHeaderView.ResizeMode.Fixed)
        self._blocking_cell_changed = False
        self.itemSelectionChanged.connect(self._selection_changed)
        self.cellChanged.connect(self._cell_changed)

    def addRow(self, text: str, shape_type: str):
        row = self.rowCount()
        self._blocking_cell_changed = True
        try:
            self.insertRow(row)
            self.setItem(row, 0, QtW.QTableWidgetItem(text))
            item = QtW.QTableWidgetItem(shape_type)
            # set read only
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.setItem(row, 1, item)
        finally:
            self._blocking_cell_changed = False
        self.setRowHeight(row, 18)

    def get_column(self, col: str) -> list[str]:
        col_idx = self._get_column_index(col)
        return [self.item(row, col_idx).text() for row in range(self.rowCount())]

    def set_column(self, col: str, values: list[str]):
        col_idx = self._get_column_index(col)
        self._blocking_cell_changed = True
        try:
            for row, value in enumerate(values):
                self.setItem(row, col_idx, QtW.QTableWidgetItem(value))
        finally:
            self._blocking_cell_changed = False

    def _get_column_index(self, col: str) -> int:
        col_idx = -1
        for i in range(self.columnCount()):
            if self.horizontalHeaderItem(i).text() == col:
                col_idx = i
                break
        else:
            raise ValueError(f"Column {col!r} not found.")
        return col_idx

    def _selection_changed(self):
        indices = {idx.row() for idx in self.selectedIndexes()}
        self.selected.emit(indices)

    def _cell_changed(self, row: int, col: int):
        if self._blocking_cell_changed or col != 0:
            return
        self.renamed.emit(row, self.item(row, col).text())


class QRoiManager(QtW.QWidget):
    def __init__(self, viewer: napari.Viewer):
        self._viewer = viewer
        super().__init__()

        layout = QtW.QHBoxLayout()
        self.setLayout(layout)

        layer = RoiManagerLayer(name="ROIs", roi_manager=self)
        viewer.add_layer(layer)

        self._btns = QRoiManagerButtons(self)
        _SP = QtW.QSizePolicy.Policy
        _AF = QtCore.Qt.AlignmentFlag
        self._btns.setSizePolicy(_SP.Fixed, _SP.Expanding)
        self._roilist = QRoiListWidget(self)
        self._roilist.setSizePolicy(_SP.Expanding, _SP.Expanding)
        layout.addWidget(self._roilist, 2, _AF.AlignTop | _AF.AlignLeft)
        layout.addWidget(self._btns, 1, _AF.AlignTop | _AF.AlignRight)
        self.connect_layer(layer)
        self._layer = layer

    @classmethod
    def get_or_create(cls):
        """Get the RoiManager from the viewer or create a new one."""
        viewer = napari.current_viewer()
        if viewer is None:
            raise RuntimeError("No active viewer found.")
        for dock_widget in viewer.window._dock_widgets.values():
            if isinstance(inner := dock_widget.widget(), cls):
                return inner
        return cls(viewer)

    def connect_layer(self, layer: RoiManagerLayer):
        btns = self._btns
        roilist = self._roilist
        btns._add_roi_btn.clicked.connect(layer.register_roi)
        btns._remove_roi_btn.clicked.connect(self._remove_button_clicked)
        btns._specify_btn.clicked.connect(self.specify_roi)
        btns._load_roiset_btn.clicked.connect(self.load_roiset)
        btns._save_roiset_btn.clicked.connect(self.save_roiset)
        btns._text_feature_name.currentIndexChanged.connect(self.set_text_feature_name)
        btns._text_font_size.valueChanged.connect(self.set_text_font_size)
        btns._to_shapes_btn.clicked.connect(self.as_shapes_layer)

        @btns._show_all_checkbox.stateChanged.connect
        def _show_all_changed(val):
            layer.show_all = val == QtCore.Qt.CheckState.Checked

        @layer.events.roi_added.connect
        def _roi_added(event):
            tp = event.shape_type
            name = getattr(event, "name", f"ROI-{event.index:>04}")
            roilist.addRow(name, tp)

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

        @roilist.renamed.connect
        def _roi_renamed(index: int, name: str):
            col = roilist.get_column("name")
            df = layer.features
            df["name"] = col
            layer.features = df

    def add(self, data, shape_type: str = "rectangle"):
        return self._layer.add(data, shape_type=shape_type)

    def register(self, data=None, shape_type: str = "rectangle"):
        """Register the current ROI to the manager."""
        if data is not None:
            self.add(data, shape_type=shape_type)
        self._layer.register_roi()

    def select(self, indices=()):
        if not isinstance(indices, Iterable):
            indices = {indices}
        self._layer.selected_data = set(indices)

    def remove(self, indices=None):
        if indices is not None:
            self._layer.selected_data = set(indices)
        self._layer.remove_selected()

    def specify_roi(self):
        from napari_roi_manager.widgets._dialogs import QSpecifyDialog

        dlg = QSpecifyDialog(self._layer, self)
        dlg.exec_()

    def _remove_button_clicked(self):
        if self._layer.show_all:
            self._layer.remove_selected()
        else:
            to_remove = sorted(
                {index.row() for index in self._roilist.selectedIndexes()},
                reverse=True,
            )
            for i in to_remove:
                self._layer._hidden_shapes.pop(i)
                self._roilist.removeRow(i)

    def set_text_feature_name(self, idx: int):
        self._layer.text_feature_name = ["id", "name"][idx]

    def set_text_font_size(self, size: int):
        self._layer.text.size = size

    def set_show_all(self, show_all: bool):
        self._btns._show_all_checkbox.setChecked(show_all)

    def as_shapes_layer(self):
        shapes = self._layer.as_shapes_layer()
        self._viewer.add_layer(shapes)

    def load_roiset(self, *, path=None, append: bool = True):
        if path is None:
            file = QtW.QFileDialog.getOpenFileName(
                self,
                "Open ROIs",
                filter="JSON (*.json;*.txt);;ImageJ ROI (*.roi;*.zip);;All Files (*)",
            )
            if file:
                path = file[0]
                if not path:
                    return
            else:
                return
            if self._layer.roi_count() > 0:
                res = QCustomDialog.construct(
                    title="Append or Replace",
                    message=(
                        "ROIs are already registered. Do you want to append the "
                        "incoming ROIs or replace the existing ones?"
                    ),
                    choices=["Append", "Replace", "Cancel"],
                    parent=self,
                ).exec_dialog()
                if res == "Replace":
                    append = False
                elif res is None or res == "Cancel":
                    return
        path = Path(path)
        if path.suffix in (".zip", ".roi"):
            self.read_ij_roi(path)
        else:
            self._layer.update_from_json(path, append=append)

    def save_roiset(self, *, path=None):
        if path is None:
            file = QtW.QFileDialog.getSaveFileName(
                self,
                "Save ROIs",
                filter="JSON (*.json;*.txt);;ImageJ ROI (*.zip);;All Files (*)",
            )
            if file:
                path = file[0]
                if not path:
                    return
            else:
                return
        path = Path(path)
        if path.suffix in (".zip",):
            self.write_ij_roi(path)
        else:
            self._layer.write_json(path)

    def read_ij_roi(self, path):
        ijrois = roiread(path)
        if isinstance(ijrois, list):
            shapes = [roi_to_shape(roi) for roi in ijrois]
        else:
            shapes = [roi_to_shape(ijrois)]
        n_multi_dims = self._viewer.dims.ndim - 2
        with self._layer.events.data.blocker():
            for idx, shape in enumerate(shapes):
                if shape is None:
                    continue
                ndata = shape.data.shape[0]
                if n_multi_dims > 0:
                    multi_dim_coords = np.empty(
                        (ndata, n_multi_dims), dtype=shape.data.dtype
                    )
                    multi_dim_coords[:] = shape.multidim[n_multi_dims:]
                    coords = np.stack([multi_dim_coords, shape.data], axis=1)
                else:
                    coords = shape.data
                self._layer.add(coords, shape_type=shape.shape_type)
                self._layer.events.roi_added(
                    index=idx, shape_type=shape.shape_type, name=shape.name
                )
        return self._layer

    def write_ij_roi(self, path):
        path = Path(path)
        if path.suffix != ".zip":
            path = path.with_suffix(".zip")
        if path.exists():
            path.unlink()
        rois = [
            shape_to_roi(shape) for shape in self._layer.get_roi_data().iter_shapes()
        ]
        roiwrite(path, rois)

from __future__ import annotations

import json
import weakref
from collections.abc import Iterable
from contextlib import nullcontext
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from napari.layers import Shapes
from napari.layers.base import ActionType
from napari.utils.events import Event

from napari_roi_manager._dataclasses import HiddenShapes, RoiData

if TYPE_CHECKING:
    from napari_roi_manager.widgets._roi_manager import QRoiManager


class TextFeatureName(Enum):
    ID = "id"
    NAME = "name"


class RoiManagerLayer(Shapes):
    """Layer for managing ROIs."""

    _type_string = "shapes"

    def __init__(self, *args, roi_manager: QRoiManager | None = None, **kwargs):
        self._current_item: int | None = None
        # the last current_item before unchecking "show all"
        self._show_all = True
        self._text_feature_name = TextFeatureName.ID
        self._hidden_shapes = HiddenShapes()
        if roi_manager is not None:
            self._roi_manager_ref = weakref.ref(roi_manager)
        else:
            self._roi_manager_ref = lambda: None

        kwargs["face_color"] = [0.0, 0.0, 0.0, 0.0]
        kwargs["edge_color"] = [1.0, 1.0, 0.0, 1.0]
        kwargs["ndim"] = 2
        kwargs["text"] = {
            "string": "{id}",
            "color": "yellow",
            "visible": False,
            "size": 9,
        }
        kwargs["features"] = {"id": np.arange(0, dtype=np.uint32)}
        super().__init__(*args, **kwargs)
        self.events.add(
            roi_added=Event,
            roi_removed=Event,
        )

        # `_current_item` is the index of the current (not registered yet) ROI.
        # It will desappear when new ROI is added.
        self.events.data.connect(self._on_data_change)

    def _on_data_change(self, ev):
        if ev.action is ActionType.ADDING:
            self._remove_current()
            if not self.show_all:
                with self.events.data.blocker():
                    self.selected_data = set(range(self.nshapes))
                    super().remove_selected()
            feature_defaults = {"id": self.nshapes}
            if "name" in self.features:
                feature_defaults["name"] = f"ROI-{self.nshapes:>04}"
            self.feature_defaults = feature_defaults
        elif ev.action is ActionType.ADDED:
            idx = ev.data_indices[0]
            if idx < 0:
                idx = self.nshapes + idx
            self._current_item = idx
            self.selected_data = {idx}
            self._relabel_feature_id()

        elif ev.action is ActionType.REMOVING:
            pass
        elif ev.action is ActionType.REMOVED:
            if self._current_item is None:
                pass  # do nothing
            elif self._current_item in ev.data_indices:
                self._current_item = None
            else:
                n_smaller = sum(
                    int(idx < self._current_item) for idx in ev.data_indices
                )
                self._current_item -= n_smaller
            self._relabel_feature_id()

    def _relabel_feature_id(self):
        df = self.features
        df["id"] = np.arange(df.shape[0], dtype=np.uint32)
        self.features = df

    def _safe_set_selected_data(self, selected_data: Iterable[int]) -> None:
        """Safely select data, ensuring it does not exceed the number of shapes."""
        selected_data = {i for i in selected_data if i < self.nshapes}
        self.selected_data = selected_data

    def _remove_current(self) -> bool:
        if self._current_item is not None:
            with self.events.data.blocker():
                self.selected_data = {self._current_item}
                super().remove_selected()

    def register_roi(self):
        """Register the current ROI to the manager."""
        if self._current_item is not None:
            self.events.roi_added(
                index=self._current_item,
                shape_type=self.shape_type[self._current_item],
            )
            if not self.show_all:
                self._hidden_shapes.data.append(self.data[self._current_item])
                self._hidden_shapes.shape_type.append(
                    self.shape_type[self._current_item]
                )
            else:
                self.selected_data = set()
        else:
            self.selected_data = set()
        self._current_item = None
        self.refresh()

    def update_from_json(self, path: str | Path, append: bool = False) -> None:
        """Update the layer state from a JSON file."""
        # clear the layer
        if not append:
            self._initialize_layer()
        with open(path) as f:
            js = json.load(f)
        rois = RoiData.from_json_dict(js)
        nshapes = self.roi_count()
        self._current_item = None
        if rois.names is not None and (roimgr := self._roi_manager_ref()) is not None:
            cur_column = roimgr._roilist.get_column("name")
        else:
            cur_column = []
        with self.events.data.blocker():
            for index, (data, shape_type) in enumerate(zip(rois.data, rois.shape_type)):
                self.add([data], shape_type=shape_type)
                self.events.roi_added(index=nshapes + index, shape_type=shape_type)
        self.selected_data = set()
        df = self.features
        df["id"] = np.arange(df.shape[0], dtype=np.uint32)
        if rois.names is not None and (roimgr := self._roi_manager_ref()) is not None:
            roilist = roimgr._roilist
            new_column = cur_column + rois.names
            roilist.set_column("name", new_column)
            df["name"] = new_column
        self.features = df
        self.refresh()
        return None

    def write_json(self, path: str | Path) -> None:
        """Write the ROI data to a JSON file."""
        js = self.get_roi_data().to_json_dict()
        with open(path, "w") as f:
            json.dump(js, f)
        return None

    def roi_count(self) -> int:
        if self.show_all:
            if self._current_item is None:
                return self.nshapes
            else:
                return self.nshapes - 1
        else:
            return self._hidden_shapes.len()

    def _initialize_layer(self):
        self.selected_data = set(range(self.nshapes))
        self.remove_selected()
        self._hidden_shapes.clear()
        self._current_item = None

    def remove_selected(self):
        """Remove the selected ROIs from the manager."""
        selected = self.selected_data.copy()
        # NOTE: there are bugs in removing all the rest of shapes
        if self.nshapes == len(self.selected_data):
            ctx = self.events.highlight.blocker()
        else:
            ctx = nullcontext()
        with ctx:
            super().remove_selected()
            if selected != {self._current_item}:
                self.events.roi_removed(indices=selected)
        self.refresh()

    @Shapes.mode.setter
    def mode(self, mode):
        Shapes.mode.fset(self, mode)
        if self._current_item is not None:
            self.selected_data = {self._current_item}

    @property
    def text_feature_name(self) -> TextFeatureName:
        """The feature name to be shown in the text."""
        return self._text_feature_name

    @text_feature_name.setter
    def text_feature_name(self, text_feature_name: str | TextFeatureName):
        text_feature_name = TextFeatureName(text_feature_name)
        self._text_feature_name = text_feature_name
        _name = TextFeatureName.NAME.value
        if (
            text_feature_name is TextFeatureName.NAME
            and _name not in (df := self.features)
            and (roi_manager := self._roi_manager_ref())
        ):
            column = roi_manager._roilist.get_column(_name)
            if df.shape[0] > len(column):
                column += [""] * (df.shape[0] - len(column))
            df[_name] = column
            self.features = df
        self.text.string = "{" + text_feature_name.value + "}"
        return None

    @property
    def show_all(self) -> bool:
        """If true, show all registered ROIs. If false, show only the current ROI."""
        return self._show_all

    @show_all.setter
    def show_all(self, show_all: bool):
        if not isinstance(show_all, bool):
            raise TypeError("show_all must be a bool")
        if self.show_all == show_all:
            return
        _current_item = self._current_item
        if show_all:  # "show all" checked
            self.selected_data = set()
            old_shape_type = self.shape_type
            self.data = self._hidden_shapes.data + self.data
            self.features = pd.concat([self._hidden_shapes.features, self.features])
            if self._hidden_shapes.shape_type + old_shape_type:
                # NOTE: bug in napari? cannot set empty list to shape_type
                self.shape_type = self._hidden_shapes.shape_type + old_shape_type
            self._current_item = _current_item  # _current_item may change in setters
            if self._hidden_shapes.current_item is not None:
                self._current_item = self._hidden_shapes.current_item
                self.selected_data = {self._current_item}
            else:
                self.selected_data = self._hidden_shapes.selected_data
            self._hidden_shapes.clear()
            self.text.visible = self._hidden_shapes.display_text
        else:  # "show all" unchecked
            self._hidden_shapes.update(
                data=self.data,
                shape_type=self.shape_type,
                features=self.features,
                selected_data=self.selected_data,
                current_item=self._current_item,
                display_text=self.text.visible,
            )
            if self._current_item is not None:
                cur, typ = self._hidden_shapes.pop(self._current_item)
                self._current_item = None
                self.data = []
                # add last current ROI to show only it.
                self.add(cur, shape_type=typ)
                self._current_item = 0
                self.selected_data = {0}
            else:
                self.selected_data = set()
                self.data = []
                self._current_item = None
            self.text.visible = False
        self._show_all = show_all

    def as_shapes_layer(self) -> Shapes:
        """Convert this layer into napari Shapes layer."""
        rois = self.get_roi_data()
        return Shapes(rois.data, shape_type=rois.shape_type, name="Shapes")

    def get_roi_data(self) -> RoiData:
        """Get the data and shape type of the ROIs."""
        if self.show_all:
            shape_data = self.data
            shape_type = self.shape_type
        else:
            shape_data = self._hidden_shapes.data
            shape_type = self._hidden_shapes.shape_type
        if (roimgr := self._roi_manager_ref()) is not None:
            names = roimgr._roilist.get_column("name")
        else:
            names = None
        if self._current_item is not None:
            shape_data.pop(self._current_item)
            shape_type.pop(self._current_item)
        return RoiData(shape_data, shape_type, names)

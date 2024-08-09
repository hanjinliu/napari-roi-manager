from __future__ import annotations

import numpy as np
from napari_roi_manager.layers._hidden_data import HiddenShapes
from napari.layers import Shapes
from napari.layers.base import ActionType
from napari.utils.events import Event


class RoiManagerLayer(Shapes):
    """Layer for managing ROIs."""

    _type_string = "shapes"

    def __init__(self, *args, **kwargs):
        self._current_item: int | None = None
        # the last current_item before unchecking "show all"
        self._show_all = True
        self._hidden_shapes = HiddenShapes()

        kwargs["face_color"] = [0.0, 0.0, 0.0, 0.0]
        kwargs["edge_color"] = [1.0, 1.0, 0.0, 1.0]
        kwargs["ndim"] = 2
        kwargs["text"] = {
            "string": "{id}",
            "color": "yellow",
            "visible": False,
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
            self.feature_defaults = {"id": self.nshapes}
        elif ev.action is ActionType.ADDED:
            idx = ev.data_indices[0]
            if idx < 0:
                idx = self.nshapes + idx
            self._current_item = idx
            self.selected_data = {idx}
            self.features = {"id": np.arange(self.nshapes, dtype=np.uint32)}

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
            self.features = {"id": np.arange(self.nshapes, dtype=np.uint32)}

    def _remove_current(self):
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
                self._hidden_shapes.shape_type.append(self.shape_type[self._current_item])
            else:
                self.selected_data = set()
        else:
            self.selected_data = set()
        self._current_item = None
        self.refresh()

    def remove_selected(self):
        """Remove the selected ROIs from the manager."""
        selected = self.selected_data.copy()
        super().remove_selected()
        if selected != {self._current_item}:
            self.events.roi_removed(indices=selected)

    @Shapes.mode.setter
    def mode(self, mode):
        Shapes.mode.fset(self, mode)
        if self._current_item is not None:
            self.selected_data = {self._current_item}

    @property
    def show_all(self) -> bool:
        """If true, show all registered ROIs. If false, show only the current ROI."""
        return self._show_all

    @show_all.setter
    def show_all(self, show_all: bool):
        if not isinstance(show_all, bool):
            raise TypeError("show_all must be a bool")
        if self._show_all == show_all:
            return
        _current_item = self._current_item
        if show_all:  # "show all" checked
            old_shape_type = self.shape_type
            self.data = self._hidden_shapes.data + self.data
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
        else:  # "show all" unchecked
            self._hidden_shapes.update(
                data=self.data,
                shape_type=self.shape_type,
                selected_data=self.selected_data,
                current_item=self._current_item,
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
        self._remove_current()
        if self.show_all:
            shape_data = self.data
            shape_type = self.shape_type
        else:
            shape_data = self._hidden_shapes.data
            shape_type = self._hidden_shapes.shape_type
        return Shapes(shape_data, shape_type=shape_type, name="Shapes")

from __future__ import annotations

import numpy as np
from napari.layers import Shapes
from napari.layers.base import ActionType
from napari.utils.events import Event


class RoiManagerLayer(Shapes):
    """Layer for managing ROIs."""

    _type_string = "shapes"

    def __init__(self, *args, **kwargs):
        self._current_item: int | None = None
        self._show_all = True
        self._hidden_roi_data: list[np.ndarray] = []
        self._hidden_roi_type: list[str] = []

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
                self._hidden_roi_data.append(self.data[self._current_item])
                self._hidden_roi_type.append(
                    self.shape_type[self._current_item]
                )
        self._current_item = None
        self.selected_data = set()
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
        if show_all:
            _current_item = self._current_item
            stype = self.shape_type
            self.data = self._hidden_roi_data + self.data
            self.shape_type = self._hidden_roi_type + stype
            self._current_item = (
                _current_item  # _current_item may change in setters
            )
            if self._current_item is not None:
                self._current_item = self.nshapes - 1
                self.selected_data = {self._current_item}
        else:
            old_data = self.data
            self._hidden_roi_data = old_data
            self._hidden_roi_type = self.shape_type
            if self._current_item is not None:
                cur = self._hidden_roi_data.pop(self._current_item)
                typ = self._hidden_roi_type.pop(self._current_item)
                self._current_item = None
                self.data = []
                self.add(cur, shape_type=typ)
                self._current_item = 0
                self.selected_data = {0}
            else:
                self.data = []
            self.text.visible = False
        self._show_all = show_all

    def as_shapes_layer(self) -> Shapes:
        """Convert this layer into napari Shapes layer."""
        self._remove_current()
        if self.show_all:
            shape_data = self.data
            shape_types = self.shape_type
        else:
            shape_data = self._hidden_roi_data
            shape_types = self._hidden_roi_type
        return Shapes(shape_data, shape_type=shape_types, name="Shapes")

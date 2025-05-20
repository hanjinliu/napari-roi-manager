from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray


@dataclass
class HiddenShapes:
    data: list[NDArray[np.number]] = field(default_factory=list)
    shape_type: list[str] = field(default_factory=list)
    selected_data: set[int] = field(default_factory=set)
    features: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    current_item: int | None = None
    display_text: bool = False

    def clear(self):
        self.data.clear()
        self.shape_type.clear()
        self.current_item = None

    def update(
        self,
        data: list[NDArray[np.number]],
        features: pd.DataFrame,
        shape_type: list[str],
        selected_data: set[int],
        current_item: int | None,
        display_text: bool = False,
    ):
        self.data = data
        self.features = features
        self.shape_type = shape_type
        self.selected_data = selected_data
        self.current_item = current_item
        self.display_text = display_text

    def pop(self, idx: int) -> tuple[NDArray[np.number], str]:
        out = self.data.pop(idx), self.shape_type.pop(idx)
        self.features = self.features.drop(self.features.index[idx])
        self.selected_data.discard(idx)
        return out

    def len(self) -> int:
        return len(self.data)


@dataclass(frozen=True)
class RoiData:
    data: list[NDArray[np.number]] = field(default_factory=list)
    shape_type: list[str] = field(default_factory=list)
    names: list[str] | None = field(default_factory=lambda: None)

    def to_json_dict(self) -> dict[str, Any]:
        """Convert RoiData to a JSON serializable dictionary."""
        data = [d.tolist() for d in self.data]
        out = {"data": data, "shape_type": self.shape_type}
        if self.names is not None:
            out["names"] = self.names
        return out

    @classmethod
    def from_json_dict(cls, js: dict[str, Any]) -> RoiData:
        """Create RoiData from a JSON serializable dictionary."""
        data = [np.array(d) for d in js["data"]]
        shape_type = js["shape_type"]
        names = js.get("names")
        return RoiData(data, shape_type=shape_type, names=names)

    def iter_shapes(self):
        """Iterate over shapes and their types."""
        for i in range(len(self.data)):
            yield RoiTuple(
                data=self.data[i],
                shape_type=self.shape_type[i],
                name=self.names[i] if self.names is not None else None,
            )


@dataclass
class RoiTuple:
    data: NDArray[np.number]
    shape_type: str
    name: str | None = None
    multidim: tuple[int, ...] = ()

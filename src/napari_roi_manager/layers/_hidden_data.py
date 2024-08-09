from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray

@dataclass
class HiddenShapes:
    data: list[NDArray[np.number]] = field(default_factory=list)
    shape_type: list[str] = field(default_factory=list)
    selected_data: set[int] = field(default_factory=set)
    current_item: int | None = None

    def clear(self):
        self.data.clear()
        self.shape_type.clear()
        self.current_item = None

    def update(
        self,
        data: list[NDArray[np.number]],
        shape_type: list[str],
        selected_data: set[int],
        current_item: int | None,
    ):
        self.data = data
        self.shape_type = shape_type
        self.selected_data = selected_data
        self.current_item = current_item

    def pop(self, idx: int) -> tuple[NDArray[np.number], str]:
        out = self.data.pop(idx), self.shape_type.pop(idx)
        self.selected_data.remove(idx)
        return out

    def len(self) -> int:
        return len(self.data)
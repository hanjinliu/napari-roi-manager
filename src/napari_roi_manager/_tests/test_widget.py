from typing import Callable

import napari
import numpy as np

from napari_roi_manager import QRoiManager


def _rectangle(y, x, size: float = 2):
    return np.array(
        [[x, y], [x + size, y], [x + size, y + size], [x, y + size]]
    )


def test_many_operations(make_napari_viewer: Callable[[], napari.Viewer]):
    viewer = make_napari_viewer()
    roi_manager = QRoiManager(viewer)
    roi_manager.add(_rectangle(0, 0), shape_type="rectangle")
    roi_manager.register()
    roi_manager.add(_rectangle(6, 6), shape_type="rectangle")
    roi_manager.register()
    roi_manager.select(0)
    roi_manager.set_show_all(False)
    roi_manager.set_show_all(True)
    roi_manager.set_show_all(False)
    roi_manager.set_show_all(True)
    roi_manager.remove()
    roi_manager.select()
    roi_manager.set_show_all(False)
    roi_manager.set_show_all(True)
    roi_manager.set_show_all(False)
    roi_manager.set_show_all(True)


def test_to_shapes(make_napari_viewer: Callable[[], napari.Viewer]):
    viewer = make_napari_viewer()
    roi_manager = QRoiManager(viewer)
    roi_manager.add(_rectangle(0, 0), shape_type="rectangle")
    roi_manager.register()
    roi_manager.add(_rectangle(6, 6), shape_type="rectangle")
    roi_manager.register()
    roi_manager.as_shapes_layer()

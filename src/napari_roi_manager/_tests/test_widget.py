import tempfile
from pathlib import Path
from typing import Callable

import napari
import numpy as np

from napari_roi_manager import QRoiManager


def _rectangle(y, x, size: float = 2):
    return np.array([[x, y], [x + size, y], [x + size, y + size], [x, y + size]])


def test_many_operations(make_napari_viewer: Callable[[], napari.Viewer]):
    viewer = make_napari_viewer()
    roi_manager = QRoiManager(viewer)
    roi_manager.add(_rectangle(0, 1), shape_type="rectangle")
    roi_manager.add(_rectangle(1, 0), shape_type="rectangle")
    roi_manager.add(_rectangle(0, 0), shape_type="rectangle")
    roi_manager.register()
    assert roi_manager._layer.nshapes == 1
    roi_manager.add(_rectangle(6, 6), shape_type="rectangle")
    roi_manager.register()
    roi_manager.select(0)
    roi_manager.set_show_all(False)
    roi_manager.set_show_all(True)
    roi_manager.set_show_all(False)
    roi_manager.set_show_all(True)
    roi_manager.remove()
    roi_manager.select(0)
    roi_manager.remove()
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


def test_add_during_not_show_all(make_napari_viewer: Callable[[], napari.Viewer]):
    viewer = make_napari_viewer()
    roi_manager = QRoiManager(viewer)
    roi_manager.register(_rectangle(0, 0), shape_type="rectangle")
    roi_manager.set_show_all(False)
    roi_manager.register(_rectangle(6, 6), shape_type="rectangle")
    roi_manager.register(_rectangle(9, 6), shape_type="rectangle")
    roi_manager.set_show_all(True)
    roi_manager.select(0)
    roi_manager.set_show_all(False)


def test_remove_during_not_show_all(make_napari_viewer: Callable[[], napari.Viewer]):
    viewer = make_napari_viewer()
    roi_manager = QRoiManager(viewer)
    roi_manager.register(_rectangle(0, 0), shape_type="rectangle")
    roi_manager.register(_rectangle(6, 6), shape_type="rectangle")
    roi_manager.register(_rectangle(9, 6), shape_type="rectangle")
    roi_manager.set_show_all(False)
    roi_manager._roilist.selectRow(2)
    roi_manager._btns._remove_roi_btn.click()
    assert roi_manager._layer.roi_count() == 2
    assert roi_manager._roilist.rowCount() == 2
    roi_manager.set_show_all(True)
    roi_manager.set_show_all(False)
    roi_manager._roilist.selectAll()
    roi_manager._btns._remove_roi_btn.click()
    assert roi_manager._layer.roi_count() == 0
    assert roi_manager._roilist.rowCount() == 0
    roi_manager.set_show_all(True)

    roi_manager.register(_rectangle(0, 0), shape_type="rectangle")
    roi_manager.register(_rectangle(6, 6), shape_type="ellipse")
    roi_manager.register(_rectangle(9, 6), shape_type="rectangle")
    roi_manager.register(_rectangle(9, 9), shape_type="ellipse")
    roi_manager.set_show_all(False)

    roi_manager._roilist.selectRow(2)
    roi_manager._btns._remove_roi_btn.click()
    roi_manager._roilist.selectRow(0)
    roi_manager._btns._remove_roi_btn.click()
    assert roi_manager._layer.roi_count() == 2
    assert roi_manager._roilist.rowCount() == 2
    roi_manager.set_show_all(True)
    assert roi_manager._layer.roi_count() == 2
    assert roi_manager._roilist.rowCount() == 2


def test_read_write(make_napari_viewer: Callable[[], napari.Viewer]):
    viewer = make_napari_viewer()
    roi_manager = QRoiManager(viewer)
    roi_manager.load_roiset(
        path=Path(__file__).parent / "_test_roiset.json", append=False
    )
    roi_manager.load_roiset(
        path=Path(__file__).parent / "_test_roiset.json", append=True
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        roi_manager.save_roiset(path=Path(tmpdir) / "test_save_roiset.json")

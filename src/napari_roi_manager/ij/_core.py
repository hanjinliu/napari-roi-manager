from pathlib import Path


def read_roi_provider(path):
    from napari_roi_manager.widgets import QRoiManager

    if not isinstance(path, (str, Path)):
        return
    path = Path(path)
    if path.suffix not in (".roi", ".zip"):
        return

    return QRoiManager.get_or_create().read_ij_roi

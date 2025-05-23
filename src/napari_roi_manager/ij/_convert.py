import warnings

import numpy as np
from numpy.typing import NDArray
from roifile import ROI_SUBTYPE, ROI_TYPE, ImagejRoi

from napari_roi_manager._dataclasses import RoiTuple


def roi_to_shape(ijroi: ImagejRoi) -> RoiTuple | None:
    """Convert an ImageJ ROI to a shape coordinates and type."""
    p = ijroi.position
    t = ijroi.t_position
    z = ijroi.z_position
    name = ijroi.name
    multidim = (p, t, z)

    if ijroi.subtype == ROI_SUBTYPE.UNDEFINED:
        if ijroi.roitype == ROI_TYPE.RECT:
            if ijroi.subpixelresolution:
                x = ijroi.xd
                y = ijroi.yd
                width = ijroi.widthd
                height = ijroi.heightd
            else:
                x = ijroi.left
                y = ijroi.top
                width = ijroi.right - ijroi.left
                height = ijroi.bottom - ijroi.top
            out = RoiTuple(
                data=[
                    [[y, x], [y, x + width], [y + height, x + width], [y + height, x]],
                ],
                shape_type="rectangle",
                name=name,
                multidim=multidim,
            )
        elif ijroi.roitype == ROI_TYPE.LINE:
            start = (ijroi.y1 - 1, ijroi.x1 - 1)
            end = (ijroi.y2 - 1, ijroi.x2 - 1)
            out = RoiTuple(
                data=[start, end],
                shape_type="line",
                name=name,
                multidim=multidim,
            )
        elif ijroi.roitype == ROI_TYPE.POINT:
            warnings.warn(
                "ImageJ point ROI encountered, but napari shapes layer does not "
                "support points. Point ROIs will be ignored.",
                UserWarning,
                stacklevel=2,
            )
            return
        elif ijroi.roitype in (ROI_TYPE.POLYGON, ROI_TYPE.FREEHAND):
            coords = _get_coords(ijroi)
            out = RoiTuple(
                data=coords,
                shape_type="polygon",
                name=name,
                multidim=multidim,
            )
        elif ijroi.roitype in (ROI_TYPE.POLYLINE, ROI_TYPE.FREELINE):
            coords = _get_coords(ijroi)
            out = RoiTuple(
                data=coords,
                shape_type="path",
                name=name,
                multidim=multidim,
            )
        elif ijroi.roitype == ROI_TYPE.OVAL:
            if ijroi.subpixelresolution:
                x = ijroi.xd
                y = ijroi.yd
                width = ijroi.widthd
                height = ijroi.heightd
            else:
                x = ijroi.left
                y = ijroi.top
                width = ijroi.right - ijroi.left
                height = ijroi.bottom - ijroi.top
            out = RoiTuple(
                data=[
                    [[y, x], [y, x + width], [y + height, x + width], [y + height, x]],
                ],
                shape_type="ellipse",
                name=name,
                multidim=multidim,
            )
        else:
            raise ValueError(f"Unsupported ROI type: {ijroi.roitype!r}")
    elif ijroi.subtype == ROI_SUBTYPE.ROTATED_RECT:
        coords = _get_coords(ijroi)
        out = RoiTuple(
            data=coords,
            shape_type="rectangle",
            name=name,
            multidim=multidim,
        )
    elif ijroi.subtype == ROI_SUBTYPE.ELLIPSE:
        # ImageJ rotated ellipse is just a freehand line
        coords = _get_coords(ijroi)
        out = RoiTuple(
            data=coords,
            shape_type="polygon",
            name=name,
            multidim=multidim,
        )
    else:
        raise ValueError(f"Unsupported ROI subtype: {ijroi.subtype}")

    return out


def shape_to_roi(shape: RoiTuple) -> ImagejRoi:
    """Convert a shape to an ImageJ ROI."""
    ys = shape.data[:, -2]
    xs = shape.data[:, -1]
    if shape.shape_type == "rectangle":
        if ys[0] == ys[1] or xs[0] == xs[1]:
            # not rotated
            y0, y1 = ys.min(), ys.max()
            x0, x1 = xs.min(), xs.max()
            roi = ImagejRoi.frompoints(
                np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]),
                name=shape.name,
                **_get_multidim_kwargs(shape),
            )
            roi.roitype = ROI_TYPE.RECT
            roi.y1 = roi.yd = y0
            roi.x1 = roi.xd = x0
            roi.y2 = y1
            roi.x2 = x1
            roi.widthd = x1 - x0
            roi.heightd = y1 - y0
        else:
            roi = ImagejRoi.frompoints(
                np.stack([xs, ys], axis=1) + 1,
                name=shape.name,
                **_get_multidim_kwargs(shape),
            )
            roi.roitype = ROI_TYPE.FREEHAND
            roi.subtype = ROI_SUBTYPE.ROTATED_RECT
            roi.x1 = xs[1:3].mean() + 1
            roi.y1 = ys[1:3].mean() + 1
            roi.x2 = xs[:4:3].mean() + 1
            roi.y2 = ys[:4:3].mean() + 1
            # roi.arrow_style_or_aspect_ratio = 65
            # roi.arrow_head_size = 135
        return roi
    elif shape.shape_type == "line":
        roi = ImagejRoi.frompoints(
            np.stack([xs, ys], axis=1) + 1,
            name=shape.name,
            **_get_multidim_kwargs(shape),
        )
        roi.x1 = xs[0] + 1
        roi.y1 = ys[0] + 1
        roi.x2 = xs[1] + 1
        roi.y2 = ys[1] + 1
        roi.roitype = ROI_TYPE.LINE
        return roi
    elif shape.shape_type == "path":
        roi = ImagejRoi.frompoints(
            np.stack([xs, ys], axis=1) + 1,
            name=shape.name,
            **_get_multidim_kwargs(shape),
        )
        roi.roitype = ROI_TYPE.POLYLINE
        return roi
    elif shape.shape_type == "polygon":
        roi = ImagejRoi.frompoints(
            np.stack([xs, ys], axis=1) + 1,
            name=shape.name,
            **_get_multidim_kwargs(shape),
        )
        roi.roitype = ROI_TYPE.POLYGON
        return roi
    elif shape.shape_type == "ellipse":
        if ys[0] == ys[1] or xs[0] == xs[1]:
            # not rotated
            y0, y1 = ys.min(), ys.max()
            x0, x1 = xs.min(), xs.max()
            roi = ImagejRoi.frompoints(
                np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]),
                name=shape.name,
                **_get_multidim_kwargs(shape),
            )
            roi.roitype = ROI_TYPE.OVAL
            roi.y1 = roi.yd = y0
            roi.x1 = roi.xd = x0
            roi.y2 = y1
            roi.x2 = x1
            roi.widthd = x1 - x0
            roi.heightd = y1 - y0
        else:
            roi = ImagejRoi.frompoints(
                np.stack([xs, ys], axis=1),
                name=shape.name,
                **_get_multidim_kwargs(shape),
            )
            roi.roitype = ROI_TYPE.FREEHAND
            roi.subtype = ROI_SUBTYPE.ELLIPSE
            raise NotImplementedError
        return roi
    raise ValueError(f"Unsupported shape type: {shape.shape_type}")


def _get_coords(ijroi: ImagejRoi) -> NDArray[np.number]:
    if ijroi.subpixelresolution:
        xy = ijroi.subpixel_coordinates - 1
    else:
        xy = ijroi.integer_coordinates - 1 + [ijroi.left, ijroi.top]
    return xy[:, ::-1]


def _get_multidim_kwargs(shape: RoiTuple) -> dict[str, int]:
    """Get the multidim kwargs for a shape."""
    if len(shape.multidim) == 0:
        return {}
    if len(shape.multidim) == 1:
        return {"z": shape.multidim[0]}
    if len(shape.multidim) == 2:
        return {
            "t": shape.multidim[0],
            "z": shape.multidim[1],
        }
    else:
        return {
            "position": shape.multidim[0],
            "t": shape.multidim[1],
            "z": shape.multidim[2],
        }

import warnings

import numpy as np
from numpy.typing import NDArray
from roifile import ROI_OPTIONS, ROI_SUBTYPE, ROI_TYPE, ImagejRoi

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
                x = (ijroi.xd,)
                y = (ijroi.yd,)
                width = (ijroi.widthd,)
                height = (ijroi.heightd,)
            else:
                x = (ijroi.left,)
                y = (ijroi.top,)
                width = (ijroi.right - ijroi.left,)
                height = (ijroi.bottom - ijroi.top,)
            out = RoiTuple(
                data=[
                    [[y, x], [y, x + width], [y + height, x + width], [y + height, x]],
                ],
                shape_type="rectangle",
                name=name,
                multidim=multidim,
            )
        elif ijroi.roitype == ROI_TYPE.LINE:
            start = (ijroi.x1 - 1, ijroi.y1 - 1)
            end = (ijroi.x2 - 1, ijroi.y2 - 1)
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


def shape_to_roi(
    shape: RoiTuple,
) -> ImagejRoi:
    """Convert a shape to an ImageJ ROI."""
    if shape.shape_type == "rectangle":
        ys = shape.data[:, -2]
        xs = shape.data[:, -1]
        if ys[0] == ys[1] or xs[0] == xs[1]:
            # not rotated
            y0, y1 = ys.min(), ys.max()
            x0, x1 = xs.min(), xs.max()
            return ImagejRoi(
                roitype=ROI_TYPE.RECT,
                name=shape.name,
                options=ROI_OPTIONS.SUB_PIXEL_RESOLUTION,
                yd=y0,
                xd=x0,
                widthd=x1 - x0,
                heightd=y1 - y0,
                **_get_multidim_kwargs(shape),
            )
        else:
            return ImagejRoi(
                roitype=ROI_TYPE.FREEHAND,
                subtype=ROI_SUBTYPE.ROTATED_RECT,
                options=ROI_OPTIONS.SUB_PIXEL_RESOLUTION,
                name=shape.name,
                subpixel_coordinates=np.stack([xs, ys], axis=1),
                **_get_multidim_kwargs(shape),
            )
    elif shape.shape_type == "line":
        start, end = shape.data
        return ImagejRoi(
            roitype=ROI_TYPE.LINE,
            name=shape.name,
            x1=start[1] + 1,
            y1=start[0] + 1,
            x2=end[1] + 1,
            y2=end[0] + 1,
            position=shape.multidim[0],
            t_position=shape.multidim[1],
            z_position=shape.multidim[2],
        )
    elif shape.shape_type == "path":
        coords = shape.data
        return ImagejRoi(
            roitype=ROI_TYPE.LINE,
            name=shape.name,
            subpixel_coordinates=coords[:, ::-1] + 1,
            **_get_multidim_kwargs(shape),
        )
    elif shape.shape_type == "polygon":
        coords = shape.data
        return ImagejRoi(
            roitype=ROI_TYPE.POLYGON,
            name=shape.name,
            options=ROI_OPTIONS.SUB_PIXEL_RESOLUTION,
            subpixel_coordinates=coords[:, ::-1] + 1,
            **_get_multidim_kwargs(shape),
        )
    elif shape.shape_type == "ellipse":
        ys = shape.data[:, -2]
        xs = shape.data[:, -1]
        y0, y1 = ys.min(), ys.max()
        x0, x1 = xs.min(), xs.max()
        return ImagejRoi(
            roitype=ROI_TYPE.OVAL,
            name=shape.name,
            options=ROI_OPTIONS.SUB_PIXEL_RESOLUTION,
            yd=y0,
            xd=x0,
            widthd=x1 - x0,
            heightd=y1 - y0,
            **_get_multidim_kwargs(shape),
        )
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
        return {"z_position": shape.multidim[0]}
    if len(shape.multidim) == 2:
        return {
            "t_position": shape.multidim[0],
            "z_position": shape.multidim[1],
        }
    else:
        return {
            "position": shape.multidim[0],
            "t_position": shape.multidim[1],
            "z_position": shape.multidim[2],
        }

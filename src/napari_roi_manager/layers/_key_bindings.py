from ._layer import RoiManagerLayer


@RoiManagerLayer.bind_key("t", overwrite=True)
def _register(layer: RoiManagerLayer):
    layer.register_roi()

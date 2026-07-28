from __future__ import annotations

__version__ = "0.1.0"

from . import _ffi_api
from . import caffe_pb2

from ._core import Blob, Layer, Net
from . import blob
from . import layer
from . import net
from . import io

from .io import (
    read_net,
    read_net_from_prototxt,
    read_net_from_binary,
    net_from_param,
    net_param_from_string,
)


def version() -> str:
    """Get caffe-ffi version string."""
    if _ffi_api.is_available():
        v = _ffi_api.get_global_func("caffe_ffi.Version")
        if v is not None:
            return v()
    return __version__


__all__ = [
    "__version__",
    "version",
    "Blob",
    "Layer",
    "Net",
    "caffe_pb2",
    "read_net",
    "read_net_from_prototxt",
    "read_net_from_binary",
    "net_from_param",
    "net_param_from_string",
]

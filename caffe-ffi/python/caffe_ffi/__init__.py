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


LOG_LEVEL_TRACE = 0
LOG_LEVEL_DEBUG = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_WARN = 3
LOG_LEVEL_ERROR = 4


def set_log_level(level: int) -> None:
    """Set C++ native log level (0=TRACE, 1=DEBUG, 2=INFO, 3=WARN, 4=ERROR)."""
    if _ffi_api.is_available():
        fn = _ffi_api.get_global_func("caffe_ffi.SetLogLevel")
        if fn is not None:
            fn(level)


def get_log_level() -> int:
    """Get current C++ native log level."""
    if _ffi_api.is_available():
        fn = _ffi_api.get_global_func("caffe_ffi.GetLogLevel")
        if fn is not None:
            return int(fn())
    return LOG_LEVEL_WARN


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
    "set_log_level",
    "get_log_level",
    "LOG_LEVEL_TRACE",
    "LOG_LEVEL_DEBUG",
    "LOG_LEVEL_INFO",
    "LOG_LEVEL_WARN",
    "LOG_LEVEL_ERROR",
]

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

from . import _core
from ._core import Blob

_logger = logging.getLogger("caffe_ffi.Blob")


def _fmt_ptr(arr: np.ndarray) -> str:
    try:
        return f"0x{arr.ctypes.data:016x}"
    except Exception:
        return "<unavailable>"


def _log_tensor_access(self, name: str, arr: np.ndarray) -> None:
    if not _logger.isEnabledFor(logging.DEBUG):
        return
    _logger.debug(
        "%s access: blob_id=%s shape=%s dtype=%s ndim=%d nbytes=%d ptr=%s strides=%s is_native=%s",
        name,
        id(self),
        arr.shape,
        arr.dtype,
        arr.ndim,
        arr.nbytes,
        _fmt_ptr(arr),
        arr.strides,
        getattr(self, '_is_native', False),
    )


@property
def data_tensor(self) -> np.ndarray:
    """Get zero-copy view of data tensor as numpy array.

    Modifications to this array directly modify the Blob's underlying memory.
    """
    if hasattr(self, '_blob_data_tensor_fn') and self._blob_data_tensor_fn is not None and self._is_native:
        arr = np.from_dlpack(self._blob_data_tensor_fn(self))
        _log_tensor_access(self, "data_tensor", arr)
        return arr
    arr = self._py_data
    _log_tensor_access(self, "data_tensor(py_fallback)", arr)
    return arr


@property
def diff_tensor(self) -> np.ndarray:
    """Get zero-copy view of diff tensor as numpy array.

    Modifications to this array directly modify the Blob's underlying memory.
    """
    if hasattr(self, '_blob_diff_tensor_fn') and self._blob_diff_tensor_fn is not None and self._is_native:
        arr = np.from_dlpack(self._blob_diff_tensor_fn(self))
        _log_tensor_access(self, "diff_tensor", arr)
        return arr
    arr = self._py_diff
    _log_tensor_access(self, "diff_tensor(py_fallback)", arr)
    return arr


@property
def data(self) -> np.ndarray:
    """Get the data array as numpy (returns a copy for safety).

    Use data_tensor for zero-copy access when you need to modify data in-place.
    """
    arr = self.data_tensor.copy()
    if _logger.isEnabledFor(logging.DEBUG):
        _logger.debug(
            "data (copy): blob_id=%s shape=%s ptr=%s (copied from data_tensor)",
            id(self), arr.shape, _fmt_ptr(arr),
        )
    return arr


@data.setter
def data(self, value: np.ndarray) -> None:
    """Set the data array from numpy."""
    arr = np.asarray(value, dtype=np.float32)
    if _logger.isEnabledFor(logging.DEBUG):
        _logger.debug(
            "data setter: blob_id=%s input_shape=%s input_dtype=%s target_shape=%s is_native=%s",
            id(self), getattr(value, 'shape', None), getattr(value, 'dtype', None),
            arr.shape, self._is_native,
        )
    if self._is_native:
        if tuple(arr.shape) != self.shape:
            _logger.debug("data setter: Reshape from %s to %s", self.shape, arr.shape)
            self.Reshape(list(arr.shape))
        self.set_data(arr.flatten().tolist())
    else:
        self._py_shape = list(arr.shape)
        self._py_data = arr.copy()
        self._py_diff = np.zeros_like(arr)


@property
def diff(self) -> np.ndarray:
    """Get the diff array as numpy (returns a copy for safety)."""
    arr = self.diff_tensor.copy()
    if _logger.isEnabledFor(logging.DEBUG):
        _logger.debug(
            "diff (copy): blob_id=%s shape=%s ptr=%s (copied from diff_tensor)",
            id(self), arr.shape, _fmt_ptr(arr),
        )
    return arr


@diff.setter
def diff(self, value: np.ndarray) -> None:
    """Set the diff array from numpy."""
    arr = np.asarray(value, dtype=np.float32)
    if _logger.isEnabledFor(logging.DEBUG):
        _logger.debug(
            "diff setter: blob_id=%s input_shape=%s target_shape=%s is_native=%s",
            id(self), getattr(value, 'shape', None), arr.shape, self._is_native,
        )
    if self._is_native:
        if tuple(arr.shape) != self.shape:
            self.Reshape(list(arr.shape))
        self.set_diff(arr.flatten().tolist())
    else:
        self._py_diff = np.asarray(value, dtype=np.float32).reshape(self._py_shape)


def Update(self) -> None:
    """Update data by subtracting diff (data -= diff)."""
    _logger.debug(
        "Update: blob_id=%s shape=%s operation=data-=diff is_native=%s",
        id(self), self.shape if hasattr(self, 'shape') else '?', self._is_native,
    )
    if self._is_native and hasattr(self, '_blob_update_fn') and self._blob_update_fn is not None:
        self._blob_update_fn(self)
    elif self._py_data is not None and self._py_diff is not None:
        self._py_data -= self._py_diff


def from_numpy(self, arr: np.ndarray, set_diff: bool = False) -> Blob:
    """Reshape blob and set data from numpy array."""
    arr = np.asarray(arr, dtype=np.float32)
    _logger.debug(
        "from_numpy: blob_id=%s shape=%s set_diff=%s nbytes=%d",
        id(self), arr.shape, set_diff, arr.nbytes,
    )
    self.Reshape(list(arr.shape))
    if set_diff:
        self.diff = arr
    else:
        self.data = arr
    return self


def to_numpy(self, get_diff: bool = False) -> np.ndarray:
    """Convert blob data to numpy array (returns a copy)."""
    arr = self.diff_tensor.copy() if get_diff else self.data_tensor.copy()
    _logger.debug(
        "to_numpy: blob_id=%s get_diff=%s shape=%s ptr=%s",
        id(self), get_diff, arr.shape, _fmt_ptr(arr),
    )
    return arr


def fill(self, value: float) -> Blob:
    """Fill data with a constant value."""
    _logger.debug(
        "fill: blob_id=%s value=%.6f shape=%s is_native=%s",
        id(self), value, self.shape if hasattr(self, 'shape') else '?', self._is_native,
    )
    if self._is_native:
        self.data_tensor.fill(np.float32(value))
    else:
        self._py_data.fill(np.float32(value))
        if self._py_diff is not None:
            self._py_diff.fill(0)
    return self


def zero(self) -> Blob:
    """Set data and diff to all zeros."""
    _logger.debug(
        "zero: blob_id=%s shape=%s is_native=%s",
        id(self), self.shape if hasattr(self, 'shape') else '?', self._is_native,
    )
    if self._is_native:
        self.data_tensor.fill(0)
        self.diff_tensor.fill(0)
    else:
        if self._py_data is not None:
            self._py_data.fill(0)
        if self._py_diff is not None:
            self._py_diff.fill(0)
    return self


def copy_from(self, other) -> Blob:
    """Copy data from another blob or numpy array."""
    if isinstance(other, Blob):
        other_data = other.data_tensor
        _logger.debug(
            "copy_from: blob_id=%s <- other_blob_id=%s shape=%s is_native=%s",
            id(self), id(other), other_data.shape, self._is_native,
        )
    else:
        other_data = np.asarray(other, dtype=np.float32)
        _logger.debug(
            "copy_from: blob_id=%s <- ndarray shape=%s nbytes=%d is_native=%s",
            id(self), other_data.shape, other_data.nbytes, self._is_native,
        )
    if self._is_native:
        if tuple(other_data.shape) != self.shape:
            self.Reshape(list(other_data.shape))
        self.data_tensor[:] = other_data
    else:
        self._py_shape = list(other_data.shape)
        self._py_data = other_data.astype(np.float32).copy()
        self._py_diff = np.zeros_like(self._py_data)
    return self


def blob_repr(self) -> str:
    return f"Blob(shape={self.shape}, dtype=float32)"


def _patch_blob():
    """Apply monkey patches to Blob class."""
    Blob.data_tensor = data_tensor
    Blob.diff_tensor = diff_tensor
    Blob.data = data
    Blob.diff = diff
    Blob.Update = Update
    Blob.from_numpy = from_numpy
    Blob.to_numpy = to_numpy
    Blob.fill = fill
    Blob.zero = zero
    Blob.copy_from = copy_from
    Blob.__repr__ = blob_repr


_patch_blob()

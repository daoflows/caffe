from __future__ import annotations

from typing import Any, Optional

import numpy as np

from . import _core
from ._core import Blob


def _dlpack_to_numpy(tensor) -> np.ndarray:
    """Convert a DLPack tensor to numpy array (zero-copy if possible)."""
    try:
        return np.from_dlpack(tensor)
    except (AttributeError, TypeError):
        if hasattr(tensor, 'data_ptr') and hasattr(tensor, 'shape'):
            data_ptr = tensor.data_ptr()
            shape = tuple(tensor.shape())
            import ctypes
            ptr = ctypes.cast(data_ptr, ctypes.POINTER(ctypes.c_float))
            arr = np.ctypeslib.as_array(ptr, shape=shape)
            return arr.copy()
    return None


def _blob_data_property(blob: Blob, is_diff: bool = False) -> np.ndarray:
    """Get data or diff as numpy array."""
    if blob._handle is not None:
        if is_diff:
            tensor = blob._handle.diff_tensor() if hasattr(blob._handle, 'diff_tensor') else None
        else:
            tensor = blob._handle.data_tensor() if hasattr(blob._handle, 'data_tensor') else None
        
        if tensor is not None:
            result = _dlpack_to_numpy(tensor)
            if result is not None:
                return result
        
        if is_diff:
            return np.array(blob.get_diff(), dtype=np.float32).reshape(blob.shape)
        else:
            return np.array(blob.get_data(), dtype=np.float32).reshape(blob.shape)
    else:
        if is_diff:
            return blob._diff.copy()
        else:
            return blob._data.copy()


def _blob_set_data_property(blob: Blob, value: np.ndarray, is_diff: bool = False) -> None:
    """Set data or diff from numpy array."""
    arr = np.asarray(value, dtype=np.float32)
    if arr.shape != blob.shape:
        blob.Reshape(list(arr.shape))
    
    if blob._handle is not None:
        if is_diff:
            if hasattr(blob._handle, 'diff_tensor'):
                tensor = blob._handle.diff_tensor()
                if tensor is not None and hasattr(tensor, 'copyfrom'):
                    tensor.copyfrom(arr)
                    return
            blob.set_diff(arr.flatten().tolist())
        else:
            if hasattr(blob._handle, 'data_tensor'):
                tensor = blob._handle.data_tensor()
                if tensor is not None and hasattr(tensor, 'copyfrom'):
                    tensor.copyfrom(arr)
                    return
            blob.set_data(arr.flatten().tolist())
    else:
        if is_diff:
            blob._diff = arr.copy()
        else:
            blob._data = arr.copy()


@property
def data(self) -> np.ndarray:
    """Get the data array as numpy (zero-copy via DLPack when available)."""
    return _blob_data_property(self, is_diff=False)


@data.setter
def data(self, value: np.ndarray) -> None:
    """Set the data array from numpy."""
    _blob_set_data_property(self, value, is_diff=False)


@property
def diff(self) -> np.ndarray:
    """Get the diff array as numpy."""
    return _blob_data_property(self, is_diff=True)


@diff.setter
def diff(self, value: np.ndarray) -> None:
    """Set the diff array from numpy."""
    _blob_set_data_property(self, value, is_diff=True)


def from_numpy(self, arr: np.ndarray, set_diff: bool = False) -> Blob:
    """Reshape blob and set data from numpy array."""
    arr = np.asarray(arr, dtype=np.float32)
    self.Reshape(list(arr.shape))
    if set_diff:
        self.diff = arr
    else:
        self.data = arr
    return self


def to_numpy(self, get_diff: bool = False) -> np.ndarray:
    """Convert blob data to numpy array."""
    if get_diff:
        return self.diff.copy()
    else:
        return self.data.copy()


def fill(self, value: float) -> Blob:
    """Fill data with a constant value."""
    self.data = np.full(self.shape, value, dtype=np.float32)
    return self


def zero(self) -> Blob:
    """Set data to all zeros."""
    return self.fill(0.0)


def copy_from(self, other: Blob) -> Blob:
    """Copy data from another blob."""
    self.Reshape(list(other.shape))
    self.data = other.data
    return self


@property
def blob_name(self) -> str:
    """Get blob name."""
    if self._handle is not None:
        if hasattr(self._handle, 'name'):
            return self._handle.name()
    return getattr(self, '_name', '')


@blob_name.setter
def blob_name(self, value: str) -> None:
    """Set blob name."""
    if self._handle is not None:
        if hasattr(self._handle, 'set_name'):
            self._handle.set_name(value)
            return
    self._name = value


def blob_repr(self) -> str:
    return f"Blob(shape={self.shape}, dtype=float32)"


def _patch_blob():
    """Apply monkey patches to Blob class."""
    Blob.data = data
    Blob.diff = diff
    Blob.from_numpy = from_numpy
    Blob.to_numpy = to_numpy
    Blob.fill = fill
    Blob.zero = zero
    Blob.copy_from = copy_from
    Blob.name = blob_name
    Blob.__repr__ = blob_repr


_patch_blob()

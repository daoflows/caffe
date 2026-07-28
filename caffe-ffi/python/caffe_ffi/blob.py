from __future__ import annotations

from typing import Any, Optional

import numpy as np

from . import _core
from ._core import Blob


@property
def data(self) -> np.ndarray:
    """Get the data array as numpy."""
    return np.array(self.get_data(), dtype=np.float32).reshape(self.shape)


@data.setter
def data(self, value: np.ndarray) -> None:
    """Set the data array from numpy."""
    arr = np.asarray(value, dtype=np.float32)
    if arr.shape != self.shape:
        self.Reshape(list(arr.shape))
    self.set_data(arr.flatten().tolist())


@property
def diff(self) -> np.ndarray:
    """Get the diff array as numpy."""
    return np.array(self.get_diff(), dtype=np.float32).reshape(self.shape)


@diff.setter
def diff(self, value: np.ndarray) -> None:
    """Set the diff array from numpy."""
    arr = np.asarray(value, dtype=np.float32)
    if arr.shape != self.shape:
        self.Reshape(list(arr.shape))
    self.set_diff(arr.flatten().tolist())


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
    Blob.__repr__ = blob_repr


_patch_blob()

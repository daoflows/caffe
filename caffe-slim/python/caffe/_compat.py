"""BVLC PyCaffe style API compatibility layer for caffe-slim."""

from __future__ import annotations

from collections import OrderedDict
from functools import reduce
from operator import mul
from typing import Any, Dict, List, Optional

import numpy as np


class BlobProxy:
    """Proxy object wrapping a Caffe blob, providing BVLC-style API.

    This proxy provides zero-copy access to blob data and diff via numpy
    arrays. Assigning to ``proxy.data[...] = arr`` directly modifies the
    underlying Caffe memory.

    Parameters
    ----------
    net : Net
        The parent Net instance.
    blob_name : str
        Name of the blob in the network.
    """

    def __init__(self, net: Any, blob_name: str):
        self._net = net
        self._blob_name = blob_name

    @property
    def data(self) -> np.ndarray:
        """Get blob data as numpy array (zero-copy view)."""
        return self._net.blob_data(self._blob_name)

    @property
    def diff(self) -> np.ndarray:
        """Get blob diff as numpy array (zero-copy view)."""
        return self._net.blob_diff(self._blob_name)

    @property
    def shape(self) -> tuple:
        """Get blob shape as a tuple."""
        return self._net.blob_shape(self._blob_name)

    @property
    def count(self) -> int:
        """Get total number of elements in the blob."""
        return reduce(mul, self.shape, 1)

    def __array__(self, dtype: Optional[np.dtype] = None) -> np.ndarray:
        """Support ``np.asarray(blob_proxy)`` conversion."""
        arr = self.data
        if dtype is not None:
            return arr.astype(dtype)
        return arr

    def __repr__(self) -> str:
        return f"BlobProxy(name={self._blob_name!r}, shape={self.shape})"


def _Net__blob_names(self) -> List[str]:
    """Return list of all blob names (alias for self.blob_names)."""
    return self.blob_names


def _Net__blobs(self) -> List[BlobProxy]:
    """Return list of BlobProxy objects for all blobs."""
    return [BlobProxy(self, name) for name in self._blob_names]


def _Net_blobs(self) -> OrderedDict:
    """Return OrderedDict mapping blob names to BlobProxy objects.

    Result is cached after first access for efficiency.
    """
    if not hasattr(self, '_blobs_dict') or self._blobs_dict is None:
        self._blobs_dict = OrderedDict(zip(self._blob_names, self._blobs))
    return self._blobs_dict


def _Net__inputs(self) -> List[int]:
    """Return list of input blob indices.

    Result is cached after first access.
    """
    if not hasattr(self, '_input_indices') or self._input_indices is None:
        self._input_indices = [
            self.blob_names.index(name) for name in self.inputs
        ]
    return self._input_indices


def _Net__outputs(self) -> List[int]:
    """Return list of output blob indices.

    Result is cached after first access.
    """
    if not hasattr(self, '_output_indices') or self._output_indices is None:
        self._output_indices = [
            self.blob_names.index(name) for name in self.outputs
        ]
    return self._output_indices


def _Net_forward(
    self,
    blobs: Optional[List[str]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    **kwargs: np.ndarray,
) -> Dict[str, np.ndarray]:
    """BVLC-compatible forward pass wrapper.

    Parameters
    ----------
    blobs : list of str, optional
        Additional blob names to include in output besides network outputs.
    start : str, optional
        NOT SUPPORTED. Starting layer name for partial forward.
    end : str, optional
        NOT SUPPORTED. Ending layer name for partial forward.
    **kwargs : np.ndarray
        Input data arrays keyed by input blob name.

    Returns
    -------
    outputs : dict
        Dictionary mapping output blob names to their data arrays.

    Raises
    ------
    NotImplementedError
        If start or end parameters are provided (partial forward not supported).
    ValueError
        If kwargs contain invalid input names or batch size mismatch.
    """
    if start is not None or end is not None:
        raise NotImplementedError(
            "Partial forward (start/end) is not supported in caffe-slim"
        )

    if blobs is None:
        blobs = []

    if kwargs:
        input_set = set(self.inputs)
        kwarg_set = set(kwargs.keys())
        if kwarg_set != input_set:
            raise ValueError(
                f"Input keys mismatch: expected {sorted(input_set)}, "
                f"got {sorted(kwarg_set)}"
            )

        batch_size = None
        for in_name, in_blob in kwargs.items():
            if batch_size is None:
                batch_size = in_blob.shape[0]
            elif in_blob.shape[0] != batch_size:
                raise ValueError(
                    f"Batch size mismatch: {in_name} has batch size "
                    f"{in_blob.shape[0]}, expected {batch_size}"
                )
            self.blobs[in_name].data[...] = in_blob

    self._forward_slim()

    output_names = set(self.outputs + blobs)
    return {out: self.blobs[out].data for out in output_names}


def enable_bvlc_compat(net_class: Any = None) -> None:
    """Enable BVLC PyCaffe compatibility via monkey patching.

    This patches the Net class to add BlobProxy-based blob access,
    OrderedDict blobs property, cached input/output indices, and
    BVLC-style forward method with kwargs support.

    Parameters
    ----------
    net_class : type, optional
        Net class to patch. Defaults to the Net class from this package.
    """
    if net_class is None:
        from . import Net as net_class

    if getattr(net_class, '_bvlc_compat_enabled', False):
        return

    net_class._bvlc_compat_enabled = True
    net_class._forward_slim = net_class.forward

    net_class._blob_names = property(_Net__blob_names)
    net_class._blobs = property(_Net__blobs)
    net_class.blobs = property(_Net_blobs)
    net_class._inputs = property(_Net__inputs)
    net_class._outputs = property(_Net__outputs)

    net_class.forward = _Net_forward

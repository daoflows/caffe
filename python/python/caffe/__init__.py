"""Caffe Python inference package (tvm-ffi slimmed version)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Union

import numpy as np

try:
    import tvm_ffi
except ImportError:
    tvm_ffi = None

_LIB_PATH = None
_mod = None


def _find_lib():
    """Find the _caffe shared library."""
    global _LIB_PATH, _mod
    if _mod is not None:
        return _mod

    if tvm_ffi is None:
        raise ImportError("tvm_ffi is required. Please install tvm-ffi.")

    current_dir = Path(__file__).resolve().parent
    search_paths = [
        current_dir,
        current_dir.parent.parent.parent / "build" / "python" / "caffe",
        current_dir.parent.parent.parent / "build",
    ]

    lib_names = ["_caffe.dll", "_caffe.so", "_caffe.dylib", "lib_caffe.so"]
    for search_path in search_paths:
        if not search_path.exists():
            continue
        for lib_name in lib_names:
            lib_path = search_path / lib_name
            if lib_path.exists():
                _LIB_PATH = str(lib_path)
                _mod = tvm_ffi.load_module(_LIB_PATH)
                return _mod

    raise ImportError(
        "Cannot find _caffe shared library. Build the project first."
    )


TRAIN = 0
TEST = 1


class Net:
    """Caffe Net for inference (CPU-only)."""

    def __init__(
        self,
        network_file: str,
        phase: int = TEST,
        weights: Optional[str] = None,
    ):
        self._mod = _find_lib()
        self._handle = None
        if weights is not None:
            self._handle = self._mod.Net_Init_Load(
                network_file, weights, phase
            )
        else:
            self._handle = self._mod.Net_Init(network_file, phase)

        self._blob_names = None
        self._input_names = None
        self._output_names = None

    def __del__(self):
        if self._handle is not None and self._mod is not None:
            try:
                self._mod.Net_Destroy(self._handle)
            except Exception:
                pass
            self._handle = None

    def reshape(self):
        """Reshape the network."""
        self._mod.Net_Reshape(self._handle)

    def forward(self):
        """Run forward pass."""
        self._mod.Net_Forward(self._handle)

    @property
    def blob_names(self) -> List[str]:
        """Get all blob names."""
        if self._blob_names is None:
            self._blob_names = list(self._mod.Net_BlobNames(self._handle))
        return self._blob_names

    @property
    def inputs(self) -> List[str]:
        """Get input blob names."""
        if self._input_names is None:
            self._input_names = list(self._mod.Net_InputBlobNames(self._handle))
        return self._input_names

    @property
    def outputs(self) -> List[str]:
        """Get output blob names."""
        if self._output_names is None:
            self._output_names = list(self._mod.Net_OutputBlobNames(self._handle))
        return self._output_names

    def blob_shape(self, blob_name: str) -> tuple:
        """Get the shape of a blob.

        Parameters
        ----------
        blob_name : str
            Name of the blob.

        Returns
        -------
        shape : tuple
            Shape tuple.
        """
        return tuple(self._mod.Blob_GetShape(self._handle, blob_name))

    def blob_data(self, blob_name: str) -> np.ndarray:
        """Get blob data as numpy array (zero-copy view).

        Parameters
        ----------
        blob_name : str
            Name of the blob.

        Returns
        -------
        data : np.ndarray
            Numpy array view of the blob data.
        """
        tensor = self._mod.Blob_GetData(self._handle, blob_name)
        return np.from_dlpack(tensor)

    def blob_diff(self, blob_name: str) -> np.ndarray:
        """Get blob diff as numpy array (zero-copy view).

        Parameters
        ----------
        blob_name : str
            Name of the blob.

        Returns
        -------
        diff : np.ndarray
            Numpy array view of the blob diff.
        """
        tensor = self._mod.Blob_GetDiff(self._handle, blob_name)
        return np.from_dlpack(tensor)

    def set_input_data(self, input_name: str, data: np.ndarray):
        """Set input blob data from numpy array.

        Parameters
        ----------
        input_name : str
            Name of the input blob.
        data : np.ndarray
            Numpy array (float32, contiguous).
        """
        if not data.flags['C_CONTIGUOUS']:
            data = np.ascontiguousarray(data)
        if data.dtype != np.float32:
            data = data.astype(np.float32)
        tensor = tvm_ffi.from_dlpack(data)
        self._mod.Blob_SetData(self._handle, input_name, tensor)

    def copy_from(self, weights_file: str):
        """Load weights from file.

        Parameters
        ----------
        weights_file : str
            Path to .caffemodel weights file.
        """
        self._mod.Net_CopyTrainedLayersFrom(self._handle, weights_file)


def set_mode_cpu():
    """Set mode to CPU."""
    _find_lib()
    _mod.SetModeCPU()


def set_random_seed(seed: int):
    """Set random seed."""
    _find_lib()
    _mod.SetRandomSeed(seed)


def layer_type_list() -> List[str]:
    """Get list of available layer types."""
    _find_lib()
    return list(_mod.LayerTypeList())


def version() -> str:
    """Get Caffe version string."""
    _find_lib()
    return _mod.Version()


set_mode_cpu()

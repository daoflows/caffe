"""Caffe Python inference package (tvm-ffi slimmed version) with BVLC compatibility layer."""

from __future__ import annotations

import logging
import os
import sys
import warnings
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

logger = logging.getLogger("caffe")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

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
        logger.debug(f"_caffe library already loaded from: {_LIB_PATH}")
        return _mod

    logger.info("Loading _caffe shared library...")
    if tvm_ffi is None:
        logger.error("tvm_ffi is not installed!")
        raise ImportError("tvm_ffi is required. Please install tvm-ffi.")

    current_dir = Path(__file__).resolve().parent
    search_paths = [
        current_dir,
        current_dir.parent.parent.parent / "build" / "python" / "caffe",
        current_dir.parent.parent.parent / "build",
    ]
    logger.debug(f"Search paths: {[str(p) for p in search_paths]}")

    lib_names = ["_caffe.dll", "_caffe.so", "_caffe.dylib", "lib_caffe.so"]
    for search_path in search_paths:
        if not search_path.exists():
            logger.debug(f"  Skip non-existent path: {search_path}")
            continue
        logger.debug(f"  Searching in: {search_path}")
        for lib_name in lib_names:
            lib_path = search_path / lib_name
            if lib_path.exists():
                _LIB_PATH = str(lib_path)
                logger.info(f"Found _caffe library at: {_LIB_PATH}")
                logger.info("Loading tvm-ffi module...")
                _mod = tvm_ffi.load_module(_LIB_PATH)
                logger.info("_caffe module loaded successfully")
                return _mod

    logger.error(f"Cannot find _caffe shared library! Tried paths: {[str(p) for p in search_paths]}")
    raise ImportError(
        "Cannot find _caffe shared library. Build the project first."
    )


TRAIN = 0
TEST = 1


class _BlobProxy:
    """Proxy for a Caffe blob, providing BVLC-style .data and .shape attributes."""

    def __init__(self, net: "Net", name: str):
        self._net = net
        self._name = name
        self._data_arr = None
        logger.debug(f"Created _BlobProxy for blob: '{name}'")

    @property
    def data(self) -> np.ndarray:
        """Get blob data as numpy array (zero-copy view, writeable)."""
        logger.debug(f"BlobProxy['{self._name}'].data getter called")
        tensor = self._net._mod.Blob_GetData(self._net._handle, self._name)
        arr = np.from_dlpack(tensor)
        try:
            arr.flags.writeable = True
        except ValueError:
            logger.debug(f"  Cannot set writeable flag for '{self._name}' (read-only tensor)")
            pass
        return arr

    @data.setter
    def data(self, value: np.ndarray):
        """Set blob data from numpy array."""
        logger.info(f"BlobProxy['{self._name}'].data setter called, shape={value.shape}, dtype={value.dtype}")
        self._net.set_input_data(self._name, value)

    @property
    def shape(self) -> Tuple[int, ...]:
        """Get blob shape as tuple."""
        s = tuple(self._net._mod.Blob_GetShape(self._net._handle, self._name))
        logger.debug(f"BlobProxy['{self._name}'].shape = {s}")
        return s

    @property
    def diff(self) -> np.ndarray:
        """Get blob diff as numpy array."""
        logger.debug(f"BlobProxy['{self._name}'].diff getter called")
        tensor = self._net._mod.Blob_GetDiff(self._net._handle, self._name)
        arr = np.from_dlpack(tensor)
        try:
            arr.flags.writeable = True
        except ValueError:
            pass
        return arr

    def reshape(self, *args):
        """Reshape the blob (stub, raises NotImplementedError)."""
        logger.warning(f"BlobProxy['{self._name}'].reshape() called (not supported in inference mode)")
        raise NotImplementedError("Blob.reshape() is not supported in inference mode")

    @property
    def num(self) -> int:
        n = self.shape[0] if len(self.shape) > 0 else 0
        logger.debug(f"BlobProxy['{self._name}'].num = {n}")
        return n

    @property
    def channels(self) -> int:
        c = self.shape[1] if len(self.shape) > 1 else 1
        logger.debug(f"BlobProxy['{self._name}'].channels = {c}")
        return c

    @property
    def height(self) -> int:
        h = self.shape[2] if len(self.shape) > 2 else 1
        logger.debug(f"BlobProxy['{self._name}'].height = {h}")
        return h

    @property
    def width(self) -> int:
        w = self.shape[3] if len(self.shape) > 3 else 1
        logger.debug(f"BlobProxy['{self._name}'].width = {w}")
        return w

    @property
    def count(self) -> int:
        """Return total number of elements in the blob."""
        s = self.shape
        n = 1
        for d in s:
            n *= d
        logger.debug(f"BlobProxy['{self._name}'].count = {n}")
        return n

    def __repr__(self) -> str:
        return f"<Blob '{self._name}' shape={self.shape}>"


class _BlobsDict:
    """Dictionary-like access to network blobs, supporting both [] and . attribute access."""

    def __init__(self, net: "Net"):
        self._net = net
        self._cache: Dict[str, _BlobProxy] = {}

    def __getitem__(self, key: str) -> _BlobProxy:
        if key not in self._cache:
            self._cache[key] = _BlobProxy(self._net, key)
        return self._cache[key]

    def __contains__(self, key: str) -> bool:
        return key in self._net.blob_names

    def keys(self):
        return self._net.blob_names

    def values(self):
        return [self[k] for k in self._net.blob_names]

    def items(self):
        return [(k, self[k]) for k in self._net.blob_names]

    def __iter__(self):
        return iter(self._net.blob_names)

    def __len__(self):
        return len(self._net.blob_names)

    def __repr__(self) -> str:
        return f"<BlobsDict with {len(self)} blobs: {list(self._net.blob_names)[:5]}...>"


class _LayerProxy:
    """Minimal Layer proxy (stub for compatibility)."""

    def __init__(self, net: "Net", idx: int):
        self._net = net
        self._idx = idx
        self.type = "Unknown"

    def __repr__(self) -> str:
        return f"<Layer {self._idx} (type={self.type})>"


class _LayersList:
    """List-like access to network layers (stub, returns placeholder objects)."""

    def __init__(self, net: "Net"):
        self._net = net

    def __getitem__(self, idx: int) -> _LayerProxy:
        return _LayerProxy(self._net, idx)

    def __len__(self) -> int:
        warnings.warn(
            "net.layers is a stub in this caffe-slim build; length may not be accurate.",
            RuntimeWarning, stacklevel=2,
        )
        return len(self._net.blob_names)

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]


class _ParamBlobsList:
    """List of parameter blobs for a layer (stub, returns empty list)."""

    def __init__(self):
        pass

    def __getitem__(self, idx):
        raise NotImplementedError(
            "Parameter blob access via net.params[layer][idx] requires C++ extensions "
            "not available in this caffe-slim build. Use model surgery before deployment."
        )

    def __len__(self):
        return 0

    def __iter__(self):
        return iter([])


class _ParamsDict:
    """Dictionary-like access to network parameters (stub)."""

    def __init__(self, net: "Net"):
        self._net = net

    def __getitem__(self, key: str):
        warnings.warn(
            f"net.params['{key}'] is a stub; parameter blobs are not directly accessible "
            "in this caffe-slim build without C++ extensions.",
            RuntimeWarning, stacklevel=2,
        )
        return _ParamBlobsList()

    def __contains__(self, key: str) -> bool:
        return False

    def keys(self):
        return []

    def __len__(self):
        return 0

    def __iter__(self):
        return iter([])


class Net:
    """Caffe Net for inference (CPU-only) with BVLC PyCaffe compatibility layer.

    Supported BVLC-style APIs:
      - net.blobs['name'].data / .shape / .diff
      - net.blobs['name'].data[:] = array
      - net.forward() returns dict of {output_name: numpy_array}
      - net.inputs / net.outputs / net.blob_names
      - net.reshape()
    """

    def __init__(
        self,
        network_file: str,
        phase: int = TEST,
        weights: Optional[str] = None,
    ):
        phase_str = "TRAIN" if phase == TRAIN else "TEST"
        logger.info(f"Initializing Caffe Net:")
        logger.info(f"  prototxt: {network_file}")
        logger.info(f"  weights:  {weights if weights else '(none)'}")
        logger.info(f"  phase:    {phase_str}")

        if not os.path.isfile(network_file):
            logger.error(f"Prototxt file not found: {network_file}")
            raise FileNotFoundError(f"Network file not found: {network_file}")
        if weights is not None and not os.path.isfile(weights):
            logger.error(f"Weights file not found: {weights}")
            raise FileNotFoundError(f"Weights file not found: {weights}")

        self._mod = _find_lib()
        self._handle = None
        logger.info("Calling C++ Net constructor...")
        if weights is not None:
            self._handle = self._mod.Net_Init_Load(
                network_file, weights, phase
            )
            logger.info("Net loaded with weights successfully")
        else:
            self._handle = self._mod.Net_Init(network_file, phase)
            logger.info("Net initialized (no weights) successfully")

        self._blob_names = None
        self._input_names = None
        self._output_names = None
        self._blobs_dict = _BlobsDict(self)
        self._layers_list = _LayersList(self)
        self._params_dict = _ParamsDict(self)

        logger.info(f"Net summary:")
        logger.info(f"  inputs:  {self.inputs}")
        logger.info(f"  outputs: {self.outputs}")
        logger.info(f"  total blobs: {len(self.blob_names)}")

    def __del__(self):
        if self._handle is not None and self._mod is not None:
            logger.debug("Destroying Net handle...")
            try:
                self._mod.Net_Destroy(self._handle)
                logger.debug("Net handle destroyed successfully")
            except Exception as e:
                logger.warning(f"Error during Net destruction: {e}")
            self._handle = None

    def reshape(self):
        """Reshape the network."""
        logger.info("Reshaping network...")
        self._mod.Net_Reshape(self._handle)
        self._blob_names = None
        self._input_names = None
        self._output_names = None
        logger.info("Network reshaped")

    def _forward_native(self):
        """Native forward pass (no return value, compatible with slim API)."""
        logger.debug("Running native forward pass...")
        self._mod.Net_Forward(self._handle)
        logger.debug("Native forward pass completed")

    def forward(self, **kwargs) -> Dict[str, np.ndarray]:
        """Run forward pass and return dict of output blobs (BVLC-style).

        Examples
        --------
        >>> out = net.forward()
        >>> prob = out['prob']
        """
        if kwargs:
            logger.info(f"forward() called with kwargs: {list(kwargs.keys())}")
            for blob_name, data in kwargs.items():
                logger.debug(f"  Setting input '{blob_name}' shape={data.shape}, dtype={data.dtype}")
                self.set_input_data(blob_name, data)
        else:
            logger.debug("forward() called (no kwargs, using pre-filled data)")

        logger.debug("Running forward pass...")
        self._mod.Net_Forward(self._handle)

        result = {}
        for name in self.outputs:
            arr = self.blobs[name].data.copy()
            result[name] = arr
            logger.debug(f"  Output '{name}' shape={arr.shape}, dtype={arr.dtype}")

        logger.info(f"forward() completed, outputs: {list(result.keys())}")
        return result

    def forward_all(self, **kwargs) -> Dict[str, np.ndarray]:
        """Alias for forward(), returns all blobs (outputs only in slim mode)."""
        return self.forward(**kwargs)

    @property
    def blobs(self) -> _BlobsDict:
        """BVLC-style blob dictionary: net.blobs['data'].data"""
        return self._blobs_dict

    @property
    def layers(self) -> _LayersList:
        """BVLC-style layer list (stub)."""
        return self._layers_list

    @property
    def params(self) -> _ParamsDict:
        """BVLC-style parameter dictionary (stub)."""
        return self._params_dict

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

    @property
    def top_names(self) -> OrderedDict:
        """Return OrderedDict mapping layer names to list of top blob names (stub)."""
        return OrderedDict()

    @property
    def bottom_names(self) -> OrderedDict:
        """Return OrderedDict mapping layer names to list of bottom blob names (stub)."""
        return OrderedDict()

    def blob_shape(self, blob_name: str) -> tuple:
        """Get the shape of a blob."""
        shape = tuple(self._mod.Blob_GetShape(self._handle, blob_name))
        logger.debug(f"blob_shape('{blob_name}') = {shape}")
        return shape

    def blob_data(self, blob_name: str) -> np.ndarray:
        """Get blob data as numpy array (zero-copy view)."""
        logger.debug(f"blob_data('{blob_name}') called")
        return self.blobs[blob_name].data

    def blob_diff(self, blob_name: str) -> np.ndarray:
        """Get blob diff as numpy array (zero-copy view)."""
        logger.debug(f"blob_diff('{blob_name}') called")
        return self.blobs[blob_name].diff

    def set_input_data(self, input_name: str, data: np.ndarray):
        """Set input blob data from numpy array."""
        logger.info(f"set_input_data('{input_name}'): shape={data.shape}, dtype={data.dtype}")

        original_dtype = data.dtype
        original_c_contiguous = data.flags['C_CONTIGUOUS']

        if not data.flags['C_CONTIGUOUS']:
            logger.debug(f"  Converting to C-contiguous array")
            data = np.ascontiguousarray(data)
        if data.dtype != np.float32:
            logger.debug(f"  Converting dtype from {original_dtype} to float32")
            data = data.astype(np.float32)

        logger.debug(f"  Final array: shape={data.shape}, dtype={data.dtype}, C-contiguous={data.flags['C_CONTIGUOUS']}")
        tensor = tvm_ffi.from_dlpack(data)
        self._mod.Blob_SetData(self._handle, input_name, tensor)
        logger.debug(f"  Input data set successfully")

    def copy_from(self, weights_file: str):
        """Load weights from file."""
        logger.info(f"copy_from('{weights_file}')")
        if not os.path.isfile(weights_file):
            logger.error(f"Weights file not found: {weights_file}")
            raise FileNotFoundError(f"Weights file not found: {weights_file}")
        self._mod.Net_CopyTrainedLayersFrom(self._handle, weights_file)
        logger.info("Weights loaded successfully")


def set_mode_cpu():
    """Set mode to CPU."""
    logger.info("Setting Caffe mode to CPU")
    _find_lib()
    _mod.SetModeCPU()
    logger.info("CPU mode set successfully")


def set_random_seed(seed: int):
    """Set random seed."""
    logger.info(f"Setting random seed to: {seed}")
    _find_lib()
    _mod.SetRandomSeed(seed)


def layer_type_list() -> List[str]:
    """Get list of available layer types."""
    logger.debug("Getting layer type list")
    _find_lib()
    types = list(_mod.LayerTypeList())
    logger.debug(f"Available layer types: {len(types)} types")
    return types


def version() -> str:
    """Get Caffe version string."""
    _find_lib()
    v = _mod.Version()
    logger.debug(f"Caffe version: {v}")
    return v


class NetSpec:
    """Stub for BVLC NetSpec (declarative network definition not supported in slim mode)."""
    def __init__(self, *args, **kwargs):
        logger.error("NetSpec() called but not supported in inference-only slim build")
        raise NotImplementedError(
            "NetSpec is not supported in caffe-slim inference mode. "
            "Use pre-trained .prototxt and .caffemodel files."
        )


def layers(*args, **kwargs):
    """Stub for BVLC layers module."""
    logger.error("caffe.layers() called but not supported in inference-only slim build")
    raise NotImplementedError(
        "Declarative layer creation (caffe.layers) is not supported in inference mode."
    )


def params(*args, **kwargs):
    """Stub for BVLC params module."""
    logger.error("caffe.params() called but not supported in inference-only slim build")
    raise NotImplementedError(
        "Parameter specification (caffe.params) is not supported in inference mode."
    )


logger.info("Initializing caffe BVLC compatibility layer...")
set_mode_cpu()
logger.info("Caffe module initialized successfully")

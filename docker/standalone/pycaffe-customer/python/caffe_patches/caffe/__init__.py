"""Caffe Python inference package (tvm-ffi slimmed version) - BVLC API compatibility layer."""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path
from collections import OrderedDict
from typing import List, Optional, Dict, Any

__version__ = "1.0-slim-cpu"


def _patch_protobuf_version():
    """Monkey-patch protobuf runtime version check to tolerate version mismatches.

    caffe_pb2.py may be generated with a newer protoc than the installed protobuf
    Python package. Rather than failing hard on VersionError, we downgrade to a
    warning so users can still run inference.
    """
    try:
        from google.protobuf import runtime_version as _rv
        _original_validate = _rv.ValidateProtobufRuntimeVersion

        def _patched_validate(domain, major, minor, micro, suffix, proto_file):
            try:
                return _original_validate(domain, major, minor, micro, suffix, proto_file)
            except Exception as e:
                warnings.warn(
                    f"Protobuf version mismatch for {proto_file}: {e}. "
                    "Attempting to continue (pure-Python runtime).",
                    RuntimeWarning,
                    stacklevel=3,
                )

        _rv.ValidateProtobufRuntimeVersion = _patched_validate
    except ImportError:
        pass
    except Exception:
        pass


_patch_protobuf_version()

import numpy as np

try:
    import tvm_ffi
except ImportError:
    tvm_ffi = None

_LIB_PATH = None
_mod = None


def _find_lib():
    global _LIB_PATH, _mod
    if _mod is not None:
        return _mod

    if tvm_ffi is None:
        raise ImportError("tvm_ffi is required. Please install tvm-ffi.")

    import ctypes

    current_dir = Path(__file__).resolve().parent
    search_paths = [current_dir]

    lib_dir = os.environ.get("CAFFE_LIB_DIR")
    if lib_dir:
        search_paths.insert(0, Path(lib_dir))

    system_lib_paths = [Path("/usr/lib"), Path("/usr/local/lib"), Path("/usr/lib/x86_64-linux-gnu")]

    # Preload libtvm_ffi.so with RTLD_GLOBAL so _caffe.so can resolve its symbols
    tvm_ffi_loaded = False
    tvm_lib_names = ["libtvm_ffi.so", "libtvm_ffi.dylib", "tvm_ffi.dll"]
    for sp in search_paths + system_lib_paths:
        if not sp.exists():
            continue
        for tlib in tvm_lib_names:
            tpath = sp / tlib
            if tpath.exists():
                try:
                    ctypes.CDLL(str(tpath), mode=ctypes.RTLD_GLOBAL)
                    tvm_ffi_loaded = True
                except OSError:
                    pass
                break
        if tvm_ffi_loaded:
            break

    lib_names = ["_caffe.so", "_caffe.dll", "_caffe.dylib", "lib_caffe.so"]
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
        f"Cannot find _caffe shared library in {current_dir}. "
        "Ensure caffe is properly installed."
    )


TRAIN = 0
TEST = 1


class _BlobView:
    """Compatibility wrapper for BVLC-style blob access (net.blobs['name'].data)."""

    def __init__(self, net: "Net", name: str):
        self._net = net
        self._name = name

    @property
    def data(self) -> np.ndarray:
        return self._net.blob_data(self._name)

    @data.setter
    def data(self, value: np.ndarray):
        self._net.set_input_data(self._name, value)

    @property
    def diff(self) -> np.ndarray:
        return self._net.blob_diff(self._name)

    @property
    def shape(self) -> tuple:
        return self._net.blob_shape(self._name)

    @property
    def num(self) -> int:
        return self.shape[0]

    @property
    def channels(self) -> int:
        return self.shape[1] if len(self.shape) > 1 else 1

    @property
    def height(self) -> int:
        return self.shape[2] if len(self.shape) > 2 else 1

    @property
    def width(self) -> int:
        return self.shape[3] if len(self.shape) > 3 else 1

    def reshape(self, *args):
        warnings.warn(
            "blob.reshape() is not fully supported in caffe-slim inference build. "
            "Input shape is determined by the deploy.prototxt. "
            "Use a prototxt with the desired input dimensions instead.",
            RuntimeWarning,
            stacklevel=2,
        )

    def __repr__(self):
        try:
            s = self.shape
            return f"<Blob '{self._name}' shape={s}>"
        except Exception:
            return f"<Blob '{self._name}'>"


class _BlobDict(OrderedDict):
    """OrderedDict wrapper providing net.blobs BVLC-style access."""

    def __init__(self, net: "Net"):
        super().__init__()
        self._net = net

    def _refresh(self):
        for name in self._net.blob_names:
            if name not in self:
                super().__setitem__(name, _BlobView(self._net, name))

    def keys(self):
        self._refresh()
        return super().keys()

    def values(self):
        self._refresh()
        return super().values()

    def items(self):
        self._refresh()
        return super().items()

    def __getitem__(self, key):
        self._refresh()
        return super().__getitem__(key)

    def __contains__(self, key):
        self._refresh()
        return super().__contains__(key)

    def __iter__(self):
        self._refresh()
        return super().__iter__()

    def __len__(self):
        self._refresh()
        return super().__len__()


class Net:
    """Caffe Net for inference (CPU-only) - BVLC API compatible wrapper.

    BVLC signature: Net(model_file, pretrained_file=None, phase=TEST)
    caffe-slim signature: Net(network_file, phase=TEST, weights=None)

    This wrapper accepts BVLC-style argument order and provides:
    - net.blobs dictionary access with .data numpy arrays
    - net.forward() returning dict of output blobs
    - net.blobs['name'].data[...] = arr for setting inputs
    """

    def __init__(
        self,
        network_file: str,
        *args,
        **kwargs,
    ):
        self._mod = _find_lib()
        self._handle = None
        self._blobs = _BlobDict(self)

        weights = None
        phase = TEST

        if len(args) >= 1:
            first = args[0]
            if isinstance(first, int):
                phase = first
                if len(args) >= 2:
                    weights = args[1]
            elif isinstance(first, (str, bytes)) or first is None:
                weights = first
                if len(args) >= 2:
                    phase = args[1]
        elif 'weights' in kwargs:
            weights = kwargs['weights']
            if 'phase' in kwargs:
                phase = kwargs['phase']
        elif 'phase' in kwargs:
            phase = kwargs['phase']
            if 'pretrained_file' in kwargs:
                weights = kwargs['pretrained_file']
        elif 'pretrained_file' in kwargs:
            weights = kwargs['pretrained_file']

        if isinstance(phase, str):
            if phase.lower() == 'train':
                phase = TRAIN
            elif phase.lower() == 'test':
                phase = TEST

        if weights is not None:
            self._handle = self._mod.Net_Init_Load(network_file, weights, phase)
        else:
            self._handle = self._mod.Net_Init(network_file, phase)

    def __del__(self):
        if self._handle is not None and self._mod is not None:
            try:
                self._mod.Net_Destroy(self._handle)
            except Exception:
                pass
            self._handle = None

    def reshape(self):
        try:
            self._mod.Net_Reshape(self._handle)
        except AttributeError:
            warnings.warn(
                "net.reshape() not available in this caffe-slim build.",
                RuntimeWarning,
                stacklevel=2,
            )

    def forward(self, **kwargs) -> Dict[str, np.ndarray]:
        """Run forward pass. Returns dict of output blobs (BVLC-compatible).

        Input blobs can be set via keyword arguments: net.forward(data=input_array)
        or beforehand via net.blobs['data'].data[...] = input_array.
        """
        for blob_name, data in kwargs.items():
            self.set_input_data(blob_name, data)
        self._mod.Net_Forward(self._handle)
        result = OrderedDict()
        for output_name in self.outputs:
            result[output_name] = self.blob_data(output_name)
        return result

    def forward_all(self, **kwargs) -> Dict[str, np.ndarray]:
        return self.forward(**kwargs)

    @property
    def blob_names(self) -> List[str]:
        return list(self._mod.Net_BlobNames(self._handle))

    @property
    def blobs(self) -> _BlobDict:
        return self._blobs

    @property
    def inputs(self) -> List[str]:
        return list(self._mod.Net_InputBlobNames(self._handle))

    @property
    def outputs(self) -> List[str]:
        return list(self._mod.Net_OutputBlobNames(self._handle))

    @property
    def layers(self):
        return []

    @property
    def layer_dict(self):
        return {}

    def blob_shape(self, blob_name: str) -> tuple:
        return tuple(self._mod.Blob_GetShape(self._handle, blob_name))

    def blob_data(self, blob_name: str) -> np.ndarray:
        tensor = self._mod.Blob_GetData(self._handle, blob_name)
        arr = np.from_dlpack(tensor)
        try:
            arr.flags.writeable = True
        except ValueError:
            pass
        return arr

    def blob_diff(self, blob_name: str) -> np.ndarray:
        tensor = self._mod.Blob_GetDiff(self._handle, blob_name)
        arr = np.from_dlpack(tensor)
        try:
            arr.flags.writeable = True
        except ValueError:
            pass
        return arr

    def set_input_data(self, input_name: str, data: np.ndarray):
        if not data.flags['C_CONTIGUOUS']:
            data = np.ascontiguousarray(data)
        if data.dtype != np.float32:
            data = data.astype(np.float32)
        tensor = tvm_ffi.from_dlpack(data)
        self._mod.Blob_SetData(self._handle, input_name, tensor)

    def copy_from(self, weights_file: str):
        self._mod.Net_CopyTrainedLayersFrom(self._handle, weights_file)

    def save(self, filename: str):
        raise NotImplementedError("save() not available in slim inference-only build")

    def share_with(self, other):
        warnings.warn("share_with() not available in caffe-slim build.", RuntimeWarning, stacklevel=2)


def set_mode_cpu():
    _find_lib()
    _mod.SetModeCPU()


def set_mode_gpu():
    warnings.warn(
        "GPU mode not available in caffe-slim CPU-only build. Using CPU.",
        RuntimeWarning,
        stacklevel=2,
    )


def set_device(device_id: int):
    pass


def set_random_seed(seed: int):
    _find_lib()
    _mod.SetRandomSeed(seed)


def layer_type_list() -> List[str]:
    _find_lib()
    return list(_mod.LayerTypeList())


def version() -> str:
    _find_lib()
    return _mod.Version()


from . import io
from . import proto
from .io import (
    Transformer,
    load_image,
    resize_image,
    blobproto_to_array,
    array_to_blobproto,
    oversample,
)

sys.modules['caffe.io'] = io
sys.modules['caffe.proto'] = proto
sys.modules['caffe.proto.caffe_pb2'] = proto.caffe_pb2

set_mode_cpu()

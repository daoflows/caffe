from __future__ import annotations

import os
from typing import List, Optional

import numpy as np

from . import _ffi_api


class Blob:
    
    _type_key = "caffe_ffi.Blob"
    
    def __init__(self, shape: Optional[List[int]] = None, handle=None):
        from . import _ffi_api as ffi
        self._handle = None
        self._name = ""
        if handle is not None:
            self._handle = handle
        elif ffi.is_available():
            new_blob = ffi.get_global_func("caffe_ffi.NewBlobFromShape")
            if new_blob is not None and shape is not None:
                self._handle = new_blob(list(shape))
            else:
                new_blob_fn = ffi.get_global_func("caffe_ffi.NewBlob")
                if new_blob_fn is not None:
                    self._handle = new_blob_fn()
                    if shape is not None:
                        self.Reshape(shape)
                else:
                    self._init_python(shape)
        else:
            self._init_python(shape)
    
    def _init_python(self, shape: Optional[List[int]]) -> None:
        if shape is None:
            shape = ()
        self._data: np.ndarray = np.zeros(shape, dtype=np.float32)
        self._diff: np.ndarray = np.zeros_like(self._data)
        self._shape: List[int] = list(shape)
    
    def Reshape(self, shape: List[int]) -> None:
        from . import _ffi_api as ffi
        if self._handle is not None:
            self._handle.Reshape(list(shape))
        else:
            self._data = np.zeros(shape, dtype=np.float32)
            self._diff = np.zeros_like(self._data)
            self._shape = list(shape)
    
    @property
    def shape(self) -> tuple:
        if self._handle is not None:
            return tuple(self._handle.shape())
        else:
            return tuple(self._shape)
    
    @property
    def num_axes(self) -> int:
        if self._handle is not None:
            return self._handle.num_axes()
        else:
            return len(self._shape)
    
    @property
    def ndim(self) -> int:
        return self.num_axes
    
    def count(self) -> int:
        if self._handle is not None:
            return self._handle.count()
        else:
            return int(np.prod(self._shape))
    
    @property
    def size(self) -> int:
        return self.count()
    
    def get_data(self) -> List[float]:
        if self._handle is not None:
            return list(self._handle.get_data())
        else:
            return self._data.flatten().tolist()
    
    def set_data(self, data: List[float]) -> None:
        if self._handle is not None:
            self._handle.set_data(data)
        else:
            self._data = np.array(data, dtype=np.float32).reshape(self._shape)
    
    def get_diff(self) -> List[float]:
        if self._handle is not None:
            return list(self._handle.get_diff())
        else:
            return self._diff.flatten().tolist()
    
    def set_diff(self, diff: List[float]) -> None:
        if self._handle is not None:
            self._handle.set_diff(diff)
        else:
            self._diff = np.array(diff, dtype=np.float32).reshape(self._shape)


class Layer:
    
    _type_key = "caffe_ffi.Layer"
    
    def __init__(self, handle=None):
        self._handle = handle
    
    @property
    def type(self) -> str:
        if self._handle is not None:
            return self._handle.type()
        return ""
    
    @property
    def blobs(self) -> List[Blob]:
        if hasattr(self, '_handle') and self._handle is not None:
            blob_arr = self._handle.blobs_array() if hasattr(self._handle, 'blobs_array') else []
            return [Blob(handle=b) for b in blob_arr]
        return getattr(self, '_blobs', [])


class Net:
    
    _type_key = "caffe_ffi.Net"
    
    def __init__(self, param=None, handle=None):
        from . import _ffi_api as ffi
        if handle is not None:
            self._handle = handle
        elif param is not None and isinstance(param, (str, os.PathLike)) and ffi.is_available():
            param_str = str(param)
            if os.path.isfile(param_str):
                new_net = ffi.get_global_func("caffe_ffi.NewNetFromFile")
                if new_net is None:
                    raise RuntimeError("caffe_ffi.NewNetFromFile not found. Ensure caffe-ffi C++ library is built correctly.")
                self._handle = new_net(param_str)
            else:
                new_net = ffi.get_global_func("caffe_ffi.NewNetFromProtoString")
                if new_net is None:
                    raise RuntimeError("caffe_ffi.NewNetFromProtoString not found. Ensure caffe-ffi C++ library is built correctly.")
                self._handle = new_net(param_str)
        else:
            self._handle = None
            self._name = ""
            self._blobs: dict = {}
            self._layers: dict = {}
            self._blob_list: List[Blob] = []
            self._layer_list: List[Layer] = []
            self._input_blobs: List[Blob] = []
            self._output_blobs: List[Blob] = []
    
    @property
    def name(self) -> str:
        if self._handle is not None:
            return self._handle.name()
        return getattr(self, '_name', '')
    
    def Forward(self, inputs=None):
        if self._handle is not None:
            input_map = {}
            if inputs:
                for k, v in inputs.items():
                    if isinstance(v, np.ndarray):
                        input_map[k] = v.flatten().tolist()
                    else:
                        input_map[k] = v
            return self._handle.Forward(input_map)
        return {}
    
    def blobs_array(self) -> List[Blob]:
        if self._handle is not None:
            return [Blob(handle=b) for b in self._handle.blobs_array()]
        return list(self._blob_list)
    
    def layers_array(self) -> List[Layer]:
        if self._handle is not None:
            return [Layer(handle=l) for l in self._handle.layers_array()]
        return list(self._layer_list)
    
    def input_blobs_array(self) -> List[Blob]:
        if self._handle is not None:
            return [Blob(handle=b) for b in self._handle.input_blobs_array()]
        return list(self._input_blobs)
    
    def output_blobs_array(self) -> List[Blob]:
        if self._handle is not None:
            return [Blob(handle=b) for b in self._handle.output_blobs_array()]
        return list(self._output_blobs)
    
    def blob_by_name(self, name: str) -> Blob:
        if self._handle is not None:
            return Blob(handle=self._handle.blob_by_name(name))
        if name in self._blobs:
            return self._blobs[name]
        raise KeyError(f"Blob '{name}' not found")
    
    def layer_by_name(self, name: str) -> Layer:
        if self._handle is not None:
            return Layer(handle=self._handle.layer_by_name(name))
        if name in self._layers:
            return self._layers[name]
        raise KeyError(f"Layer '{name}' not found")
    
    def has_blob(self, name: str) -> bool:
        if self._handle is not None:
            return self._handle.has_blob(name)
        return name in self._blobs
    
    def has_layer(self, name: str) -> bool:
        if self._handle is not None:
            return self._handle.has_layer(name)
        return name in self._layers


def _register_types():
    if not _ffi_api.is_available():
        return
    
    try:
        _ffi_api.registry.register_object(Blob._type_key, Blob)
        _ffi_api.registry.register_object(Layer._type_key, Layer)
        _ffi_api.registry.register_object(Net._type_key, Net)
    except Exception:
        pass


_register_types()

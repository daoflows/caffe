from __future__ import annotations

import os
from typing import List, Optional

import numpy as np

from . import _ffi_api

import tvm_ffi


class Blob(tvm_ffi.Object):

    _type_key = "caffe_ffi.Blob"
    __slots__ = ['_py_shape', '_py_data', '_py_diff', '_py_name']

    def __new__(cls, shape=None, handle=None):
        inst = super().__new__(cls)
        inst._py_shape = []
        inst._py_data = None
        inst._py_diff = None
        inst._py_name = ""
        return inst

    @property
    def _handle(self):
        return self if self._is_native else None

    @property
    def _data(self):
        return self._py_data

    @_data.setter
    def _data(self, value):
        self._py_data = value

    @property
    def _diff(self):
        return self._py_diff

    @_diff.setter
    def _diff(self, value):
        self._py_diff = value

    def __init__(self, shape: Optional[List[int]] = None, handle=None):
        if self._is_native:
            return
        if handle is not None and not isinstance(handle, (list, tuple)):
            if hasattr(handle, 'shape'):
                self._py_shape = list(handle.shape)
                self._py_data = np.zeros(self._py_shape, dtype=np.float32)
                self._py_diff = np.zeros_like(self._py_data)
                return
        if _ffi_api.is_available():
            new_blob_fn = _ffi_api.get_global_func("caffe_ffi.NewBlob")
            if new_blob_fn is not None:
                self.__init_handle_by_constructor__(new_blob_fn)
                if shape is not None:
                    Blob._native_reshape(self, list(shape))
                return
        self._init_python(shape)

    def _init_python(self, shape: Optional[List[int]]) -> None:
        if shape is None:
            shape = ()
        self._py_data = np.zeros(shape, dtype=np.float32)
        self._py_diff = np.zeros_like(self._py_data)
        self._py_shape = list(shape)

    @property
    def _is_native(self) -> bool:
        return self.__chandle__() != 0


class Layer(tvm_ffi.Object):

    _type_key = "caffe_ffi.Layer"
    __slots__ = ['_py_blobs', '_py_name']

    def __new__(cls, handle=None):
        inst = super().__new__(cls)
        inst._py_blobs = []
        inst._py_name = ""
        return inst

    def __init__(self, handle=None):
        if self._is_native:
            return

    @property
    def _is_native(self) -> bool:
        return self.__chandle__() != 0


class Net(tvm_ffi.Object):

    _type_key = "caffe_ffi.Net"
    __slots__ = ['_py_name', '_py_blobs', '_py_layers', '_py_blob_list',
                 '_py_layer_list', '_py_input_blobs', '_py_output_blobs',
                 '_py_input_blob_names', '_py_output_blob_names']

    def __new__(cls, param=None, handle=None):
        inst = super().__new__(cls)
        inst._py_name = ""
        inst._py_blobs = {}
        inst._py_layers = {}
        inst._py_blob_list = []
        inst._py_layer_list = []
        inst._py_input_blobs = []
        inst._py_output_blobs = []
        inst._py_input_blob_names = []
        inst._py_output_blob_names = []
        return inst

    def __init__(self, param=None, handle=None):
        if self._is_native:
            return
        if param is not None and isinstance(param, (str, os.PathLike)) and _ffi_api.is_available():
            param_str = str(param)
            if os.path.isfile(param_str):
                ctor = _ffi_api.get_global_func("caffe_ffi.NewNetFromFile")
                if ctor is None:
                    raise RuntimeError("caffe_ffi.NewNetFromFile not found")
                self.__init_handle_by_constructor__(ctor, param_str)
                return
            else:
                ctor = _ffi_api.get_global_func("caffe_ffi.NewNetFromProtoString")
                if ctor is None:
                    raise RuntimeError("caffe_ffi.NewNetFromProtoString not found")
                self.__init_handle_by_constructor__(ctor, param_str)
                return

    @property
    def _is_native(self) -> bool:
        return self.__chandle__() != 0


def _register_types():
    if not _ffi_api.is_available():
        return
    try:
        _ffi_api.registry.register_object(Blob._type_key, Blob)
        _ffi_api.registry.register_object(Layer._type_key, Layer)
        _ffi_api.registry.register_object(Net._type_key, Net)
    except Exception:
        return
    _add_python_wrappers()


def _add_python_wrappers():
    Blob._native_shape = getattr(Blob, 'shape', None)
    Blob._native_num_axes = getattr(Blob, 'num_axes', None)
    Blob._native_count = getattr(Blob, 'count', None)
    Blob._native_reshape = getattr(Blob, 'Reshape', None)
    Blob._native_get_data = getattr(Blob, 'get_data', None)
    Blob._native_set_data = getattr(Blob, 'set_data', None)
    Blob._native_get_diff = getattr(Blob, 'get_diff', None)
    Blob._native_set_diff = getattr(Blob, 'set_diff', None)
    Blob._native_name = getattr(Blob, 'name', None)
    Blob._native_set_name = getattr(Blob, 'set_name', None)

    def _blob_shape(self):
        if self._is_native and Blob._native_shape is not None:
            return tuple(Blob._native_shape(self))
        return tuple(self._py_shape)

    def _blob_num_axes(self):
        if self._is_native and Blob._native_num_axes is not None:
            return Blob._native_num_axes(self)
        return len(self._py_shape)

    def _blob_count(self):
        if self._is_native and Blob._native_count is not None:
            return Blob._native_count(self)
        return int(np.prod(self._py_shape)) if self._py_shape else 0

    def _blob_reshape(self, shape):
        if self._is_native and Blob._native_reshape is not None:
            Blob._native_reshape(self, list(shape))
        else:
            self._py_data = np.zeros(shape, dtype=np.float32)
            self._py_diff = np.zeros_like(self._py_data)
            self._py_shape = list(shape)

    def _blob_get_data(self):
        if self._is_native and Blob._native_get_data is not None:
            return list(Blob._native_get_data(self))
        return self._py_data.flatten().tolist() if self._py_data is not None else []

    def _blob_set_data(self, data):
        if self._is_native and Blob._native_set_data is not None:
            Blob._native_set_data(self, data)
        else:
            self._py_data = np.array(data, dtype=np.float32).reshape(self._py_shape)

    def _blob_get_diff(self):
        if self._is_native and Blob._native_get_diff is not None:
            return list(Blob._native_get_diff(self))
        return self._py_diff.flatten().tolist() if self._py_diff is not None else []

    def _blob_set_diff(self, diff):
        if self._is_native and Blob._native_set_diff is not None:
            Blob._native_set_diff(self, diff)
        else:
            self._py_diff = np.array(diff, dtype=np.float32).reshape(self._py_shape)

    def _blob_get_name(self):
        if self._is_native and Blob._native_name is not None:
            return Blob._native_name(self)
        return getattr(self, '_py_name', '')

    def _blob_set_name(self, value):
        if self._is_native and Blob._native_set_name is not None:
            Blob._native_set_name(self, value)
        else:
            self._py_name = value

    Blob.shape = property(_blob_shape)
    Blob.num_axes = property(_blob_num_axes)
    Blob.ndim = property(_blob_num_axes)
    Blob.size = property(_blob_count)
    Blob.count = _blob_count
    Blob.Reshape = _blob_reshape
    Blob.get_data = _blob_get_data
    Blob.set_data = _blob_set_data
    Blob.get_diff = _blob_get_diff
    Blob.set_diff = _blob_set_diff
    Blob.name = property(_blob_get_name, _blob_set_name)

    def _blob_data_property(self):
        data_list = self.get_data()
        if not data_list:
            return np.zeros(self.shape, dtype=np.float32)
        return np.array(data_list, dtype=np.float32).reshape(self.shape)

    def _blob_diff_property(self):
        diff_list = self.get_diff()
        if not diff_list:
            return np.zeros(self.shape, dtype=np.float32)
        return np.array(diff_list, dtype=np.float32).reshape(self.shape)

    Blob.data = property(_blob_data_property)
    Blob.diff = property(_blob_diff_property)

    Layer._native_type = getattr(Layer, 'type', None)
    Layer._native_blobs_array = getattr(Layer, 'blobs_array', None)
    Layer._native_name = getattr(Layer, 'name', None)

    def _layer_type(self):
        if self._is_native and Layer._native_type is not None:
            return Layer._native_type(self)
        return ""

    def _layer_blobs(self):
        if self._is_native and Layer._native_blobs_array is not None:
            return list(Layer._native_blobs_array(self))
        return list(self._py_blobs)

    def _layer_get_name(self):
        if self._is_native and Layer._native_name is not None:
            return Layer._native_name(self)
        return getattr(self, '_py_name', '')

    def _layer_set_name(self, value):
        self._py_name = value

    Layer.type = property(_layer_type)
    Layer.blobs = property(_layer_blobs)
    Layer.name = property(_layer_get_name, _layer_set_name)

    Net._native_name = getattr(Net, 'name', None)
    Net._native_forward = getattr(Net, 'Forward', None)
    Net._native_blobs_array = getattr(Net, 'blobs_array', None)
    Net._native_layers_array = getattr(Net, 'layers_array', None)
    Net._native_input_blobs = getattr(Net, 'input_blobs_array', None)
    Net._native_output_blobs = getattr(Net, 'output_blobs_array', None)
    Net._native_blob_by_name = getattr(Net, 'blob_by_name', None)
    Net._native_layer_by_name = getattr(Net, 'layer_by_name', None)
    Net._native_has_blob = getattr(Net, 'has_blob', None)
    Net._native_has_layer = getattr(Net, 'has_layer', None)
    Net._native_copy_trained = getattr(Net, 'CopyTrainedLayersFrom', None)
    Net._native_input_blob_names = getattr(Net, 'input_blob_names', None)
    Net._native_output_blob_names = getattr(Net, 'output_blob_names', None)
    Net._native_blob_names = getattr(Net, 'blob_names', None)
    Net._native_layer_names = getattr(Net, 'layer_names', None)

    def _net_name(self):
        if self._is_native and Net._native_name is not None:
            return Net._native_name(self)
        return getattr(self, '_py_name', '')

    def _net_forward(self, inputs=None):
        if self._is_native and Net._native_forward is not None:
            input_map = {}
            if inputs:
                for k, v in inputs.items():
                    if isinstance(v, np.ndarray):
                        input_map[k] = v.flatten().tolist()
                    else:
                        input_map[k] = v
            return Net._native_forward(self, input_map)
        return {}

    def _net_blobs_array(self):
        if self._is_native and Net._native_blobs_array is not None:
            return list(Net._native_blobs_array(self))
        return list(self._py_blob_list)

    def _net_layers_array(self):
        if self._is_native and Net._native_layers_array is not None:
            return list(Net._native_layers_array(self))
        return list(self._py_layer_list)

    def _net_input_blobs(self):
        if self._is_native and Net._native_input_blobs is not None:
            return list(Net._native_input_blobs(self))
        return list(self._py_input_blobs)

    def _net_output_blobs(self):
        if self._is_native and Net._native_output_blobs is not None:
            return list(Net._native_output_blobs(self))
        return list(self._py_output_blobs)

    def _net_blob_by_name(self, name):
        if self._is_native and Net._native_blob_by_name is not None:
            return Net._native_blob_by_name(self, name)
        if name in self._py_blobs:
            return self._py_blobs[name]
        raise KeyError(f"Blob '{name}' not found")

    def _net_layer_by_name(self, name):
        if self._is_native and Net._native_layer_by_name is not None:
            return Net._native_layer_by_name(self, name)
        if name in self._py_layers:
            return self._py_layers[name]
        raise KeyError(f"Layer '{name}' not found")

    def _net_has_blob(self, name):
        if self._is_native and Net._native_has_blob is not None:
            return Net._native_has_blob(self, name)
        return name in self._py_blobs

    def _net_has_layer(self, name):
        if self._is_native and Net._native_has_layer is not None:
            return Net._native_has_layer(self, name)
        return name in self._py_layers

    def _net_input_blob_names(self):
        if self._is_native and Net._native_input_blob_names is not None:
            return list(Net._native_input_blob_names(self))
        return list(self._py_input_blob_names)

    def _net_output_blob_names(self):
        if self._is_native and Net._native_output_blob_names is not None:
            return list(Net._native_output_blob_names(self))
        return list(self._py_output_blob_names)

    def _net_blob_names(self):
        if self._is_native and Net._native_blob_names is not None:
            return list(Net._native_blob_names(self))
        return list(self._py_blobs.keys())

    def _net_layer_names(self):
        if self._is_native and Net._native_layer_names is not None:
            return list(Net._native_layer_names(self))
        return list(self._py_layers.keys())

    def _net_copy_trained(self, trained_filename):
        if self._is_native and Net._native_copy_trained is not None:
            Net._native_copy_trained(self, str(trained_filename))

    Net.name = property(_net_name)
    Net.Forward = _net_forward
    Net.blobs_array = _net_blobs_array
    Net.layers_array = _net_layers_array
    Net.input_blobs_array = _net_input_blobs
    Net.output_blobs_array = _net_output_blobs
    Net.blob_by_name = _net_blob_by_name
    Net.layer_by_name = _net_layer_by_name
    Net.has_blob = _net_has_blob
    Net.has_layer = _net_has_layer
    Net.input_blob_names = _net_input_blob_names
    Net.output_blob_names = _net_output_blob_names
    Net.blob_names = _net_blob_names
    Net.layer_names = _net_layer_names
    Net.CopyTrainedLayersFrom = _net_copy_trained


_register_types()

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

import numpy as np

from . import caffe_pb2
from .io import read_net_from_binary
from ._core import Net, Blob, Layer


def _set_input_blobs(net: Net, input_dict: Dict[str, np.ndarray]) -> None:
    """Set input blobs from numpy arrays."""
    input_blobs = net.input_blobs_array()
    input_names = []
    if hasattr(net, '_handle') and net._handle is not None:
        if hasattr(net._handle, 'input_blob_names'):
            input_names = list(net._handle.input_blob_names())
    
    if input_dict:
        for name, arr in input_dict.items():
            try:
                blob = net.blob_by_name(name)
                blob.data = np.asarray(arr, dtype=np.float32)
            except (KeyError, AttributeError):
                for input_blob in input_blobs:
                    if input_blob.shape == np.asarray(arr).shape:
                        input_blob.data = np.asarray(arr, dtype=np.float32)
                        break
    else:
        pass


def forward(self, input_dict: Optional[Dict[str, np.ndarray]] = None) -> Dict[str, np.ndarray]:
    """
    Run forward pass and return output blobs as numpy arrays.
    
    Args:
        input_dict: Dictionary mapping input blob names to numpy arrays.
    
    Returns:
        Dictionary mapping output blob names to numpy arrays.
    """
    if input_dict is None:
        input_dict = {}
    
    _set_input_blobs(self, input_dict)
    
    if hasattr(self, '_handle') and self._handle is not None:
        result_map = self.Forward()
        result = {}
        if result_map:
            for name, blob_handle in result_map.items():
                blob = Blob(handle=blob_handle)
                result[name] = blob.data
        else:
            output_blobs = self.output_blobs_array()
            output_names = []
            if hasattr(self._handle, 'output_blob_names'):
                try:
                    output_names = list(self._handle.output_blob_names())
                except Exception:
                    pass
            for i, blob in enumerate(output_blobs):
                name = output_names[i] if i < len(output_names) else f"output_{i}"
                result[name] = blob.data
        return result
    else:
        return self._forward_pure_python(input_dict)


def forward_all(self, **kwargs: np.ndarray) -> Dict[str, np.ndarray]:
    """Convenience wrapper for forward with keyword arguments."""
    return self.forward(kwargs)


def copy_from(self, trained_filename: Union[str, Path]) -> None:
    """
    Copy trained layers from a caffemodel file.
    
    Args:
        trained_filename: Path to .caffemodel binary file
    """
    if hasattr(self, '_handle') and self._handle is not None:
        self._handle.CopyTrainedLayersFrom(str(trained_filename))
    else:
        self._copy_from_pure_python(trained_filename)


def _copy_from_pure_python(self, trained_filename: Union[str, Path]) -> None:
    """Pure Python implementation of copy_from."""
    trained_net_param = read_net_from_binary(trained_filename)
    
    trained_layer_map = {}
    for layer in trained_net_param.layer:
        trained_layer_map[layer.name] = layer
    
    for layer in self.layers_array():
        layer_name = layer.name
        if not layer_name or layer_name not in trained_layer_map:
            continue
        
        source_layer = trained_layer_map[layer_name]
        target_blobs = layer.blobs
        num_blobs_to_copy = min(len(target_blobs), len(source_layer.blobs))
        
        for j in range(num_blobs_to_copy):
            source_blob_proto = source_layer.blobs[j]
            target_blob = target_blobs[j]
            
            if source_blob_proto.HasField('shape') and source_blob_proto.shape.dim:
                dims = list(source_blob_proto.shape.dim)
            else:
                dims = [source_blob_proto.num, source_blob_proto.channels, 
                       source_blob_proto.height, source_blob_proto.width]
                dims = [d for d in dims if d != 0]
            
            data_list = None
            if source_blob_proto.data:
                data_list = list(source_blob_proto.data)
            elif source_blob_proto.double_data:
                data_list = [float(v) for v in source_blob_proto.double_data]
            
            if not dims and data_list:
                dims = [len(data_list)]
            
            if dims:
                target_blob.Reshape(dims)
            
            if data_list:
                target_blob.data = np.array(data_list, dtype=np.float32).reshape(target_blob.shape)


@property
def blobs_dict(self) -> Dict[str, Blob]:
    """Return dictionary of all blobs by name."""
    result = {}
    if hasattr(self, '_handle') and self._handle is not None:
        if hasattr(self._handle, 'blob_names'):
            names = list(self._handle.blob_names())
        else:
            names = []
        blobs = self.blobs_array()
        for i, blob in enumerate(blobs):
            if i < len(names):
                result[names[i]] = blob
            else:
                result[f"blob_{i}"] = blob
    else:
        result = dict(self._blobs)
    return result


@property
def layers_dict(self) -> Dict[str, Layer]:
    """Return dictionary of all layers by name."""
    result = {}
    if hasattr(self, '_handle') and self._handle is not None:
        if hasattr(self._handle, 'layer_names'):
            names = list(self._handle.layer_names())
        else:
            names = []
        layers = self.layers_array()
        for i, layer in enumerate(layers):
            if i < len(names):
                result[names[i]] = layer
            else:
                result[f"layer_{i}"] = layer
    else:
        result = dict(self._layers)
    return result


def __getitem__(self, name: str) -> Blob:
    """Access blob by name."""
    return self.blob_by_name(name)


def __contains__(self, name: str) -> bool:
    """Check if blob exists."""
    return self.has_blob(name)


def __iter__(self) -> Iterator[str]:
    """Iterate over blob names."""
    return iter(self.blobs_dict.keys())


def __len__(self) -> int:
    return len(self.blobs_array())


def net_repr(self) -> str:
    return f"Net(name='{self.name}', {len(self.blobs_array())} blobs, {len(self.layers_array())} layers)"


def _forward_pure_python(self, input_dict: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """Pure Python forward implementation for testing (stub)."""
    for name, arr in input_dict.items():
        if name in self._blobs:
            self._blobs[name].from_numpy(arr)
    
    result = {}
    for blob in self._output_blobs:
        result[blob.name] = blob.data
    return result


def _patch_net():
    """Apply monkey patches to Net class."""
    Net.forward = forward
    Net.forward_all = forward_all
    Net.copy_from = copy_from
    Net.blobs_dict = blobs_dict
    Net.layers_dict = layers_dict
    Net.__getitem__ = __getitem__
    Net.__contains__ = __contains__
    Net.__iter__ = __iter__
    Net.__len__ = __len__
    Net.__repr__ = net_repr
    Net._forward_pure_python = _forward_pure_python
    Net._copy_from_pure_python = _copy_from_pure_python


_patch_net()

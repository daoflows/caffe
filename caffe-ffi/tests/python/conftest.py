from __future__ import annotations

import sys
from pathlib import Path

import pytest
import numpy as np

_project_root = Path(__file__).resolve().parent.parent.parent
_python_dir = _project_root / "python"
if str(_python_dir) not in sys.path:
    sys.path.insert(0, str(_python_dir))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "require_cpp_extension: mark test as requiring C++ extension"
    )


from caffe_ffi import _ffi_api


def _check_cpp_extension_available() -> bool:
    return _ffi_api.is_available()


require_cpp_extension = pytest.mark.skipif(
    not _check_cpp_extension_available(),
    reason="C++ extension not available, skipping test"
)


@pytest.fixture
def mlp_prototxt() -> str:
    """Simple MLP prototxt: Input -> InnerProduct -> ReLU -> InnerProduct -> Softmax."""
    return """name: "mlp_test"
input: "data"
input_shape {
  dim: 2
  dim: 3
}
layer {
  name: "ip1"
  type: "InnerProduct"
  bottom: "data"
  top: "ip1"
  inner_product_param {
    num_output: 4
    bias_term: true
  }
}
layer {
  name: "relu1"
  type: "ReLU"
  bottom: "ip1"
  top: "ip1"
}
layer {
  name: "ip2"
  type: "InnerProduct"
  bottom: "ip1"
  top: "ip2"
  inner_product_param {
    num_output: 2
    bias_term: true
  }
}
layer {
  name: "prob"
  type: "Softmax"
  bottom: "ip2"
  top: "prob"
}
"""


@pytest.fixture
def mlp_weights():
    """Manual weights for MLP testing."""
    np.random.seed(42)
    W1 = np.array([
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
        [0.7, 0.8, 0.9],
        [1.0, 1.1, 1.2],
    ], dtype=np.float32)
    b1 = np.array([0.01, 0.02, 0.03, 0.04], dtype=np.float32)
    
    W2 = np.array([
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
    ], dtype=np.float32)
    b2 = np.array([0.001, 0.002], dtype=np.float32)
    
    return {"W1": W1, "b1": b1, "W2": W2, "b2": b2}


@pytest.fixture
def mlp_net(mlp_prototxt):
    """Create MLP network (uses C++ extension when available)."""
    from caffe_ffi import net_from_param, net_param_from_string, caffe_pb2
    from caffe_ffi._core import Blob
    
    param = net_param_from_string(mlp_prototxt)
    
    if _ffi_api.is_available():
        net = net_from_param(param)
        W1 = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
            [1.0, 1.1, 1.2],
        ], dtype=np.float32)
        b1 = np.array([0.01, 0.02, 0.03, 0.04], dtype=np.float32)
        W2 = np.array([
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7, 0.8],
        ], dtype=np.float32)
        b2 = np.array([0.001, 0.002], dtype=np.float32)
        
        layers = net.layers_array()
        if len(layers) >= 1 and hasattr(layers[0], 'blobs') and len(layers[0].blobs) >= 2:
            layers[0].blobs[0].from_numpy(W1)
            layers[0].blobs[1].from_numpy(b1.reshape(-1))
        if len(layers) >= 3 and hasattr(layers[3], 'blobs') and len(layers[3].blobs) >= 2:
            layers[3].blobs[0].from_numpy(W2)
            layers[3].blobs[1].from_numpy(b2.reshape(-1))
    else:
        net = _build_mlp_python(param)
    
    return net


def _build_mlp_python(param):
    """Build a minimal MLP net in pure Python for testing (without C++ extension)."""
    from caffe_ffi._core import Net, Blob, Layer
    
    net = Net.__new__(Net)
    net._handle = None
    net._name = param.name
    net._blobs = {}
    net._layers = {}
    net._blob_list = []
    net._layer_list = []
    net._input_blobs = []
    net._output_blobs = []
    
    data_blob = Blob([2, 3])
    data_blob.name = "data"
    net._blobs["data"] = data_blob
    net._blob_list.append(data_blob)
    net._input_blobs.append(data_blob)
    
    ip1_blob = Blob([2, 4])
    ip1_blob.name = "ip1"
    net._blobs["ip1"] = ip1_blob
    net._blob_list.append(ip1_blob)
    
    ip2_blob = Blob([2, 2])
    ip2_blob.name = "ip2"
    net._blobs["ip2"] = ip2_blob
    net._blob_list.append(ip2_blob)
    
    prob_blob = Blob([2, 2])
    prob_blob.name = "prob"
    net._blobs["prob"] = prob_blob
    net._blob_list.append(prob_blob)
    net._output_blobs.append(prob_blob)
    
    W1 = np.array([
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
        [0.7, 0.8, 0.9],
        [1.0, 1.1, 1.2],
    ], dtype=np.float32)
    b1 = np.array([0.01, 0.02, 0.03, 0.04], dtype=np.float32)
    W2 = np.array([
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
    ], dtype=np.float32)
    b2 = np.array([0.001, 0.002], dtype=np.float32)
    
    ip1_layer = Layer()
    ip1_layer._handle = None
    ip1_layer._name = "ip1"
    ip1_layer._type_str = "InnerProduct"
    ip1_w = Blob([4, 3])
    ip1_w.from_numpy(W1)
    ip1_b = Blob([4])
    ip1_b.from_numpy(b1)
    ip1_layer._blobs = [ip1_w, ip1_b]
    
    relu1_layer = Layer()
    relu1_layer._handle = None
    relu1_layer._name = "relu1"
    relu1_layer._type_str = "ReLU"
    relu1_layer._blobs = []
    
    ip2_layer = Layer()
    ip2_layer._handle = None
    ip2_layer._name = "ip2"
    ip2_layer._type_str = "InnerProduct"
    ip2_w = Blob([2, 4])
    ip2_w.from_numpy(W2)
    ip2_b = Blob([2])
    ip2_b.from_numpy(b2)
    ip2_layer._blobs = [ip2_w, ip2_b]
    
    prob_layer = Layer()
    prob_layer._handle = None
    prob_layer._name = "prob"
    prob_layer._type_str = "Softmax"
    prob_layer._blobs = []
    
    net._layers["ip1"] = ip1_layer
    net._layers["relu1"] = relu1_layer
    net._layers["ip2"] = ip2_layer
    net._layers["prob"] = prob_layer
    net._layer_list = [ip1_layer, relu1_layer, ip2_layer, prob_layer]
    
    def _forward_pure_python(self, input_dict):
        data = input_dict.get("data", self._blobs["data"].data)
        self._blobs["data"].data = data
        
        W1 = self._layers["ip1"]._blobs[0].data
        b1 = self._layers["ip1"]._blobs[1].data
        ip1 = np.maximum(0, data @ W1.T + b1)
        self._blobs["ip1"].data = ip1
        
        W2 = self._layers["ip2"]._blobs[0].data
        b2 = self._layers["ip2"]._blobs[1].data
        ip2 = ip1 @ W2.T + b2
        self._blobs["ip2"].data = ip2
        
        exp_ip2 = np.exp(ip2 - np.max(ip2, axis=1, keepdims=True))
        prob = exp_ip2 / np.sum(exp_ip2, axis=1, keepdims=True)
        self._blobs["prob"].data = prob
        
        return {"prob": prob}
    
    import types
    net._forward_pure_python = types.MethodType(_forward_pure_python, net)
    
    def forward(self, input_dict=None):
        if input_dict is None:
            input_dict = {}
        return self._forward_pure_python(input_dict)
    
    net.forward = types.MethodType(forward, net)
    
    return net

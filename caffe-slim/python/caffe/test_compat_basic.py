"""Basic tests for _compat.py (no actual model required)."""

from __future__ import annotations

import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "_compat", Path(__file__).resolve().parent / "_compat.py"
)
_compat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_compat)

BlobProxy = _compat.BlobProxy
enable_bvlc_compat = _compat.enable_bvlc_compat


class MockNet:
    """Mock Net class for testing compatibility layer without real Caffe."""

    def __init__(self):
        self._test_data = {
            'data': np.random.randn(1, 3, 224, 224).astype(np.float32),
            'conv1': np.random.randn(1, 64, 112, 112).astype(np.float32),
            'prob': np.random.randn(1, 1000).astype(np.float32),
        }
        self._test_diff = {
            name: np.zeros_like(arr) for name, arr in self._test_data.items()
        }
        self.forward_called = False

    @property
    def blob_names(self):
        return list(self._test_data.keys())

    @property
    def inputs(self):
        return ['data']

    @property
    def outputs(self):
        return ['prob']

    def blob_shape(self, name):
        return self._test_data[name].shape

    def blob_data(self, name):
        return self._test_data[name]

    def blob_diff(self, name):
        return self._test_diff[name]

    def forward(self):
        self.forward_called = True


def test_blob_proxy_init():
    """Test BlobProxy can be instantiated."""
    net = MockNet()
    proxy = BlobProxy(net, 'data')
    assert proxy._blob_name == 'data'
    assert proxy._net is net
    print("✓ BlobProxy instantiation works")


def test_blob_proxy_data():
    """Test BlobProxy.data property returns numpy array."""
    net = MockNet()
    proxy = BlobProxy(net, 'data')
    data = proxy.data
    assert isinstance(data, np.ndarray)
    assert data.shape == (1, 3, 224, 224)
    assert data.dtype == np.float32
    print("✓ BlobProxy.data returns correct numpy array")


def test_blob_proxy_diff():
    """Test BlobProxy.diff property returns numpy array."""
    net = MockNet()
    proxy = BlobProxy(net, 'prob')
    diff = proxy.diff
    assert isinstance(diff, np.ndarray)
    assert np.all(diff == 0)
    print("✓ BlobProxy.diff returns correct numpy array")


def test_blob_proxy_shape():
    """Test BlobProxy.shape property returns tuple."""
    net = MockNet()
    proxy = BlobProxy(net, 'conv1')
    shape = proxy.shape
    assert isinstance(shape, tuple)
    assert shape == (1, 64, 112, 112)
    print("✓ BlobProxy.shape returns correct tuple")


def test_blob_proxy_count():
    """Test BlobProxy.count returns correct element count."""
    net = MockNet()
    proxy = BlobProxy(net, 'prob')
    assert proxy.count == 1 * 1000
    print("✓ BlobProxy.count returns correct element count")


def test_blob_proxy_array():
    """Test np.asarray(blob_proxy) works."""
    net = MockNet()
    proxy = BlobProxy(net, 'data')
    arr = np.asarray(proxy)
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (1, 3, 224, 224)
    print("✓ np.asarray(BlobProxy) works")


def test_blob_proxy_repr():
    """Test BlobProxy __repr__ works."""
    net = MockNet()
    proxy = BlobProxy(net, 'data')
    r = repr(proxy)
    assert 'BlobProxy' in r
    assert 'data' in r
    print("✓ BlobProxy __repr__ works")


def test_blob_proxy_zero_copy_assignment():
    """Test that proxy.data[...] = arr modifies underlying memory."""
    net = MockNet()
    proxy = BlobProxy(net, 'data')
    new_data = np.ones((1, 3, 224, 224), dtype=np.float32)
    proxy.data[...] = new_data
    assert np.all(net._test_data['data'] == 1.0)
    print("✓ BlobProxy zero-copy assignment works")


def test_enable_bvlc_compat():
    """Test enable_bvlc_compat patches Net class correctly."""
    net = MockNet()
    enable_bvlc_compat(MockNet)

    assert hasattr(MockNet, '_forward_slim')
    assert hasattr(MockNet, '_blob_names')
    assert hasattr(MockNet, '_blobs')
    assert hasattr(MockNet, 'blobs')
    assert hasattr(MockNet, '_inputs')
    assert hasattr(MockNet, '_outputs')
    print("✓ enable_bvlc_compat adds all required properties")


def test_net_blob_names_property():
    """Test _blob_names property works."""
    net = MockNet()
    enable_bvlc_compat(MockNet)
    assert net._blob_names == ['data', 'conv1', 'prob']
    print("✓ Net._blob_names property works")


def test_net_blobs_list():
    """Test _blobs property returns list of BlobProxy."""
    net = MockNet()
    enable_bvlc_compat(MockNet)
    blobs_list = net._blobs
    assert len(blobs_list) == 3
    assert all(isinstance(b, BlobProxy) for b in blobs_list)
    print("✓ Net._blobs returns list of BlobProxy")


def test_net_blobs_ordered_dict():
    """Test blobs property returns OrderedDict with caching."""
    net = MockNet()
    enable_bvlc_compat(MockNet)

    blobs = net.blobs
    assert isinstance(blobs, OrderedDict)
    assert list(blobs.keys()) == ['data', 'conv1', 'prob']
    assert all(isinstance(v, BlobProxy) for v in blobs.values())

    blobs2 = net.blobs
    assert blobs is blobs2
    assert hasattr(net, '_blobs_dict')
    print("✓ Net.blobs returns cached OrderedDict")


def test_net_inputs_indices():
    """Test _inputs property returns correct indices with caching."""
    net = MockNet()
    enable_bvlc_compat(MockNet)
    assert net._inputs == [0]

    net2 = MockNet()
    assert hasattr(net2, '_input_indices') is False
    _ = net2._inputs
    assert hasattr(net2, '_input_indices')
    assert net2._input_indices == [0]
    print("✓ Net._inputs returns correct cached indices")


def test_net_outputs_indices():
    """Test _outputs property returns correct indices with caching."""
    net = MockNet()
    enable_bvlc_compat(MockNet)
    assert net._outputs == [2]
    print("✓ Net._outputs returns correct cached indices")


def test_forward_basic():
    """Test forward() calls _forward_slim and returns outputs."""
    net = MockNet()
    enable_bvlc_compat(MockNet)

    result = net.forward()
    assert net.forward_called is True
    assert 'prob' in result
    assert isinstance(result['prob'], np.ndarray)
    print("✓ forward() calls native forward and returns outputs")


def test_forward_with_blobs():
    """Test forward(blobs=[...]) includes additional blobs."""
    net = MockNet()
    enable_bvlc_compat(MockNet)

    result = net.forward(blobs=['conv1'])
    assert 'prob' in result
    assert 'conv1' in result
    print("✓ forward(blobs=[...]) includes extra blobs")


def test_forward_partial_not_supported():
    """Test forward(start=.../end=...) raises NotImplementedError."""
    net = MockNet()
    enable_bvlc_compat(MockNet)

    try:
        net.forward(start='conv1')
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError:
        pass

    try:
        net.forward(end='prob')
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError:
        pass

    print("✓ forward(start/end) raises NotImplementedError")


def test_forward_kwargs():
    """Test forward(**kwargs) validates inputs and assigns data."""
    net = MockNet()
    enable_bvlc_compat(MockNet)

    input_data = np.random.randn(2, 3, 224, 224).astype(np.float32)
    original_data = net._test_data['data'].copy()

    net._test_data['data'] = np.zeros((2, 3, 224, 224), dtype=np.float32)

    result = net.forward(data=input_data)
    assert np.allclose(net._test_data['data'], input_data)
    assert 'prob' in result
    print("✓ forward(**kwargs) assigns input data correctly")


def test_forward_kwargs_wrong_keys():
    """Test forward with wrong kwargs keys raises ValueError."""
    net = MockNet()
    enable_bvlc_compat(MockNet)

    try:
        net.forward(invalid=np.zeros((1, 3, 224, 224), dtype=np.float32))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert 'mismatch' in str(e)
    print("✓ forward with wrong kwargs keys raises ValueError")


def test_import():
    """Test that module imports correctly."""
    assert hasattr(_compat, 'BlobProxy')
    assert hasattr(_compat, 'enable_bvlc_compat')
    print("✓ Module imports correctly")


if __name__ == '__main__':
    print("Running basic _compat.py tests (no model needed)...\n")
    test_import()
    test_blob_proxy_init()
    test_blob_proxy_data()
    test_blob_proxy_diff()
    test_blob_proxy_shape()
    test_blob_proxy_count()
    test_blob_proxy_array()
    test_blob_proxy_repr()
    test_blob_proxy_zero_copy_assignment()
    test_enable_bvlc_compat()
    test_net_blob_names_property()
    test_net_blobs_list()
    test_net_blobs_ordered_dict()
    test_net_inputs_indices()
    test_net_outputs_indices()
    test_forward_basic()
    test_forward_with_blobs()
    test_forward_partial_not_supported()
    test_forward_kwargs()
    test_forward_kwargs_wrong_keys()
    print("\n✅ All tests passed!")

from __future__ import annotations

import numpy as np
import pytest

import caffe_ffi
from caffe_ffi import Blob


class TestBlobReshape:
    def test_reshape_1d(self):
        b = Blob()
        b.Reshape([5])
        assert b.shape == (5,)
        assert b.ndim == 1
        assert b.size == 5

    def test_reshape_2d(self):
        b = Blob()
        b.Reshape([2, 3])
        assert b.shape == (2, 3)
        assert b.ndim == 2
        assert b.size == 6

    def test_reshape_4d(self):
        b = Blob()
        b.Reshape([1, 2, 3, 4])
        assert b.shape == (1, 2, 3, 4)
        assert b.ndim == 4
        assert b.size == 24

    def test_reshape_changes_size(self):
        b = Blob([2, 3])
        assert b.size == 6
        b.Reshape([4, 5])
        assert b.shape == (4, 5)
        assert b.size == 20


class TestBlobNumpy:
    def test_from_numpy_to_numpy(self):
        arr = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
        b = Blob()
        b.from_numpy(arr)
        assert b.shape == (2, 3)
        result = b.to_numpy()
        np.testing.assert_array_equal(result, arr)

    def test_from_numpy_creates_copy(self):
        arr = np.array([1, 2, 3], dtype=np.float32)
        b = Blob()
        b.from_numpy(arr)
        arr[0] = 999
        assert b.to_numpy()[0] != 999

    def test_to_numpy_creates_copy(self):
        b = Blob()
        b.from_numpy(np.array([1, 2, 3], dtype=np.float32))
        result = b.to_numpy()
        result[0] = 999
        assert b.to_numpy()[0] != 999

    def test_data_property(self):
        arr = np.array([[1, 2], [3, 4]], dtype=np.float32)
        b = Blob()
        b.data = arr
        np.testing.assert_array_equal(b.data, arr)

    def test_data_setter_reshape(self):
        b = Blob([5])
        new_data = np.ones((2, 3), dtype=np.float32)
        b.data = new_data
        assert b.shape == (2, 3)
        np.testing.assert_array_equal(b.data, new_data)

    def test_diff_property(self):
        arr = np.array([1, 2, 3], dtype=np.float32)
        b = Blob()
        b.diff = arr
        np.testing.assert_array_equal(b.diff, arr)


class TestBlobFill:
    def test_fill(self):
        b = Blob([2, 3])
        b.fill(3.14)
        assert np.all(b.data == 3.14)

    def test_zero(self):
        b = Blob([2, 3])
        b.fill(1.0)
        b.zero()
        assert np.all(b.data == 0.0)


class TestBlobCopy:
    def test_copy_from(self):
        b1 = Blob([2, 3])
        b1.from_numpy(np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32))
        b2 = Blob()
        b2.copy_from(b1)
        assert b2.shape == b1.shape
        np.testing.assert_array_equal(b2.data, b1.data)

    def test_copy_from_is_independent(self):
        b1 = Blob([2, 3])
        b1.from_numpy(np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32))
        b2 = Blob()
        b2.copy_from(b1)
        b1.fill(0)
        assert not np.all(b2.data == 0)


class TestBlobProperties:
    def test_shape(self):
        b = Blob([2, 3, 4])
        assert b.shape == (2, 3, 4)

    def test_ndim(self):
        b = Blob([2, 3, 4])
        assert b.ndim == 3

    def test_size(self):
        b = Blob([2, 3, 4])
        assert b.size == 24

    def test_num_axes(self):
        b = Blob([2, 3, 4])
        assert b.num_axes == 3


class TestBlobRepr:
    def test_repr(self):
        b = Blob([2, 3])
        r = repr(b)
        assert "Blob" in r
        assert "(2, 3)" in r


class TestBlobZeroCopy:
    def test_data_tensor_returns_ndarray(self):
        b = Blob([2, 3, 4, 5])
        dt = b.data_tensor
        assert isinstance(dt, np.ndarray)
        assert dt.shape == (2, 3, 4, 5)
        assert dt.dtype == np.float32

    def test_data_tensor_zero_copy_write(self):
        b = Blob([2, 3, 4, 5])
        b.data_tensor[0, 0, 0, 0] = 42.0
        assert abs(b.data_tensor[0, 0, 0, 0] - 42.0) < 0.01

    def test_data_property_returns_copy(self):
        b = Blob([2, 3])
        b.data_tensor[0, 0] = 1.0
        d = b.data
        assert abs(d[0, 0] - 1.0) < 0.01
        d[0, 0] = 99.0
        assert abs(b.data_tensor[0, 0] - 1.0) < 0.01

    def test_diff_tensor_returns_ndarray(self):
        b = Blob([2, 3])
        dt = b.diff_tensor
        assert isinstance(dt, np.ndarray)
        assert dt.shape == (2, 3)
        assert dt.dtype == np.float32

    def test_diff_tensor_zero_copy_write(self):
        b = Blob([3])
        b.diff_tensor[0] = 7.77
        assert abs(b.diff_tensor[0] - 7.77) < 0.01

    def test_diff_property_returns_copy(self):
        b = Blob([3])
        b.diff_tensor[0] = 2.0
        d = b.diff
        assert abs(d[0] - 2.0) < 0.01
        d[0] = 99.0
        assert abs(b.diff_tensor[0] - 2.0) < 0.01

    def test_update_subtracts_diff_from_data(self):
        b = Blob([3])
        b.data_tensor[:] = [10.0, 20.0, 30.0]
        b.diff_tensor[:] = [1.0, 2.0, 3.0]
        b.Update()
        np.testing.assert_allclose(b.data_tensor, [9.0, 18.0, 27.0], rtol=1e-5)

    def test_data_tensor_persists_across_calls(self):
        b = Blob([2, 2])
        t1 = b.data_tensor
        t1[0, 0] = 5.0
        t2 = b.data_tensor
        assert abs(t2[0, 0] - 5.0) < 0.01

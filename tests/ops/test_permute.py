# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import logging
import numpy as np
import pytest
from utils import L, _test_op, assert_op_correct

logger = logging.getLogger(__name__)


def _test_permute(data, test_dir, **kwargs):
    """One iteration of Permute."""
    logger.info(f"Testing Permute, input shape: {data.shape}")
    logger.debug(f"Permute params: {kwargs}")
    return _test_op(data, L.Permute, "Permute", test_dir, **kwargs)


def test_forward_Permute(caffe_test_dir):
    """Permute"""
    logger.info("Running test_forward_Permute")
    data = np.random.rand(2, 3, 4).astype(np.float32)
    logger.debug(f"Testing Permute order=[0,1,2], shape: {data.shape}")
    _test_permute(data, caffe_test_dir, permute_param={"order": [0, 1, 2]})
    logger.debug(f"Testing Permute order=[0,2,1], shape: {data.shape}")
    _test_permute(data, caffe_test_dir, permute_param={"order": [0, 2, 1]})
    logger.debug(f"Testing Permute order=[1,0,2], shape: {data.shape}")
    _test_permute(data, caffe_test_dir, permute_param={"order": [1, 0, 2]})
    logger.debug(f"Testing Permute order=[1,2,0], shape: {data.shape}")
    _test_permute(data, caffe_test_dir, permute_param={"order": [1, 2, 0]})
    logger.debug(f"Testing Permute order=[2,0,1], shape: {data.shape}")
    _test_permute(data, caffe_test_dir, permute_param={"order": [2, 0, 1]})
    logger.debug(f"Testing Permute order=[2,1,0], shape: {data.shape}")
    _test_permute(data, caffe_test_dir, permute_param={"order": [2, 1, 0]})


@pytest.mark.skip(reason="Permute layer permute_param not available in this Caffe version")
@pytest.mark.correctness
def test_permute_correctness(caffe_test_dir):
    """Permute correctness test with numpy transpose reference."""
    logger.info("Running test_permute_correctness")
    np.random.seed(42)

    logger.debug("Testing Permute identity order=[0,1,2] on 3D")
    x = np.random.randn(2, 3, 4).astype(np.float32)
    order = [0, 1, 2]
    ref = np.transpose(x, order).astype(np.float32)
    caffe_out = _test_permute(x, caffe_test_dir, permute_param={"order": order})
    assert_op_correct(caffe_out, ref, op_name=f"Permute({order})")

    logger.debug("Testing Permute order=[0,2,1] on 3D")
    x = np.random.randn(2, 3, 4).astype(np.float32)
    order = [0, 2, 1]
    ref = np.transpose(x, order).astype(np.float32)
    caffe_out = _test_permute(x, caffe_test_dir, permute_param={"order": order})
    assert_op_correct(caffe_out, ref, op_name=f"Permute({order})")

    logger.debug("Testing Permute order=[2,1,0] reverse on 3D")
    x = np.random.randn(2, 3, 4).astype(np.float32)
    order = [2, 1, 0]
    ref = np.transpose(x, order).astype(np.float32)
    caffe_out = _test_permute(x, caffe_test_dir, permute_param={"order": order})
    assert_op_correct(caffe_out, ref, op_name=f"Permute({order})")

    logger.debug("Testing Permute 4D NCHW->NHWC order=[0,2,3,1]")
    x = np.random.randn(2, 3, 4, 5).astype(np.float32)
    order = [0, 2, 3, 1]
    ref = np.transpose(x, order).astype(np.float32)
    caffe_out = _test_permute(x, caffe_test_dir, permute_param={"order": order})
    assert_op_correct(caffe_out, ref, op_name=f"Permute({order})")
    assert caffe_out[0].shape == (2, 4, 5, 3)

    logger.debug("Testing Permute 2D transpose order=[1,0]")
    x = np.random.randn(4, 5).astype(np.float32)
    order = [1, 0]
    ref = np.transpose(x, order).astype(np.float32)
    caffe_out = _test_permute(x, caffe_test_dir, permute_param={"order": order})
    assert_op_correct(caffe_out, ref, op_name=f"Permute({order})")


@pytest.mark.edge
def test_permute_edge_cases(caffe_test_dir):
    """Permute edge cases."""
    logger.info("Running test_permute_edge_cases")

    logger.debug("Testing all zeros input permutation")
    x = np.zeros((2, 3, 4), dtype=np.float32)
    order = [2, 0, 1]
    caffe_out = _test_permute(x, caffe_test_dir, permute_param={"order": order})
    assert caffe_out[0].shape == (4, 2, 3)
    assert np.all(caffe_out[0] == 0)

    logger.debug("Testing all ones input permutation")
    x = np.ones((2, 3, 4, 5), dtype=np.float32)
    order = [0, 3, 1, 2]
    caffe_out = _test_permute(x, caffe_test_dir, permute_param={"order": order})
    assert caffe_out[0].shape == (2, 5, 3, 4)
    assert np.all(caffe_out[0] == 1.0)

    logger.debug("Testing singleton dimension permutation")
    x = np.random.randn(1, 1, 10).astype(np.float32)
    order = [0, 2, 1]
    caffe_out = _test_permute(x, caffe_test_dir, permute_param={"order": order})
    assert caffe_out[0].shape == (1, 10, 1)

    logger.debug("Testing value consistency after double permutation (inverse)")
    x = np.random.randn(2, 3, 4).astype(np.float32)
    order1 = [2, 0, 1]
    order2 = [1, 2, 0]
    out1 = _test_permute(x, caffe_test_dir, permute_param={"order": order1})
    out2 = _test_permute(out1[0], caffe_test_dir, permute_param={"order": order2})
    assert_op_correct(out2, x, op_name="Permute(double-inverse)")

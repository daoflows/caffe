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
from utils import L, _test_op

logger = logging.getLogger(__name__)


def _test_reshape(data, test_dir, **kwargs):
    """One iteration of Reshape."""
    logger.info(f"Testing Reshape, input shape: {data.shape}")
    logger.debug(f"Reshape params: {kwargs}")
    _test_op(data, L.Reshape, "Reshape", test_dir, **kwargs)


def test_forward_Reshape(caffe_test_dir):
    """Reshape"""
    logger.info("Running test_forward_Reshape")
    data = np.random.rand(1, 8, 6).astype(np.float32)
    logger.debug(f"Testing Reshape to [4,3,4], shape: {data.shape}")
    _test_reshape(data, caffe_test_dir, reshape_param={"shape": {"dim": [4, 3, 4]}})
    logger.debug(f"Testing Reshape to [2,0,3] (infer), shape: {data.shape}")
    _test_reshape(data, caffe_test_dir, reshape_param={"shape": {"dim": [2, 0, 3]}})
    logger.debug(f"Testing Reshape to [2,0,-1] (flatten), shape: {data.shape}")
    _test_reshape(data, caffe_test_dir, reshape_param={"shape": {"dim": [2, 0, -1]}})
    logger.debug(f"Testing Reshape to [0,-1], shape: {data.shape}")
    _test_reshape(data, caffe_test_dir, reshape_param={"shape": {"dim": [0, -1]}})

    logger.debug(f"Testing Reshape with axis=2, shape: {data.shape}")
    _test_reshape(data, caffe_test_dir, reshape_param={"shape": {"dim": [2, 4]}, "axis": 2})
    logger.debug(f"Testing Reshape with axis=1, shape: {data.shape}")
    _test_reshape(data, caffe_test_dir, reshape_param={"shape": {"dim": [4, 3, 4]}, "axis": 1})
    logger.debug(f"Testing Reshape with axis=-3, shape: {data.shape}")
    _test_reshape(data, caffe_test_dir, reshape_param={"shape": {"dim": [4, 3, 4]}, "axis": -3})

    logger.debug(f"Testing Reshape with axis=1, num_axes=1, shape: {data.shape}")
    _test_reshape(data, caffe_test_dir, reshape_param={"shape": {"dim": [2, 4]}, "axis": 1, "num_axes": 1})
    logger.debug(f"Testing Reshape with axis=1, num_axes=2, shape: {data.shape}")
    _test_reshape(data, caffe_test_dir, reshape_param={"shape": {"dim": [3, 16]}, "axis": 1, "num_axes": 2})

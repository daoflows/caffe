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


def _test_permute(data, test_dir, **kwargs):
    """One iteration of Permute."""
    logger.info(f"Testing Permute, input shape: {data.shape}")
    logger.debug(f"Permute params: {kwargs}")
    _test_op(data, L.Permute, "Permute", test_dir, **kwargs)


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

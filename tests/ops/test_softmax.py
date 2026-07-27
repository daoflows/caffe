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


def _test_softmax(data, test_dir, **kwargs):
    """One iteration of Softmax"""
    logger.info(f"Testing Softmax, input shape: {data.shape}")
    logger.debug(f"Softmax params: {kwargs}")
    _test_op(data, L.Softmax, "Softmax", test_dir, **kwargs)


def test_forward_Softmax(caffe_test_dir):
    """Softmax"""
    logger.info("Running test_forward_Softmax")
    logger.debug("Testing Softmax 4D, default axis=1")
    _test_softmax(np.random.rand(1, 3, 10, 10).astype(np.float32), caffe_test_dir)
    logger.debug("Testing Softmax 4D, axis=2")
    _test_softmax(np.random.rand(1, 3, 10, 10).astype(np.float32), caffe_test_dir, axis=2)
    logger.debug("Testing Softmax 2D, axis=0")
    _test_softmax(np.random.rand(10, 10).astype(np.float32), caffe_test_dir, axis=0)
    logger.debug("Testing Softmax 3D, axis=1")
    _test_softmax(np.random.rand(2, 10, 10).astype(np.float32), caffe_test_dir, axis=1)

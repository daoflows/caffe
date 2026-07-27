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


def _test_prelu(data, test_dir, **kwargs):
    """One iteration of PReLU."""
    logger.info(f"Testing PReLU, input shape: {data.shape}")
    logger.debug(f"PReLU params: {kwargs}")
    _test_op(data, L.PReLU, "PReLU", test_dir, **kwargs)


def test_forward_PReLU(caffe_test_dir):
    """PReLU"""
    logger.info("Running test_forward_PReLU")
    data = np.random.rand(1, 3, 10, 10).astype(np.float32)
    logger.debug(f"Testing PReLU with constant filler=0.5, shape: {data.shape}")
    _test_prelu(data, caffe_test_dir, filler=dict(type="constant", value=0.5))
    logger.debug(f"Testing PReLU default params, shape: {data.shape}")
    _test_prelu(data, caffe_test_dir)
    data2 = np.random.rand(10, 20).astype(np.float32)
    logger.debug(f"Testing PReLU 2D input, shape: {data2.shape}")
    _test_prelu(data2, caffe_test_dir)

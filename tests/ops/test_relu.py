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


def _test_relu(data, test_dir, **kwargs):
    """One iteration of ReLU."""
    logger.info(f"Testing ReLU, input shape: {data.shape}")
    logger.debug(f"ReLU params: {kwargs}")
    _test_op(data, L.ReLU, "ReLU", test_dir, **kwargs)


def test_forward_ReLU(caffe_test_dir):
    """ReLU"""
    logger.info("Running test_forward_ReLU")
    data = np.random.rand(1, 3, 10, 10).astype(np.float32)
    logger.debug(f"Calling _test_relu with 4D data shape {data.shape}")
    _test_relu(data, caffe_test_dir)
    data2 = np.random.rand(10, 20).astype(np.float32)
    logger.debug(f"Calling _test_relu with 2D data shape {data2.shape}")
    _test_relu(data2, caffe_test_dir)

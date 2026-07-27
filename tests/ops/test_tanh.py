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


def _test_tanh(data, test_dir, **kwargs):
    """One iteration of TanH"""
    logger.info(f"Testing TanH, input shape: {data.shape}")
    logger.debug(f"TanH params: {kwargs}")
    _test_op(data, L.TanH, "TanH", test_dir, **kwargs)


def test_forward_TanH(caffe_test_dir):
    """TanH"""
    logger.info("Running test_forward_TanH")
    logger.debug("Testing TanH 4D input")
    _test_tanh(np.random.rand(1, 3, 10, 10).astype(np.float32), caffe_test_dir)
    logger.debug("Testing TanH 3D input")
    _test_tanh(np.random.rand(3, 10, 10).astype(np.float32), caffe_test_dir)
    logger.debug("Testing TanH 2D input")
    _test_tanh(np.random.rand(10, 10).astype(np.float32), caffe_test_dir)
    logger.debug("Testing TanH 1D input")
    _test_tanh(np.random.rand(10).astype(np.float32), caffe_test_dir)

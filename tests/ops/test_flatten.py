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


def _test_flatten(data, test_dir, axis=1):
    """One iteration of Flatten"""
    logger.info(f"Testing Flatten, input shape: {data.shape}")
    logger.debug(f"Flatten params - axis: {axis}")
    _test_op(data, L.Flatten, "Flatten", test_dir, axis=axis)


def test_forward_Flatten(caffe_test_dir):
    """Flatten"""
    logger.info("Running test_forward_Flatten")
    data = np.random.rand(1, 3, 10, 10).astype(np.float32)
    logger.debug(f"Calling _test_flatten with data shape {data.shape}, default axis=1")
    _test_flatten(data, caffe_test_dir)
    logger.debug(f"Calling _test_flatten with data shape {data.shape}, axis=1")
    _test_flatten(data, caffe_test_dir, axis=1)

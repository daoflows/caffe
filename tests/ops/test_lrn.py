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


def _test_lrn(data, test_dir, local_size=5, alpha=1.0, beta=0.75, k=1.0):
    """One iteration of LRN"""
    logger.info(f"Testing LRN, input shape: {data.shape}")
    logger.debug(f"LRN params - local_size: {local_size}, alpha: {alpha}, beta: {beta}, k: {k}")
    _test_op(data, L.LRN, "LRN", test_dir, local_size=local_size, alpha=alpha, beta=beta, k=k)


def test_forward_LRN(caffe_test_dir):
    """LRN"""
    logger.info("Running test_forward_LRN")
    data = np.random.rand(1, 3, 10, 10).astype(np.float32)
    logger.debug(f"Calling _test_lrn with data shape {data.shape}, default params")
    _test_lrn(data, caffe_test_dir)
    logger.debug(f"Calling _test_lrn with data shape {data.shape}, local_size=3")
    _test_lrn(data, caffe_test_dir, local_size=3)
    logger.debug(f"Calling _test_lrn with data shape {data.shape}, local_size=3, alpha=2.0")
    _test_lrn(data, caffe_test_dir, local_size=3, alpha=2.0)
    logger.debug(f"Calling _test_lrn with data shape {data.shape}, local_size=3, alpha=2.0, beta=0.5")
    _test_lrn(data, caffe_test_dir, local_size=3, alpha=2.0, beta=0.5)
    logger.debug(f"Calling _test_lrn with data shape {data.shape}, local_size=3, alpha=2.0, beta=0.5, k=2.0")
    _test_lrn(data, caffe_test_dir, local_size=3, alpha=2.0, beta=0.5, k=2.0)

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


def _test_batchnorm(data, test_dir, moving_average_fraction=0.999, eps=1e-5):
    """One iteration of BatchNorm"""
    logger.info(f"Testing BatchNorm, input shape: {data.shape}")
    logger.debug(
        f"BatchNorm params - moving_average_fraction: {moving_average_fraction}, eps: {eps}"
    )
    _test_op(data, L.BatchNorm, "BatchNorm", test_dir, moving_average_fraction=moving_average_fraction, eps=eps)


def test_forward_BatchNorm(caffe_test_dir):
    """BatchNorm"""
    logger.info("Running test_forward_BatchNorm")
    data = np.random.rand(1, 3, 10, 10).astype(np.float32)
    logger.debug(f"Calling _test_batchnorm with data shape {data.shape}, default params")
    _test_batchnorm(data, caffe_test_dir)
    logger.debug(f"Calling _test_batchnorm with data shape {data.shape}, moving_average_fraction=0.88, eps=1e-4")
    _test_batchnorm(data, caffe_test_dir, moving_average_fraction=0.88, eps=1e-4)

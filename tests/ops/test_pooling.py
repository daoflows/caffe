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
from utils import L, P, _test_op

logger = logging.getLogger(__name__)


def _test_pooling(data, test_dir, **kwargs):
    """One iteration of Pooling."""
    logger.info(f"Testing Pooling, input shape: {data.shape}")
    logger.debug(f"Pooling params: {kwargs}")
    _test_op(data, L.Pooling, "Pooling", test_dir, **kwargs)


def test_forward_Pooling(caffe_test_dir):
    """Pooling"""
    logger.info("Running test_forward_Pooling")
    data = np.random.rand(1, 3, 10, 10).astype(np.float32)
    logger.debug(f"Testing MAX pooling with kernel_size=2, stride=2, shape: {data.shape}")
    _test_pooling(data, caffe_test_dir, kernel_size=2, stride=2, pad=0, pool=P.Pooling.MAX)
    logger.debug(f"Testing MAX pooling with explicit h/w params, shape: {data.shape}")
    _test_pooling(
        data, caffe_test_dir, kernel_h=2, kernel_w=3, stride_h=2, stride_w=1, pad_h=1, pad_w=2, pool=P.Pooling.MAX
    )
    logger.debug(f"Testing MAX global pooling, shape: {data.shape}")
    _test_pooling(data, caffe_test_dir, pool=P.Pooling.MAX, global_pooling=True)

    logger.debug(f"Testing AVE pooling with kernel_size=2, stride=2, shape: {data.shape}")
    _test_pooling(data, caffe_test_dir, kernel_size=2, stride=2, pad=0, pool=P.Pooling.AVE)
    logger.debug(f"Testing AVE pooling with explicit h/w params, shape: {data.shape}")
    _test_pooling(
        data, caffe_test_dir, kernel_h=2, kernel_w=3, stride_h=2, stride_w=1, pad_h=1, pad_w=2, pool=P.Pooling.AVE
    )
    logger.debug(f"Testing AVE global pooling, shape: {data.shape}")
    _test_pooling(data, caffe_test_dir, pool=P.Pooling.AVE, global_pooling=True)

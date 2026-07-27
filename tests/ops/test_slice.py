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


def _test_slice(data, test_dir, **kwargs):
    """One iteration of Slice"""
    logger.info(f"Testing Slice, input shape: {data.shape}")
    logger.debug(f"Slice params: {kwargs}")
    _test_op(data, L.Slice, "Slice", test_dir, **kwargs)


def test_forward_Slice(caffe_test_dir):
    """Slice"""
    logger.info("Running test_forward_Slice")
    data = np.random.rand(1, 3, 10, 10).astype(np.float32)
    logger.debug(f"Testing Slice ntop=2, axis=1, slice_point=[1], shape: {data.shape}")
    _test_slice(data, caffe_test_dir, ntop=2, slice_param=dict(axis=1, slice_point=[1]))
    logger.debug(f"Testing Slice ntop=2, axis=-1, slice_point=[1], shape: {data.shape}")
    _test_slice(data, caffe_test_dir, ntop=2, slice_param=dict(axis=-1, slice_point=[1]))
    logger.debug(f"Testing Slice ntop=3, axis=2, slice_point=[1,6], shape: {data.shape}")
    _test_slice(data, caffe_test_dir, ntop=3, slice_param=dict(axis=2, slice_point=[1, 6]))
    logger.debug(f"Testing Slice ntop=3 default params, shape: {data.shape}")
    _test_slice(data, caffe_test_dir, ntop=3)

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


def _test_crop(data, test_dir, **kwargs):
    """One iteration of Crop"""
    input_shapes = [d.shape for d in data]
    logger.info(f"Testing Crop, num inputs: {len(data)}, shapes: {input_shapes}")
    logger.debug(f"Crop params: {kwargs}")
    _test_op(data, L.Crop, "Crop", test_dir, **kwargs)


def test_forward_Crop(caffe_test_dir):
    """Crop"""
    logger.info("Running test_forward_Crop")
    logger.debug("Testing Crop 4D, default params")
    _test_crop([np.random.rand(10, 10, 120, 120), np.random.rand(10, 5, 50, 60)], caffe_test_dir)
    logger.debug("Testing Crop 4D, axis=1")
    _test_crop([np.random.rand(10, 10, 120, 120), np.random.rand(10, 5, 50, 60)], caffe_test_dir, axis=1)
    logger.debug("Testing Crop 4D, axis=1, offset=2")
    _test_crop([np.random.rand(10, 10, 120, 120), np.random.rand(10, 5, 50, 60)], caffe_test_dir, axis=1, offset=2)
    logger.debug("Testing Crop 4D, axis=1, offset=[1,2,4]")
    _test_crop(
        [np.random.rand(10, 10, 120, 120), np.random.rand(10, 5, 50, 60)], caffe_test_dir, axis=1, offset=[1, 2, 4]
    )
    logger.debug("Testing Crop 4D, axis=2, offset=[2,4]")
    _test_crop(
        [np.random.rand(10, 10, 120, 120), np.random.rand(10, 5, 50, 60)], caffe_test_dir, axis=2, offset=[2, 4]
    )
    logger.debug("Testing Crop 3D, axis=1, offset=[2,4]")
    _test_crop([np.random.rand(10, 120, 120), np.random.rand(5, 50, 60)], caffe_test_dir, axis=1, offset=[2, 4])
    logger.debug("Testing Crop 2D, axis=0, offset=[2,4]")
    _test_crop([np.random.rand(120, 120), np.random.rand(50, 60)], caffe_test_dir, axis=0, offset=[2, 4])

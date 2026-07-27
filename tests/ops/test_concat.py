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


def _test_concat(data_list, test_dir, axis=1):
    """One iteration of Concat"""
    input_shapes = [d.shape for d in data_list]
    logger.info(f"Testing Concat, num inputs: {len(data_list)}, shapes: {input_shapes}")
    logger.debug(f"Concat params - axis: {axis}")
    _test_op(data_list, L.Concat, "Concat", test_dir, axis=axis)


def test_forward_Concat(caffe_test_dir):
    """Concat"""
    logger.info("Running test_forward_Concat")
    logger.debug("Testing Concat 4D, axis=1")
    _test_concat([np.random.rand(1, 3, 10, 10), np.random.rand(1, 2, 10, 10)], caffe_test_dir, axis=1)
    logger.debug("Testing Concat 3D, axis=0")
    _test_concat([np.random.rand(3, 10, 10), np.random.rand(2, 10, 10)], caffe_test_dir, axis=0)
    logger.debug("Testing Concat 2D, axis=0")
    _test_concat([np.random.rand(3, 10), np.random.rand(2, 10)], caffe_test_dir, axis=0)

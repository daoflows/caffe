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


def _test_eltwise(data_list, test_dir, **kwargs):
    """One iteration of Eltwise"""
    input_shapes = [d.shape for d in data_list]
    logger.info(f"Testing Eltwise, num inputs: {len(data_list)}, shapes: {input_shapes}")
    logger.debug(f"Eltwise params: {kwargs}")
    _test_op(data_list, L.Eltwise, "Eltwise", test_dir, **kwargs)


def test_forward_Eltwise(caffe_test_dir):
    """Eltwise"""
    logger.info("Running test_forward_Eltwise")
    logger.debug("Testing Eltwise operation=0 (PROD), 2 inputs")
    _test_eltwise(
        [
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
        ],
        caffe_test_dir,
        operation=0,
    )
    logger.debug("Testing Eltwise operation=1 (SUM), 2 inputs")
    _test_eltwise(
        [
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
        ],
        caffe_test_dir,
        operation=1,
    )
    logger.debug("Testing Eltwise operation=2 (MAX), 2 inputs")
    _test_eltwise(
        [
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
        ],
        caffe_test_dir,
        operation=2,
    )
    logger.debug("Testing Eltwise operation=1 with coeff=[0.5, 1]")
    _test_eltwise(
        [
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
        ],
        caffe_test_dir,
        operation=1,
        coeff=[0.5, 1],
    )
    logger.debug("Testing Eltwise operation=0, 3 inputs")
    _test_eltwise(
        [
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
        ],
        caffe_test_dir,
        operation=0,
    )
    logger.debug("Testing Eltwise operation=1, 4 inputs")
    _test_eltwise(
        [
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
        ],
        caffe_test_dir,
        operation=1,
    )
    logger.debug("Testing Eltwise operation=2, 5 inputs")
    _test_eltwise(
        [
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
        ],
        caffe_test_dir,
        operation=2,
    )
    logger.debug("Testing Eltwise operation=1 with coeff for 6 inputs")
    _test_eltwise(
        [
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
            np.random.rand(1, 3, 10, 11).astype(np.float32),
        ],
        caffe_test_dir,
        operation=1,
        coeff=[0.5, 1, 0.2, 1.8, 3.1, 0.1],
    )

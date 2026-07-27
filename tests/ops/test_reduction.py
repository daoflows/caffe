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


def _test_reduction(data, test_dir, **kwargs):
    """One iteration of Reduction"""
    logger.info(f"Testing Reduction, input shape: {data.shape}")
    logger.debug(f"Reduction params: {kwargs}")
    _test_op(data, L.Reduction, "Reduction", test_dir, **kwargs)


def test_forward_Reduction(caffe_test_dir):
    """Reduction"""
    logger.info("Running test_forward_Reduction")
    reduction_op = {"SUM": 1, "ASUM": 2, "SUMSQ": 3, "MEAN": 4}
    logger.debug("Testing Reduction SUM 1D, axis=0")
    _test_reduction(np.random.rand(10).astype(np.float32), caffe_test_dir, operation=reduction_op["SUM"], axis=0)
    logger.debug("Testing Reduction SUM 4D, axis=3")
    _test_reduction(
        np.random.rand(10, 20, 30, 40).astype(np.float32), caffe_test_dir, operation=reduction_op["SUM"], axis=3
    )
    logger.debug("Testing Reduction SUM 4D, axis=1")
    _test_reduction(
        np.random.rand(10, 20, 30, 40).astype(np.float32), caffe_test_dir, operation=reduction_op["SUM"], axis=1
    )
    logger.debug("Testing Reduction SUM 1D, axis=0, coeff=0.5")
    _test_reduction(
        np.random.rand(10).astype(np.float32), caffe_test_dir, operation=reduction_op["SUM"], axis=0, coeff=0.5
    )
    logger.debug("Testing Reduction SUM 4D, axis=3, coeff=5.0")
    _test_reduction(
        np.random.rand(10, 20, 30, 40).astype(np.float32),
        caffe_test_dir,
        operation=reduction_op["SUM"],
        axis=3,
        coeff=5.0,
    )
    logger.debug("Testing Reduction ASUM 1D")
    _test_reduction(np.random.rand(10).astype(np.float32), caffe_test_dir, operation=reduction_op["ASUM"])
    logger.debug("Testing Reduction ASUM 2D, axis=1")
    _test_reduction(
        np.random.rand(10, 20).astype(np.float32), caffe_test_dir, operation=reduction_op["ASUM"], axis=1
    )
    logger.debug("Testing Reduction ASUM 4D, axis=3")
    _test_reduction(
        np.random.rand(10, 20, 30, 40).astype(np.float32), caffe_test_dir, operation=reduction_op["ASUM"], axis=3
    )
    logger.debug("Testing Reduction ASUM 1D, axis=0, coeff=0.0")
    _test_reduction(
        np.random.rand(10).astype(np.float32), caffe_test_dir, operation=reduction_op["ASUM"], axis=0, coeff=0.0
    )
    logger.debug("Testing Reduction ASUM 3D, axis=2, coeff=7.0")
    _test_reduction(
        np.random.rand(10, 20, 30).astype(np.float32),
        caffe_test_dir,
        operation=reduction_op["ASUM"],
        axis=2,
        coeff=7.0,
    )
    logger.debug("Testing Reduction ASUM 5D, axis=3, coeff=1.0")
    _test_reduction(
        np.random.rand(10, 20, 30, 40, 10).astype(np.float32),
        caffe_test_dir,
        operation=reduction_op["ASUM"],
        axis=3,
        coeff=1.0,
    )
    logger.debug("Testing Reduction SUMSQ 1D, axis=0")
    _test_reduction(np.random.rand(10).astype(np.float32), caffe_test_dir, operation=reduction_op["SUMSQ"], axis=0)
    logger.debug("Testing Reduction SUMSQ 4D, axis=3")
    _test_reduction(
        np.random.rand(10, 20, 30, 40).astype(np.float32), caffe_test_dir, operation=reduction_op["SUMSQ"], axis=3
    )
    logger.debug("Testing Reduction SUMSQ 1D, axis=0, coeff=0.0")
    _test_reduction(
        np.random.rand(10).astype(np.float32), caffe_test_dir, operation=reduction_op["SUMSQ"], axis=0, coeff=0.0
    )
    logger.debug("Testing Reduction SUMSQ 5D, axis=4, coeff=2.0")
    _test_reduction(
        np.random.rand(10, 20, 30, 40, 50).astype(np.float32),
        caffe_test_dir,
        operation=reduction_op["SUMSQ"],
        axis=4,
        coeff=2.0,
    )
    logger.debug("Testing Reduction MEAN 1D, axis=0")
    _test_reduction(np.random.rand(10).astype(np.float32), caffe_test_dir, operation=reduction_op["MEAN"], axis=0)
    logger.debug("Testing Reduction MEAN 4D, axis=3")
    _test_reduction(
        np.random.rand(10, 20, 30, 40).astype(np.float32), caffe_test_dir, operation=reduction_op["MEAN"], axis=3
    )
    logger.debug("Testing Reduction MEAN 1D, axis=0, coeff=0.0")
    _test_reduction(
        np.random.rand(10).astype(np.float32), caffe_test_dir, operation=reduction_op["MEAN"], axis=0, coeff=0.0
    )
    logger.debug("Testing Reduction MEAN 4D, axis=3, coeff=2.0")
    _test_reduction(
        np.random.rand(10, 20, 30, 40).astype(np.float32),
        caffe_test_dir,
        operation=reduction_op["MEAN"],
        axis=3,
        coeff=2.0,
    )

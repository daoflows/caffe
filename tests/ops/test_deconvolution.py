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


def _test_deconvolution(data, test_dir, **kwargs):
    """One iteration of Deconvolution"""
    logger.info(f"Testing Deconvolution, input shape: {data.shape}")
    logger.debug(f"Deconvolution params: {kwargs}")
    _test_op(data, L.Deconvolution, "Deconvolution", test_dir, **kwargs)


def test_forward_Deconvolution(caffe_test_dir):
    """Deconvolution"""
    logger.info("Running test_forward_Deconvolution")
    data = np.random.rand(1, 16, 32, 32).astype(np.float32)
    logger.debug("Testing Deconvolution with basic params")
    _test_deconvolution(
        data,
        caffe_test_dir,
        convolution_param=dict(
            num_output=20,
            bias_term=True,
            pad=0,
            kernel_size=3,
            stride=2,
            dilation=1,
            weight_filler=dict(type="xavier"),
            bias_filler=dict(type="xavier"),
        ),
    )
    logger.debug("Testing Deconvolution with pad=[1,2], bias_term=False")
    _test_deconvolution(
        data,
        caffe_test_dir,
        convolution_param=dict(
            num_output=20,
            bias_term=False,
            pad=[1, 2],
            kernel_size=3,
            stride=2,
            dilation=1,
            weight_filler=dict(type="xavier"),
            bias_filler=dict(type="xavier"),
        ),
    )
    logger.debug("Testing Deconvolution with explicit h/w params")
    _test_deconvolution(
        data,
        caffe_test_dir,
        convolution_param=dict(
            num_output=20,
            bias_term=True,
            pad_h=1,
            pad_w=2,
            kernel_h=3,
            kernel_w=5,
            stride_h=2,
            stride_w=1,
            dilation=1,
            weight_filler=dict(type="xavier"),
            bias_filler=dict(type="xavier"),
        ),
    )
    logger.debug("Testing Deconvolution with group=16")
    _test_deconvolution(
        data,
        caffe_test_dir,
        convolution_param=dict(
            num_output=16,
            bias_term=False,
            pad=0,
            kernel_size=2,
            stride=2,
            dilation=1,
            group=16,
            weight_filler=dict(type="xavier"),
            bias_filler=dict(type="xavier"),
        ),
    )
    data = np.random.rand(1, 100, 32, 32).astype(np.float32)
    logger.debug("Testing Deconvolution with group=100, 100 channels")
    _test_deconvolution(
        data,
        caffe_test_dir,
        convolution_param=dict(
            num_output=100,
            bias_term=False,
            pad=0,
            kernel_size=2,
            stride=2,
            dilation=1,
            group=100,
            weight_filler=dict(type="xavier"),
            bias_filler=dict(type="xavier"),
        ),
    )

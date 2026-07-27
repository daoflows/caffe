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


def _test_convolution(data, test_dir, **kwargs):
    """One iteration of Convolution"""
    logger.info(f"Testing Convolution, input shape: {data.shape}")
    logger.debug(f"Convolution params: {kwargs}")
    _test_op(data, L.Convolution, "Convolution", test_dir, **kwargs)


def test_forward_Convolution(caffe_test_dir):
    """Convolution"""
    logger.info("Running test_forward_Convolution")
    data = np.random.rand(1, 3, 10, 10).astype(np.float32)
    logger.debug("Testing Convolution with basic params, bias_term=True")
    _test_convolution(
        data,
        caffe_test_dir,
        num_output=20,
        bias_term=True,
        pad=0,
        kernel_size=3,
        stride=2,
        dilation=1,
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )
    logger.debug("Testing Convolution with pad=[1,2], bias_term=False")
    _test_convolution(
        data,
        caffe_test_dir,
        num_output=20,
        bias_term=False,
        pad=[1, 2],
        kernel_size=3,
        stride=2,
        dilation=1,
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )
    logger.debug("Testing Convolution with kernel_size=[3,5], stride=[2,1], dilation=[1,2]")
    _test_convolution(
        data,
        caffe_test_dir,
        num_output=20,
        bias_term=True,
        pad=[1, 2],
        kernel_size=[3, 5],
        stride=[2, 1],
        dilation=[1, 2],
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )
    logger.debug("Testing Convolution with group=2, 2 input channels")
    _test_convolution(
        np.random.rand(1, 2, 10, 10).astype(np.float32),
        caffe_test_dir,
        num_output=20,
        bias_term=True,
        pad=[1, 2],
        kernel_size=[3, 5],
        stride=[2, 1],
        dilation=[1, 2],
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
        group=2,
    )
    logger.debug("Testing Convolution with explicit pad_h/pad_w/kernel_h/kernel_w/stride_h/stride_w")
    _test_convolution(
        data,
        caffe_test_dir,
        num_output=20,
        bias_term=True,
        pad_h=1,
        pad_w=2,
        kernel_h=3,
        kernel_w=5,
        stride_h=2,
        stride_w=1,
        dilation=[1, 2],
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )

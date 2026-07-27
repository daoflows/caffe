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


def _test_embed(data, test_dir, **kwargs):
    """One iteration of Embed"""
    logger.info(f"Testing Embed, input shape: {data.shape}")
    logger.debug(f"Embed params: {kwargs}")
    _test_op(data, L.Embed, "Embed", test_dir, **kwargs)


def test_forward_Embed(caffe_test_dir):
    """Embed"""
    logger.info("Running test_forward_Embed")
    k = 20
    data = list(i for i in range(k))
    np.random.shuffle(data)
    data = np.asarray(data)
    logger.debug(f"Testing Embed 1D, bias_term=True, shape: {data.shape}")
    _test_embed(
        data,
        caffe_test_dir,
        num_output=30,
        input_dim=k,
        bias_term=True,
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )
    logger.debug(f"Testing Embed 1D, bias_term=False, shape: {data.shape}")
    _test_embed(
        data,
        caffe_test_dir,
        num_output=30,
        input_dim=k,
        bias_term=False,
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )
    data = np.reshape(data, [4, 5])
    logger.debug(f"Testing Embed 2D, bias_term=True, shape: {data.shape}")
    _test_embed(
        data,
        caffe_test_dir,
        num_output=30,
        input_dim=k,
        bias_term=True,
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )
    logger.debug(f"Testing Embed 2D, bias_term=False, shape: {data.shape}")
    _test_embed(
        data,
        caffe_test_dir,
        num_output=30,
        input_dim=k,
        bias_term=False,
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )
    data = np.reshape(data, [2, 2, 5])
    logger.debug(f"Testing Embed 3D, bias_term=True, shape: {data.shape}")
    _test_embed(
        data,
        caffe_test_dir,
        num_output=30,
        input_dim=k,
        bias_term=True,
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )
    logger.debug(f"Testing Embed 3D, bias_term=False, shape: {data.shape}")
    _test_embed(
        data,
        caffe_test_dir,
        num_output=30,
        input_dim=k,
        bias_term=False,
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )
    data = np.reshape(data, [2, 2, 5, 1])
    logger.debug(f"Testing Embed 4D, bias_term=True, shape: {data.shape}")
    _test_embed(
        data,
        caffe_test_dir,
        num_output=30,
        input_dim=k,
        bias_term=True,
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )
    logger.debug(f"Testing Embed 4D, bias_term=False, shape: {data.shape}")
    _test_embed(
        data,
        caffe_test_dir,
        num_output=30,
        input_dim=k,
        bias_term=False,
        weight_filler=dict(type="xavier"),
        bias_filler=dict(type="xavier"),
    )

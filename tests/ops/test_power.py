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


def _test_power(data, test_dir, **kwargs):
    """One iteration of Power."""
    logger.info(f"Testing Power, input shape: {data.shape}")
    logger.debug(f"Power params: {kwargs}")
    _test_op(data, L.Power, "Power", test_dir, **kwargs)


def test_forward_Power(caffe_test_dir):
    """Power"""
    logger.info("Running test_forward_Power")
    data = np.random.rand(1, 3, 10, 10).astype(np.float32)
    logger.debug("Testing Power with power=0.37, scale=0.83, shift=-2.4")
    _test_power(data, caffe_test_dir, power_param={"power": 0.37, "scale": 0.83, "shift": -2.4})
    logger.debug("Testing Power with power=0.37, scale=0.83, shift=0.0")
    _test_power(data, caffe_test_dir, power_param={"power": 0.37, "scale": 0.83, "shift": 0.0})
    logger.debug("Testing Power with power=0.0, scale=0.83, shift=-2.4")
    _test_power(data, caffe_test_dir, power_param={"power": 0.0, "scale": 0.83, "shift": -2.4})
    logger.debug("Testing Power with power=1.0, scale=0.83, shift=-2.4")
    _test_power(data, caffe_test_dir, power_param={"power": 1.0, "scale": 0.83, "shift": -2.4})
    logger.debug("Testing Power with power=2.0, scale=0.34, shift=-2.4")
    _test_power(data, caffe_test_dir, power_param={"power": 2.0, "scale": 0.34, "shift": -2.4})
    logger.debug("Testing Power with identity params (power=1.0, scale=1.0, shift=0.0)")
    _test_power(data, caffe_test_dir, power_param={"power": 1.0, "scale": 1.0, "shift": 0.0})

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


def _test_dropout(data, test_dir, **kwargs):
    """One iteration of Dropout"""
    logger.info(f"Testing Dropout, input shape: {data.shape}")
    logger.debug(f"Dropout params: {kwargs}")
    _test_op(data, L.Dropout, "Dropout", test_dir, **kwargs)


def test_forward_Dropout(caffe_test_dir):
    """Dropout"""
    logger.info("Running test_forward_Dropout")
    data = np.random.rand(1, 3, 10, 10).astype(np.float32)
    logger.debug(f"Calling _test_dropout with data shape {data.shape}, default params")
    _test_dropout(data, caffe_test_dir)
    logger.debug(f"Calling _test_dropout with data shape {data.shape}, dropout_ratio=0.7")
    _test_dropout(data, caffe_test_dir, dropout_ratio=0.7)

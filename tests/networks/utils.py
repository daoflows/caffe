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

import os
import logging
import urllib.request
import numpy as np
import caffe

os.environ["GLOG_minloglevel"] = "2"
logging.basicConfig(level=logging.ERROR)


def _download_model(url, filename, cache_dir):
    local_path = os.path.join(cache_dir, filename)
    if os.path.exists(local_path):
        return local_path
    urllib.request.urlretrieve(url, local_path)
    return local_path


def _preprocess_imagenet(data, mean_val=None, scale=1.0):
    if mean_val is None:
        mean_val = [103.939, 116.779, 123.68]
    mean = np.array(mean_val, dtype=np.float32)
    mean = mean.reshape((1, 3, 1, 1))
    mean = np.tile(mean, (1, 1, data.shape[2], data.shape[3]))
    data_process = data - mean
    if scale != 1.0:
        data_process = data_process / scale
    return data_process.astype(np.float32)


def _test_network(data, proto_file, blob_file):
    net = caffe.Net(proto_file, blob_file, caffe.TEST)
    net.blobs["data"].data[...] = data
    out = net.forward()
    return list(out.values())

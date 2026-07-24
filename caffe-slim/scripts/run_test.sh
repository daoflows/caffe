#!/bin/bash
# ============================================================================
# python-module 测试脚本 (Docker 环境)
# 验证 caffeproto + operators 模块功能
# ============================================================================
set -euo pipefail

export GLOG_minloglevel=2

echo "=== Import test ==="
python -c "
import caffe; print('caffe', caffe.__version__)
from caffeproto import caffe_pb2; print('caffe_pb2 OK')
from caffeproto.caffe_pb2 import TRAIN, TEST; print('TRAIN:', TRAIN, 'TEST:', TEST)
"
echo ""

echo "=== caffeproto utilities test ==="
python -c "
from caffeproto.caffe_pb2 import NetParameter, LayerParameter, BlobShape, InputParameter, FillerParameter
from caffeproto.caffe_utils import unity_struct, convert_num_to_name, unity_inputs
# 创建测试网络
net = NetParameter()
net.name = 'test_net'
net.input.append('data')
net.input_dim.append(1)
net.input_dim.append(3)
net.input_dim.append(32)
net.input_dim.append(32)
# 标准化
net = unity_struct(net)
assert len(net.layer) > 0, 'No layers after unity_struct'
assert net.layer[0].type == 'Input', 'First layer should be Input'
print('caffe_utils OK')
"
echo ""

echo "=== BN-Scale fusion test ==="
python -c "
import numpy as np
from caffeproto.caffe_pb2 import NetParameter, LayerParameter, BlobProto, BatchNormParameter, ScaleParameter, FillerParameter
from caffeproto.caffe_fuse import fuse_network
# 创建预测网络
predict_net = NetParameter()
predict_net.name = 'fusion_test'
# Input 层
input_layer = predict_net.layer.add()
input_layer.name = 'data'
input_layer.type = 'Input'
input_layer.top.append('data')
input_layer.input_param.shape.add().dim.extend([1, 3, 32, 32])
# Conv 层
conv_layer = predict_net.layer.add()
conv_layer.name = 'conv1'
conv_layer.type = 'Convolution'
conv_layer.bottom.append('data')
conv_layer.top.append('conv1')
conv_layer.convolution_param.num_output = 64
conv_layer.convolution_param.kernel_size.append(3)
# BN 层
bn_layer = predict_net.layer.add()
bn_layer.name = 'bn1'
bn_layer.type = 'BatchNorm'
bn_layer.bottom.append('conv1')
bn_layer.top.append('bn1')
bn_layer.batch_norm_param.eps = 1e-5
# Scale 层
scale_layer = predict_net.layer.add()
scale_layer.name = 'scale1'
scale_layer.type = 'Scale'
scale_layer.bottom.append('bn1')
scale_layer.top.append('scale1')
scale_layer.scale_param.bias_term = True
# 创建初始化网络
init_net = NetParameter()
init_net.name = 'fusion_test'
for name, blob_count in [('conv1', 2), ('bn1', 3), ('scale1', 2)]:
    layer = init_net.layer.add()
    layer.name = name
    for _ in range(blob_count):
        blob = layer.blobs.add()
        blob.data.extend(np.random.randn(64).astype(np.float32).tolist())
# 执行融合
init_net, predict_net = fuse_network(init_net, predict_net)
# 验证 Scale 层被移除了
layer_names = [l.name for l in predict_net.layer]
assert 'scale1' not in layer_names, 'Scale layer should be fused'
assert 'bn1' in layer_names, 'BN layer should be kept'
print('BN-Scale fusion OK')
"
echo ""

echo "=== All tests passed ==="
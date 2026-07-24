#!/usr/bin/env python3
"""
python-module 纯 Python 模块单元测试
测试 caffeproto、caffe_utils、caffe_fuse 等不依赖 C++ 编译的模块
"""
import sys
import os
import traceback

CAFFE_PYTHON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'python'))
sys.path.insert(0, CAFFE_PYTHON_DIR)

test_results = []
PASS = 0
FAIL = 0
SKIP = 0

def test(name, func):
    global PASS, FAIL, SKIP
    print(f'[TEST] {name} ... ', end='', flush=True)
    try:
        func()
        print('PASS')
        test_results.append(('PASS', name, None))
        PASS += 1
    except Exception as e:
        print(f'FAIL: {e}')
        traceback.print_exc()
        test_results.append(('FAIL', name, str(e)))
        FAIL += 1

def test_skip(name, func, reason="dependency not available"):
    global PASS, FAIL, SKIP
    print(f'[TEST] {name} ... ', end='', flush=True)
    try:
        func()
        print('PASS')
        test_results.append(('PASS', name, None))
        PASS += 1
    except Exception as e:
        print(f'SKIP ({reason})')
        test_results.append(('SKIP', name, str(e)))
        SKIP += 1


# ============================================================================
# 1. caffe_pb2 Protobuf 模块测试
# ============================================================================
print('=' * 60)
print('1. Protobuf 模块测试 (caffe_pb2)')
print('=' * 60)

def test_caffe_pb2_import():
    from protos import caffe_pb2
    assert caffe_pb2 is not None

def test_caffeproto_import():
    from caffeproto import caffe_pb2
    assert caffe_pb2 is not None

def test_caffeproto_alias():
    from caffeproto import caffe_pb2 as pb1
    from protos import caffe_pb2 as pb2
    assert pb1 is pb2, "caffeproto.caffe_pb2 should be same as protos.caffe_pb2"

def test_protobuf_constants():
    from caffeproto.caffe_pb2 import TRAIN, TEST
    assert TRAIN == 0, f"TRAIN should be 0, got {TRAIN}"
    assert TEST == 1, f"TEST should be 1, got {TEST}"

def test_netparameter_creation():
    from caffeproto.caffe_pb2 import NetParameter
    net = NetParameter()
    net.name = 'test_net'
    assert net.name == 'test_net'

def test_layerparameter_creation():
    from caffeproto.caffe_pb2 import LayerParameter, ConvolutionParameter
    layer = LayerParameter()
    layer.name = 'conv1'
    layer.type = 'Convolution'
    layer.convolution_param.num_output = 64
    layer.convolution_param.kernel_size.append(3)
    assert layer.name == 'conv1'
    assert layer.type == 'Convolution'
    assert layer.convolution_param.num_output == 64
    assert list(layer.convolution_param.kernel_size) == [3]

def test_blobshape_creation():
    from caffeproto.caffe_pb2 import BlobShape
    shape = BlobShape()
    shape.dim.extend([1, 3, 224, 224])
    assert list(shape.dim) == [1, 3, 224, 224]

def test_input_layer():
    from caffeproto.caffe_pb2 import NetParameter, LayerParameter, BlobShape, InputParameter
    net = NetParameter()
    net.name = 'test'
    inp = LayerParameter()
    inp.name = 'data'
    inp.type = 'Input'
    inp.top.append('data')
    inp.input_param.shape.add().dim.extend([1, 3, 32, 32])
    net.layer.append(inp)
    assert len(net.layer) == 1
    assert net.layer[0].type == 'Input'

test('protos.caffe_pb2 import', test_caffe_pb2_import)
test('caffeproto.caffe_pb2 import', test_caffeproto_import)
test('caffeproto alias consistency', test_caffeproto_alias)
test('TRAIN/TEST constants', test_protobuf_constants)
test('NetParameter creation', test_netparameter_creation)
test('LayerParameter creation', test_layerparameter_creation)
test('BlobShape creation', test_blobshape_creation)
test('Input layer definition', test_input_layer)


# ============================================================================
# 2. caffe_utils 工具函数测试
# ============================================================================
print()
print('=' * 60)
print('2. caffe_utils 工具函数测试')
print('=' * 60)

def test_unity_inputs_old_format():
    from caffeproto.caffe_pb2 import NetParameter
    from caffeproto.caffe_utils import unity_inputs
    net = NetParameter()
    net.name = 'old_format'
    net.input.append('data')
    net.input_dim.append(1)
    net.input_dim.append(3)
    net.input_dim.append(32)
    net.input_dim.append(32)
    net = unity_inputs(net)
    assert len(net.input) == 0, "input field should be cleared"
    assert len(net.input_dim) == 0, "input_dim field should be cleared"
    assert len(net.layer) >= 1, "Input layer should be added"
    assert net.layer[0].type == 'Input'
    assert net.layer[0].name == 'data'

def test_unity_inputs_already_has_input():
    from caffeproto.caffe_pb2 import NetParameter, LayerParameter
    from caffeproto.caffe_utils import unity_inputs
    net = NetParameter()
    net.name = 'has_input'
    net.input.append('data')
    inp = LayerParameter()
    inp.name = 'data'
    inp.type = 'Input'
    net.layer.append(inp)
    net = unity_inputs(net)
    assert len(net.input) == 0

def test_convert_num_to_name():
    from caffeproto.caffe_pb2 import NetParameter, LayerParameter
    from caffeproto.caffe_utils import convert_num_to_name
    net = NetParameter()
    net.name = 'test'
    inp = LayerParameter(name='data', type='Input', top=['data'])
    conv = LayerParameter(name='conv1', type='Convolution', bottom=['data'], top=['conv1'])
    net.layer.extend([inp, conv])
    net = convert_num_to_name(net)
    assert net.layer[0].top[0] == 'data'
    assert net.layer[1].top[0] == 'conv1'

def test_unity_struct_full():
    from caffeproto.caffe_pb2 import NetParameter
    from caffeproto.caffe_utils import unity_struct
    net = NetParameter()
    net.name = 'full_test'
    net.input.append('data')
    net.input_dim.append(1)
    net.input_dim.append(3)
    net.input_dim.append(32)
    net.input_dim.append(32)
    net = unity_struct(net)
    assert len(net.input) == 0
    assert len(net.layer) > 0
    assert net.layer[0].type == 'Input'

def test_unity_struct_inplace():
    from caffeproto.caffe_pb2 import NetParameter, LayerParameter
    from caffeproto.caffe_utils import unity_struct
    net = NetParameter()
    net.name = 'inplace_test'
    inp = LayerParameter(name='data', type='Input', top=['data'])
    relu = LayerParameter(name='relu1', type='ReLU', bottom=['data'], top=['data'])  # in-place
    net.layer.extend([inp, relu])
    net = unity_struct(net)
    # in-place 层的输出应该被重命名
    assert net.layer[1].top[0] != 'data' or net.layer[1].bottom[0] != 'data'

test('unity_inputs (old format)', test_unity_inputs_old_format)
test('unity_inputs (already has Input)', test_unity_inputs_already_has_input)
test('convert_num_to_name', test_convert_num_to_name)
test('unity_struct full pipeline', test_unity_struct_full)
test('unity_struct in-place handling', test_unity_struct_inplace)


# ============================================================================
# 3. caffe_fuse 融合模块测试
# ============================================================================
print()
print('=' * 60)
print('3. caffe_fuse 融合模块测试')
print('=' * 60)

def test_batchnorm_params():
    import numpy as np
    from caffeproto.caffe_fuse import BatchNormParams
    mean = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    var = np.array([0.01, 0.02, 0.03], dtype=np.float32)
    inv_std = np.array([10.0, 7.07, 5.77], dtype=np.float32)
    bn = BatchNormParams(mean=mean, var=var, eps=1e-5, inv_std=inv_std)
    assert bn.eps == 1e-5

def test_scale_params():
    import numpy as np
    from caffeproto.caffe_fuse import ScaleParams
    gamma = np.array([1.0, 1.5, 2.0], dtype=np.float32)
    beta = np.array([0.0, 0.1, 0.2], dtype=np.float32)
    sp = ScaleParams(gamma=gamma, beta=beta, has_bias=True)
    assert sp.has_bias is True

def test_bn_scale_fusion():
    import numpy as np
    from caffeproto.caffe_pb2 import NetParameter, LayerParameter, BatchNormParameter, ScaleParameter
    from caffeproto.caffe_fuse import fuse_network
    predict_net = NetParameter()
    predict_net.name = 'fusion_test'
    inp = LayerParameter(name='data', type='Input', top=['data'])
    inp.input_param.shape.add().dim.extend([1, 3, 32, 32])
    conv = LayerParameter
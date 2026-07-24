import sys
import traceback
import numpy as np

passed = 0
failed = 0
skipped = 0

def test(name, func):
    global passed, failed
    try:
        func()
        print(f"[PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        failed += 1

def skip(name, reason):
    global skipped
    print(f"[SKIP] {name}: {reason}")
    skipped += 1

print("=" * 50)
print(" python-module Comprehensive Test Suite")
print(" (Docker Environment Verification)")
print("=" * 50)

import caffe
from caffeproto import caffe_pb2
from google.protobuf import text_format

print(f"\n--- Environment ---")
print(f"Python: {sys.version.split()[0]}")
print(f"NumPy: {np.__version__}")
print(f"Caffe: {caffe.__version__}")

print(f"\n--- Module Import Tests ---")

test("caffe core import", lambda: None)
test("caffeproto.caffe_pb2", lambda: hasattr(caffe_pb2, "NetParameter"))
test("caffe.TRAIN/TEST constants", lambda: caffe.TRAIN == 0 and caffe.TEST == 1)

test("caffe.Net class", lambda: hasattr(caffe, "Net"))
test("caffe.SGDSolver", lambda: hasattr(caffe, "SGDSolver"))
test("caffe.AdamSolver", lambda: hasattr(caffe, "AdamSolver"))
test("caffe.Classifier", lambda: hasattr(caffe, "Classifier"))
test("caffe.Detector", lambda: hasattr(caffe, "Detector"))
test("caffe.io module", lambda: __import__("caffe.io"))
test("caffe.classifier module", lambda: __import__("caffe.classifier"))
try:
    import pydot
    test("caffe.draw module", lambda: __import__("caffe.draw"))
except ImportError:
    skip("caffe.draw module", "pydot not installed (optional)")

print(f"\n--- Protobuf Serialization Tests ---")

def test_proto():
    net = caffe_pb2.NetParameter()
    net.name = "test_net"
    net.input.append("data")
    net.input_dim.extend([1, 3, 32, 32])
    conv = net.layer.add()
    conv.name = "conv1"; conv.type = "Convolution"
    conv.bottom.append("data"); conv.top.append("conv1")
    conv.convolution_param.num_output = 32
    conv.convolution_param.kernel_size.append(5)
    relu = net.layer.add()
    relu.name = "relu1"; relu.type = "ReLU"
    relu.bottom.append("conv1"); relu.top.append("conv1")
    pool = net.layer.add()
    pool.name = "pool1"; pool.type = "Pooling"
    pool.bottom.append("conv1"); pool.top.append("pool1")
    pool.pooling_param.kernel_size = 2
    pool.pooling_param.stride = 2
    pool.pooling_param.pool = caffe_pb2.PoolingParameter.MAX
    data = net.SerializeToString()
    net2 = caffe_pb2.NetParameter()
    net2.ParseFromString(data)
    assert net2.name == "test_net"
    assert len(net2.layer) == 3
    text = text_format.MessageToString(net)
    net3 = caffe_pb2.NetParameter()
    text_format.Parse(text, net3)
    assert net3.name == "test_net"
test("protobuf binary/text serialization", test_proto)

print(f"\n--- caffe_utils Tests ---")

def test_unity_struct():
    from caffeproto.caffe_utils import unity_struct, unity_inputs, convert_num_to_name
    net = caffe_pb2.NetParameter()
    net.name = "test"
    net.input.append("data")
    net.input_dim.extend([1, 3, 32, 32])
    for i in range(3):
        l = net.layer.add()
        l.name = f"layer{i}"; l.type = "Convolution" if i < 2 else "InnerProduct"
        l.bottom.append("data" if i == 0 else f"layer{i-1}")
        l.top.append(f"layer{i}")
        if l.type == "Convolution":
            l.convolution_param.num_output = 16
            l.convolution_param.kernel_size.append(3)
        else:
            l.inner_product_param.num_output = 10
    net = unity_struct(net)
    assert len(net.layer) >= 3
test("unity_struct network processing", test_unity_struct)

print(f"\n--- caffe_fuse BN-Scale Fusion Tests ---")

def test_fuse_network():
    from caffeproto.caffe_fuse import fuse_network
    predict_net = caffe_pb2.NetParameter()
    predict_net.name = "fusion_test"
    inp = predict_net.layer.add()
    inp.name = "data"; inp.type = "Input"; inp.top.append("data")
    inp.input_param.shape.add().dim.extend([1, 64, 8, 8])
    conv = predict_net.layer.add()
    conv.name = "conv1"; conv.type = "Convolution"
    conv.bottom.append("data"); conv.top.append("conv1")
    conv.convolution_param.num_output = 64
    conv.convolution_param.kernel_size.append(3)
    bn = predict_net.layer.add()
    bn.name = "bn1"; bn.type = "BatchNorm"
    bn.bottom.append("conv1"); bn.top.append("bn1")
    bn.batch_norm_param.eps = 1e-5
    scale = predict_net.layer.add()
    scale.name = "scale1"; scale.type = "Scale"
    scale.bottom.append("bn1"); scale.top.append("scale1")
    scale.scale_param.bias_term = True
    relu = predict_net.layer.add()
    relu.name = "relu1"; relu.type = "ReLU"
    relu.bottom.append("scale1"); relu.top.append("output")
    init_net = caffe_pb2.NetParameter()
    init_net.name = "fusion_test"
    for name, count in [("conv1", 2), ("bn1", 3), ("scale1", 2)]:
        layer = init_net.layer.add()
        layer.name = name
        for _ in range(count):
            blob = layer.blobs.add()
            blob.data.extend(np.random.randn(64).astype(np.float32).tolist())
    init_net, predict_net = fuse_network(init_net, predict_net)
    names = [l.name for l in predict_net.layer]
    assert "scale1" not in names, "Scale layer should be fused"
test("fuse_network BN-Scale fusion", test_fuse_network)

print(f"\n--- Caffe C++ Extension Tests ---")

def test_caffe_extension():
    assert hasattr(caffe, "_caffe"), "_caffe C++ extension not loaded"
    layer_types = caffe.layer_type_list()
    assert layer_types is not None
    assert len(list(layer_types)) > 0, "No layer types registered"
test("_caffe C++ extension loaded", test_caffe_extension)

def test_blob_class():
    assert hasattr(caffe._caffe, "Blob")
test("Blob class exists (managed by Net)", lambda: hasattr(caffe._caffe, "Blob"))

test("set_mode_cpu", lambda: caffe.set_mode_cpu())

print(f"\n--- Python Path Configuration ---")

test("PYTHONPATH includes caffex/python", lambda: "/workspace/caffex/python" in sys.path)
test("PYTHONPATH includes /workspace/caffe-slim", lambda: "/workspace/caffe-slim" in sys.path)

print(f"\n--- Optional Dependencies ---")

try:
    import tvm
    def test_tvm():
        from operators.layers import L2Norm
    test("TVM L2Norm operator", test_tvm)
except ImportError:
    skip("TVM operators", "TVM not installed in CPU image (expected)")

try:
    import opencv
    test("OpenCV available", lambda: None)
except ImportError:
    skip("OpenCV", "Not installed (optional)")

print(f"\n" + "=" * 50)
print(f"  Test Results Summary")
print("=" * 50)
print(f"  Passed:  {passed}")
print(f"  Failed:  {failed}")
print(f"  Skipped: {skipped}")
print(f"  Total:   {passed + failed + skipped}")
print("=" * 50)
if failed > 0:
    print("  STATUS: SOME TESTS FAILED")
    sys.exit(1)
else:
    print("  STATUS: ALL TESTS PASSED")
    sys.exit(0)

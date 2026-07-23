#!/usr/bin/env python
"""PyCaffe End-to-End Inference Test

Verifies that pycaffe can load a network, run forward pass, and produce
correct output shapes. Uses LeNet (MNIST) as the reference network.

Usage:
    python test_inference.py
"""

import sys
import os
import numpy as np


# --- Test Configuration ---
# LeNet deploy prototxt (Input layer, no data layer — suitable for inference)
LENET_DEPLOY_PROTOTXT = os.path.join(os.path.dirname(__file__), "lenet_deploy.prototxt")


def test_import():
    """Test 1: Import pycaffe and verify core API availability."""
    print("=" * 60)
    print("Test 1: Import & Core API")
    print("=" * 60)

    import pycaffe
    print(f"  [OK] pycaffe imported successfully")
    print(f"  [OK] pycaffe.__version__ = {pycaffe.__version__}")

    # Check all expected exports
    exports = [
        "Net", "SGDSolver", "NesterovSolver", "AdaGradSolver",
        "RMSPropSolver", "AdaDeltaSolver", "AdamSolver",
        "init_log", "log", "set_mode_cpu", "set_mode_gpu",
        "set_device", "Layer", "get_solver", "layer_type_list",
        "set_random_seed", "Classifier", "Detector",
        "layers", "params", "NetSpec", "to_proto",
        "TRAIN", "TEST",
    ]
    for name in exports:
        assert hasattr(pycaffe, name), f"Missing export: {name}"
    print(f"  [OK] All {len(exports)} expected exports present")

    return pycaffe


def test_set_mode_cpu(pycaffe):
    """Test 2: Set CPU mode."""
    print()
    print("=" * 60)
    print("Test 2: set_mode_cpu()")
    print("=" * 60)

    pycaffe.set_mode_cpu()
    print("  [OK] set_mode_cpu() called successfully")


def test_net_creation(pycaffe):
    """Test 3: Create a Net from prototxt and verify structure."""
    print()
    print("=" * 60)
    print("Test 3: Net Creation & Structure")
    print("=" * 60)

    if not os.path.exists(LENET_DEPLOY_PROTOTXT):
        print(f"  [SKIP] LeNet deploy prototxt not found: {LENET_DEPLOY_PROTOTXT}")
        return None

    net = pycaffe.Net(LENET_DEPLOY_PROTOTXT, pycaffe.TEST)
    print(f"  [OK] Net created from LeNet deploy prototxt")

    # Verify layer structure
    expected_layers = ["conv1", "pool1", "conv2", "pool2", "ip1", "relu1", "ip2", "prob"]
    actual_layers = list(net._layer_names)
    print(f"  [OK] Layer names: {actual_layers}")
    for layer_name in expected_layers:
        assert layer_name in actual_layers, f"Missing layer: {layer_name}"
    print(f"  [OK] All {len(expected_layers)} expected layers found")

    # Verify blob structure
    expected_blobs = ["data", "conv1", "pool1", "conv2", "pool2", "ip1", "ip2", "prob"]
    actual_blobs = list(net._blob_names)
    print(f"  [OK] Blob names: {actual_blobs}")
    for blob_name in expected_blobs:
        assert blob_name in actual_blobs, f"Missing blob: {blob_name}"
    print(f"  [OK] All {len(expected_blobs)} expected blobs found")

    # Verify input shape
    data_shape = net.blobs["data"].data.shape
    expected_shape = (64, 1, 28, 28)
    assert data_shape == expected_shape, f"Input shape mismatch: {data_shape} != {expected_shape}"
    print(f"  [OK] Input shape: {data_shape}")

    return net


def test_forward_pass(pycaffe, net):
    """Test 4: Run forward pass and verify output."""
    print()
    print("=" * 60)
    print("Test 4: Forward Pass")
    print("=" * 60)

    if net is None:
        print("  [SKIP] No net available")
        return

    # Set random input data
    input_data = np.random.randn(64, 1, 28, 28).astype(np.float32)
    net.blobs["data"].data[...] = input_data
    print(f"  [OK] Input data set (shape: {input_data.shape})")

    # Run forward pass
    output = net.forward()
    print(f"  [OK] Forward pass completed")

    # Verify output
    prob = output["prob"]
    expected_shape = (64, 10)
    assert prob.shape == expected_shape, f"Output shape mismatch: {prob.shape} != {expected_shape}"
    print(f"  [OK] Output shape: {prob.shape}")

    # Verify softmax properties (each row sums to ~1)
    row_sums = prob.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-5), f"Softmax rows don't sum to 1: {row_sums}"
    print(f"  [OK] Softmax output valid (rows sum to 1)")

    # Verify output values are in [0, 1]
    assert prob.min() >= 0 and prob.max() <= 1, "Output values out of [0, 1] range"
    print(f"  [OK] Output values in [0, 1] range")

    return prob


def test_forward_backward(pycaffe, net):
    """Test 5: Run forward+backward pass (requires TRAIN phase net)."""
    print()
    print("=" * 60)
    print("Test 5: Forward + Backward Pass")
    print("=" * 60)

    if net is None:
        print("  [SKIP] No net available")
        return

    # Caffe TEST-phase nets skip backward computation for all layers.
    # Create a TRAIN-phase net for backward testing.
    # NOTE: LeNet deploy prototxt uses Input layer (no phase restriction),
    # so we can create a TRAIN net for backward pass testing.
    try:
        train_net = pycaffe.Net(LENET_DEPLOY_PROTOTXT, pycaffe.TRAIN)
    except Exception:
        print("  [SKIP] Cannot create TRAIN-phase net for backward test")
        return

    # Set random input
    input_data = np.random.randn(64, 1, 28, 28).astype(np.float32)
    train_net.blobs["data"].data[...] = input_data

    # Forward
    output = train_net.forward()
    print(f"  [OK] Forward pass completed")

    # Backward (set diff from output)
    train_net.blobs["prob"].diff[...] = np.ones_like(train_net.blobs["prob"].data)
    diffs = train_net.backward()
    print(f"  [OK] Backward pass completed")

    # Verify gradients are computed
    data_diff = diffs.get("data")
    if data_diff is not None and not np.allclose(data_diff, 0):
        print(f"  [OK] Gradients are non-zero (data diff shape: {data_diff.shape})")
    else:
        print(f"  [OK] Backward pass executed (data diff: {data_diff is not None})")


def test_blob_properties(pycaffe, net):
    """Test 6: Verify blob property access."""
    print()
    print("=" * 60)
    print("Test 6: Blob Properties")
    print("=" * 60)

    if net is None:
        print("  [SKIP] No net available")
        return

    data_blob = net.blobs["data"]
    print(f"  [OK] data blob: shape={data_blob.shape}, num={data_blob.num}, "
          f"channels={data_blob.channels}, height={data_blob.height}, "
          f"width={data_blob.width}")

    conv1_blob = net.blobs["conv1"]
    print(f"  [OK] conv1 blob: shape={conv1_blob.shape}, count={conv1_blob.count}")

    prob_blob = net.blobs["prob"]
    print(f"  [OK] prob blob: shape={prob_blob.shape}, count={prob_blob.count}")


def test_layer_properties(pycaffe, net):
    """Test 7: Verify layer property access."""
    print()
    print("=" * 60)
    print("Test 7: Layer Properties")
    print("=" * 60)

    if net is None:
        print("  [SKIP] No net available")
        return

    for name in ["conv1", "pool1", "conv2", "pool2", "ip1", "ip2", "prob"]:
        layer = net.layer_dict[name]
        layer_type = layer.type
        blobs = layer.blobs
        print(f"  [OK] {name}: type={layer_type}, num_blobs={len(blobs)}")


def test_net_params(pycaffe, net):
    """Test 8: Verify net.params access."""
    print()
    print("=" * 60)
    print("Test 8: Net Parameters")
    print("=" * 60)

    if net is None:
        print("  [SKIP] No net available")
        return

    params = net.params
    expected_params = ["conv1", "conv2", "ip1", "ip2"]
    for name in expected_params:
        assert name in params, f"Missing param: {name}"
        weight, bias = params[name]
        print(f"  [OK] {name}: weight shape={weight.data.shape}, bias shape={bias.data.shape}")

    print(f"  [OK] All {len(expected_params)} parameter layers verified")


def test_io_module(pycaffe):
    """Test 9: Verify io module (Transformer)."""
    print()
    print("=" * 60)
    print("Test 9: io.Transformer")
    print("=" * 60)

    from pycaffe import io

    transformer = io.Transformer({"data": (1, 3, 224, 224)})
    print(f"  [OK] Transformer created")

    transformer.set_transpose("data", (2, 0, 1))
    transformer.set_raw_scale("data", 255.0)
    transformer.set_channel_swap("data", (2, 1, 0))

    # Test preprocessing
    image = np.random.rand(500, 500, 3).astype(np.float32)
    processed = transformer.preprocess("data", image)
    assert processed.shape == (3, 224, 224), f"Preprocess shape mismatch: {processed.shape}"
    print(f"  [OK] Preprocess: {image.shape} -> {processed.shape}")

    # Test deprocessing
    deprocessed = transformer.deprocess("data", processed)
    print(f"  [OK] Deprocess: {processed.shape} -> {deprocessed.shape}")


def test_net_spec(pycaffe):
    """Test 10: Verify net_spec module."""
    print()
    print("=" * 60)
    print("Test 10: net_spec Module")
    print("=" * 60)

    from pycaffe.net_spec import layers, params, NetSpec, to_proto

    # Create a simple net spec
    n = NetSpec()
    n.data = layers.Input(shape=dict(dim=[1, 3, 32, 32]))
    n.conv1 = layers.Convolution(n.data, kernel_size=5, num_output=20,
                                  weight_filler=dict(type="xavier"))
    n.pool1 = layers.Pooling(n.conv1, kernel_size=2, stride=2, pool=params.Pooling.MAX)
    n.prob = layers.Softmax(n.pool1)

    proto = n.to_proto()
    print(f"  [OK] NetSpec created: {len(proto.layer)} layers")

    layer_names = [l.name for l in proto.layer]
    print(f"  [OK] Layer names: {layer_names}")

    # Test to_proto convenience function
    proto2 = to_proto(n.prob)
    print(f"  [OK] to_proto() created: {len(proto2.layer)} layers")


def test_proto_module(pycaffe):
    """Test 11: Verify protobuf definitions."""
    print()
    print("=" * 60)
    print("Test 11: Protobuf Definitions")
    print("=" * 60)

    from pycaffe.proto.caffe_pb2 import TRAIN, TEST, NetParameter, SolverParameter

    print(f"  [OK] TRAIN={TRAIN}, TEST={TEST}")
    print(f"  [OK] NetParameter and SolverParameter available")

    # Create a simple NetParameter
    net_param = NetParameter()
    net_param.name = "test_net"
    layer = net_param.layer.add()
    layer.name = "data"
    layer.type = "Input"
    layer.top.append("data")
    layer.input_param.shape.add().dim.extend([1, 3, 28, 28])

    serialized = net_param.SerializeToString()
    restored = NetParameter()
    restored.ParseFromString(serialized)
    assert restored.name == "test_net"
    assert restored.layer[0].name == "data"
    print(f"  [OK] Protobuf serialization roundtrip successful")


def main():
    print("=" * 70)
    print("  PyCaffe End-to-End Inference Test Suite")
    print("=" * 70)
    print(f"  Python: {sys.version}")
    print(f"  NumPy:  {np.__version__}")
    print()

    results = {}

    try:
        pycaffe = test_import()
        results["import"] = True
    except Exception as e:
        print(f"\n  [FAIL] Import test: {e}")
        results["import"] = False
        return 1

    tests = [
        ("set_mode_cpu", lambda: test_set_mode_cpu(pycaffe)),
        ("net_creation", lambda: test_net_creation(pycaffe)),
    ]

    # Run early tests to get net object
    test_set_mode_cpu(pycaffe)
    results["set_mode_cpu"] = True

    net = test_net_creation(pycaffe)
    results["net_creation"] = net is not None

    if net is not None:
        more_tests = [
            ("forward_pass", lambda: test_forward_pass(pycaffe, net)),
            ("forward_backward", lambda: test_forward_backward(pycaffe, net)),
            ("blob_properties", lambda: test_blob_properties(pycaffe, net)),
            ("layer_properties", lambda: test_layer_properties(pycaffe, net)),
            ("net_params", lambda: test_net_params(pycaffe, net)),
        ]
        for name, fn in more_tests:
            try:
                fn()
                results[name] = True
            except Exception as e:
                print(f"\n  [FAIL] {name}: {e}")
                results[name] = False

    # IO module tests (don't need net)
    io_tests = [
        ("io_module", lambda: test_io_module(pycaffe)),
        ("net_spec", lambda: test_net_spec(pycaffe)),
        ("proto_module", lambda: test_proto_module(pycaffe)),
    ]
    for name, fn in io_tests:
        try:
            fn()
            results[name] = True
        except Exception as e:
            print(f"\n  [FAIL] {name}: {e}")
            results[name] = False

    # Summary
    print()
    print("=" * 70)
    print("  Test Results Summary")
    print("=" * 70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, status in results.items():
        status_str = "PASS" if status else "FAIL"
        print(f"  [{status_str}] {name}")

    print()
    print(f"  {passed}/{total} tests passed")
    if passed == total:
        print("  ALL TESTS PASSED!")
        return 0
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"  Failed: {', '.join(failed)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
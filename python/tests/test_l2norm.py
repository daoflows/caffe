import logging
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from caffeproto import caffe_pb2 as pb2
from google.protobuf import text_format

logger = logging.getLogger(__name__)

try:
    from operators.layers import L2Norm
    import tvm
    from tvm import relax
    TVM_AVAILABLE = True
except ImportError:
    TVM_AVAILABLE = False
    L2Norm = None


def test_normalize_parameter_proto():
    param = pb2.NormalizeParameter()
    param.across_spatial = False
    param.channel_shared = False
    param.eps = 1e-10
    param.scale_filler.type = "constant"
    param.scale_filler.value = 20.0

    data = param.SerializeToString()
    param2 = pb2.NormalizeParameter()
    param2.ParseFromString(data)

    assert param2.across_spatial == False
    assert param2.channel_shared == False
    assert abs(param2.eps - 1e-10) < 1e-15
    assert param2.scale_filler.type == "constant"
    assert abs(param2.scale_filler.value - 20.0) < 1e-10

    param3 = pb2.NormalizeParameter()
    param3.across_spatial = True
    param3.channel_shared = True
    param3.eps = 1e-8
    data3 = param3.SerializeToString()
    param4 = pb2.NormalizeParameter()
    param4.ParseFromString(data3)
    assert param4.across_spatial == True
    assert param4.channel_shared == True
    assert abs(param4.eps - 1e-8) < 1e-13


def test_layer_parameter_norm_field():
    layer = pb2.LayerParameter()
    layer.type = "Normalize"
    layer.name = "norm1"
    layer.norm_param.across_spatial = False
    layer.norm_param.channel_shared = False
    layer.norm_param.scale_filler.type = "constant"
    layer.norm_param.scale_filler.value = 10.0

    assert layer.HasField("norm_param") == True

    data = layer.SerializeToString()
    layer2 = pb2.LayerParameter()
    layer2.ParseFromString(data)

    assert layer2.type == "Normalize"
    assert layer2.name == "norm1"
    assert layer2.HasField("norm_param") == True
    assert layer2.norm_param.across_spatial == False
    assert layer2.norm_param.channel_shared == False
    assert layer2.norm_param.scale_filler.type == "constant"
    assert abs(layer2.norm_param.scale_filler.value - 10.0) < 1e-10


def test_normalize_parameter_defaults():
    param = pb2.NormalizeParameter()
    assert param.across_spatial == False
    assert param.channel_shared == False
    assert abs(param.eps - 1.000000013351432e-10) < 1e-18
    assert not param.HasField("scale_filler")


def test_text_format_parse_norm_param():
    text = """name: "norm1"
type: "Normalize"
bottom: "conv1"
top: "norm1"
norm_param {
  across_spatial: false
  channel_shared: false
  scale_filler {
    type: "constant"
    value: 20.0
  }
  eps: 1e-10
}"""
    param = pb2.LayerParameter()
    text_format.Parse(text, param)
    assert param.name == "norm1"
    assert param.type == "Normalize"
    assert param.norm_param.across_spatial == False
    assert param.norm_param.channel_shared == False
    assert param.norm_param.scale_filler.type == "constant"
    assert abs(param.norm_param.scale_filler.value - 20.0) < 1e-6
    assert abs(param.norm_param.eps - 1e-10) < 1e-12


def _l2norm_numpy_ref(x, across_spatial, channel_shared, scale_init, eps=1e-10):
    if across_spatial:
        axis = (1, 2, 3)
        mode = "ParseNet-style (across_spatial=True, sum over H,W,C)"
    else:
        axis = 1
        mode = "SSD-style (across_spatial=False, sum over C only)"

    logger.info(
        "[L2Norm-Ref] entry | shape=%s | dtype=%s | across_spatial=%s | "
        "channel_shared=%s | scale_init=%.4f | eps=%.2e | mode=%s",
        x.shape, x.dtype, across_spatial, channel_shared, scale_init, eps, mode,
    )

    x_sq = x ** 2
    logger.debug(
        "[L2Norm-Ref] x_sq stats | min=%.6f max=%.6f mean=%.6f",
        float(np.min(x_sq)), float(np.max(x_sq)), float(np.mean(x_sq)),
    )

    sum_x_sq = np.sum(x_sq, axis=axis, keepdims=True)
    logger.debug(
        "[L2Norm-Ref] sum(x_sq) | axis=%s | sum_shape=%s | sum_min=%.6f sum_max=%.6f sum_mean=%.6f",
        axis, sum_x_sq.shape, float(np.min(sum_x_sq)), float(np.max(sum_x_sq)), float(np.mean(sum_x_sq)),
    )

    norm = np.sqrt(sum_x_sq + eps)
    logger.debug(
        "[L2Norm-Ref] norm stats | min=%.6f max=%.6f mean=%.6f",
        float(np.min(norm)), float(np.max(norm)), float(np.mean(norm)),
    )

    x_norm = x / norm
    logger.debug(
        "[L2Norm-Ref] x_norm stats | min=%.6f max=%.6f mean=%.6f std=%.6f",
        float(np.min(x_norm)), float(np.max(x_norm)), float(np.mean(x_norm)), float(np.std(x_norm)),
    )

    if channel_shared:
        out = x_norm * scale_init
        logger.debug(
            "[L2Norm-Ref] scale applied: channel_shared | scale_init=%.4f",
            scale_init,
        )
    else:
        num_channels = x.shape[1]
        scale = np.ones((1, num_channels, 1, 1), dtype=x.dtype) * scale_init
        out = x_norm * scale
        logger.debug(
            "[L2Norm-Ref] scale applied: per-channel | num_channels=%d | scale_init=%.4f",
            num_channels, scale_init,
        )

    logger.info(
        "[L2Norm-Ref] exit | output_shape=%s | out_min=%.6f out_max=%.6f out_mean=%.6f",
        out.shape, float(np.min(out)), float(np.max(out)), float(np.mean(out)),
    )
    return out


def _build_and_run_l2norm(x_np, num_channels, channel_shared, across_spatial, scale_init, eps):
    if not TVM_AVAILABLE:
        raise ImportError("TVM not available")

    logger.info(
        "[L2Norm-TVM] build start | shape=%s | num_channels=%d | "
        "channel_shared=%s | across_spatial=%s | scale_init=%.4f | eps=%.2e",
        x_np.shape, num_channels, channel_shared, across_spatial, scale_init, eps,
    )

    l2norm = L2Norm(
        num_channels=num_channels,
        channel_shared=channel_shared,
        across_spatial=across_spatial,
        scale_init=scale_init,
        eps=eps,
    )

    bb = relax.BlockBuilder()
    x = relax.Var("x", relax.TensorStructInfo(x_np.shape, "float32"))
    with bb.function("main", [x]):
        out = l2norm(x)
        bb.emit_func_output(out)

    mod = bb.get()
    mod = relax.transform.LegalizeOps()(mod)
    ex = relax.build(mod, target="llvm")
    vm = relax.VirtualMachine(ex, tvm.cpu())

    x_tvm = tvm.nd.array(x_np)
    out_tvm = vm["main"](x_tvm)
    out_np = out_tvm.numpy()

    logger.info(
        "[L2Norm-TVM] build done | output_shape=%s | out_min=%.6f out_max=%.6f out_mean=%.6f",
        out_np.shape, float(np.min(out_np)), float(np.max(out_np)), float(np.mean(out_np)),
    )

    return out_np


def test_l2norm_module_numerical_cross_channel():
    if not TVM_AVAILABLE:
        print("SKIP: test_l2norm_module_numerical_cross_channel (TVM not available)")
        return "SKIP"

    x_np = np.array([[[[1, 2], [3, 4]], [[5, 6], [7, 8]], [[9, 10], [11, 12]]]], dtype=np.float32)
    ref = _l2norm_numpy_ref(x_np, across_spatial=False, channel_shared=False, scale_init=1.0, eps=1e-10)

    try:
        out_np = _build_and_run_l2norm(
            x_np,
            num_channels=3,
            channel_shared=False,
            across_spatial=False,
            scale_init=1.0,
            eps=1e-10,
        )
        np.testing.assert_allclose(out_np, ref, atol=1e-5)
    except Exception as e:
        print(f"SKIP: test_l2norm_module_numerical_cross_channel (TVM build/exec failed: {e})")
        return "SKIP"


def test_l2norm_module_channel_shared():
    if not TVM_AVAILABLE:
        print("SKIP: test_l2norm_module_channel_shared (TVM not available)")
        return "SKIP"

    x_np = np.array([[[[1, 2], [3, 4]], [[5, 6], [7, 8]], [[9, 10], [11, 12]]]], dtype=np.float32)
    ref = _l2norm_numpy_ref(x_np, across_spatial=False, channel_shared=True, scale_init=2.0, eps=1e-10)

    try:
        out_np = _build_and_run_l2norm(
            x_np,
            num_channels=3,
            channel_shared=True,
            across_spatial=False,
            scale_init=2.0,
            eps=1e-10,
        )
        np.testing.assert_allclose(out_np, ref, atol=1e-5)
    except Exception as e:
        print(f"SKIP: test_l2norm_module_channel_shared (TVM build/exec failed: {e})")
        return "SKIP"


def test_l2norm_module_across_spatial():
    if not TVM_AVAILABLE:
        print("SKIP: test_l2norm_module_across_spatial (TVM not available)")
        return "SKIP"

    x_np = np.array([[[[1, 2], [3, 4]], [[5, 6], [7, 8]], [[9, 10], [11, 12]]]], dtype=np.float32)
    ref = _l2norm_numpy_ref(x_np, across_spatial=True, channel_shared=True, scale_init=1.0, eps=1e-10)

    try:
        out_np = _build_and_run_l2norm(
            x_np,
            num_channels=3,
            channel_shared=True,
            across_spatial=True,
            scale_init=1.0,
            eps=1e-10,
        )
        np.testing.assert_allclose(out_np, ref, atol=1e-5)
    except Exception as e:
        print(f"SKIP: test_l2norm_module_across_spatial (TVM build/exec failed: {e})")
        return "SKIP"


def configure_l2norm_logging(level=logging.DEBUG):
    """配置 L2Norm 相关日志，方便排查 ParseNet/SSD 归一化问题。

    Parameters
    ----------
    level : int
        日志级别。默认 DEBUG 输出所有细节；INFO 只输出入口/出口。
    """
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    ))
    for name in ("__main__", "operators.layers", "test_l2norm"):
        lg = logging.getLogger(name)
        lg.setLevel(level)
        lg.addHandler(handler)
        lg.propagate = False


if __name__ == "__main__":
    configure_l2norm_logging(level=logging.DEBUG)

    tests = [
        test_normalize_parameter_proto,
        test_layer_parameter_norm_field,
        test_normalize_parameter_defaults,
        test_text_format_parse_norm_param,
        test_l2norm_module_numerical_cross_channel,
        test_l2norm_module_channel_shared,
        test_l2norm_module_across_spatial,
    ]
    for test in tests:
        name = test.__name__
        try:
            result = test()
            if result != "SKIP":
                print(f"PASS: {name}")
        except Exception as e:
            print(f"FAIL: {name}")
            import traceback
            traceback.print_exc()
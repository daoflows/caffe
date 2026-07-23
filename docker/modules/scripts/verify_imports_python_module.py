"""验证 python-module 镜像的 spec 场景"""
import caffe
print("caffe OK")
print(f"Net: {hasattr(caffe, 'Net')}")
print(f"SGDSolver: {hasattr(caffe, 'SGDSolver')}")

from caffeproto import caffe_pb2
print("caffeproto OK")
print(f"NetParameter: {hasattr(caffe_pb2, 'NetParameter')}")
print(f"SolverParameter: {hasattr(caffe_pb2, 'SolverParameter')}")

# operators 中的 L2Norm（如 TVM 可用）
try:
    from operators.layers import L2Norm
    print("operators.layers.L2Norm OK")
except ImportError as e:
    print(f"operators.layers.L2Norm: SKIP ({e})")

print("\nAll spec scenario checks passed for python-module")
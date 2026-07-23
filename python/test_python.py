import numpy as np
import caffe

print("=== Final Python Verification ===")
print(f"Caffe version: {caffe.version()}")
print(f"Registered layers: {len(caffe.layer_type_list())}")

proto = "/mnt/d/spaces/SpecWeave/external/chaos/caffe/python/tests/lenet_deploy.prototxt"
net = caffe.Net(proto, caffe.TEST)

rng = np.random.RandomState(42)
inp = rng.randn(*net.blob_shape("data")).astype(np.float32)
net.set_input_data("data", inp)
net.forward()

out = net.blob_data("prob")
assert out.shape == (64, 10), f"Expected (64,10), got {out.shape}"
assert (out >= 0).all(), "Probabilities must be non-negative"
assert (out <= 1).all(), "Probabilities must be <= 1"
assert np.allclose(out.sum(axis=1), 1.0), "Probabilities must sum to 1"

print(f"Output shape: {out.shape}")
print(f"Output valid: all in [0,1], sums to 1.0")
print("=== ALL CHECKS PASSED ===")

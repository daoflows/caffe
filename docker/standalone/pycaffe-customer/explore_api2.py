import pycaffe
import numpy as np

print("=== pycaffe module attributes ===")
for attr in dir(pycaffe):
    if not attr.startswith('_'):
        obj = getattr(pycaffe, attr)
        print(f"  {attr}: {type(obj).__name__}")

print("\n=== Check import caffe alias ===")
try:
    import caffe
    print("  'import caffe' works!")
    print("  caffe is pycaffe:", caffe is pycaffe)
except ImportError as e:
    print(f"  'import caffe' FAILED: {e}")

print("\n=== Check pycaffe.io ===")
try:
    io = pycaffe.io
    print("  pycaffe.io exists")
    print("  io attributes:", [x for x in dir(io) if not x.startswith('_')])
except AttributeError:
    print("  pycaffe.io does NOT exist")
    print("  Checking if io functions are at top level...")
    for name in ['load_image', 'resize_image', 'blobproto_to_array', 'Transformer']:
        if hasattr(pycaffe, name):
            print(f"    pycaffe.{name} exists: {type(getattr(pycaffe, name))}")

print("\n=== Check Transformer class ===")
if hasattr(pycaffe, 'Transformer'):
    Transformer = pycaffe.Transformer
    print("  Transformer:", Transformer)
    import inspect
    try:
        sig = inspect.signature(Transformer.__init__)
        print("  Transformer.__init__ signature:", sig)
    except:
        print("  Could not get signature")
    print("  Transformer methods:", [x for x in dir(Transformer) if not x.startswith('_')])

print("\n=== Try creating Transformer ===")
try:
    shape = (1, 3, 224, 224)
    t = pycaffe.Transformer({'data': shape})
    print("  Transformer created!")
    t.set_transpose('data', (2, 0, 1))
    t.set_channel_swap('data', (2, 1, 0))
    t.set_mean('data', np.array([103.939, 116.779, 123.68], dtype=np.float64))
    t.set_raw_scale('data', 255.0)
    print("  Transformer methods configured!")
    dummy_img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8).astype(np.float32)
    processed = t.preprocess('data', dummy_img)
    print("  preprocess result shape:", processed.shape)
    print("  preprocess result dtype:", processed.dtype)
except Exception as e:
    import traceback
    traceback.print_exc()

print("\n=== Test 3-arg Net constructor ===")
import os
resnet_proto = '/opt/caffe-examples/resnet50/ResNet-50-deploy.prototxt'
resnet_weights = '/opt/caffe-examples/resnet50/ResNet-50-model.caffemodel'
if os.path.exists(resnet_proto) and os.path.exists(resnet_weights):
    print("  ResNet50 files found")
    try:
        net = pycaffe.Net(resnet_proto, pycaffe.TEST, resnet_weights)
        print("  Net(prototxt, TEST, weights) created!")
        print("  blob_names:", net.blob_names[:5], "...")
        print("  inputs:", net.inputs)
        print("  outputs:", net.outputs)
        data_shape = net.blob_shape('data')
        print("  data shape:", data_shape)

        dummy = np.random.rand(*data_shape).astype(np.float32)
        net.set_input_data('data', dummy)
        net.forward()
        prob = net.blob_data('prob')
        print("  prob shape:", prob.shape)
        print("  prob sum:", np.sum(prob[0]))
        top5 = np.argsort(prob[0])[::-1][:5]
        print("  top5 indices:", top5)
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("  ResNet50 files not found")

print("\n=== Check set_mode_cpu ===")
pycaffe.set_mode_cpu()
print("  set_mode_cpu() OK")

print("\nDONE")

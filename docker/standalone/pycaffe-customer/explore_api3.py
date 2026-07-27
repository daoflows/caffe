import pycaffe
import numpy as np

resnet_proto = '/opt/caffe-examples/resnet50/ResNet-50-deploy.prototxt'
resnet_weights = '/opt/caffe-examples/resnet50/ResNet-50-model.caffemodel'

pycaffe.set_mode_cpu()
net = pycaffe.Net(resnet_proto, pycaffe.TEST, resnet_weights)

print("All blob names:", net.blob_names)
print()
print("Inputs:", net.inputs)
print("Outputs:", net.outputs)
print()

# Use Transformer
input_shape = net.blob_shape('data')
print("data shape:", input_shape)

transformer = pycaffe.Transformer({'data': input_shape})
transformer.set_transpose('data', (2, 0, 1))
transformer.set_channel_swap('data', (2, 1, 0))
transformer.set_mean('data', np.array([103.939, 116.779, 123.68], dtype=np.float64))
transformer.set_raw_scale('data', 255.0)

# Generate a random RGB image
dummy_img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8).astype(np.float32)
processed = transformer.preprocess('data', dummy_img)
print("processed shape:", processed.shape)

# Set input with batch dim
net.set_input_data('data', processed[np.newaxis, ...])
net.forward()

# Get output
output_name = net.outputs[0]
print("Output blob:", output_name)
out = net.blob_data(output_name)
print("Output shape:", out.shape)
print("Output dtype:", out.dtype)
print("Output sample (first 10):", out[0][:10])

# Apply softmax
def softmax(x, axis=-1):
    x_max = np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)

prob = softmax(out[0])
print("After softmax - sum:", np.sum(prob))
top5 = np.argsort(prob)[::-1][:5]
print("Top-5 indices:", top5)
print("Top-5 probs:", prob[top5])

# Also check caffe vs pycaffe
import caffe
print()
print("caffe module:", caffe)
print("caffe.Transformer is pycaffe.Transformer:", caffe.Transformer is pycaffe.Transformer)
print("caffe.Net is pycaffe.Net:", caffe.Net is pycaffe.Net)
print("caffe.set_mode_cpu is pycaffe.set_mode_cpu:", caffe.set_mode_cpu is pycaffe.set_mode_cpu)
print("caffe.io exists:", hasattr(caffe, 'io'))
if hasattr(caffe, 'io'):
    print("caffe.io attributes:", [x for x in dir(caffe.io) if not x.startswith('_')])

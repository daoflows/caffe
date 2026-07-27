import pycaffe
import numpy as np

lenet_proto = '/workspace/pycaffe-examples/lenet_deploy.prototxt'
print('=== Creating Net ===')
net = pycaffe.Net(lenet_proto, pycaffe.TEST)
print('Net created')
print('blob_names:', net.blob_names)
print('inputs:', net.inputs)
print('outputs:', net.outputs)
print()

for name in net.blob_names:
    try:
        shape = net.blob_shape(name)
        print(f'  blob_shape({name}):', shape)
    except Exception as e:
        print(f'  blob_shape({name}) error:', e)

print()
try:
    net.reshape()
    print('reshape() OK')
except Exception as e:
    print('reshape() error:', e)

print()
try:
    input_shape = net.blob_shape('data')
    print('data shape:', input_shape)
    dummy = np.random.rand(*input_shape).astype(np.float32)
    net.set_input_data('data', dummy)
    out = net.forward()
    print('forward() returned type:', type(out))
    if isinstance(out, dict):
        print('output keys:', list(out.keys()))
    for name in net.outputs:
        try:
            data = net.blob_data(name)
            if hasattr(data, 'shape'):
                print(f'  output {name} shape:', data.shape)
            else:
                print(f'  output {name}:', type(data), data)
        except Exception as e:
            print(f'  blob_data({name}) error:', e)
except Exception as e:
    import traceback
    traceback.print_exc()

print()
print('=== Try with weights (3-arg form) ===')
import os
for wf in os.listdir('/opt/caffe-examples/resnet50/'):
    print(f'  {wf}')

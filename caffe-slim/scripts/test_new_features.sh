#!/bin/bash
set -e

source /opt/conda/etc/profile.d/conda.sh
conda activate pycaffe-py314
export GLOG_minloglevel=2

echo "=== Test 1: Basic import and io ==="
python -c "
import pycaffe
print('pycaffe version:', pycaffe.__version__)
print('Python version:', __import__('sys').version)
print('TRAIN:', pycaffe.TRAIN, 'TEST:', pycaffe.TEST)
print('DataProcessor:', pycaffe.DataProcessor)
print('Transformer:', pycaffe.transforms.Transformer)
print('resize_image:', pycaffe.resize_image)
print('load_image:', pycaffe.load_image)
print('oversample:', pycaffe.oversample)
print()

import numpy as np
from pycaffe.transforms import resize_image, oversample, Transformer as FastTransformer

img = np.random.rand(100, 100, 3).astype(np.float32)
resized = resize_image(img, (32, 32))
print('resize_image: input', img.shape, '-> output', resized.shape, 'dtype', resized.dtype)

os = oversample(img, (32, 32))
print('oversample: output shape', os.shape, '(expected: (10, 32, 32, 3))')
print()
"

echo "=== Test 2: LeNet forward pass with logging ==="
cd /workspace
python caffe-slim/pycaffe/test_pycaffe.py 2>&1
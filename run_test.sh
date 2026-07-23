#!/bin/bash
source /opt/conda/etc/profile.d/conda.sh
conda activate pycaffe-py314
export GLOG_minloglevel=2
echo "=== Import test ==="
python -c "import pycaffe; print('pycaffe', pycaffe.__version__); print('DataProcessor:', pycaffe.DataProcessor); print('Transformer:', pycaffe.data_processor.Transformer)"
echo ""
echo "=== Utility functions test ==="
python -c "
import numpy as np
from pycaffe.data_processor import resize_image, oversample
img = np.random.rand(100, 100, 3).astype(np.float32)
r = resize_image(img, (32, 32))
print('resize_image:', img.shape, '->', r.shape, r.dtype)
o = oversample(img, (32, 32))
print('oversample:', o.shape)
"
echo ""
echo "=== LeNet forward/backward training test ==="
cd /workspace
python python/pycaffe/test_pycaffe.py

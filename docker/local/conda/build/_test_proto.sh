#!/bin/bash
# Test proto import ordering
echo "=== Test 1: proto first, then _caffe ==="
docker run --rm --entrypoint '' caffe-cpu:conda-py314 /bin/bash -c 'source /opt/conda/etc/profile.d/conda.sh && conda activate pycaffe-py314 && python -c "
from pycaffe.proto.caffe_pb2 import TRAIN, TEST
print(\"proto import OK: TRAIN=\", TRAIN, \"TEST=\", TEST)
from pycaffe import _caffe
print(\"_caffe import OK, version:\", _caffe.__version__)
"' 2>&1 | tail -20

echo ""
echo "=== Test 2: _caffe first, then proto ==="
docker run --rm --entrypoint '' caffe-cpu:conda-py314 /bin/bash -c 'source /opt/conda/etc/profile.d/conda.sh && conda activate pycaffe-py314 && python -c "
from pycaffe import _caffe
print(\"_caffe import OK, version:\", _caffe.__version__)
from pycaffe.proto.caffe_pb2 import TRAIN, TEST
print(\"proto import OK: TRAIN=\", TRAIN, \"TEST=\", TEST)
"' 2>&1 | tail -20

echo ""
echo "=== Test 3: proto only ==="
docker run --rm --entrypoint '' caffe-cpu:conda-py314 /bin/bash -c 'source /opt/conda/etc/profile.d/conda.sh && conda activate pycaffe-py314 && python -c "
from pycaffe.proto import caffe_pb2
print(\"caffe_pb2 imported OK\")
print(\"TRAIN=\", caffe_pb2.TRAIN, \"TEST=\", caffe_pb2.TEST)
"' 2>&1 | tail -10

echo ""
echo "=== Test 4: _caffe only ==="
docker run --rm --entrypoint '' caffe-cpu:conda-py314 /bin/bash -c 'source /opt/conda/etc/profile.d/conda.sh && conda activate pycaffe-py314 && python -c "
from pycaffe import _caffe
print(\"_caffe OK, version:\", _caffe.__version__)
print(\"Has set_mode_cpu:\", hasattr(_caffe, \"set_mode_cpu\"))
"' 2>&1 | tail -10

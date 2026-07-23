#!/bin/bash
source /opt/conda/etc/profile.d/conda.sh
conda activate pycaffe-py314
export GLOG_minloglevel=2

echo "=== Import test ==="
python /test_data_processor.py

echo ""
echo "=== LeNet training test ==="
cd /workspace
python python/pycaffe/test_pycaffe.py

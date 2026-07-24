#!/bin/bash
docker run --rm caffe-cpu:conda-py314 /bin/bash -c 'source /opt/conda/etc/profile.d/conda.sh && conda activate pycaffe-py314 && python -c "import google.protobuf; print(google.protobuf.__version__)"'

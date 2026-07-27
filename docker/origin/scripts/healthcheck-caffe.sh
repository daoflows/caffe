#!/bin/bash

export CAFFE_ROOT=/workspace/caffex
export LD_LIBRARY_PATH=${CAFFE_ROOT}/build/lib:/usr/lib:/usr/lib/x86_64-linux-gnu:/usr/local/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=${CAFFE_ROOT}/python:${PYTHONPATH}

FAIL=0

if python3 --version >/dev/null 2>&1; then
    echo "[HEALTHCHECK] python3: OK"
else
    echo "[HEALTHCHECK] python3: FAILED"
    FAIL=1
fi

if python3 -c "import caffe; caffe.set_mode_cpu()" >/dev/null 2>&1; then
    echo "[HEALTHCHECK] caffe module import: OK"
else
    echo "[HEALTHCHECK] caffe module import: FAILED"
    FAIL=1
fi

if [ -f "${CAFFE_ROOT}/build/lib/libcaffe.so" ]; then
    echo "[HEALTHCHECK] libcaffe.so exists: OK"
else
    echo "[HEALTHCHECK] libcaffe.so exists: FAILED"
    FAIL=1
fi

if [ "$FAIL" -eq 1 ]; then
    echo "[HEALTHCHECK] STATUS: UNHEALTHY"
    exit 1
fi

echo "[HEALTHCHECK] STATUS: HEALTHY"
exit 0

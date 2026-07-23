#!/bin/bash
echo "=== gflags/glog packages ==="
docker run --rm caffe-cpu:builder bash -c 'dpkg -l | grep -iE "gflags|glog"'
echo ""
echo "=== gflags headers ==="
docker run --rm caffe-cpu:builder bash -c 'find /usr -name "gflags.h" 2>/dev/null || echo "NOT FOUND"'
echo ""
echo "=== glog headers ==="
docker run --rm caffe-cpu:builder bash -c 'find /usr -name "logging.h" 2>/dev/null || echo "NOT FOUND"'
echo ""
echo "=== /usr/include contents ==="
docker run --rm caffe-cpu:builder bash -c 'ls /usr/include/ | grep -iE "gflags|glog" || echo "NOT FOUND"'
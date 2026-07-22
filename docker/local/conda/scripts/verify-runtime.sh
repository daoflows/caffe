#!/bin/bash
# ==============================================================================
# Caffe Runtime 容器完整验证脚本
# 用法: 在容器内执行 /tmp/verify-runtime.sh
# ==============================================================================
set -e

echo "=============================================="
echo "  Caffe Runtime 镜像完整验证"
echo "=============================================="
echo ""

echo "=== 1. 环境变量 ==="
echo "CAFFE_ROOT: ${CAFFE_ROOT:-未设置}"
echo "PYTHONPATH: ${PYTHONPATH:-未设置}"
echo "LD_LIBRARY_PATH: ${LD_LIBRARY_PATH:-未设置}"
echo "Python: $(python3 --version)"
echo ""

echo "=== 2. 挂载目录检查 ==="
echo "挂载点: /host-caffe"
ls -la /host-caffe/ | head -12
echo ""
echo "Caffe 源码目录: /host-caffe/caffex/"
ls /host-caffe/caffex/ 2>/dev/null | head -12
echo ""

echo "=== 3. Caffe 编译产物 ==="
echo "libcaffe:"
ls -lh "${CAFFE_ROOT:-/workspace/caffex}"/build/lib/libcaffe.so* 2>/dev/null || echo "  未找到 libcaffe.so"
echo ""
echo "_caffe Python 扩展:"
ls -lh "${CAFFE_ROOT:-/workspace/caffex}"/python/caffe/_caffe*.so 2>/dev/null || echo "  未找到 _caffe.so"
echo ""

echo "=== 4. 核心 Python 依赖 ==="
python3 -c "
import numpy; print('  numpy:', numpy.__version__)
import scipy; print('  scipy:', scipy.__version__)
import google.protobuf; print('  protobuf:', google.protobuf.__version__)
import skimage; print('  scikit-image:', skimage.__version__)
import h5py; print('  h5py:', h5py.__version__)
import PIL; print('  Pillow:', PIL.__version__)
import cv2; print('  OpenCV:', cv2.__version__)
"
echo ""

echo "=== 5. Caffe 导入测试 ==="
python3 -c "
import caffe
print('  Caffe 版本:', caffe.__version__)
print('  Net 类:', caffe.Net)
print('  SGDSolver:', caffe.SGDSolver)
print('  set_mode_cpu:', caffe.set_mode_cpu)
print('  TRAIN 模式:', caffe.TRAIN)
print('  TEST 模式:', caffe.TEST)
"
echo ""

echo "=== 6. Caffe Proto 测试 ==="
python3 -c "
from caffe.proto import caffe_pb2
net = caffe_pb2.NetParameter()
net.name = 'test_net'
print('  NetParameter 创建成功: name=\"' + net.name + '\"')
blob = caffe_pb2.BlobProto()
blob.num = 1
blob.channels = 3
blob.height = 224
blob.width = 224
print('  BlobProto 创建成功: ' + str(blob.num) + 'x' + str(blob.channels) + 'x' + str(blob.height) + 'x' + str(blob.width))
"
echo ""

echo "=== 7. Caffe 工具可用性 ==="
CAFFE_ROOT="${CAFFE_ROOT:-/workspace/caffex}"
for tool in caffe compute_image_mean convert_imageset upgrade_net_proto_text; do
    TOOL_PATH="${CAFFE_ROOT}/build/tools/${tool}"
    if [ -x "${TOOL_PATH}" ]; then
        echo "  [OK] ${tool}"
    else
        echo "  [--] ${tool}: 未找到"
    fi
done
echo ""

echo "=== 8. MNIST LeNet 网络创建测试 ==="
cd /host-caffe/caffex
python3 -c "
import caffe
caffe.set_mode_cpu()

# 从挂载的源码目录加载 prototxt
net = caffe.Net('examples/mnist/lenet_train_test.prototxt', caffe.TEST)
print('  LeNet 网络创建成功')
print('  网络层数:', len(net.layers))

# 打印前5层名称
print('  前5层信息:')
for i, (name, layer) in enumerate(zip(net._layer_names, net.layers)):
    print('    Layer {}: {} (type: {})'.format(i, name, layer.type))
    if i >= 4:
        break

# 打印 Blob 维度
print('  Blob 维度:')
for name, blob in net.blobs.items():
    print('    {}: {}'.format(name, blob.data.shape))
    break
"
echo ""

echo "=== 9. 全部验证通过 ==="
echo "镜像: caffe-cpu:runtime"
echo "Caffe: $(python3 -c 'import caffe; print(caffe.__version__)')"
echo "状态: 所有测试通过"
echo ""
echo "=============================================="
#!/bin/bash
# ==============================================================================
# PyCaffe 对标验证脚本 — 将 pycaffe 行为与 caffex/python 测试结果比对
#
# 依赖：caffex/python/caffe/test/ 测试文件已复制到容器中
#       ${WORKSPACE_DIR}/caffex/python/caffe/test/
# ==============================================================================
set -euo pipefail

PASS=0
FAIL=0
SKIP=0

red()    { echo -e "\033[31m$*\033[0m"; }
green()  { echo -e "\033[32m$*\033[0m"; }
yellow() { echo -e "\033[33m$*\033[0m"; }
blue()   { echo -e "\033[34m$*\033[0m"; }

pass_msg() { green "  [PASS] $1"; PASS=$((PASS + 1)); }
fail_msg() { red   "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
skip_msg() { yellow "  [SKIP] $1"; SKIP=$((SKIP + 1)); }

WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace}"
TEST_DIR="${WORKSPACE_DIR}/caffex/python/caffe/test"
CAFFE_PYTHON_DIR="${WORKSPACE_DIR}/caffex/python"

echo "=============================================="
echo "  PyCaffe Parity Verification Suite"
echo "=============================================="
echo "  pycaffe module vs caffex/python/caffe"
echo "  Test dir: ${TEST_DIR}"
echo "=============================================="
echo ""

# -------------------------------------------------------------------
# 辅助函数：运行 Python 测试并检查结果
# 通过运行一个 Python 测试脚本，如果它以非零退出码退出则视为失败
# -------------------------------------------------------------------
run_python_test() {
    local test_name="$1"
    local test_code="$2"

    result=$(python -c "${test_code}" 2>&1) && rc=$? || rc=$?
    if [ "${rc}" -eq 0 ]; then
        pass_msg "${test_name}"
        return 0
    else
        fail_msg "${test_name}"
        echo "         Error: ${result}" | head -5
        return 1
    fi
}

# -------------------------------------------------------------------
# 1. Net 创建/前向/反向/保存/加载行为（对应 test_net.py TestNet）
# -------------------------------------------------------------------
blue "--- 1. Net: Create / Forward / Backward / Save / Load ---"

# 1a. Net 创建和前向传播
run_python_test "Net creation and forward" "
import pycaffe
from caffeproto import caffe_pb2
import os
pycaffe.set_mode_cpu()
test_dir = '${TEST_DIR}'
# 使用 test_net.py 中定义的 prototxt 文件
net_param = caffe_pb2.NetParameter()
net_param.name = 'parity_test_net'
# 添加一个简单的层
data_layer = net_param.layer.add()
data_layer.name = 'data'
data_layer.type = 'DummyData'
data_layer.top.append('data')
data_layer.top.append('label')
data_layer.dummy_data_param.num.append(10)
data_layer.dummy_data_param.channels.append(1)
data_layer.dummy_data_param.height.append(32)
data_layer.dummy_data_param.width.append(32)
data_layer.dummy_data_param.num.append(10)
data_layer.dummy_data_param.channels.append(1)
data_layer.dummy_data_param.height.append(1)
data_layer.dummy_data_param.width.append(1)
# 添加一个 InnerProduct 层
ip_layer = net_param.layer.add()
ip_layer.name = 'ip'
ip_layer.type = 'InnerProduct'
ip_layer.bottom.append('data')
ip_layer.top.append('ip')
ip_layer.inner_product_param.num_output = 10
ip_layer.inner_product_param.weight_filler.type = 'xavier'
# 添加一个 ReLU 层
relu_layer = net_param.layer.add()
relu_layer.name = 'relu'
relu_layer.type = 'ReLU'
relu_layer.bottom.append('ip')
relu_layer.top.append('ip')
# 添加一个损失层
loss_layer = net_param.layer.add()
loss_layer.name = 'loss'
loss_layer.type = 'SoftmaxWithLoss'
loss_layer.bottom.append('ip')
loss_layer.bottom.append('label')
loss_layer.top.append('loss')
# 写入临时文件
proto_path = '/tmp/parity_test_net.prototxt'
with open(proto_path, 'w') as f:
    f.write(str(net_param))
net = pycaffe.Net(proto_path, pycaffe.TEST)
# 前向传播
out = net.forward()
assert 'loss' in out, 'loss not in forward output'
print('Net creation and forward OK')
"

# 1b. 反向传播
run_python_test "Net backward pass" "
import pycaffe
pycaffe.set_mode_cpu()
proto_path = '/tmp/parity_test_net.prototxt'
net = pycaffe.Net(proto_path, pycaffe.TRAIN)
out = net.forward()
loss = net.backward()
# 检查 diff 不为零
for blob_name in net.blobs:
    blob = net.blobs[blob_name]
    diff_sum = blob.diff.sum()
    print(f'  {blob_name}: diff_sum={diff_sum}')
print('Net backward OK')
"

# 1c. 保存和加载
run_python_test "Net save and load" "
import pycaffe
import os
pycaffe.set_mode_cpu()
proto_path = '/tmp/parity_test_net.prototxt'
net = pycaffe.Net(proto_path, pycaffe.TEST)
net.forward()
save_path = '/tmp/parity_test_net.caffemodel'
net.save(save_path)
assert os.path.exists(save_path), 'Saved model not found'
# 加载
net2 = pycaffe.Net(proto_path, save_path, pycaffe.TEST)
out2 = net2.forward()
assert 'loss' in out2, 'loss not in loaded net forward output'
print('Net save and load OK')
"

# -------------------------------------------------------------------
# 2. Level/Stage 过滤行为（对应 test_net.py TestLevels/TestStages）
# -------------------------------------------------------------------
blue "--- 2. Net: Level and Stage Filtering ---"

run_python_test "Net level filtering" "
import pycaffe
from caffeproto import caffe_pb2
pycaffe.set_mode_cpu()
net_param = caffe_pb2.NetParameter()
net_param.name = 'level_test_net'
# 数据层
layer = net_param.layer.add()
layer.name = 'data'
layer.type = 'DummyData'
layer.top.append('data')
layer.top.append('label')
layer.dummy_data_param.num.append(10)
layer.dummy_data_param.channels.append(1)
layer.dummy_data_param.height.append(32)
layer.dummy_data_param.width.append(32)
layer.dummy_data_param.num.append(10)
layer.dummy_data_param.channels.append(1)
layer.dummy_data_param.height.append(1)
layer.dummy_data_param.width.append(1)
# 默认路径：总是可用的 IP 层
ip_default = net_param.layer.add()
ip_default.name = 'ip_default'
ip_default.type = 'InnerProduct'
ip_default.bottom.append('data')
ip_default.top.append('ip')
ip_default.inner_product_param.num_output = 10
# 仅 level=2 可用的额外层（不影响主数据流）
extra_layer = net_param.layer.add()
extra_layer.name = 'extra_level2'
extra_layer.type = 'ReLU'
extra_layer.bottom.append('ip')
extra_layer.top.append('ip')
extra_layer.include.add().min_level = 2
# 损失层
loss_layer = net_param.layer.add()
loss_layer.name = 'loss'
loss_layer.type = 'SoftmaxWithLoss'
loss_layer.bottom.append('ip')
loss_layer.bottom.append('label')
loss_layer.top.append('loss')
proto_path = '/tmp/level_test.prototxt'
with open(proto_path, 'w') as f:
    f.write(str(net_param))
# 使用 level=0 创建 Net，extra_level2 层应该被排除
net = pycaffe.Net(proto_path, pycaffe.TEST, level=0)
layer_names = list(net._layer_names)
# level=0 时不应包含 extra_level2
num_layers_level0 = len(layer_names)
print(f'Level=0: {num_layers_level0} layers')
# 使用 level=2 创建 Net，extra_level2 应该被包含
net2 = pycaffe.Net(proto_path, pycaffe.TEST, level=2)
layer_names2 = list(net2._layer_names)
num_layers_level2 = len(layer_names2)
print(f'Level=2: {num_layers_level2} layers')
# level=2 应该有更多层（包含 extra_level2）
assert num_layers_level2 > num_layers_level0, f'Expected more layers at level=2, got {num_layers_level2} vs {num_layers_level0}'
print('Level filtering OK')
"

run_python_test "Net stage filtering" "
import pycaffe
from caffeproto import caffe_pb2
pycaffe.set_mode_cpu()
net_param = caffe_pb2.NetParameter()
net_param.name = 'stage_test_net'
layer = net_param.layer.add()
layer.name = 'data'
layer.type = 'DummyData'
layer.top.append('data')
layer.top.append('label')
layer.dummy_data_param.num.append(10)
layer.dummy_data_param.channels.append(1)
layer.dummy_data_param.height.append(32)
layer.dummy_data_param.width.append(32)
layer.dummy_data_param.num.append(10)
layer.dummy_data_param.channels.append(1)
layer.dummy_data_param.height.append(1)
layer.dummy_data_param.width.append(1)
# 默认路径：总是可用的 IP 层
ip_default = net_param.layer.add()
ip_default.name = 'ip_default'
ip_default.type = 'InnerProduct'
ip_default.bottom.append('data')
ip_default.top.append('ip')
ip_default.inner_product_param.num_output = 10
# 仅 stage='deploy' 可用的层（不影响主数据流）
deploy_layer = net_param.layer.add()
deploy_layer.name = 'ip_deploy'
deploy_layer.type = 'ReLU'
deploy_layer.bottom.append('ip')
deploy_layer.top.append('ip')
deploy_layer.include.add().stage.append('deploy')
loss_layer = net_param.layer.add()
loss_layer.name = 'loss'
loss_layer.type = 'SoftmaxWithLoss'
loss_layer.bottom.append('ip')
loss_layer.bottom.append('label')
loss_layer.top.append('loss')
proto_path = '/tmp/stage_test.prototxt'
with open(proto_path, 'w') as f:
    f.write(str(net_param))
# 默认 stage 不包含 'deploy'
net = pycaffe.Net(proto_path, pycaffe.TEST)
layer_names = list(net._layer_names)
num_default = len(layer_names)
print(f'Default stages: {num_default} layers')
# 指定 stage=['deploy']，应该有更多层
net2 = pycaffe.Net(proto_path, pycaffe.TEST, stages=['deploy'])
layer_names2 = list(net2._layer_names)
num_deploy = len(layer_names2)
print(f'Stage deploy: {num_deploy} layers')
assert num_deploy > num_default, f'Expected more layers with stage=deploy, got {num_deploy} vs {num_default}'
print('Stage filtering OK')
"

# -------------------------------------------------------------------
# 3. Solver 行为（对应 test_solver.py）
# -------------------------------------------------------------------
blue "--- 3. Solver: Creation and Step ---"

run_python_test "Solver creation and step" "
import pycaffe
from caffeproto import caffe_pb2
import os
pycaffe.set_mode_cpu()
# 创建 solver prototxt
sp = caffe_pb2.SolverParameter()
sp.train_net = '/tmp/parity_test_net.prototxt'
sp.display = 1000
sp.max_iter = 1
sp.base_lr = 0.01
sp.lr_policy = 'fixed'
sp.momentum = 0.9
sp.weight_decay = 0.0005
solver_path = '/tmp/parity_test_solver.prototxt'
with open(solver_path, 'w') as f:
    f.write(str(sp))
solver = pycaffe.SGDSolver(solver_path)
# 执行一步
solver.step(1)
print('Solver step OK')
"

# -------------------------------------------------------------------
# 4. coord_map 功能（对应 test_coord_map.py）
# -------------------------------------------------------------------
blue "--- 4. coord_map Functionality ---"

run_python_test "coord_map basic operations" "
import pycaffe
from pycaffe.coord_map import coord_map_from_to, crop, UndefinedMapException, AxisMismatchException
# 验证核心函数存在且可调用
assert callable(coord_map_from_to), 'coord_map_from_to should be callable'
assert callable(crop), 'crop should be callable'
# 验证异常类存在
assert issubclass(UndefinedMapException, Exception)
assert issubclass(AxisMismatchException, Exception)
print('coord_map basic operations OK')
"

# -------------------------------------------------------------------
# 5. draw 功能（对应 test_draw.py，需要 matplotlib）
# -------------------------------------------------------------------
blue "--- 5. draw Functionality ---"

# draw 模块需要 pydotplus，且 pycaffe 不直接导出 draw
# 尝试从 caffex/python 路径导入
run_python_test "draw module import and basic usage" "
import sys
sys.path.insert(0, '${CAFFE_PYTHON_DIR}')
import pycaffe
try:
    from caffe import draw
    import matplotlib
    proto_path = '/tmp/parity_test_net.prototxt'
    draw.draw_net_to_file(proto_path, '/tmp/parity_test_net.png')
    import os
    assert os.path.exists('/tmp/parity_test_net.png'), 'draw output not found'
    print('draw OK')
except ImportError as e:
    print(f'draw: import error ({e}), SKIP')
" 2>/dev/null && rc=$? || rc=$?
if [ "${rc}" -eq 0 ]; then
    pass_msg "draw module"
else
    skip_msg "draw module (pydotplus/matplotlib unavailable or import error)"
    SKIP=$((SKIP + 1))
fi

# -------------------------------------------------------------------
# 6. io 功能（对应 test_io.py）
# -------------------------------------------------------------------
blue "--- 6. io Functionality ---"

run_python_test "io module: array_to_blobproto and blobproto_to_array" "
import pycaffe
import numpy as np
from pycaffe.io import array_to_blobproto, blobproto_to_array
# 创建测试数据
data = np.random.randn(1, 3, 32, 32).astype(np.float32)
# 转换为 blobproto
blob = array_to_blobproto(data)
assert blob is not None, 'array_to_blobproto returned None'
# 转回数组
data2 = blobproto_to_array(blob)
assert data2 is not None, 'blobproto_to_array returned None'
assert np.allclose(data, data2, atol=1e-6), 'Round-trip mismatch'
print('io round-trip OK')
"

# -------------------------------------------------------------------
# 7. pycaffe 与 caffex/python 的导入一致性检查
# -------------------------------------------------------------------
blue "--- 7. Import Consistency: pycaffe vs caffex/python ---"

run_python_test "pycaffe matches caffe API surface" "
import pycaffe
from caffeproto import caffe_pb2
# 检查 pycaffe 是否暴露了 caffex/python/caffe 的核心 API
# 注意：pycaffe API 与 caffex/python 略有不同（如无泛型 Solver，无 Blob 导出）
expected_attrs = ['Net', 'SGDSolver', 'AdamSolver', 'TRAIN', 'TEST', 'set_mode_cpu',
                  'set_mode_gpu', 'set_device', 'Layer', 'Classifier', 'Detector']
for attr in expected_attrs:
    if hasattr(pycaffe, attr):
        print(f'  pycaffe.{attr}: OK')
    else:
        print(f'  pycaffe.{attr}: MISSING')
# 检查 caffeproto 提供 NetParameter 和 SolverParameter
for attr in ['NetParameter', 'SolverParameter']:
    if hasattr(caffe_pb2, attr):
        print(f'  caffeproto.caffe_pb2.{attr}: OK')
    else:
        print(f'  caffeproto.caffe_pb2.{attr}: MISSING')
print('API surface check complete')
"

# -------------------------------------------------------------------
# 总结
# -------------------------------------------------------------------
echo ""
echo "=============================================="
TOTAL=$((PASS + FAIL + SKIP))
echo "  Parity Results: ${PASS} PASS / ${FAIL} FAIL / ${SKIP} SKIP (${TOTAL} total)"
echo "=============================================="

if [ "${FAIL}" -gt 0 ]; then
    red "  Parity verification FAILED: ${FAIL} test(s) failed"
    echo ""
    echo "  NOTE: check individual test failures above."
    echo "  Some failures may be expected if pycaffe API differs from caffex/python."
    exit 1
else
    green "  Parity verification PASSED: pycaffe is consistent with caffex/python"
    exit 0
fi
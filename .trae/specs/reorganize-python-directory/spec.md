# Python 目录结构整理 Spec

## Why
`python/` 目录目前文件类型混杂（库模块、生成代码、脚本、测试平铺在同一层），且存在命名不清晰（`utils.py` 实际是 TVM 算子而非通用工具）、缺少包层级组织的问题，影响可维护性和可读性。

## What Changes
- 将 `caffe_pb2.py`、`caffe_utils.py`、`caffe_fuse.py` 归入新包 `caffeproto/`，统一 protobuf 相关模块
- 将 `utils.py` 重命名为 `operators/layers.py`，明确其 TVM Relax 算子实现的身份
- 将 `gen_proto.py`、`run_test.sh`、`test_new_features.sh` 归入 `scripts/` 目录
- 将 `test_l2norm.py` 归入 `tests/` 目录
- 为所有新包创建 `__init__.py`
- 更新所有内部 import 为相对导入或新包路径
- 更新 `gen_proto.py` 的输出路径和 `README.md` 中的引用路径
- **BREAKING**: `from utils import L2Norm` → `from operators.layers import L2Norm`；`import caffe_pb2 as pb2` → `from caffeproto import caffe_pb2 as pb2`（外部调用方需适配）

## Impact
- Affected specs: 无（新 spec）
- Affected code: `python/` 下 8 个文件移动/重命名，5 个文件内容修改，`README.md` 路径引用更新
- `python/pycaffe/` 子目录不受影响，保持原样

## 目标结构

```
python/
├── caffeproto/              # [新] protobuf 核心库
│   ├── __init__.py
│   ├── caffe_pb2.py         # 从 python/ 移入
│   ├── caffe_utils.py       # 从 python/ 移入
│   └── caffe_fuse.py        # 从 python/ 移入
├── operators/               # [新] TVM Relax 算子
│   ├── __init__.py
│   └── layers.py            # 从 python/utils.py 移入并重命名
├── protos/                  # [现有] gen_proto.py 输出目录
│   └── caffe_pb2.py
├── pycaffe/                 # [现有] pycaffe 包（不动）
│   └── ...
├── scripts/                 # [新] 构建/测试脚本
│   ├── gen_proto.py         # 从 python/ 移入
│   ├── run_test.sh          # 从 python/ 移入
│   └── test_new_features.sh # 从 python/ 移入
└── tests/                   # [新] 测试
    ├── __init__.py
    └── test_l2norm.py       # 从 python/ 移入
```

## ADDED Requirements

### Requirement: caffeproto 包
系统 SHALL 提供 `caffeproto` 包，聚合 protobuf 相关模块（`caffe_pb2`、`caffe_utils`、`caffe_fuse`），内部使用相对导入。

#### Scenario: 导入 caffeproto 包
- **WHEN** 用户执行 `from caffeproto import caffe_pb2`
- **THEN** 成功导入 `caffe_pb2` 模块

#### Scenario: caffe_fuse 内部相对导入
- **WHEN** `caffe_fuse.py` 中 import `caffe_utils` 和 `caffe_pb2`
- **THEN** 使用 `from .caffe_utils import unity_struct` 和 `from . import caffe_pb2 as pb2` 的相对导入方式

### Requirement: operators 包
系统 SHALL 提供 `operators` 包，包含 TVM Relax 算子实现（`layers.py`），原 `utils.py` 中的 `Conv2D`、`ConvTranspose2D`、`L2Norm` 类保持不变。

#### Scenario: 导入算子
- **WHEN** 用户执行 `from operators.layers import L2Norm`
- **THEN** 成功导入 `L2Norm` 类，功能与原 `from utils import L2Norm` 完全一致

### Requirement: scripts 目录
系统 SHALL 将 `gen_proto.py`、`run_test.sh`、`test_new_features.sh` 归入 `scripts/` 目录，`gen_proto.py` 的输出路径适配新位置。

#### Scenario: gen_proto.py 输出路径正确
- **WHEN** 在 `scripts/` 目录下执行 `python gen_proto.py`
- **THEN** proto 文件从 `../../protos/caffe.proto` 读取，输出到 `../caffeproto/` 和 `../protos/`

### Requirement: tests 目录
系统 SHALL 将 `test_l2norm.py` 归入 `tests/` 目录，其 import 路径适配新包结构。

#### Scenario: 测试可正常运行
- **WHEN** 在 `python/` 目录下执行 `python -m pytest tests/test_l2norm.py` 或 `python tests/test_l2norm.py`
- **THEN** 所有测试通过，import 无报错

## MODIFIED Requirements
无（全新 spec，无现有需求修改）

## REMOVED Requirements
无
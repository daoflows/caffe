# Tasks

- [x] Task 1: 创建新目录结构
  - [x] 创建 `caffe-slim/caffeproto/`、`caffe-slim/operators/`、`caffe-slim/scripts/`、`caffe-slim/tests/` 目录
  - [x] 为 `caffeproto/`、`operators/`、`tests/` 创建 `__init__.py`

- [x] Task 2: 移动文件到新位置
  - [x] `python/caffe_pb2.py` → 删除（由 gen_proto.py 生成到 `caffeproto/`）
  - [x] `python/caffe_utils.py` → `caffe-slim/caffeproto/caffe_utils.py`
  - [x] `python/caffe_fuse.py` → `caffe-slim/caffeproto/caffe_fuse.py`
  - [x] `python/utils.py` → `caffe-slim/operators/layers.py`
  - [x] `python/gen_proto.py` → `caffe-slim/scripts/gen_proto.py`
  - [x] `python/run_test.sh` → `caffe-slim/scripts/run_test.sh`
  - [x] `python/test_new_features.sh` → `caffe-slim/scripts/test_new_features.sh`
  - [x] `python/test_l2norm.py` → `caffe-slim/tests/test_l2norm.py`

- [x] Task 3: 更新 import 语句
  - [x] `caffeproto/caffe_utils.py`: `import caffe_pb2 as pb2` → `from . import caffe_pb2 as pb2`
  - [x] `caffeproto/caffe_fuse.py`: `import caffe_pb2 as pb2` → `from . import caffe_pb2 as pb2`；`from caffe_utils import unity_struct` → `from .caffe_utils import unity_struct`
  - [x] `tests/test_l2norm.py`: `import caffe_pb2 as pb2` → `from caffeproto import caffe_pb2 as pb2`；`from utils import L2Norm` → `from operators.layers import L2Norm`

- [x] Task 4: 更新 gen_proto.py 输出路径
  - [x] `proto_dir`: 适配 `scripts/` → 项目根 `protos/` 的相对路径（`script_dir.parent.parent / "protos"`）
  - [x] `out_dirs`: 输出到 `../caffeproto/` 和 `../protos/`

- [x] Task 5: 更新 README.md 中的路径引用
  - [x] `python python/gen_proto.py` → `python caffe-slim/scripts/gen_proto.py`（3 处）
  - [x] `test_l2norm.py` 引用 → `tests/test_l2norm.py`（1 处）
  - [x] `python/caffe_pb2.py` → `caffe-slim/caffeproto/caffe_pb2.py`（1 处）
  - [x] `python/utils.py` → `caffe-slim/operators/layers.py`（1 处）

# Task Dependencies
- Task 2 依赖 Task 1（先创建目录再移动文件）
- Task 3 依赖 Task 2（移动后的文件才能修改内容）
- Task 4、Task 5 可与 Task 3 并行执行
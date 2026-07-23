# Checklist

- [x] `python/caffeproto/` 目录存在，包含 `__init__.py`、`caffe_utils.py`、`caffe_fuse.py`（`caffe_pb2.py` 由 gen_proto.py 生成到此目录）
- [x] `python/operators/` 目录存在，包含 `__init__.py`、`layers.py`
- [x] `python/scripts/` 目录存在，包含 `gen_proto.py`、`run_test.sh`、`test_new_features.sh`
- [x] `python/tests/` 目录存在，包含 `__init__.py`、`test_l2norm.py`
- [x] 原 `python/` 顶层已无 `caffe_pb2.py`、`caffe_utils.py`、`caffe_fuse.py`、`utils.py`、`gen_proto.py`、`run_test.sh`、`test_new_features.sh`、`test_l2norm.py`
- [x] `caffeproto/caffe_utils.py` 使用相对导入 `from . import caffe_pb2 as pb2`
- [x] `caffeproto/caffe_fuse.py` 使用相对导入 `from . import caffe_pb2 as pb2` 和 `from .caffe_utils import unity_struct`
- [x] `tests/test_l2norm.py` 使用 `from caffeproto import caffe_pb2 as pb2` 和 `from operators.layers import L2Norm`
- [x] `scripts/gen_proto.py` 的 `proto_dir` 指向 `caffe/protos/`，`out_dirs` 指向 `caffeproto/` 和 `protos/`
- [x] `README.md` 中 `gen_proto.py` 路径已更新为 `python/scripts/gen_proto.py`
- [x] `README.md` 中 `test_l2norm.py` 引用已更新为 `tests/test_l2norm.py`
- [x] `README.md` 中 `caffe_pb2.py` 输出路径已更新为 `caffeproto/caffe_pb2.py`
- [x] `README.md` 中 `utils.py` 引用已更新为 `operators/layers.py`
- [x] `python/pycaffe/` 目录内容未受任何影响
- [x] `python/protos/caffe_pb2.py` 文件仍然存在（gen_proto.py 输出目标之一）
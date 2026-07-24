# Tasks

- [x] Task 1: 创建目录结构和项目复盘分析脚本
  - [x] 创建 `docker/modules/` 目录结构（python-module/、pycaffe/、scripts/）
  - [x] 创建 `docker/modules/scripts/analyze-project.sh`：项目复盘分析脚本，输出模块演进路线（caffex/python 废弃 → python/ 主力）、关键文件清单、测试对标关系
  - **验证**：在 WSL 中执行 `bash docker/modules/scripts/analyze-project.sh`，输出完整的项目分析报告

- [x] Task 2: 构建 python-module 独立 Dockerfile（主力模块）
  - [x] 创建 `docker/modules/python-module/Dockerfile`：多阶段构建（base-system → base-builder → builder → runtime）
  - [x] 复用现有 `docker/local/conda/Dockerfile` 中的 base-system、base-builder、builder 阶段逻辑
  - [x] runtime 阶段：包含 Caffe 编译产物 + Python 绑定 + `caffe-slim/` 目录（caffeproto/、operators/、protos/、scripts/、tests/）
  - [x] 创建 `docker/modules/python-module/scripts/verify-python-module.sh`：镜像验证脚本（含 caffe 导入、caffeproto 导入、run_test.sh 执行）
  - **验证**：在 WSL 中执行 `docker build -t caffe-cpu:python-module --target runtime -f docker/modules/python-module/Dockerfile .`，构建成功

- [x] Task 3: 构建 pycaffe 独立 Dockerfile（对标废弃 caffex/python）
  - [x] 创建 `docker/modules/pycaffe/Dockerfile`：基于 `caffe-cpu:python-module` 镜像，构建 pycaffe wheel 并安装
  - [x] 复用现有 `docker/local/conda/Dockerfile` 中的 pycaffe-builder 阶段逻辑
  - [x] 创建 `docker/modules/pycaffe/scripts/verify-pycaffe.sh`：pycaffe 镜像验证脚本（含导入、API 测试、LeNet 推理）
  - [x] 创建 `docker/modules/pycaffe/scripts/verify-parity.sh`：对标验证脚本，将 pycaffe 的 Net/Solver/coord_map/draw/io 行为与 `caffex/python/caffe/test/` 测试结果逐一比对
  - **验证**：在 WSL 中执行 `docker build -t caffe-cpu:pycaffe -f docker/modules/pycaffe/Dockerfile .`，构建成功

- [x] Task 4: 创建统一构建入口 Makefile
  - [x] 创建 `docker/modules/Makefile`：支持 `all`、`python-module`、`pycaffe`、`clean`、`analyze` 目标
  - [x] `analyze` 目标：执行项目复盘分析脚本
  - [x] `all` 目标：先执行 analyze，再按序构建 python-module → pycaffe
  - [x] 正确处理镜像间依赖关系（pycaffe 依赖 python-module）
  - **验证**：在 WSL 中执行 `make -C docker/modules all`，复盘分析输出 + 两个镜像按顺序构建成功

- [x] Task 5: 端到端验证
  - [x] 验证 python-module 镜像：启动容器，执行 `import caffe`、`from caffeproto import caffe_pb2`、`from operators.layers import L2Norm`
  - [x] 验证 python-module 镜像：运行 `caffe-slim/scripts/run_test.sh` 全部通过
  - [x] 验证 pycaffe 镜像：启动容器，执行 `import pycaffe`，验证 Net/TRAIN/TEST API
  - [x] 验证 pycaffe 镜像：运行 `verify-parity.sh`，确认测试结果与 caffex/python 测试对标一致
  - [x] 验证两个镜像的独立性和可移植性（互不依赖，可独立运行）
  - **验证**：所有验证脚本通过，两个镜像均可在 WSL Docker 环境中正常运行

# Task Dependencies
- Task 2 依赖 Task 1（需要目录结构）
- Task 3 依赖 Task 2（pycaffe 镜像以 python-module 镜像为基础，且需要 caffex/ 测试文件做对标）
- Task 4 依赖 Task 2、Task 3（Makefile 需要引用两个 Dockerfile）
- Task 5 依赖 Task 2、Task 3、Task 4（端到端验证需要所有镜像和构建入口）
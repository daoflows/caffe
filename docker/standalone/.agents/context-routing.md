# 上下文路由表（详细版）

> 本文件是 standalone 目录的任务类型→必读文件映射详细版。AGENTS.md 中的路由表是简版，本文件提供更细粒度的路由指引。

## 按任务类型路由

### 构建类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 构建 pycaffe 基础镜像 | `pycaffe/Dockerfile` + `pycaffe/README.md` + `pycaffe/CMakeLists.txt` | 4阶段构建：base-system → base-builder → caffe-builder → runtime；构建上下文为 `vendor/` |
| 构建 jupyter-ssh 镜像 | `pycaffe-jupyter-ssh/Dockerfile` + `pycaffe-jupyter-ssh/README.md` + `pycaffe-jupyter-ssh/entrypoint.sh` | 基于 pycaffe 构建层，额外安装 SSH/Jupyter/supervisord |
| 修改 Dockerfile | 对应 `Dockerfile` + 本文件 `build-constraints.md` | 必须遵守多阶段构建规范、基础镜像固定、零caffex依赖 |
| 新增 Docker 构建目标 | 参考现有 Dockerfile 结构 + `REGRESSION-TEST.md` | 需同步更新 REGRESSION-TEST.md 和 AGENTS.md 镜像清单 |

### 验证类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 修改 verify-pycaffe.sh | `pycaffe/scripts/verify-pycaffe.sh` | 区分 PASS/WARN/SKIP 级别；核心项必须 PASS，辅助项可 WARN |
| 修改 verify-parity.sh | `pycaffe/scripts/verify-parity.sh` | 独立版本不引用 caffex；仅做占位说明+调用 verify-pycaffe.sh |
| 修改 healthcheck.sh | `pycaffe-jupyter-ssh/scripts/healthcheck.sh` | 同时检测 SSH(22) 和 Jupyter(8888) 端口 |
| 运行回归测试 | `REGRESSION-TEST.md` | 5个阶段：源码检查→构建测试→功能测试→隔离性验证→Jupyter扩展测试 |

### 配置类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 修改 SSH 配置 | `pycaffe-jupyter-ssh/config/sshd_config` | ED25519优先、禁用root登录、非root用户builder |
| 修改 Jupyter 配置 | `pycaffe-jupyter-ssh/config/jupyter_notebook_config.py` | Token/Password认证、绑定0.0.0.0、CORS同源限制 |
| 修改 supervisord 配置 | `pycaffe-jupyter-ssh/config/supervisord.conf` + `config/supervisor/conf.d/` | 管理 jupyter + sshd 双服务，自动重启 |
| 修改 entrypoint.sh | `pycaffe-jupyter-ssh/entrypoint.sh` | 6步启动流程：密码设置→SSH key生成→Jupyter配置→权限设置→访问信息打印→supervisord启动 |

### 隔离性检查任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 检查caffex依赖 | `build-constraints.md` + `REGRESSION-TEST.md`（T1/T4阶段） | grep搜索caffex引用，排除注释说明性引用 |
| .dockerignore 检查 | `../../../.dockerignore`（vendor/.dockerignore） | 不得排除tvm-ffi/3rdparty/libbacktrace/整个目录 |
| 容器内caffex搜索 | `REGRESSION-TEST.md`（T4.1-T4.3） | 容器内find/grep搜索caffex文件和引用 |

### 运行类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 启动pycaffe容器 | 参考AGENTS.md构建与验证速查 | `docker run --rm caffe-cpu:standalone-pycaffe <command>` |
| 启动jupyter容器 | `pycaffe-jupyter-ssh/run.sh` + `pycaffe-jupyter-ssh/README.md` | 端口映射2222:22 + 8888:8888，设置USER_PASSWORD和JUPYTER_TOKEN |
| 进入容器调试 | AGENTS.md注意事项 | `docker exec -it <container> bash`；ENTRYPOINT为空可直接覆盖 |

## 关键文件定位速查

| 需要修改/查看的内容 | 文件路径 |
|-------------------|---------|
| PyCaffe 验证逻辑 | `pycaffe/scripts/verify-pycaffe.sh` |
| Parity 占位脚本 | `pycaffe/scripts/verify-parity.sh` |
| 多阶段构建定义(pycaffe) | `pycaffe/Dockerfile` |
| CMake 构建入口 | `pycaffe/CMakeLists.txt` |
| Jupyter+SSH 启动流程 | `pycaffe-jupyter-ssh/entrypoint.sh` |
| 健康检查逻辑 | `pycaffe-jupyter-ssh/scripts/healthcheck.sh` |
| 一键回归脚本 | `regression-test.sh`（由REGRESSION-TEST.md定义） |
| 完整回归测试文档 | `REGRESSION-TEST.md` |

## 向上回溯路径

当任务超出 standalone 目录范围时，按嵌套优先原则逐层回溯：

1. **caffe 框架源码分析** → `../../AGENTS.md`（caffe/ 入口，向上2层）→ `../../.agents/architecture-map.md`
2. **vendor 区域资产** → `../../../AGENTS.md`（vendor/ 入口，向上3层）
3. **tvm-ffi 构建问题** → `../../tvm-ffi/AGENTS.md`（caffe/ 的同级目录）
4. **SpecWeave 全局规范** → 通过 caffe/AGENTS.md → vendor/AGENTS.md → xuanspace/AGENTS.md 逐层回溯到 SpecWeave 根
5. **Docker 构建方法论** → SpecWeave `.agents/docs/retrospective/patterns/` 下的构建工程模式

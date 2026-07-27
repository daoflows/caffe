# 上下文路由表（详细版）

> 本文件是 origin 目录的任务类型→必读文件映射详细版。AGENTS.md 中的路由表是简版，本文件提供更细粒度的路由指引。

## 按任务类型路由

### 构建类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 构建 origin-runtime 镜像 | `build.sh` + `Dockerfile` + `build-constraints.md` | 4阶段构建：base-system→base-builder→builder→runtime；默认标签 `caffe-cpu:origin-runtime`；构建上下文为 `caffe/`（向上两层） |
| 构建 origin-jupyter 镜像 | `build.sh --jupyter` + `Dockerfile.jupyter-ssh` + `entrypoint-jupyter.sh` | 基于builder层，额外安装SSH/Jupyter/supervisord；标签 `caffe-cpu:origin-jupyter`；工作目录 `/workspace` |
| 一次性构建两个镜像 | `build.sh --all` | 先构建runtime成功后再构建jupyter；任一失败不阻断另一个，最后汇总 |
| 修改 Dockerfile | 对应 `Dockerfile` 或 `Dockerfile.jupyter-ssh` + `build-constraints.md` | 必须遵守多阶段构建规范、版本锁定约束、COPY路径相对性 |
| Makefile.config生成逻辑 | `scripts/generate-makefile-config.sh` | 自动检测HDF5/Boost/OpenBLAS/protobuf路径；生成Makefile.config供make使用 |
| 无缓存重建 | `build.sh --no-cache` | 约15-40分钟，建议使用 `--progress=plain` 查看详细日志 |
| 自定义构建参数 | `build.sh --build-arg KEY=VAL` | BUILDER_UID/BUILDER_GID/PYTHON_VERSION等 |

### 验证类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 修改 verify-caffe.sh | `scripts/verify-caffe.sh` + `build-constraints.md`（验证分级） | 12项检查：Python版本、numpy/scipy/protobuf导入、caffe导入、版本号、libcaffe.so、_caffe*.so、Blob创建、Blob数据读写、caffe_pb2、caffe命令行工具；颜色输出（PASS绿/FAIL红/WARN黄）；正确退出码 |
| 修改 healthcheck-caffe.sh | `scripts/healthcheck-caffe.sh` | Runtime镜像健康检查：验证Python可用、caffe可导入、libcaffe.so存在；间隔30s/超时10s/启动等待5s/重试3次 |
| 修改 healthcheck-jupyter.sh | `scripts/healthcheck-jupyter.sh` | Jupyter镜像健康检查：检测sshd进程+22端口、jupyter进程+8888端口（HTTP 200/302/401/403均视为正常） |
| protobuf版本验证 | `build-constraints.md`（版本锁定） | 必须为3.20.3；验证脚本中检查protobuf版本，4.x标记为FAIL |

### 运行类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 分发给用户运行（推荐） | `run-standalone.sh` + `USER_GUIDE.md` | **不挂载宿主机目录**；runtime模式交互bash或一次性命令；jupyter模式端口映射127.0.0.1:8888/2222 |
| 本地开发运行 | `run.sh` + `run-jupyter.sh` | 挂载宿主机目录，会覆盖镜像内产物；仅用于本地开发调试，不要用于分发 |
| 一次性命令执行（分发模式） | `run-standalone.sh runtime -- <command>` | 自动添加 `--rm`，命令结束后删除容器 |
| Jupyter服务启动（分发模式） | `run-standalone.sh jupyter` | 后台运行(-d)，启动后等待5秒显示访问信息；支持USER_PASSWORD/JUPYTER_TOKEN/GRANT_SUDO环境变量 |
| 查看Jupyter访问信息 | `docker logs caffe-jupyter` 或 `run-jupyter.sh status` | Token和密码在启动日志中打印 |
| 进入运行中容器调试 | `docker exec -it <container> bash` | runtime镜像默认用户builder，jupyter镜像默认用户caffe-origin |

### 分发类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 导出镜像tar文件 | `export.sh` | 默认导出两个镜像到 `dist/`；文件名含日期戳；支持 `--compress` gzip压缩；导出后验证文件存在、大小、manifest.json、SHA256校验和 |
| 用户加载镜像 | `load-and-verify.sh` + `USER_GUIDE.md` | 自动检测dist/下最新tar；使用 `--entrypoint verify-caffe.sh` 绕过jupyter entrypoint；加载后自动运行验证脚本 |
| 分发包组装 | `export.sh` + `USER_GUIDE.md` | dist/*.tar(.gz) + run-standalone.sh + load-and-verify.sh + USER_GUIDE.md |
| 用户使用文档 | `USER_GUIDE.md` | 面向非开发者；中文；避免内部术语；包含快速开始、详细使用、FAQ（9个问题） |

### 配置类任务（Jupyter镜像）

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 修改SSH配置 | `config/sshd_config` | ED25519优先、PermitRootLogin no、非root用户caffe-origin |
| 修改Jupyter配置 | `config/jupyter_notebook_config.py` | Token/Password认证、绑定0.0.0.0、CORS同源限制 |
| 修改supervisord配置 | `config/supervisord.conf` + `config/supervisor/conf.d/` | 管理jupyter+sshd双服务，autorestart=true |
| 修改entrypoint-jupyter.sh | `entrypoint-jupyter.sh` | 6步启动：密码设置→SSH key生成→Jupyter配置→权限→访问信息打印→supervisord启动 |
| 修改环境变量profile | `config/profile.d/caffe.sh` | 登录shell自动加载CAFFE_ROOT/PYTHONPATH/LD_LIBRARY_PATH |

### 文档类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 更新开发者文档 | `README.md` | 包含构建、运行、FAQ、与conda版本对比；保持原有内容，新增分发章节 |
| 更新用户指南 | `USER_GUIDE.md` | 面向非开发者；通俗易懂；命令可直接复制；FAQ≥8个问题 |
| 更新AI协作者入口 | `AGENTS.md`（本文件目录） | 修改后需同步更新.agents/下的相关规范 |
| 历史构建报告 | `BUILD_REPORT.md` | 记录过往构建验证结果，供参考 |

## 关键文件定位速查

| 需要修改/查看的内容 | 文件路径 |
|-------------------|---------|
| 构建参数与镜像标签 | `build.sh` |
| 多阶段构建定义(runtime) | `Dockerfile` |
| 多阶段构建定义(jupyter) | `Dockerfile.jupyter-ssh` |
| Caffe安装验证逻辑 | `scripts/verify-caffe.sh` |
| Runtime健康检查 | `scripts/healthcheck-caffe.sh` |
| Jupyter健康检查 | `scripts/healthcheck-jupyter.sh` |
| Makefile.config自动生成 | `scripts/generate-makefile-config.sh` |
| Jupyter入口启动流程 | `entrypoint-jupyter.sh` |
| 独立运行（分发用） | `run-standalone.sh` |
| 开发运行（挂载用） | `run.sh` / `run-jupyter.sh` |
| 镜像导出 | `export.sh` |
| 镜像加载验证 | `load-and-verify.sh` |
| 用户使用指南 | `USER_GUIDE.md` |
| 开发者文档 | `README.md` |
| 构建约束规则 | `build-constraints.md` |

## 两套脚本对比速查

| 维度 | 开发脚本（run.sh/run-jupyter.sh） | 分发脚本（run-standalone.sh） |
|------|-------------------------------|---------------------------|
| 用途 | 本地开发调试 | 分发给最终用户 |
| 宿主机挂载 | **是**（-v挂载caffex目录） | **否**（无任何-v参数） |
| 镜像内产物 | 被宿主机目录覆盖 | 使用镜像内置产物 |
| 适合场景 | 修改源码后快速测试 | 用户直接使用，无需源码 |
| caffe是否可用 | 需要先make pycaffe编译 | 开箱即用 |
| 分发支持 | 不适合 | 配合export.sh/load-and-verify.sh使用 |

## 向上回溯路径

当任务超出 origin 目录范围时，按嵌套优先原则逐层回溯：

1. **caffex源码分析** → `../../AGENTS.md`（caffe/ 入口，向上2层）→ `../../.agents/architecture-map.md`
2. **caffe-slim对比** → `../standalone/AGENTS.md`（docker/standalone/ 同级目录）
3. **vendor 区域资产** → `../../../AGENTS.md`（vendor/ 入口，向上3层）
4. **SpecWeave全局规范** → 通过 caffe/AGENTS.md → vendor/AGENTS.md → xuanspace/AGENTS.md 逐层回溯到 SpecWeave 根
5. **Docker构建方法论** → SpecWeave `.agents/docs/retrospective/patterns/` 下的构建工程模式

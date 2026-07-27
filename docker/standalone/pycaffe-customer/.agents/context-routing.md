# 上下文路由表（详细版）

> 本文件是 pycaffe-customer 目录的任务类型→必读文件映射详细版。AGENTS.md 中的路由表是简版，本文件提供更细粒度的路由指引。

## 按任务类型路由

### 构建类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 构建客户镜像（标准模式） | `Dockerfile` + `build.sh` + `build-constraints.md` | 4阶段构建：base-system → base-builder → caffe-builder → customer-runtime；构建上下文为 `vendor/` |
| 构建客户镜像（国内模式） | `Dockerfile` + `build.sh --china` + `build-constraints.md` | APT使用北外源，PyPI使用清华源；适用于中国大陆用户 |
| 修改 Dockerfile | 对应 `Dockerfile` + 本文件 `build-constraints.md` | 必须遵守多阶段构建规范、基础镜像固定、零caffex依赖、客户交付要求 |
| 新增/修改示例模型 | `Dockerfile`（COPY示例部分） | ResNet-50示例位于 `/opt/caffe-examples/`，infer.py 推理脚本 |

### 配置类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 修改 SSH 配置 | `config/sshd_config` | ED25519优先、禁用root登录、非root用户builder、每次启动重新生成主机密钥 |
| 修改 Jupyter 配置 | `config/jupyter_notebook_config.py` | Token/Password认证、绑定0.0.0.0、CORS同源限制 |
| 修改 supervisord 配置 | `config/supervisord.conf` + `config/supervisor/conf.d/` | 管理 jupyter + sshd 双服务，自动重启 |
| 修改 entrypoint.sh | `entrypoint.sh` | 6步启动流程：密码设置→SSH key生成→Jupyter配置→权限设置→访问信息打印→supervisord启动 |
| 修改环境变量 | `Dockerfile`（ENV部分） + `entrypoint.sh` | USER_PASSWORD、JUPYTER_TOKEN、DISABLE_SSH、GRANT_SUDO、TZ等 |

### 验证类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 修改 caffe-verify | `scripts/caffe-verify` | 7项必须PASS：pycaffe导入、版本、Net类、LeNet推理、Jupyter、SSH、ResNet50推理 |
| 修改 healthcheck.sh | `scripts/healthcheck.sh` | 同时检测 SSH(22) 和 Jupyter(8888) 端口 |
| 运行自验证 | `README.md`（验证安装章节） | `docker exec caffe caffe-verify` |

### 分发类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 导出分发包 | `export.sh` | 生成 tar（或 tar.gz）+ sha256 校验和；支持自定义版本标签和输出目录 |
| 修改 build.sh | `build.sh` | 支持 --china、-t 标签、--no-cache 等参数；调用 docker build |
| 修改 export.sh | `export.sh` | 支持 -z 压缩、-t 标签、-o 输出目录、--version 版本号；生成sha256 |

### 文档类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 修改客户使用文档 | `README.md`（中文用户指南） | 面向最终客户，步骤清晰，中文表述，代码示例可直接复制 |
| 更新构建文档 | `AGENTS.md` + `.agents/build-constraints.md` | 面向AI协作者和分发者，记录约束和规则 |
| 添加故障排查指南 | `README.md`（故障排查章节） | 常见问题：容器无法启动、Jupyter无法连接、SSH被拒绝、内存不足等 |

### 运行类任务

| 任务 | 必读文件 | 关键要点 |
|------|---------|---------|
| 启动容器（基础模式） | `README.md`（快速开始章节） | `docker run -d -p 8888:8888 -p 2222:22 caffe-cpu:customer` |
| 启动容器（自定义凭据） | `README.md`（运行容器章节） | -e USER_PASSWORD 和 -e JUPYTER_TOKEN |
| 启动容器（禁用SSH） | `README.md`（运行容器章节） | -e DISABLE_SSH=yes |
| 挂载工作目录 | `README.md`（运行容器章节） | -v /local/path:/workspace/user-data |
| 进入容器调试 | `README.md`（容器管理章节） | `docker exec -it caffe bash`；root用户加 `-u root` |
| 查看日志 | `README.md`（查看日志章节） | `docker logs caffe` 或 `docker logs -f caffe` |

## 关键文件定位速查

| 需要修改/查看的内容 | 文件路径 |
|-------------------|---------|
| 多阶段构建定义 | `Dockerfile` |
| 构建辅助脚本 | `build.sh` |
| 导出分发脚本 | `export.sh` |
| 容器启动流程 | `entrypoint.sh` |
| 自验证脚本 | `scripts/caffe-verify` |
| 健康检查逻辑 | `scripts/healthcheck.sh` |
| SSH服务配置 | `config/sshd_config` |
| Jupyter配置 | `config/jupyter_notebook_config.py` |
| supervisord主配置 | `config/supervisord.conf` |
| Jupyter进程配置 | `config/supervisor/conf.d/jupyter.conf` |
| SSH进程配置 | `config/supervisor/conf.d/sshd.conf` |
| Docker构建忽略规则 | `Dockerfile.dockerignore` |
| 中文用户指南 | `README.md` |
| 构建约束规则 | `.agents/build-constraints.md` |

## 向上回溯路径

当任务超出 pycaffe-customer 目录范围时，按嵌套优先原则逐层回溯：

1. **standalone 通用构建** → `../AGENTS.md`（standalone/ 入口，向上1层）→ `../.agents/build-constraints.md`
2. **caffe 框架源码分析** → `../../AGENTS.md`（caffe/ 入口，向上2层）→ `../../.agents/architecture-map.md`
3. **vendor 区域资产** → `../../../AGENTS.md`（vendor/ 入口，向上3层）
4. **tvm-ffi 构建问题** → `../../tvm-ffi/AGENTS.md`（caffe/ 的同级目录）
5. **SpecWeave 全局规范** → 通过 caffe/AGENTS.md → vendor/AGENTS.md → xuanspace/AGENTS.md 逐层回溯到 SpecWeave 根
6. **Docker 构建方法论** → SpecWeave `.agents/docs/retrospective/patterns/` 下的构建工程模式
7. **客户分发最佳实践** → 参考本目录 `build-constraints.md` 中的客户交付规范

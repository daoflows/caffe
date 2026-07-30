# caffe-ffi 迁移收尾与文档演进 - The Implementation Plan (Decomposed and Prioritized Task List)

## [ ] Task 1: 更新 README.md 三层架构概览表和模块详解中的路径引用
- **Priority**: high
- **Depends On**: None
- **Description**:
  - 更新三层架构概览表中 caffe-ffi 行，标注「已迁移至 libs/caffe-ffi（独立库）」
  - 更新 caffe-ffi 模块详解章节中的安装路径说明，将 `cd caffe-ffi` 等命令指向新路径
  - 更新「环境准备与安装」章节中的 conda 环境文件路径和 cd 命令路径
  - 确保所有代码块中的路径正确
- **Acceptance Criteria Addressed**: [AC-1, AC-5]
- **Test Requirements**:
  - `programmatic` TR-1.1: grep 验证 README.md 中不再有以 `caffe-ffi/` 开头的相对路径引用（仅允许在「架构演进历程」章节中作为历史提及）
  - `programmatic` TR-1.2: 验证更新后的路径 `../../libs/caffe-ffi/environment.yml` 指向实际存在的文件
  - `human-judgement` TR-1.3: 安装说明章节的命令用户可以直接复制执行，路径正确
- **Notes**: 环境准备章节的路径是从 vendor/caffe/ 出发的相对路径

## [ ] Task 2: 更新 README.md Protobuf代码生成和目录结构章节
- **Priority**: high
- **Depends On**: [Task 1]
- **Description**:
  - 更新「Protobuf代码生成」章节中 protoc 命令的 `--python_out` 路径，从 `caffe-ffi/python/...` 改为 `../../libs/caffe-ffi/python/...`
  - 更新目录结构树，移除 caffe-ffi/ 目录条目，替换为说明注释指向 libs/caffe-ffi
  - 更新参考资料链接中的 caffe-ffi 文档路径
  - 更新示例代码路径说明
- **Acceptance Criteria Addressed**: [AC-1, AC-5]
- **Test Requirements**:
  - `programmatic` TR-2.1: protoc 命令中的 --python_out 路径指向有效目录
  - `programmatic` TR-2.2: 目录结构章节不再列出 caffe-ffi/ 作为当前目录的子目录
  - `programmatic` TR-2.3: `caffe-ffi/docs/OPTIMIZATION_REPORT.md` 链接更新为 `../../libs/caffe-ffi/docs/OPTIMIZATION_REPORT.md` 且文件存在
  - `programmatic` TR-2.4: `caffe-ffi/examples/` 路径更新为 `../../libs/caffe-ffi/examples/` 且目录存在

## [ ] Task 3: 新增「架构演进历程」章节
- **Priority**: high
- **Depends On**: [Task 2]
- **Description**:
  - 在 README.md 中「三层架构概览」之后新增「架构演进历程」章节
  - 采用时间线或表格形式描述四个阶段：
    1. 阶段一：caffex - BVLC Caffe原始fork（基础参考）
    2. 阶段二：caffe-slim - CPU精简推理版（移除GPU，现代化构建）
    3. 阶段三：caffe-ffi (vendor内) - TVM FFI现代绑定孵化（双类模型、零拷贝、类型异常）
    4. 阶段四：caffe-ffi (libs) - 独立库成熟（20+层、conda打包、Docker环境、独立AGENTS.md）
  - 每个阶段包含：定位、关键特性、时间/版本、与下一阶段的关系
- **Acceptance Criteria Addressed**: [AC-2, AC-5]
- **Test Requirements**:
  - `human-judgement` TR-3.1: 四个阶段描述清晰，演进逻辑连贯（为什么需要下一阶段）
  - `human-judgement` TR-3.2: 每个阶段有关键特性和定位说明
  - `programmatic` TR-3.3: 章节标题层级正确（## 级别，与其他章节一致）
  - `programmatic` TR-3.4: 无HTML实体转义错误，无emoji符号
- **Notes**: 演进叙事应该说明"为什么"：为什么需要从caffex到caffe-slim，为什么需要caffe-ffi，为什么要提升到libs独立库

## [ ] Task 4: 最终路径扫描与格式验证
- **Priority**: high
- **Depends On**: [Task 3]
- **Description**:
  - 全面扫描 README.md，确保所有 caffe-ffi 相关路径正确
  - 检查是否有遗漏的 `caffe-ffi/` 开头的相对路径
  - 验证所有更新后的相对路径确实指向存在的文件/目录
  - 检查Markdown格式：表格语法、标题层级、代码块标记
  - 检查无HTML实体转义（&gt;=等）、无emoji符号
- **Acceptance Criteria Addressed**: [AC-1, AC-5]
- **Test Requirements**:
  - `programmatic` TR-4.1: grep -n "caffe-ffi/" README.md 结果中，所有非「架构演进历程」历史提及的路径都以 `../../libs/caffe-ffi/` 开头
  - `programmatic` TR-4.2: 无 `&gt;=` / `&lt;` 等HTML实体
  - `programmatic` TR-4.3: 无emoji符号（✅/❌等）
  - `human-judgement` TR-4.4: 整体文档阅读流畅，格式一致

## [ ] Task 5: 删除 vendor/caffe/caffe-ffi/ 残留目录
- **Priority**: high
- **Depends On**: [Task 4]
- **Description**:
  - 使用 `git rm -r caffe-ffi/` 从vendor/caffe/子模块中删除旧目录
  - 确认删除后 libs/caffe-ffi/ 完好无损
  - 确认删除后 apps/caffe-ffi-jupyter/ 和 caffe-slim/ 不受影响
- **Acceptance Criteria Addressed**: [AC-3, AC-4]
- **Test Requirements**:
  - `programmatic` TR-5.1: `ls caffe-ffi/` 失败（目录不存在）
  - `programmatic` TR-5.2: `ls ../../libs/caffe-ffi/CMakeLists.txt` 成功（新目录完好）
  - `programmatic` TR-5.3: `ls ../../../../apps/caffe-ffi-jupyter/Dockerfile` 成功（Docker应用完好）
  - `programmatic` TR-5.4: `ls ../caffe-slim/CMakeLists.txt` 成功（caffe-slim完好）
  - `programmatic` TR-5.5: `git status --short` 显示 caffe-ffi/ 为 D（删除）状态
- **Notes**: 必须使用 git rm 而非直接删除文件系统，确保版本控制正确追踪删除操作

## [ ] Task 6: 删除后引用完整性验证
- **Priority**: high
- **Depends On**: [Task 5]
- **Description**:
  - 删除后全局扫描 vendor/caffe/ 目录（除已删除目录和历史spec外）是否还有引用 vendor/caffe/caffe-ffi/ 路径
  - 验证 README.md 中所有指向 ../../libs/caffe-ffi/ 的相对路径在删除旧目录后仍然有效
  - 验证 apps/caffe-ffi-jupyter/Dockerfile 中的 CAFFE_FFI_SRC_DIR 路径正确
- **Acceptance Criteria Addressed**: [AC-4]
- **Test Requirements**:
  - `programmatic` TR-6.1: grep -r "vendor/caffe/caffe-ffi" 在 vendor/caffe/ 下无结果（排除.trae/specs/历史文档和已删除的caffe-ffi/本身）
  - `programmatic` TR-6.2: 验证 README.md 中所有 ../../libs/caffe-ffi/ 开头的路径均有效（文件/目录存在）
  - `programmatic` TR-6.3: 验证 Dockerfile L325 `CAFFE_FFI_SRC_DIR="${CAFFE_FFI_SRC_DIR:-${SRC_ROOT}/projects/xuanspace/libs/caffe-ffi}"` 路径正确

## [ ] Task 7: 原子提交
- **Priority**: high
- **Depends On**: [Task 6]
- **Description**:
  - 使用 atomic-commit-cmd 执行原子提交
  - 提交类型：docs（因为主要是文档更新+旧目录清理）
  - 提交信息：docs(readme): 完成caffe-ffi迁移收尾——更新路径引用、新增演进历史、删除残留目录
  - 提交应包含：README.md的修改 + caffe-ffi/目录的删除
- **Acceptance Criteria Addressed**: [AC-6]
- **Test Requirements**:
  - `programmatic` TR-7.1: git log -1 显示提交信息符合 Conventional Commits 格式
  - `programmatic` TR-7.2: git status --short 显示工作区干净（无未提交变更）
  - `programmatic` TR-7.3: git show --stat HEAD 显示变更仅包含 README.md 和 caffe-ffi/ 删除
  - `programmatic` TR-7.4: 使用 git cat-file -p HEAD 验证中文commit message无乱码
- **Notes**: 这是vendor/caffe子模块内的提交，之后可能需要在xuanspace父仓库更新子模块引用

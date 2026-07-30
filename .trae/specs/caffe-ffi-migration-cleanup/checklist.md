# caffe-ffi 迁移收尾与文档演进 - Verification Checklist

## G1: 前置条件检查
- [x] libs/caffe-ffi/ 目录存在且完整（含 CMakeLists.txt、pyproject.toml、src/、python/、tests/）
- [x] apps/caffe-ffi-jupyter/Dockerfile 已引用 libs/caffe-ffi 路径（L14, L325）
- [x] caffe-slim/ 目录下无对 caffe-ffi/ 的引用
- [x] 确认无构建脚本或CI配置引用 vendor/caffe/caffe-ffi/ 旧路径
- [x] 已识别 README.md 中所有需要更新的路径位置（L141, L147, L349, L388-406, L452, L461-466）

## G2: README路径更新验证
- [ ] 三层架构概览表中 caffe-ffi 行已标注「已迁移至 libs/caffe-ffi（独立库）」
- [ ] 环境准备章节 conda env create 路径已更新为 ../../libs/caffe-ffi/environment.yml
- [ ] 环境准备章节 cd 命令已更新为 cd ../../libs/caffe-ffi
- [ ] caffe-ffi 模块详解中的路径说明已更新
- [ ] Protobuf代码生成章节 protoc 命令 --python_out 路径已更新
- [ ] 目录结构章节不再将 caffe-ffi/ 列为当前子目录，改为说明已迁移
- [ ] 参考资料中 caffe-ffi 优化报告链接已更新
- [ ] 示例代码章节中 examples/ 路径已更新
- [ ] grep 验证无残留以 `caffe-ffi/` 开头的错误相对路径（架构演进历史提及除外）
- [ ] 所有更新后的相对路径指向实际存在的文件/目录

## G3: 架构演进历史验证
- [ ] 「架构演进历程」章节已添加，位置在三层架构概览之后
- [ ] 包含四个阶段：caffex → caffe-slim → caffe-ffi(vendor内) → caffe-ffi(libs独立库)
- [ ] 每个阶段有定位说明
- [ ] 每个阶段有关键特性列举
- [ ] 演进逻辑清晰（说明为什么需要下一阶段）
- [ ] 章节标题层级正确（## 级别）
- [ ] 语言清晰，阅读流畅

## G4: 文档格式验证
- [ ] 无HTML实体转义错误（&gt;=、&lt; 等）
- [ ] 无emoji/Unicode特殊符号（✅、❌ 等）
- [ ] Markdown表格语法正确（列分隔符对齐）
- [ ] 标题层级一致（H1→H2→H3 无跳级）
- [ ] 代码块语法标记正确（bash/python）
- [ ] 相对路径链接格式正确（无file:///绝对路径）

## G5: 删除操作验证
- [ ] 使用 git rm -r caffe-ffi/ 执行删除（非直接rm）
- [ ] vendor/caffe/caffe-ffi/ 目录已不存在
- [ ] libs/caffe-ffi/ 目录完好无损
- [ ] caffe-slim/ 目录完好无损
- [ ] apps/caffe-ffi-jupyter/ 目录完好无损
- [ ] git status 显示 caffe-ffi/ 为 D（已删除）状态
- [ ] 删除后 grep -r "vendor/caffe/caffe-ffi" 在 vendor/caffe/ 下无结果（排除.trae/specs/历史文档）

## G6: 原子提交验证
- [ ] 提交信息遵循 Conventional Commits 格式（type(scope): subject）
- [ ] 提交类型为 docs
- [ ] 提交信息为中文，描述"为什么"
- [ ] 提交范围单一（仅README.md更新 + caffe-ffi/删除）
- [ ] git status --short 显示工作区干净
- [ ] git show --stat HEAD 变更文件列表正确
- [ ] git cat-file -p HEAD 验证中文无乱码
- [ ] 无敏感信息、临时文件、构建产物被提交

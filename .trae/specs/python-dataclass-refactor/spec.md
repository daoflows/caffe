# Python 目录 Dataclass 系统性重构 - Product Requirement Document

## Overview
- **Summary**: 对 `caffe-slim/` 目录下所有 Python 代码文件进行系统性重构，全面采用 Python 3.14+ dataclass 特性。将合适的类转换为数据类，利用 `@dataclass` 装饰器优化类定义，合理使用 `field()` 函数配置字段属性（默认值、类型提示、比较规则、初始化行为等），同时保留原有功能逻辑，提高代码可读性和维护性，符合 PEP 8 编码规范。
- **Purpose**: 现代化 Python 代码结构，利用 dataclass 减少样板代码（`__init__`、`__repr__`、`__eq__` 等），提高类型安全性，使数据结构定义更清晰。
- **Target Users**: PyCaffe 框架开发者、维护者、贡献者

## Goals
- 将所有纯数据类转换为 `@dataclass`，包括 `Top` 等简单数据结构
- 为 `Transformer` 和 `DataProcessor` 提取独立的配置 dataclass
- 为日志记录、计时统计、张量健康检查创建专用 dataclass
- 使用 `field()` 正确配置字段属性（default_factory、compare、init、repr 等）
- 使用 Python 3.14+ 特性（如 `slots=True`、`kw_only=True` 等适用场景）
- 保持 100% 向后兼容，所有现有功能和 API 不变
- 编写完整的单元测试验证重构正确性
- 提供重构前后代码对比文档
- 符合 PEP 8 编码规范

## Non-Goals (Out of Scope)
- 不修改 `caffex/` 目录下的原始 C++/Python 代码
- 不改变任何公共 API 签名或行为
- 不重构继承自 C++ 扩展类（如 Net、Classifier、Detector 的核心继承关系）
- 不重构使用 `__getattr__`/`__setattr__` 动态魔法方法的类（NetSpec、Layers、Parameters）
- 不修改 protobuf 生成的代码（caffe_pb2.py）
- 不添加新功能，仅重构现有代码结构

## Background & Context
- 项目已部分使用 dataclass：`BatchNormParams`、`ScaleParams`、`Conv2D`、`ConvTranspose2D`、`L2Norm` 已使用 `@dataclass`
- Python 版本要求：3.14 及以上，可使用最新 dataclass 特性
- 现有代码存在大量样板 `__init__` 方法，主要用于属性赋值
- 日志计时、张量统计等结构化数据目前使用普通 dict，可改为类型安全的 dataclass
- 项目已有 Docker 测试环境，可用于验证重构正确性

## Functional Requirements
- **FR-1**: `Top` 类（net_spec.py）必须转换为 `@dataclass`，保留 `fn` 和 `n` 字段
- **FR-2**: 为 `Transformer` 创建 `TransformerConfig` dataclass，封装 transpose、channel_swap、raw_scale、mean、input_scale 等配置
- **FR-3**: 为 `DataProcessor` 创建 `DataProcessorConfig` dataclass，封装 transformer、input_blob、json_log 配置
- **FR-4**: 创建 `TimingStats` dataclass 封装预处理各阶段计时信息
- **FR-5**: 创建 `TensorStats` dataclass 封装张量统计信息（shape、min/max/mean/std、per-channel stats）
- **FR-6**: 创建 `ValueHealthWarning` dataclass 封装值健康检查警告
- **FR-7**: 创建 `PreprocessResult` dataclass 封装预处理结果（数据 + 计时 + 统计）
- **FR-8**: 重构现有 dataclass（BatchNormParams、ScaleParams、Conv2D、ConvTranspose2D、L2Norm），正确使用 `field()` 配置
- **FR-9**: 适用场景使用 `slots=True` 优化内存占用
- **FR-10**: 适用场景使用 `kw_only=True` 强制关键字参数提高 API 清晰度
- **FR-11**: 使用 `field(default_factory=...)` 处理可变默认值（list、dict、np.ndarray）
- **FR-12**: 使用 `field(compare=False)` 标记不参与相等比较的字段
- **FR-13**: 使用 `field(repr=False)` 标记不需要在 repr 中显示的大字段（如 numpy 数组）

## Non-Functional Requirements
- **NFR-1**: 所有重构后代码必须通过现有单元测试，功能 100% 兼容
- **NFR-2**: 代码符合 PEP 8 规范（行宽、命名、导入顺序）
- **NFR-3**: 所有公共类和方法必须有完整类型提示
- **NFR-4**: 重构后代码行数应减少（样板代码消除）
- **NFR-5**: 性能不下降（dataclass 初始化开销可忽略）
- **NFR-6**: 所有 dataclass 使用 `frozen=True` 仅在真正不可变数据场景中使用
- **NFR-7**: 文档字符串保留并更新

## Constraints
- **Technical**: Python 3.14+，必须兼容现有 numpy、tvm、protobuf 依赖
- **Business**: 不破坏现有 API，所有现有测试必须通过
- **Dependencies**: numpy, tvm, protobuf, opencv-python/skimage（可选）

## Assumptions
- Python 3.14 环境可用，支持所有 dataclass 高级特性
- 现有 Docker 测试环境可以用于验证
- 不修改 caffex/ 下的代码
- protobuf 生成代码保持原样
- 向后兼容性是最高优先级

## Acceptance Criteria

### AC-1: Top 类成功转换为 dataclass
- **Given**: net_spec.py 中的 Top 类
- **When**: 重构完成
- **Then**: Top 使用 @dataclass 装饰器，fn 和 n 字段正确定义，所有现有方法（to_proto, _to_proto）正常工作
- **Verification**: `programmatic`
- **Notes**: Top 类的行为必须与重构前完全一致

### AC-2: Transformer 配置提取为 TransformerConfig
- **Given**: io.py 中的 Transformer 类
- **When**: 重构完成
- **Then**: TransformerConfig 作为独立 dataclass 存在，Transformer 使用该配置，所有 set_* 方法正常工作
- **Verification**: `programmatic`

### AC-3: DataProcessor 配置提取为 DataProcessorConfig
- **Given**: io.py 中的 DataProcessor 类
- **When**: 重构完成
- **Then**: DataProcessorConfig 作为独立 dataclass 存在，DataProcessor 使用该配置
- **Verification**: `programmatic`

### AC-4: 日志/计时/统计结构改为 dataclass
- **Given**: io.py 中使用 dict 存储 timing、stats、warnings
- **When**: 重构完成
- **Then**: TimingStats、TensorStats、ValueHealthWarning、PreprocessResult 等 dataclass 被使用，类型安全
- **Verification**: `programmatic` + `human-judgment`

### AC-5: 现有 dataclass 正确使用 field() 配置
- **Given**: BatchNormParams、ScaleParams、Conv2D、ConvTranspose2D、L2Norm
- **When**: 重构完成
- **Then**: numpy 数组字段使用 field(repr=False)，可变默认值使用 default_factory，比较字段正确配置
- **Verification**: `programmatic` + `human-judgment`

### AC-6: 所有现有单元测试通过
- **Given**: 现有测试套件
- **When**: 重构后运行测试
- **Then**: 所有测试通过，无失败、无错误
- **Verification**: `programmatic`

### AC-7: 新增单元测试覆盖 dataclass 行为
- **Given**: 重构后的代码
- **When**: 运行新增测试
- **Then**: dataclass 的初始化、比较、repr、不可变性（如适用）等行为正确
- **Verification**: `programmatic`

### AC-8: 代码符合 PEP 8 规范
- **Given**: 重构后的所有 Python 文件
- **When**: 代码审查
- **Then**: 无 PEP 8 违规（使用 lint 工具验证）
- **Verification**: `programmatic` + `human-judgment`

### AC-9: 提供重构前后对比文档
- **Given**: 重构完成
- **When**: 文档审查
- **Then**: 存在对比文档，展示关键类重构前后的代码差异和改进点
- **Verification**: `human-judgment`

### AC-10: Docker 环境完整验证通过
- **Given**: Docker 镜像 caffe-cpu:python-module 和 caffe-cpu:pycaffe
- **When**: 在容器中运行所有测试
- **Then**: 所有验证脚本通过，功能完整
- **Verification**: `programmatic`

## Open Questions
- [ ] 是否需要为 Conv2D 等 TVM 模块类启用 slots=True？（需评估 TVM nn.Module 的兼容性）
- [ ] 重构后是否需要更新版本号或 CHANGELOG？
- [ ] 对比文档格式偏好：Markdown 表格 vs 逐文件对比？

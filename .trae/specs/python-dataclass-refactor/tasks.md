# Python 目录 Dataclass 系统性重构 - The Implementation Plan (Decomposed and Prioritized Task List)

## [x] Task 1: 创建基础数据类定义（新文件：python/pycaffe/python/pycaffe/dataclasses.py）
- **Priority**: high
- **Depends On**: None
- **Description**: 
  - 创建新的 dataclasses.py 模块，集中存放所有通用 dataclass 定义
  - 定义 `TransformerConfig`：封装 transpose、channel_swap、raw_scale、mean、input_scale 配置
  - 定义 `DataProcessorConfig`：封装 input_blob、json_log 配置
  - 定义 `TimingStats`：封装 cast、resize、transforms、contiguous、total 等各阶段计时
  - 定义 `PerImageTiming`：封装单张图像处理计时
  - 定义 `BatchTimingStats`：封装批处理计时（含 per_image 统计）
  - 定义 `ChannelStats`：封装单通道统计（channel, min, max, mean, std）
  - 定义 `TensorStats`：封装全局+per-channel张量统计
  - 定义 `ValueHealthWarning`：封装 NaN/Inf/high_zero/all_non_positive 警告
  - 定义 `PreprocessResult`：封装 data + timing + stats
  - 定义 `ImageLoadInfo`：封装图像加载信息（index, load_ms, shape）
  - 定义 `BatchInputInfo`：封装批处理输入信息（count, files, arrays, image_loads, unique_shapes, mixed_shapes）
  - 使用 `field(default_factory=...)` 处理可变默认值
  - 对 numpy 数组等大字段使用 `field(repr=False)`
  - 添加完整类型提示和文档字符串
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-1.1: 所有 dataclass 可以正确初始化，无报错
  - `programmatic` TR-1.2: 可变默认字段正确隔离（不同实例不共享）
  - `programmatic` TR-1.3: repr 输出合理（大数组不显示）
  - `human-judgement` TR-1.4: 类型提示完整，符合 PEP 8
- **Notes**: 使用 slots=True 优化内存；frozen=True 仅用于真正不可变的数据

## [x] Task 2: 重构 net_spec.py 中的 Top 类为 dataclass
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 将 Top 类转换为 @dataclass
  - 保留 fn 和 n 字段，使用正确类型提示
  - 保留 to_proto() 和 _to_proto() 方法
  - 确保与 Function、NetSpec 等类的交互不变
  - 注意：dataclass 与普通类继承的兼容性
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-2.1: Top 实例可以正常创建
  - `programmatic` TR-2.2: Top.to_proto() 正常工作
  - `programmatic` TR-2.3: 与 Function、NetSpec 的集成正常
  - `programmatic` TR-2.4: 网络构建功能不受影响
- **Notes**: Top 是纯数据载体，是 dataclass 的理想候选；保持 slots=True

## [x] Task 3: 重构 caffeproto/caffe_fuse.py 中的现有 dataclass
- **Priority**: medium
- **Depends On**: Task 1
- **Description**: 
  - 更新 BatchNormParams：为 numpy 数组字段添加 field(repr=False)，启用 slots=True
  - 更新 ScaleParams：为 numpy 数组字段添加 field(repr=False)，启用 slots=True
  - 验证 get_bn_params() 和 get_scale_params() 工厂函数正常工作
  - 验证 fuse_layers() 和 fuse_network() 正常工作
  - 添加必要的 __post_init__ 进行数据验证
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `programmatic` TR-3.1: BatchNormParams 和 ScaleParams 正确初始化
  - `programmatic` TR-3.2: numpy 数组字段在 repr 中被省略
  - `programmatic` TR-3.3: get_bn_params/get_scale_params 返回正确类型
  - `programmatic` TR-3.4: 网络融合功能正常

## [x] Task 4: 重构 operators/layers.py 中的 TVM 层类
- **Priority**: medium
- **Depends On**: Task 1
- **Description**: 
  - 注意：这些类继承自 tvm.relax.testing.nn.Module，需评估 dataclass 兼容性
  - 若兼容：更新 Conv2D、ConvTranspose2D、L2Norm 使用 field() 正确配置
  - 为 numpy/TVM 参数字段添加 field(repr=False, compare=False)
  - 为列表默认值使用 field(default_factory=list)
  - 若不兼容 nn.Module：保留现有 @dataclass 装饰器但优化 field 配置
  - 保持 __post_init__ 逻辑不变
  - 保持 forward() 方法不变
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `programmatic` TR-4.1: Conv2D 可以正常实例化
  - `programmatic` TR-4.2: ConvTranspose2D 可以正常实例化
  - `programmatic` TR-4.3: L2Norm 可以正常实例化
  - `programmatic` TR-4.4: forward() 方法正常工作（若 TVM 环境可用）
- **Notes**: 如果 TVM nn.Module 与 dataclass 有冲突，保持最小改动，仅优化 field 配置

## [x] Task 5: 重构 io.py 中的 Transformer 类，使用 TransformerConfig
- **Priority**: high
- **Depends On**: Task 1, Task 2
- **Description**: 
  - 导入 TransformerConfig from dataclasses
  - 修改 Transformer.__init__ 使用 TransformerConfig 存储配置
  - 保留 inputs 参数（必填，不是配置）
  - 保留 _pipeline_cache 作为运行时状态（不放入 config）
  - 重构 set_transpose/set_channel_swap/set_raw_scale/set_mean/set_input_scale 更新 config
  - 重构 _build_pipeline 使用 config 中的值
  - 保持 preprocess/preprocess_batch/deprocess 方法逻辑不变
  - 保持向后兼容：所有公共 API 签名不变
  - Transformer 本身是否转为 dataclass 需评估：有大量行为方法，可能保持普通类但内部使用 config dataclass
- **Acceptance Criteria Addressed**: AC-2, AC-4
- **Test Requirements**:
  - `programmatic` TR-5.1: Transformer 可以用 inputs dict 正常初始化
  - `programmatic` TR-5.2: set_transpose/set_channel_swap/set_raw_scale/set_mean/set_input_scale 正常工作
  - `programmatic` TR-5.3: preprocess() 单张图像处理正确
  - `programmatic` TR-5.4: preprocess_batch() 批处理正确
  - `programmatic` TR-5.5: deprocess() 逆处理正确
  - `programmatic` TR-5.6: pipeline 缓存机制正常工作

## [x] Task 6: 重构 io.py 中的 DataProcessor 类，使用 DataProcessorConfig 和结构化 dataclass
- **Priority**: high
- **Depends On**: Task 5
- **Description**: 
  - 导入 DataProcessorConfig、TimingStats、TensorStats、ValueHealthWarning、PreprocessResult 等
  - 修改 DataProcessor.__init__ 使用 DataProcessorConfig
  - 重构 _collect_tensor_stats_dict 返回 TensorStats 而非 dict
  - 重构 _collect_value_health 返回 list[ValueHealthWarning] 而非 list[dict]
  - 重构 prepare_single 返回 PreprocessResult（或保持返回 ndarray，内部使用 dataclass）
  - 重构 prepare_batch 使用结构化 dataclass 记录 timing/stats
  - 重构 prepare_oversample 使用结构化 dataclass
  - 保持 get_json_records/flush_json_log 正常工作
  - 保持向后兼容：所有公共 API 签名和返回值类型不变
  - 内部日志记录使用结构化 dataclass，最终序列化为 JSON 时格式不变
- **Acceptance Criteria Addressed**: AC-3, AC-4
- **Test Requirements**:
  - `programmatic` TR-6.1: DataProcessor 可以正常初始化
  - `programmatic` TR-6.2: prepare_single() 处理 ndarray 输入正确
  - `programmatic` TR-6.3: prepare_single() 处理文件路径输入正确
  - `programmatic` TR-6.4: prepare_batch() 处理混合输入（文件+数组）正确
  - `programmatic` TR-6.5: prepare_oversample() 10-crop 采样正确
  - `programmatic` TR-6.6: JSON 日志记录正常（启用时）
  - `programmatic` TR-6.7: 张量统计和值健康检查正常工作
  - `programmatic` TR-6.8: 计时信息准确收集

## [x] Task 7: 更新模块 __init__.py 导出，确保公共 API 不变
- **Priority**: medium
- **Depends On**: Task 1-6
- **Description**: 
  - 更新 pycaffe/__init__.py 导出必要的类（如果需要）
  - 确保所有现有导入路径仍然有效
  - dataclasses 模块中的类可选择导出，但主要供内部使用
  - 检查并修复所有相对导入
  - 确保 caffeproto 和 operators 模块的导出正确
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-3
- **Test Requirements**:
  - `programmatic` TR-7.1: `from pycaffe import io` 正常
  - `programmatic` TR-7.2: `from pycaffe.io import Transformer, DataProcessor` 正常
  - `programmatic` TR-7.3: `from pycaffe import net_spec` 正常
  - `programmatic` TR-7.4: `from caffeproto import caffe_fuse` 正常
  - `programmatic` TR-7.5: `from operators import layers` 正常

## [x] Task 8: 编写单元测试（新文件：python/tests/test_dataclasses.py）
- **Priority**: high
- **Depends On**: Task 1-7
- **Description**: 
  - 创建 test_dataclasses.py
  - 测试所有基础 dataclass 的初始化、默认值、repr、eq
  - 测试可变默认字段不共享
  - 测试 TransformerConfig 的字段正确性
  - 测试 DataProcessorConfig 的字段正确性
  - 测试 TimingStats/TensorStats/ValueHealthWarning 等的创建和使用
  - 测试 Top dataclass 与 net_spec 的集成
  - 测试 Transformer 使用 TransformerConfig 的行为
  - 测试 DataProcessor 使用结构化 dataclass 的行为
  - 重构后所有现有测试仍然通过
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-8.1: 所有新增测试通过
  - `programmatic` TR-8.2: 现有 test_inference.py 通过
  - `programmatic` TR-8.3: 现有 test_l2norm.py 通过（若存在）
  - `human-judgement` TR-8.4: 测试覆盖所有新 dataclass
- **Notes**: 测试应独立于 TVM/GPU 要求，使用 mock 或纯 numpy 测试

## [x] Task 9: PEP 8 合规性检查与修复
- **Priority**: medium
- **Depends On**: Task 1-8
- **Description**: 
  - 运行 pycodestyle/flake8 检查所有修改过的 Python 文件
  - 修复行宽问题（最大 119 字符，遵循现有项目风格）
  - 修复导入顺序问题（stdlib → third-party → local）
  - 修复命名规范问题
  - 确保文档字符串格式一致
  - 确保类型提示完整
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `programmatic` TR-9.1: pycodestyle 检查无错误（忽略现有代码的历史遗留问题）
  - `human-judgement` TR-9.2: 代码风格与项目现有风格一致

## [x] Task 10: Docker 环境完整验证
- **Priority**: high
- **Depends On**: Task 1-9
- **Description**: 
  - 构建更新后的 Docker 镜像（如需要）
  - 在 caffe-cpu:python-module 容器中运行所有测试
  - 在 caffe-cpu:pycaffe 容器中运行所有测试
  - 运行 verify-python-module.sh 验证脚本
  - 运行 verify-pycaffe.sh 验证脚本
  - 运行 verify-parity.sh 验证两个模块一致性
  - 记录测试结果
- **Acceptance Criteria Addressed**: AC-6, AC-10
- **Test Requirements**:
  - `programmatic` TR-10.1: python-module 容器所有测试通过
  - `programmatic` TR-10.2: pycaffe 容器所有测试通过
  - `programmatic` TR-10.3: parity 验证通过（两个模块行为一致）
  - `programmatic` TR-10.4: 无 segfault 或崩溃
- **Notes**: 使用 WSL 环境运行 Docker；不需要重建镜像如果代码目录是挂载的

## [x] Task 11: 编写重构前后对比文档
- **Priority**: medium
- **Depends On**: Task 1-10
- **Description**: 
  - 创建 refactor-comparison.md 文档
  - 包含每个重构类的前后代码对比（关键片段）
  - 说明每个 dataclass 的设计决策
  - 统计样板代码减少行数
  - 列出 field() 配置的使用场景和原因
  - 说明向后兼容性保证
  - 提供使用示例
- **Acceptance Criteria Addressed**: AC-9
- **Test Requirements**:
  - `human-judgement` TR-11.1: 文档清晰展示重构前后差异
  - `human-judgement` TR-11.2: 设计决策有合理解释
  - `human-judgement` TR-11.3: 包含具体代码示例

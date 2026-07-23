# 最小化 caffe protobuf 库

参考：[caffe-proto](https://github.com/daoflows/caffe)

创建最小化的 caffe protobuf 库文件。

## 安装依赖

1. 在 [conda 环境中安装 protobuf](https://xinetzone.github.io/tao/fields/protobuf/installation.html)。

```bash
conda create -n proto-env python=3.14
conda activate proto-env
conda install -c conda-forge libprotobuf
pip install protobuf -i https://pypi.tuna.tsinghua.edu.cn/simple
```

2. 安装 cmake、conan 和 ninja

```bash
conda install -c conda-forge ninja
pip install cmake -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install conan -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 生成 Python 代码

### 方式一：快速生成（推荐）

使用内置的 Python 生成脚本（自动检查版本一致性）：

```bash
python python/scripts/gen_proto.py
```

脚本会自动：查找 protoc → 检查版本一致性 → 编译 proto → 验证生成代码。

### 方式二：CMake 构建

```bash
# 检测 Conan 环境
conan profile detect --force
# 安装依赖
conan install . -c tools.cmake.cmaketoolchain:generator=Ninja --build=missing
# 配置 CMake
cmake --preset conan-release
# 构建项目
cmake --build --preset conan-release
```

### 方式三：直接调用 protoc

```bash
protoc --proto_path=python/protos --python_out=python/caffeproto python/protos/caffe.proto
```

## 添加新算子（四步法）

在 caffeproto 中添加新的 Caffe 层/算子支持，遵循以下四步流程：

### 步骤1：扩展 Protocol Buffer 协议

编辑 `python/protos/caffe.proto`：

1. 在文件末尾（PReLUParameter 之后）添加新的 `XxxParameter` 消息定义
2. 在 `LayerParameter` 消息中添加 `optional XxxParameter xxx_param = <next_id>;`
3. 更新 `LayerParameter` 注释中的 `next available layer-specific ID`（当前最大ID+1）
4. 字段编号严格递增，不与现有字段冲突

参考 NormalizeParameter 添加示例（搜索 `norm_param` 查看上下文）。

### 步骤2：重新生成 Python 代码

```bash
python python/scripts/gen_proto.py
```

脚本会自动检查版本一致性并生成代码到 `python/caffeproto/caffe_pb2.py` 和 `python/protos/caffe_pb2.py`。

### 步骤3：实现 TVM Relax 模块

在 `python/operators/layers.py` 中添加继承 `nn.Module` 的算子类：

```python
@dataclass
class NewLayer(nn.Module):
    # 参数字段（与 XxxParameter 对应）
    param1: int
    param2: float = default_value
    name: str = "new_layer"
    define_subroutine: bool = True

    def __post_init__(self):
        # 创建 nn.Parameter（如有权重/偏置/scale 等可学习参数）
        self.weight = nn.Parameter(weight_shape, name="weight")

    def forward(self, x: relax.Expr) -> relax.Var:
        # 使用 tvm.relax.op（_op）算子实现前向计算
        # 最后通过 nn.emit 返回结果
        out = ...
        return nn.emit(out, self.name)
```

代码风格参考已有的 `Conv2D`、`ConvTranspose2D`、`L2Norm` 类。

### 步骤4：添加测试

在 `python/` 目录下创建测试文件（参考 `tests/test_l2norm.py`），包含：

1. **protobuf 序列化/反序列化测试**：验证 XxxParameter 字段正确序列化往返
2. **text_format 解析测试**：验证 prototxt 文本格式正确解析
3. **默认值测试**：验证字段默认值正确
4. **TVM 数值正确性测试**（有 TVM 环境时）：用 numpy 参考实现对比 TVM 输出（atol=1e-5）
5. **caffe_utils 兼容性测试**：验证 `unity_struct` 处理新层类型无报错

### 注意事项

- `caffe_utils.py` 是类型无关的（只对 Input 层特殊处理），新层无需修改 caffe_utils
- 不要在 `caffe_utils.py` 中添加特定层类型的分支逻辑
- `repeated scalar` 字段用 `append()`，`repeated message` 字段用 `add()`
- `text_format.Parse` 解析 `LayerParameter` 时不需要外层 `layer {}` 包装
- 确保 protoc 版本与 Python protobuf runtime 兼容（运行 `python python/scripts/gen_proto.py` 会自动检查）
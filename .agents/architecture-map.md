# Caffe 核心架构索引（Architecture Map）

> 8大核心组件的文件定位、职责与关键机制，用于快速建立全局认知。

## 架构分层图

```
┌─────────────────────────────────────────────────┐
│                   Solver                        │  优化策略/训练循环
│  solver.hpp / sgd_solvers.hpp                   │  Solve()→Step()→ApplyUpdate()
├─────────────────────────────────────────────────┤
│                    Net                          │  DAG计算图
│  net.hpp                                        │  Init()→Forward()/Backward()
├─────────────────────────────────────────────────┤
│                  Layers                         │  计算单元（75+种实现）
│  layer.hpp / layers/*.hpp+cpp+cu                │  SetUp()→Forward()→Backward()
├─────────────────────────────────────────────────┤
│                   Blob                          │  多维张量（data+diff对偶）
│  blob.hpp                                       │  data_/diff_ → SyncedMemory
├─────────────────────────────────────────────────┤
│               SyncedMemory                      │  CPU/GPU透明内存
│  syncedmem.hpp                                  │  四状态机 + 懒同步
└─────────────────────────────────────────────────┘
      ▲                    ▲
      │                    │
LayerRegistry          Caffe Singleton    ← 横切关注点
layer_factory.hpp       common.hpp         ← 工厂注册/全局状态
      ▲                    ▲
┌─────┴────────────────────┴─────────────┐
│           Protocol Buffers              │  声明式配置
│  src/caffe/proto/caffe.proto            │  NetParameter/LayerParameter/...
└─────────────────────────────────────────┘
```

## 8大核心组件

### 1. SyncedMemory — CPU/GPU 透明内存同步

| 属性 | 值 |
|------|-----|
| 头文件 | `caffex/include/caffe/syncedmem.hpp` |
| 核心机制 | 四状态机（UNINITIALIZED → HEAD_AT_CPU / HEAD_AT_GPU / SYNCED） |
| 关键方法 | `cpu_data()`、`gpu_data()`（只读，不改变head）；`mutable_cpu_data()`、`mutable_gpu_data()`（写，标记脏位） |
| 设计模式 | 延迟同步（Lazy Sync）——只在访问过期端时才触发拷贝 |
| 优化 | Pinned Memory（cudaMallocHost）加速DMA传输 |

```
访问器语义：
  cpu_data() / gpu_data()      → const void*，只读，不改变head状态
  mutable_cpu_data()/mutable_gpu_data() → void*，写访问，head标记为对应设备
  私有 to_cpu()/to_gpu()       → 实际执行跨设备拷贝
```

### 2. Blob — 多维张量与值/梯度对偶存储

| 属性 | 值 |
|------|-----|
| 头文件 | `caffex/include/caffe/blob.hpp` |
| 实现 | `caffex/src/caffe/blob.cpp` |
| 核心成员 | `shared_ptr<SyncedMemory> data_`（前向值）；`shared_ptr<SyncedMemory> diff_`（反向梯度）；`vector<int> shape_`（维度） |
| 关键方法 | `Reshape()`（动态调整形状，只增容不释放）；`Update()`（data -= diff × lr）；`FromProto()/ToProto()`（序列化）；`ShareData()/ShareDiff()`（零拷贝共享） |
| 数学辅助 | `asum_data()/sumsq_data()/scale_data()`等范数计算 |
| CPU/GPU访问 | `cpu_data()/gpu_data()/mutable_cpu_data()/mutable_gpu_data()` 转发到内部SyncedMemory |

**核心洞察**：data_/diff_ 的对偶设计完美契合深度学习中"值-梯度"对称的计算需求——前向传播读/写data_，反向传播读top diff、写bottom diff和param diff。

### 3. Layer — 计算单元的NVI契约设计

| 属性 | 值 |
|------|-----|
| 头文件 | `caffex/include/caffe/layer.hpp` |
| 实现 | `caffex/src/caffe/layer.cpp` |
| 设计模式 | NVI（Non-Virtual Interface）模板方法 |
| 生命周期 | `SetUp()`（非虚模板方法）：CheckBlobCounts → LayerSetUp → Reshape → SetLossWeights |
| 计算流程 | `Forward()`（非虚）：Reshape检查 → switch(mode) → Forward_cpu/gpu → loss加权；`Backward()`（非虚）：switch(mode) → Backward_cpu/gpu |
| 子类扩展点 | `LayerSetUp()`（虚，层特定初始化）；`Reshape()`（纯虚，输出形状推断）；`Forward_cpu()`（纯虚）；`Forward_gpu()`（虚，默认fallback到CPU）；`Backward_cpu()`（纯虚）；`Backward_gpu()`（虚，默认fallback到CPU） |
| 契约函数 | `ExactNumBottomBlobs()/MinBottomBlobs()/MaxBottomBlobs()/ExactNumTopBlobs()/...`（虚函数声明IO契约） |
| 参数管理 | `vector<shared_ptr<Blob<Dtype>>> blobs_`（可学习参数）；`vector<bool> param_propagate_down_`（每个参数是否需要梯度） |
| loss机制 | `SetLossWeights()`将loss_weight写入top[0]->diff，作为反向传播的梯度起点 |

**核心洞察**：NVI模式将"公共接口不变性"（SetUp流程、设备分派、loss加权）固化在非虚模板方法中，将"具体计算逻辑"下放给虚函数，子类只需实现cpu/gpu版本的核心算法。

### 4. Net — 声明式DAG计算图

| 属性 | 值 |
|------|-----|
| 头文件 | `caffex/include/caffe/net.hpp` |
| 实现 | `caffex/src/caffe/net.cpp` |
| 核心成员 | `vector<shared_ptr<Layer<Dtype>>> layers_`；`vector<shared_ptr<Blob<Dtype>>> blobs_`；`vector<vector<Blob*>> bottom_vecs_/top_vecs_` |
| DAG构建 | `Init()`：从NetParameter解析层定义→AppendTop/AppendBottom建立blob映射→available_blobs追踪中间结果→自动处理扇入扇出 |
| 执行顺序 | `ForwardFromTo(start,end)` 按拓扑序执行Forward；`BackwardFromTo(start,end)` 逆序执行Backward |
| 权重共享 | `ShareWeights()`通过ParamSpec.name实现跨层参数共享（底层共享SyncedMemory） |
| 回调钩子 | `before_forward_/after_forward_/before_backward_/after_backward_` Callback注入点 |
| 预训练加载 | `CopyTrainedLayersFrom()`从.caffemodel加载权重用于微调 |
| 参数收集 | `params_`收集所有可学习参数；`learnable_params_`过滤需更新的参数；`params_lr_/params_weight_decay_`存储超参数 |

### 5. Solver — 优化器与训练循环

| 属性 | 值 |
|------|-----|
| 头文件 | `caffex/include/caffe/solver.hpp` |
| 实现 | `caffex/src/caffe/solver.cpp` |
| 具体求解器 | `sgd_solvers.hpp`（SGD/AdaGrad/RMSProp/AdaDelta/Adam/Nesterov/...） |
| 训练循环 | `Solve()`→循环调用`Step(iters)`→每次迭代：ForwardBackward → ApplyUpdate |
| 扩展点 | `ApplyUpdate()`（纯虚）——不同优化算法的核心更新逻辑 |
| 快照机制 | `Snapshot()`保存.caffemodel（权重）+.solverstate（求解器状态）；`Restore()`从快照恢复续训 |
| 优雅中断 | `SolverAction::STOP/SNAPSHOT`通过action_request_function_支持外部请求（Ctrl+C） |
| 双网管理 | `net_`（训练网络）；`test_nets_`（多个测试网络）；`TestAll()/Test()`定期评估 |
| 回调 | `on_start()/on_gradients_ready()`支持学习率调度、日志等扩展 |
| 损失平滑 | `smoothed_loss_`指数移动平均稳定显示 |

### 6. LayerRegistry — 自注册工厂

| 属性 | 值 |
|------|-----|
| 头文件 | `caffex/include/caffe/layer_factory.hpp` |
| 实现 | `caffex/src/caffe/layer_factory.cpp` |
| 设计模式 | 自注册工厂（Self-Registering Factory）+ 宏注册 |
| 核心机制 | `Registry()`返回函数内静态`map<string, Creator>`单例；`LayerRegisterer`构造函数调用AddCreator()；全局静态变量在main()前构造→自动注册 |
| 注册宏 | `REGISTER_LAYER_CLASS(name)` 一行完成注册（自动生成Creator函数，为float/double分别实例化）；`REGISTER_LAYER_CREATOR(name, creator)` 自定义工厂函数（如cuDNN后端选择） |
| 工厂方法 | `CreateLayer(param)` 根据LayerParameter.type查找Creator并构造实例，类型不存在时输出已知类型列表 |

**核心洞察**：宏+静态构造的组合实现了开闭原则——添加新Layer只需写一个.cpp文件加一行`REGISTER_LAYER_CLASS(MyLayer)`，无需修改任何工厂代码。

### 7. Caffe 单例 — 全局运行时环境

| 属性 | 值 |
|------|-----|
| 头文件 | `caffex/include/caffe/common.hpp` |
| 实现 | `caffex/src/caffe/common.cpp` |
| 模式 | 线程局部单例（Thread-Local Singleton） |
| Brew模式 | `set_mode(Caffe::CPU/GPU)` 全局设备切换；`mode()`查询当前模式 |
| CUDA句柄 | `cublas_handle()/curand_generator()` 延迟初始化CUDA资源 |
| RNG | 类Boost的随机数生成器 |
| 并行训练 | `solver_rank()/solver_count()/multiprocess()` 多GPU/多进程支持 |
| 全局宏 | `NOT_IMPLEMENTED`（GPU未实现时友好报错）；`CUDA_CHECK`（CUDA错误检查） |

### 8. Protocol Buffers — 声明式配置层

| 属性 | 值 |
|------|-----|
| Proto文件 | `caffex/src/caffe/proto/caffe.proto` |
| 核心消息 | `BlobProto`（序列化张量）；`LayerParameter`（层配置）；`NetParameter`（网络配置）；`SolverParameter`（求解器配置）；`ParamSpec`（参数超参数）；`NetState`/`NetStateRule`（条件包含） |
| Phase枚举 | `TRAIN`/`TEST` 控制不同阶段的网络结构 |
| 扩展字段 | 每个Layer通过`xxx_param`扩展字段定义自己的配置（如ConvolutionParameter、PoolingParameter） |
| V1LayerParameter | 旧版兼容（已废弃但保留升级路径） |

**核心洞察**：Proto配置将"网络结构声明"与"计算实现"完全分离——用户用.prototxt文本文件描述网络，框架自动解析构建DAG，无需写C++代码。这是声明式编程的典型应用。

## 数据流三阶段

### 前向传播（Forward Pass）

```
Net::Forward()
  → FOR i = 0..layers_.size()-1:
      layers_[i]->Forward(bottom_vecs_[i], top_vecs_[i])
        → Reshape(bottom, top)  // 检查/推断形状
        → switch(Caffe::mode()) { CPU/GPU分派 }
        → Forward_cpu/gpu(bottom, top)  // 读bottom->data，计算写top->data
        → 对loss层：loss += weighted_loss_by_loss_weight
  → 返回总loss
```

### 反向传播（Backward Pass）

```
Net::Backward()
  → FOR i = layers_.size()-1..0:
      layers_[i]->Backward(top_vecs_[i], propagate_down, bottom_vecs_[i])
        → switch(Caffe::mode()) { CPU/GPU分派 }
        → Backward_cpu/gpu(top, propagate_down, bottom)
            // 读 top[*]->diff（上游梯度）
            // 计算写 bottom[*]->diff（传给下游的梯度，若propagate_down[j]）
            // 计算写 blobs_[*]->diff（参数梯度，用于后续更新）
```

梯度起点：`SetLossWeights()`将`loss_weight`（通常为1.0）写入`top[0]->diff_`，作为反向传播的种子梯度。

### 参数更新（Parameter Update）

```
Solver::Step(iter)
  → FOR each iteration:
      net_->ForwardBackward()  // Forward + Backward，计算所有diff
      ApplyUpdate()            // 虚函数，具体优化算法实现
        → net_->Update()
          → FOR each learnable param blob:
              blob->Update()  // data -= diff * lr（带动量/自适应学习率等变体）
```

## 设计模式索引

| 模式名称 | 应用位置 | 核心思想 |
|---------|---------|---------|
| 延迟同步状态机 | SyncedMemory | 脏位+按需同步，避免不必要的数据传输 |
| 自注册工厂注册表 | LayerRegistry/SolverRegistry | 宏+静态构造实现开闭原则 |
| 对偶存储双向计算 | Blob（data_/diff_） | 值/梯度双存储支撑前向/反向对称计算 |
| NVI契约生命周期 | Layer（SetUp/Forward/Backward模板方法） | 非虚接口固化流程，虚函数下放实现 |
| 声明式DAG组装 | Net+Proto | 文本描述结构，自动构建拓扑执行 |
| 单例模式 | Caffe类 | 线程局部单例持有全局运行时状态 |
| 策略模式 | Solver::ApplyUpdate | 不同优化算法替换更新策略 |
| RAII/智能指针 | 所有shared_ptr | Blob/Layer通过shared_ptr管理生命周期 |

## 相关资源

- **已有架构分析**：`../../.agents/docs/knowledge/learning/caffe-architecture-wiki/README.md`
- **核心架构思维导图**：同上文档中"Mermaid mindmap"章节
- **可复用模式库**：同上文档中"可复用架构模式"章节（5个跨领域模式）
- **对抗审查结论**：同上文档中"对抗审查"章节（历史局限 vs 永恒原则）

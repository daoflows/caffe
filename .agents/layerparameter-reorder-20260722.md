# LayerParameter 字段 ID 重排记录

> **日期**：2026-07-22
> **文件**：`caffex/src/caffe/proto/caffe.proto`
> **操作**：将 LayerParameter 的 50 个 layer-type-specific 字段按字段 ID 升序重排（100 → 149）

---

## 1. 重排后的完整定义

> 以下为 `caffe.proto` 中 LayerParameter message 的 layer-type-specific 字段部分（ID 100-149），不含注释。

```protobuf
message LayerParameter {
  optional string name = 1;       // the layer name
  optional string type = 2;       // the layer type
  repeated string bottom = 3;     // the name of each bottom blob
  repeated string top = 4;        // the name of each top blob

  optional Phase phase = 10;
  repeated float loss_weight = 5;
  repeated ParamSpec param = 6;
  repeated BlobProto blobs = 7;
  repeated bool propagate_down = 11;
  repeated NetStateRule include = 8;
  repeated NetStateRule exclude = 9;

  optional TransformationParameter transform_param = 100;
  optional LossParameter loss_param = 101;

  // Layer type-specific parameters (sorted by ID ascending)
  optional AccuracyParameter accuracy_param = 102;
  optional ArgMaxParameter argmax_param = 103;
  optional ConcatParameter concat_param = 104;
  optional ContrastiveLossParameter contrastive_loss_param = 105;
  optional ConvolutionParameter convolution_param = 106;
  optional DataParameter data_param = 107;
  optional DropoutParameter dropout_param = 108;
  optional DummyDataParameter dummy_data_param = 109;
  optional EltwiseParameter eltwise_param = 110;
  optional ExpParameter exp_param = 111;
  optional HDF5DataParameter hdf5_data_param = 112;
  optional HDF5OutputParameter hdf5_output_param = 113;
  optional HingeLossParameter hinge_loss_param = 114;
  optional ImageDataParameter image_data_param = 115;
  optional InfogainLossParameter infogain_loss_param = 116;
  optional InnerProductParameter inner_product_param = 117;
  optional LRNParameter lrn_param = 118;
  optional MemoryDataParameter memory_data_param = 119;
  optional MVNParameter mvn_param = 120;
  optional PoolingParameter pooling_param = 121;
  optional PowerParameter power_param = 122;
  optional ReLUParameter relu_param = 123;
  optional SigmoidParameter sigmoid_param = 124;
  optional SoftmaxParameter softmax_param = 125;
  optional SliceParameter slice_param = 126;
  optional TanHParameter tanh_param = 127;
  optional ThresholdParameter threshold_param = 128;
  optional WindowDataParameter window_data_param = 129;
  optional PythonParameter python_param = 130;
  optional PReLUParameter prelu_param = 131;
  optional SPPParameter spp_param = 132;
  optional ReshapeParameter reshape_param = 133;
  optional LogParameter log_param = 134;
  optional FlattenParameter flatten_param = 135;
  optional ReductionParameter reduction_param = 136;
  optional EmbedParameter embed_param = 137;
  optional TileParameter tile_param = 138;
  optional BatchNormParameter batch_norm_param = 139;
  optional ELUParameter elu_param = 140;
  optional BiasParameter bias_param = 141;
  optional ScaleParameter scale_param = 142;
  optional InputParameter input_param = 143;
  optional CropParameter crop_param = 144;
  optional ParameterParameter parameter_param = 145;
  optional RecurrentParameter recurrent_param = 146;
  optional SwishParameter swish_param = 147;
  optional ClipParameter clip_param = 148;
  optional NormalizeParameter norm_param = 149;
}
```

---

## 2. 变更对比

### 2.1 重排前（原始顺序）

```
ID 102: accuracy_param
ID 103: argmax_param
ID 139: batch_norm_param     ← 错位
ID 141: bias_param            ← 错位
ID 148: clip_param            ← 错位
ID 149: norm_param            ← 错位
ID 104: concat_param          ← 错位
ID 105: contrastive_loss_param
ID 106: convolution_param
ID 144: crop_param            ← 错位
ID 107: data_param            ← 错位
ID 108: dropout_param
ID 109: dummy_data_param
ID 110: eltwise_param
ID 140: elu_param             ← 错位
ID 137: embed_param           ← 错位
ID 111: exp_param             ← 错位
ID 135: flatten_param         ← 错位
ID 112: hdf5_data_param
ID 113: hdf5_output_param
ID 114: hinge_loss_param
ID 115: image_data_param
ID 116: infogain_loss_param
ID 117: inner_product_param
ID 143: input_param           ← 错位
ID 134: log_param             ← 错位
ID 118: lrn_param             ← 错位
ID 119: memory_data_param
ID 120: mvn_param
ID 145: parameter_param       ← 错位
ID 121: pooling_param         ← 错位
ID 122: power_param
ID 131: prelu_param           ← 错位
ID 130: python_param          ← 错位
ID 146: recurrent_param       ← 错位
ID 136: reduction_param       ← 错位
ID 123: relu_param            ← 错位
ID 133: reshape_param         ← 错位
ID 142: scale_param           ← 错位
ID 124: sigmoid_param
ID 125: softmax_param
ID 132: spp_param             ← 错位
ID 126: slice_param           ← 错位
ID 147: swish_param           ← 错位
ID 127: tanh_param
ID 128: threshold_param
ID 138: tile_param            ← 错位
ID 129: window_data_param
```

### 2.2 重排后（升序）

```
ID 102: accuracy_param
ID 103: argmax_param
ID 104: concat_param
ID 105: contrastive_loss_param
ID 106: convolution_param
ID 107: data_param
ID 108: dropout_param
ID 109: dummy_data_param
ID 110: eltwise_param
ID 111: exp_param
ID 112: hdf5_data_param
ID 113: hdf5_output_param
ID 114: hinge_loss_param
ID 115: image_data_param
ID 116: infogain_loss_param
ID 117: inner_product_param
ID 118: lrn_param
ID 119: memory_data_param
ID 120: mvn_param
ID 121: pooling_param
ID 122: power_param
ID 123: relu_param
ID 124: sigmoid_param
ID 125: softmax_param
ID 126: slice_param
ID 127: tanh_param
ID 128: threshold_param
ID 129: window_data_param
ID 130: python_param
ID 131: prelu_param
ID 132: spp_param
ID 133: reshape_param
ID 134: log_param
ID 135: flatten_param
ID 136: reduction_param
ID 137: embed_param
ID 138: tile_param
ID 139: batch_norm_param
ID 140: elu_param
ID 141: bias_param
ID 142: scale_param
ID 143: input_param
ID 144: crop_param
ID 145: parameter_param
ID 146: recurrent_param
ID 147: swish_param
ID 148: clip_param
ID 149: norm_param
```

---

## 3. 统计摘要

| 指标 | 值 |
|------|-----|
| 总字段数 | 50（ID 100-149） |
| 重排前错位字段数 | 48 |
| 重排后错位字段数 | 0 |
| 原始 BVLC 字段 | 28（ID 100-129） |
| 后续新增字段 | 22（ID 130-149） |
| 变更类型 | 纯排序变更，无字段增删，无 ID 变更 |

---

## 4. 影响分析

| 维度 | 影响 |
|------|------|
| 二进制兼容性 | 无影响 — protobuf 按 ID 序列化，与声明顺序无关 |
| JSON/text_format 兼容性 | 无影响 — 解析器按 ID 匹配，不依赖声明顺序 |
| 生成的代码 | 无影响 — protoc 按 ID 排序生成代码 |
| 可读性 | 提升 — 按 ID 升序排列，便于查找和比对 |
| 后续扩展 | 改善 — 新字段按 ID 150+ 追加，不再出现交错 |

---

*文档生成时间：2026-07-22*
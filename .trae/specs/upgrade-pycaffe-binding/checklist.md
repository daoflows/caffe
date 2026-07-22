# Checklist

- [x] NormalizeParameter 消息定义已添加到 caffe.proto（PReLUParameter 之后）
- [x] LayerParameter 中已添加 `optional NormalizeParameter norm_param = 149;`
- [x] LayerParameter 注释中 next available ID 已更新为 150
- [x] _caffe.cpp 中所有 `NULL` 已替换为 `nullptr`
- [x] _caffe.cpp 中虚函数已添加 `override` 关键字
- [x] _caffe.cpp 中 `const int` 已替换为 `constexpr`
- [x] _caffe.cpp 中不必要的 `NOLINT` 注释已清理
- [x] caffex/python/CMakeLists.txt 中已添加 `CXX_STANDARD 14` + `CXX_STANDARD_REQUIRED ON`
- [x] 代码风格与现有代码保持一致
- [x] 未引入新文件，仅修改现有文件
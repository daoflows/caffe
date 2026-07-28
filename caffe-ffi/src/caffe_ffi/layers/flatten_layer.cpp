#include "caffe_ffi/layers/flatten_layer.hpp"

#include <vector>

#include "caffe_ffi/fill.hpp"
#include "caffe_ffi/layer_factory.hpp"

namespace caffe_ffi {

void FlattenLayer::Reshape(const std::vector<Blob*>& bottom,
                            const std::vector<Blob*>& top) {
  TVM_FFI_ICHECK_NE(top[0], bottom[0]) << this->type() << " Layer does not allow in-place.";
  const int start_axis = bottom[0]->CanonicalAxisIndex(
      this->layer_param_.flatten_param().axis());
  int end_axis = bottom[0]->CanonicalAxisIndex(
      this->layer_param_.flatten_param().end_axis());
  std::vector<int64_t> top_shape;
  for (int i = 0; i < start_axis; ++i) {
    top_shape.push_back(bottom[0]->shape(i));
  }
  const int64_t flattened_dim = bottom[0]->count(start_axis, end_axis + 1);
  top_shape.push_back(flattened_dim);
  for (int i = end_axis + 1; i < bottom[0]->num_axes(); ++i) {
    top_shape.push_back(bottom[0]->shape(i));
  }
  top[0]->Reshape(top_shape);
  TVM_FFI_ICHECK_EQ(top[0]->count(), bottom[0]->count());
}

void FlattenLayer::Forward_cpu(const std::vector<Blob*>& bottom,
                                const std::vector<Blob*>& top) {
  caffe_copy_fp32(static_cast<size_t>(bottom[0]->count()),
                   bottom[0]->cpu_data(), top[0]->cpu_data());
}

REGISTER_LAYER_CLASS(Flatten);

}  // namespace caffe_ffi

#include "caffe_ffi/layers/bias_layer.hpp"

#include <vector>

#include <tvm/ffi/memory.h>

#include "caffe_ffi/fill.hpp"
#include "caffe_ffi/layer_factory.hpp"
#include "caffe_ffi/math_utils.hpp"

namespace caffe_ffi {

void BiasLayer::LayerSetUp(const std::vector<Blob*>& bottom,
                            const std::vector<Blob*>& top) {
  const caffe::BiasParameter& param = this->layer_param_.bias_param();
  axis_ = bottom[0]->CanonicalAxisIndex(param.axis());
  num_axes_ = param.num_axes();

  TVM_FFI_ICHECK_GE(num_axes_, 1) << "num_axes should be >= 1";
  TVM_FFI_ICHECK_LE(axis_ + num_axes_, bottom[0]->num_axes())
      << "axis + num_axes exceeds blob dimensions";

  if (bottom.size() == 1 && this->blobs_.size() == 0) {
    this->blobs_.resize(1);
    std::vector<int64_t> bias_shape;
    for (int i = 0; i < num_axes_; ++i) {
      bias_shape.push_back(bottom[0]->shape(axis_ + i));
    }
    this->blobs_[0] = make_object<Blob>(bias_shape);
    caffe_set_fp32(static_cast<size_t>(this->blobs_[0]->count()), 0.0f, this->blobs_[0]->cpu_data());
  }
  this->param_propagate_down_.resize(this->blobs_.size(), true);
}

void BiasLayer::Reshape(const std::vector<Blob*>& bottom,
                         const std::vector<Blob*>& top) {
  top[0]->ReshapeLike(*bottom[0]);
  outer_dim_ = static_cast<int>(bottom[0]->count(0, axis_));
  bias_dim_ = static_cast<int>((bottom.size() > 1) ? bottom[1]->count()
                               : this->blobs_[0]->count());
  inner_dim_ = static_cast<int>(bottom[0]->count(axis_ + num_axes_));

  int dim = bias_dim_;
  for (int i = 0; i < num_axes_; ++i) {
    TVM_FFI_ICHECK_EQ(bottom[0]->shape(axis_ + i), (bottom.size() > 1)
                 ? bottom[1]->shape(i) : this->blobs_[0]->shape(i))
        << "Dimensions mismatch for bias";
    dim /= static_cast<int>(bottom[0]->shape(axis_ + i));
  }
}

void BiasLayer::Forward_cpu(const std::vector<Blob*>& bottom,
                             const std::vector<Blob*>& top) {
  const float* bias_data = (bottom.size() > 1) ? bottom[1]->cpu_data()
                          : this->blobs_[0]->cpu_data();
  const float* bottom_data = bottom[0]->cpu_data();
  float* top_data = top[0]->cpu_data();
  const int count = static_cast<int>(bottom[0]->count());

  caffe_copy_fp32(static_cast<size_t>(count), bottom_data, top_data);

  for (int n = 0; n < outer_dim_; ++n) {
    for (int d = 0; d < bias_dim_; ++d) {
      const float bias = bias_data[d];
      for (int i = 0; i < inner_dim_; ++i) {
        const int idx = n * bias_dim_ * inner_dim_ + d * inner_dim_ + i;
        top_data[idx] += bias;
      }
    }
  }
}

REGISTER_LAYER_CLASS(Bias);

}  // namespace caffe_ffi

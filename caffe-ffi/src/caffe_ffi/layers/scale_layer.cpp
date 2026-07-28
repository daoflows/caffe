#include "caffe_ffi/layers/scale_layer.hpp"

#include <vector>

#include <tvm/ffi/memory.h>

#include "caffe_ffi/fill.hpp"
#include "caffe_ffi/layer_factory.hpp"
#include "caffe_ffi/math_utils.hpp"

namespace caffe_ffi {

void ScaleLayer::LayerSetUp(const std::vector<Blob*>& bottom,
                             const std::vector<Blob*>& top) {
  const caffe::ScaleParameter& param = this->layer_param_.scale_param();
  axis_ = bottom[0]->CanonicalAxisIndex(param.axis());
  num_axes_ = param.num_axes();
  bias_term_ = param.bias_term();

  TVM_FFI_ICHECK_GE(num_axes_, 1) << "num_axes should be >= 1";
  TVM_FFI_ICHECK_LE(axis_ + num_axes_, bottom[0]->num_axes())
      << "axis + num_axes exceeds blob dimensions";

  std::vector<int64_t> scale_shape;
  for (int i = 0; i < num_axes_; ++i) {
    scale_shape.push_back(bottom[0]->shape(axis_ + i));
  }
  const int64_t scale_dim = Count(ShapeView(scale_shape.data(), scale_shape.size()));

  if (bottom.size() == 1 && this->blobs_.size() > 0) {
    TVM_FFI_ICHECK_GE(this->blobs_.size(), 1U);
    if (bias_term_) {
      TVM_FFI_ICHECK_EQ(this->blobs_.size(), 2U);
      TVM_FFI_ICHECK_EQ(this->blobs_[1]->count(), scale_dim);
    }
    TVM_FFI_ICHECK_EQ(this->blobs_[0]->count(), scale_dim);
  } else if (bottom.size() == 1) {
    if (bias_term_) {
      this->blobs_.resize(2);
    } else {
      this->blobs_.resize(1);
    }
    this->blobs_[0] = make_object<Blob>(scale_shape);
    caffe_set_fp32(static_cast<size_t>(this->blobs_[0]->count()), 1.0f, this->blobs_[0]->cpu_data());
    if (bias_term_) {
      this->blobs_[1] = make_object<Blob>(scale_shape);
      caffe_set_fp32(static_cast<size_t>(this->blobs_[1]->count()), 0.0f, this->blobs_[1]->cpu_data());
    }
  }
  this->param_propagate_down_.resize(this->blobs_.size(), true);
}

void ScaleLayer::Reshape(const std::vector<Blob*>& bottom,
                          const std::vector<Blob*>& top) {
  top[0]->ReshapeLike(*bottom[0]);
  outer_dim_ = static_cast<int>(bottom[0]->count(0, axis_));
  scale_dim_ = static_cast<int>((bottom.size() > 1) ? bottom[1]->count()
                               : this->blobs_[0]->count());
  inner_dim_ = static_cast<int>(bottom[0]->count(axis_ + num_axes_));
}

void ScaleLayer::Forward_cpu(const std::vector<Blob*>& bottom,
                              const std::vector<Blob*>& top) {
  const float* bottom_data = bottom[0]->cpu_data();
  float* top_data = top[0]->cpu_data();
  const float* scale_data = (bottom.size() > 1) ? bottom[1]->cpu_data()
                           : this->blobs_[0]->cpu_data();
  const int count = static_cast<int>(bottom[0]->count());

  caffe_copy_fp32(static_cast<size_t>(count), bottom_data, top_data);

  for (int n = 0; n < outer_dim_; ++n) {
    for (int d = 0; d < scale_dim_; ++d) {
      const float factor = scale_data[d];
      for (int i = 0; i < inner_dim_; ++i) {
        const int idx = n * scale_dim_ * inner_dim_ + d * inner_dim_ + i;
        top_data[idx] *= factor;
      }
    }
  }

  if (bias_term_ && this->blobs_.size() > 1) {
    const float* bias_data = this->blobs_[1]->cpu_data();
    for (int n = 0; n < outer_dim_; ++n) {
      for (int d = 0; d < scale_dim_; ++d) {
        const float bias = bias_data[d];
        for (int i = 0; i < inner_dim_; ++i) {
          const int idx = n * scale_dim_ * inner_dim_ + d * inner_dim_ + i;
          top_data[idx] += bias;
        }
      }
    }
  }
}

REGISTER_LAYER_CLASS(Scale);

}  // namespace caffe_ffi

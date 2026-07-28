#include "caffe_ffi/layers/elu_layer.hpp"

#include <algorithm>
#include <cmath>
#include <vector>

#include "caffe_ffi/layer_factory.hpp"

namespace caffe_ffi {

void ELULayer::LayerSetUp(const std::vector<Blob*>& bottom,
                           const std::vector<Blob*>& top) {
  alpha_ = this->layer_param_.elu_param().alpha();
}

void ELULayer::Forward_cpu(const std::vector<Blob*>& bottom,
                            const std::vector<Blob*>& top) {
  const float* bottom_data = bottom[0]->cpu_data();
  float* top_data = top[0]->cpu_data();
  const int64_t count = bottom[0]->count();
  for (int64_t i = 0; i < count; ++i) {
    if (bottom_data[i] >= 0.0f) {
      top_data[i] = bottom_data[i];
    } else {
      top_data[i] = alpha_ * (std::exp(bottom_data[i]) - 1.0f);
    }
  }
}

REGISTER_LAYER_CLASS(ELU);

}  // namespace caffe_ffi

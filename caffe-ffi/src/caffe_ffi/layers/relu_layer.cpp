#include "caffe_ffi/layers/relu_layer.hpp"

#include <algorithm>
#include <vector>

#include "caffe_ffi/layer_factory.hpp"

namespace caffe_ffi {

void ReLULayer::Forward_cpu(const std::vector<Blob*>& bottom,
                            const std::vector<Blob*>& top) {
  const float* bottom_data = bottom[0]->cpu_data();
  float* top_data = top[0]->cpu_data();
  const int64_t count = bottom[0]->count();
  float negative_slope = this->layer_param_.relu_param().negative_slope();
  for (int64_t i = 0; i < count; ++i) {
    top_data[i] = std::max(bottom_data[i], 0.0f)
        + negative_slope * std::min(bottom_data[i], 0.0f);
  }
}

REGISTER_LAYER_CLASS(ReLU);

}  // namespace caffe_ffi

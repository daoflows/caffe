#include "caffe_ffi/layers/sigmoid_layer.hpp"

#include <algorithm>
#include <cmath>
#include <vector>

#include "caffe_ffi/layer_factory.hpp"

namespace caffe_ffi {

void SigmoidLayer::Forward_cpu(const std::vector<Blob*>& bottom,
                               const std::vector<Blob*>& top) {
  const float* bottom_data = bottom[0]->cpu_data();
  float* top_data = top[0]->cpu_data();
  const int64_t count = bottom[0]->count();
  for (int64_t i = 0; i < count; ++i) {
    top_data[i] = 1.0f / (1.0f + std::exp(-bottom_data[i]));
  }
}

REGISTER_LAYER_CLASS(Sigmoid);

}  // namespace caffe_ffi

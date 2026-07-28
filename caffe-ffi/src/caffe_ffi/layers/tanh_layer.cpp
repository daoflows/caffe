#include "caffe_ffi/layers/tanh_layer.hpp"

#include <algorithm>
#include <cmath>
#include <vector>

#include "caffe_ffi/layer_factory.hpp"

namespace caffe_ffi {

void TanHLayer::Forward_cpu(const std::vector<Blob*>& bottom,
                            const std::vector<Blob*>& top) {
  const float* bottom_data = bottom[0]->cpu_data();
  float* top_data = top[0]->cpu_data();
  const int64_t count = bottom[0]->count();
  for (int64_t i = 0; i < count; ++i) {
    top_data[i] = std::tanh(bottom_data[i]);
  }
}

REGISTER_LAYER_CLASS(TanH);

}  // namespace caffe_ffi

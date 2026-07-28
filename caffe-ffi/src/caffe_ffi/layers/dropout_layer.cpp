#include "caffe_ffi/layers/dropout_layer.hpp"

#include <algorithm>
#include <cstring>
#include <vector>

#include "caffe_ffi/layer_factory.hpp"

namespace caffe_ffi {

void DropoutLayer::Forward_cpu(const std::vector<Blob*>& bottom,
                                const std::vector<Blob*>& top) {
  const float* bottom_data = bottom[0]->cpu_data();
  float* top_data = top[0]->cpu_data();
  const int64_t count = bottom[0]->count();
  if (bottom[0] != top[0]) {
    std::memcpy(top_data, bottom_data, sizeof(float) * count);
  }
}

REGISTER_LAYER_CLASS(Dropout);

}  // namespace caffe_ffi

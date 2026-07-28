#include "caffe_ffi/layers/accuracy_layer.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <utility>
#include <vector>

#include "caffe_ffi/fill.hpp"
#include "caffe_ffi/layer_factory.hpp"
#include "caffe_ffi/math_utils.hpp"

namespace caffe_ffi {

void AccuracyLayer::LayerSetUp(const std::vector<Blob*>& bottom,
                                const std::vector<Blob*>& top) {
  const caffe::AccuracyParameter& param = this->layer_param_.accuracy_param();
  top_k_ = static_cast<int>(param.top_k());
  has_ignore_label_ = param.has_ignore_label();
  if (has_ignore_label_) {
    ignore_label_ = param.ignore_label();
  }
}

void AccuracyLayer::Reshape(const std::vector<Blob*>& bottom,
                             const std::vector<Blob*>& top) {
  label_axis_ = bottom[0]->CanonicalAxisIndex(
      this->layer_param_.accuracy_param().axis());
  outer_num_ = static_cast<int>(bottom[0]->count(0, label_axis_));
  inner_num_ = static_cast<int>(bottom[0]->count(label_axis_ + 1));

  int dim = static_cast<int>(bottom[0]->count() / outer_num_);
  TVM_FFI_ICHECK_LE(top_k_, dim) << "top_k must be <= number of classes.";

  std::vector<int64_t> top_shape = {1};
  top[0]->Reshape(top_shape);
  if (top.size() > 1) {
    std::vector<int64_t> per_class_shape = {static_cast<int64_t>(bottom[0]->shape(label_axis_))};
    top[1]->Reshape(per_class_shape);
    caffe_set_fp32(static_cast<size_t>(top[1]->count()), 0.0f, top[1]->cpu_data());
  }
}

void AccuracyLayer::Forward_cpu(const std::vector<Blob*>& bottom,
                                 const std::vector<Blob*>& top) {
  const float* bottom_data = bottom[0]->cpu_data();
  const float* bottom_label = bottom[1]->cpu_data();
  float* top_data = top[0]->cpu_data();

  int channels = static_cast<int>(bottom[0]->shape(label_axis_));
  int dim = channels * inner_num_;
  int count = 0;
  float accuracy = 0.0f;

  std::vector<std::pair<float, int>> bottom_data_vector(channels);

  for (int i = 0; i < outer_num_; ++i) {
    for (int j = 0; j < inner_num_; ++j) {
      const int label_value = static_cast<int>(bottom_label[i * inner_num_ + j]);
      if (has_ignore_label_ && label_value == ignore_label_) {
        continue;
      }
      TVM_FFI_ICHECK_GE(label_value, 0);
      TVM_FFI_ICHECK_LT(label_value, channels);

      for (int k = 0; k < channels; ++k) {
        bottom_data_vector[k] = std::make_pair(
            bottom_data[i * dim + k * inner_num_ + j], k);
      }
      std::partial_sort(
          bottom_data_vector.begin(),
          bottom_data_vector.begin() + top_k_,
          bottom_data_vector.end(),
          std::greater<std::pair<float, int>>());

      for (int k = 0; k < top_k_; ++k) {
        if (bottom_data_vector[k].second == label_value) {
          ++accuracy;
          break;
        }
      }
      ++count;
    }
  }

  top_data[0] = (count > 0) ? accuracy / count : 0.0f;
}

REGISTER_LAYER_CLASS(Accuracy);

}  // namespace caffe_ffi

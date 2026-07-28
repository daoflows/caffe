#include "caffe_ffi/layers/reshape_layer.hpp"

#include <algorithm>
#include <cstring>
#include <vector>

#include "caffe_ffi/layer_factory.hpp"
#include "caffe_ffi/math_utils.hpp"

namespace caffe_ffi {

void ReshapeLayer::LayerSetUp(const std::vector<Blob*>& bottom,
                               const std::vector<Blob*>& top) {
  const caffe::ReshapeParameter& param = this->layer_param_.reshape_param();
  axis_ = param.axis();
  num_axes_ = param.num_axes();
}

void ReshapeLayer::Reshape(const std::vector<Blob*>& bottom,
                            const std::vector<Blob*>& top) {
  const Blob* input_blob = bottom[0];
  const int input_num_axes = input_blob->num_axes();
  const caffe::ReshapeParameter& param = this->layer_param_.reshape_param();
  const caffe::BlobShape& shape = param.shape();
  const int shape_dim_size = shape.dim_size();

  int start_axis = CanonicalAxisIndex(axis_, input_num_axes + 1);
  TVM_FFI_ICHECK_GE(start_axis, 0);
  TVM_FFI_ICHECK_LE(start_axis, input_num_axes);

  int end_axis;
  if (num_axes_ == -1) {
    end_axis = input_num_axes;
  } else {
    end_axis = start_axis + num_axes_;
    end_axis = std::min(end_axis, input_num_axes);
  }
  TVM_FFI_ICHECK_GE(end_axis, start_axis);

  std::vector<int64_t> top_shape;
  for (int i = 0; i < start_axis; ++i) {
    top_shape.push_back(input_blob->shape(i));
  }

  int inferred_axis = -1;
  int64_t constant_count = 1;
  for (int i = 0; i < shape_dim_size; ++i) {
    int dim = static_cast<int>(shape.dim(i));
    if (dim == 0) {
      TVM_FFI_ICHECK_LT(start_axis + i, input_num_axes)
          << "dim=0 (copy axis) out of input bounds";
      top_shape.push_back(input_blob->shape(start_axis + i));
      constant_count *= top_shape.back();
    } else if (dim == -1) {
      TVM_FFI_ICHECK_EQ(inferred_axis, -1)
          << "Reshape shape contains multiple -1 dims";
      inferred_axis = top_shape.size();
      top_shape.push_back(0);
    } else {
      TVM_FFI_ICHECK_GT(dim, 0) << "Reshape dim must be positive, -1, or 0";
      top_shape.push_back(dim);
      constant_count *= dim;
    }
  }

  for (int i = end_axis; i < input_num_axes; ++i) {
    top_shape.push_back(input_blob->shape(i));
  }

  int64_t input_region_count = 1;
  for (int i = start_axis; i < end_axis; ++i) {
    input_region_count *= input_blob->shape(i);
  }

  if (inferred_axis >= 0) {
    TVM_FFI_ICHECK_GT(constant_count, 0);
    TVM_FFI_ICHECK_EQ(input_region_count % constant_count, 0)
        << "Cannot infer reshape dim: input count not divisible by constant count";
    top_shape[inferred_axis] = input_region_count / constant_count;
  } else {
    TVM_FFI_ICHECK_EQ(input_region_count, constant_count)
        << "Reshape count mismatch";
  }

  top[0]->Reshape(top_shape);
}

void ReshapeLayer::Forward_cpu(const std::vector<Blob*>& bottom,
                                const std::vector<Blob*>& top) {
  const float* bottom_data = bottom[0]->cpu_data();
  float* top_data = top[0]->cpu_data();
  const int64_t count = bottom[0]->count();
  if (bottom[0] != top[0]) {
    std::memcpy(top_data, bottom_data, sizeof(float) * count);
  }
}

REGISTER_LAYER_CLASS(Reshape);

}  // namespace caffe_ffi

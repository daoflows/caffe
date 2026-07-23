#ifndef CAFFE_UTIL_DEVICE_ALTERNATE_HPP_
#define CAFFE_UTIL_DEVICE_ALTERNATE_HPP_

#include "caffe/compat/logging.hpp"

#ifndef CPU_ONLY
#define CPU_ONLY 1
#endif

#define NO_GPU LOG(FATAL) << "CPU-only mode: Cannot use GPU in this build."

#define STUB_GPU(classname) \
  template <typename Dtype> \
  void classname<Dtype>::Forward_gpu( \
      const std::vector<Blob<Dtype>*>& bottom, \
      const std::vector<Blob<Dtype>*>& top) { NO_GPU; } \
  template <typename Dtype> \
  void classname<Dtype>::Backward_gpu( \
      const std::vector<Blob<Dtype>*>& top, \
      const std::vector<bool>& propagate_down, \
      const std::vector<Blob<Dtype>*>& bottom) { NO_GPU; }

#define STUB_GPU_FORWARD(classname, funcname) \
  template <typename Dtype> \
  void classname<Dtype>::funcname##_gpu( \
      const std::vector<Blob<Dtype>*>& bottom, \
      const std::vector<Blob<Dtype>*>& top) { NO_GPU; }

#define STUB_GPU_BACKWARD(classname, funcname) \
  template <typename Dtype> \
  void classname<Dtype>::funcname##_gpu( \
      const std::vector<Blob<Dtype>*>& top, \
      const std::vector<bool>& propagate_down, \
      const std::vector<Blob<Dtype>*>& bottom) { NO_GPU; }

#endif  // CAFFE_UTIL_DEVICE_ALTERNATE_HPP_

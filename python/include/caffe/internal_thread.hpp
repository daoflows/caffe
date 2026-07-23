#ifndef CAFFE_INTERNAL_THREAD_HPP_
#define CAFFE_INTERNAL_THREAD_HPP_

#include "caffe/common.hpp"

namespace caffe {

class InternalThread {
 public:
  InternalThread() {}
  virtual ~InternalThread() {}

  bool StartInternalThread() { return false; }
  void WaitForInternalThreadToExit() {}
  bool is_started() const { return false; }

 protected:
  virtual void InternalThreadEntry() {}
};

}  // namespace caffe

#endif

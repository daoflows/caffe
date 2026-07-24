#ifndef CAFFE_UTIL_BLOCKING_QUEUE_HPP_
#define CAFFE_UTIL_BLOCKING_QUEUE_HPP_

#include <queue>
#include <string>

#include "caffe/compat/thread.hpp"
#include "caffe/compat/smart_ptr.hpp"

namespace caffe {

using std::string;

template<typename T>
class BlockingQueue {
 public:
  explicit BlockingQueue();

  void push(const T& t);

  bool try_pop(T* t);

  T pop(const string& log_on_wait = "");

  bool try_peek(T* t);

  T peek();

  size_t size() const;

  bool empty() const;

 protected:
  class sync;

  std::queue<T> queue_;
  shared_ptr<sync> sync_;

DISABLE_COPY_AND_ASSIGN(BlockingQueue);
};

}  // namespace caffe

#endif

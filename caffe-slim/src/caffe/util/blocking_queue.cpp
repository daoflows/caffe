#include <string>

#include "caffe/compat/logging.hpp"
#include "caffe/layers/base_data_layer.hpp"
#include "caffe/util/blocking_queue.hpp"

namespace caffe {

template<typename T>
class BlockingQueue<T>::sync {
 public:
  mutable mutex mutex_;
  condition_variable condition_;
};

template<typename T>
BlockingQueue<T>::BlockingQueue()
    : sync_(new sync()) {
}

template<typename T>
void BlockingQueue<T>::push(const T& t) {
  unique_lock<mutex> lock(sync_->mutex_);
  queue_.push(t);
  lock.unlock();
  sync_->condition_.notify_one();
}

template<typename T>
bool BlockingQueue<T>::try_pop(T* t) {
  unique_lock<mutex> lock(sync_->mutex_);

  if (queue_.empty()) {
    return false;
  }

  *t = queue_.front();
  queue_.pop();
  return true;
}

template<typename T>
T BlockingQueue<T>::pop(const string& log_on_wait) {
  unique_lock<mutex> lock(sync_->mutex_);

  while (queue_.empty()) {
    if (!log_on_wait.empty()) {
      LOG_EVERY_N(INFO, 1000)<< log_on_wait;
    }
    sync_->condition_.wait(lock);
  }

  T t = queue_.front();
  queue_.pop();
  return t;
}

template<typename T>
bool BlockingQueue<T>::try_peek(T* t) {
  unique_lock<mutex> lock(sync_->mutex_);

  if (queue_.empty()) {
    return false;
  }

  *t = queue_.front();
  return true;
}

template<typename T>
T BlockingQueue<T>::peek() {
  unique_lock<mutex> lock(sync_->mutex_);

  while (queue_.empty()) {
    sync_->condition_.wait(lock);
  }

  return queue_.front();
}

template<typename T>
size_t BlockingQueue<T>::size() const {
  unique_lock<mutex> lock(sync_->mutex_);
  return queue_.size();
}

template<typename T>
bool BlockingQueue<T>::empty() const {
  unique_lock<mutex> lock(sync_->mutex_);
  return queue_.empty();
}

template class BlockingQueue<Batch<float>*>;
template class BlockingQueue<Batch<double>*>;

}  // namespace caffe

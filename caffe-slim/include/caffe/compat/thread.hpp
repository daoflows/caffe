#ifndef CAFFE_COMPAT_THREAD_HPP_
#define CAFFE_COMPAT_THREAD_HPP_

#include <atomic>
#include <condition_variable>
#include <chrono>
#include <mutex>
#include <thread>

namespace caffe {

using std::mutex;
using std::condition_variable;
using std::unique_lock;
using std::lock_guard;
using std::thread;
using std::atomic;
using std::atomic_bool;
using std::atomic_int;

namespace this_thread = std::this_thread;
namespace chrono_literals = std::chrono_literals;

inline void yield() { std::this_thread::yield(); }
inline void sleep_for_ms(int ms) {
  std::this_thread::sleep_for(std::chrono::milliseconds(ms));
}

class Barrier {
 public:
  explicit Barrier(int count) : threshold_(count), count_(count), generation_(0) {}

  void Wait() {
    std::unique_lock<std::mutex> lock(mutex_);
    int gen = generation_;
    if (--count_ == 0) {
      generation_++;
      count_ = threshold_;
      cond_.notify_all();
    } else {
      cond_.wait(lock, [this, gen]() { return gen != generation_; });
    }
  }

 private:
  std::mutex mutex_;
  std::condition_variable cond_;
  int threshold_;
  int count_;
  int generation_;
};

}  // namespace caffe

#endif  // CAFFE_COMPAT_THREAD_HPP_

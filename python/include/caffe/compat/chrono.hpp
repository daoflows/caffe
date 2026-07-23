#ifndef CAFFE_COMPAT_CHRONO_HPP_
#define CAFFE_COMPAT_CHRONO_HPP_

#include <chrono>

#include "caffe/compat/logging.hpp"

namespace caffe {

using Clock = std::chrono::high_resolution_clock;
using TimePoint = std::chrono::time_point<Clock>;

class Timer {
 public:
  Timer() : initted_(false), running_(false), has_run_at_least_once_(false) {
    Init();
  }

  void Start() {
    running_ = true;
    start_cpu_ = Clock::now();
  }

  void Stop() {
    CHECK(running_);
    stop_cpu_ = Clock::now();
    running_ = false;
    has_run_at_least_once_ = true;
    elapsed_milliseconds_ = std::chrono::duration<double, std::milli>(
        stop_cpu_ - start_cpu_).count();
    elapsed_micros_ = std::chrono::duration<double, std::micro>(
        stop_cpu_ - start_cpu_).count();
    elapsed_seconds_ = std::chrono::duration<double>(
        stop_cpu_ - start_cpu_).count();
  }

  float MilliSeconds() const {
    CHECK(has_run_at_least_once_);
    return static_cast<float>(elapsed_milliseconds_);
  }

  float MicroSeconds() const {
    CHECK(has_run_at_least_once_);
    return static_cast<float>(elapsed_micros_);
  }

  float Seconds() const {
    CHECK(has_run_at_least_once_);
    return static_cast<float>(elapsed_seconds_);
  }

  bool initted() const { return initted_; }
  bool running() const { return running_; }
  bool has_run_at_least_once() const { return has_run_at_least_once_; }

 protected:
  void Init() { initted_ = true; }

  bool initted_;
  bool running_;
  bool has_run_at_least_once_;
  TimePoint start_cpu_;
  TimePoint stop_cpu_;
  double elapsed_milliseconds_;
  double elapsed_micros_;
  double elapsed_seconds_;
};

}  // namespace caffe

#endif  // CAFFE_COMPAT_CHRONO_HPP_

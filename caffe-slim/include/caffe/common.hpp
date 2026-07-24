#ifndef CAFFE_COMMON_HPP_
#define CAFFE_COMMON_HPP_

#include <climits>
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "caffe/compat/logging.hpp"
#include "caffe/compat/smart_ptr.hpp"
#include "caffe/compat/thread.hpp"
#include "caffe/compat/random.hpp"
#include "caffe/compat/thread_local.hpp"
#include "caffe/util/device_alternate.hpp"

#define STRINGIFY(m) #m
#define AS_STRING(m) STRINGIFY(m)

#define DISABLE_COPY_AND_ASSIGN(classname) \
 private:                                  \
  classname(const classname&);             \
  classname& operator=(const classname&)

#define INSTANTIATE_CLASS(classname) \
  char gInstantiationGuard##classname; \
  template class classname<float>;    \
  template class classname<double>

namespace cv { class Mat; }

namespace caffe {

using std::fstream;
using std::ios;
using std::isnan;
using std::isinf;
using std::iterator;
using std::make_pair;
using std::map;
using std::ostringstream;
using std::pair;
using std::set;
using std::string;
using std::stringstream;
using std::vector;

void GlobalInit(int* pargc, char*** pargv);

class Caffe {
 public:
  ~Caffe();

  static Caffe& Get();

  enum Brew { CPU };

  class RNG {
   public:
    RNG();
    explicit RNG(unsigned int seed);
    explicit RNG(const RNG&);
    RNG& operator=(const RNG&);
    void* generator();
   private:
    class Generator;
    shared_ptr<Generator> generator_;
  };

  inline static RNG& rng_stream() {
    if (!Get().random_generator_) {
      Get().random_generator_.reset(new RNG());
    }
    return *(Get().random_generator_);
  }

  inline static Brew mode() { return CPU; }
  inline static void set_mode(Brew /*mode*/) {}
  static void set_random_seed(const unsigned int seed);
  static void SetDevice(const int device_id);
  static void DeviceQuery();
  static bool CheckDevice(const int device_id);
  static int FindDevice(const int start_id = 0);

  inline static int solver_count() { return 1; }
  inline static void set_solver_count(int /*val*/) {}
  inline static int solver_rank() { return 0; }
  inline static void set_solver_rank(int /*val*/) {}
  inline static bool multiprocess() { return false; }
  inline static void set_multiprocess(bool /*val*/) {}
  inline static bool root_solver() { return true; }

 protected:
  shared_ptr<RNG> random_generator_;

 private:
  Caffe();

  DISABLE_COPY_AND_ASSIGN(Caffe);
};

}  // namespace caffe

#endif  // CAFFE_COMMON_HPP_

#include <cmath>
#include <cstdio>
#include <ctime>
#include <cstdlib>
#ifdef _WIN32
#include <process.h>
#define GETPID _getpid
#else
#include <unistd.h>
#define GETPID getpid
#endif

#include "caffe/common.hpp"
#include "caffe/util/rng.hpp"

namespace caffe {

static ThreadLocalPtr<Caffe> thread_instance_;

Caffe& Caffe::Get() {
  if (!thread_instance_.get()) {
    thread_instance_.reset(new Caffe());
  }
  return *(thread_instance_.get());
}

static int64_t cluster_seedgen(void) {
  int64_t s, seed, pid;
  FILE* f = fopen("/dev/urandom", "rb");
  if (f && fread(&seed, 1, sizeof(seed), f) == sizeof(seed)) {
    fclose(f);
    return seed;
  }

  LOG(INFO) << "System entropy source not available, "
               "using fallback algorithm to generate seed instead.";
  if (f) fclose(f);

  pid = GETPID();
  s = time(NULL);
  seed = std::abs(((s * 181) * ((pid - 83) * 359)) % 104729);
  return seed;
}

void GlobalInit(int* /*pargc*/, char*** /*pargv*/) {
}

Caffe::Caffe() : random_generator_() {}

Caffe::~Caffe() {}

void Caffe::set_random_seed(const unsigned int seed) {
  Get().random_generator_.reset(new RNG(seed));
}

void Caffe::SetDevice(const int /*device_id*/) {
  NO_GPU;
}

void Caffe::DeviceQuery() {
  NO_GPU;
}

bool Caffe::CheckDevice(const int /*device_id*/) {
  NO_GPU;
  return false;
}

int Caffe::FindDevice(const int /*start_id*/) {
  NO_GPU;
  return -1;
}

class Caffe::RNG::Generator {
 public:
  Generator() : rng_(new caffe::rng_t(static_cast<uint32_t>(cluster_seedgen()))) {}
  explicit Generator(unsigned int seed) : rng_(new caffe::rng_t(seed)) {}
  caffe::rng_t* rng() { return rng_.get(); }
 private:
  shared_ptr<caffe::rng_t> rng_;
};

Caffe::RNG::RNG() : generator_(new Generator()) {}

Caffe::RNG::RNG(unsigned int seed) : generator_(new Generator(seed)) {}

Caffe::RNG& Caffe::RNG::operator=(const RNG& other) {
  generator_ = other.generator_;
  return *this;
}

void* Caffe::RNG::generator() {
  return static_cast<void*>(generator_->rng());
}

}  // namespace caffe

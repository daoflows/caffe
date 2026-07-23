#ifndef CAFFE_SYNCEDMEM_HPP_
#define CAFFE_SYNCEDMEM_HPP_

#include <cstdlib>
#include <cstring>

#include "caffe/common.hpp"

namespace caffe {

inline void CaffeMallocHost(void** ptr, size_t size) {
#ifdef _MSC_VER
  *ptr = _aligned_malloc(size ? size : 1, 64);
  if (*ptr == nullptr) *ptr = malloc(size ? size : 1);
#else
  int ret = posix_memalign(ptr, 64, size ? size : 1);
  if (ret != 0) *ptr = malloc(size ? size : 1);
#endif
  CHECK(*ptr) << "host allocation of size " << size << " failed";
}

inline void CaffeFreeHost(void* ptr) {
#ifdef _MSC_VER
  _aligned_free(ptr);
#else
  free(ptr);
#endif
}

class SyncedMemory {
 public:
  SyncedMemory();
  explicit SyncedMemory(size_t size);
  ~SyncedMemory();
  const void* cpu_data();
  void set_cpu_data(void* data);
  void* mutable_cpu_data();
  enum SyncedHead { UNINITIALIZED, HEAD_AT_CPU };
  SyncedHead head() const { return head_; }
  size_t size() const { return size_; }

 private:
  void to_cpu();
  void* cpu_ptr_;
  size_t size_;
  SyncedHead head_;
  bool own_cpu_data_;

  DISABLE_COPY_AND_ASSIGN(SyncedMemory);
};

}  // namespace caffe

#endif  // CAFFE_SYNCEDMEM_HPP_

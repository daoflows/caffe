#ifndef CAFFE_COMPAT_THREAD_LOCAL_HPP_
#define CAFFE_COMPAT_THREAD_LOCAL_HPP_

namespace caffe {

template <typename T>
class ThreadLocalStore {
 public:
  static T*& Get() {
    thread_local T* ptr = nullptr;
    return ptr;
  }
};

template <typename T>
class ThreadLocalPtr {
 public:
  ThreadLocalPtr() = default;

  T* get() const {
    return ThreadLocalStore<T>::Get();
  }

  T* operator->() const { return get(); }
  T& operator*() const { return *get(); }

  void reset(T* new_ptr = nullptr) {
    T*& ptr = ThreadLocalStore<T>::Get();
    T* old = ptr;
    ptr = new_ptr;
    if (old != new_ptr) {
      delete old;
    }
  }

  ~ThreadLocalPtr() {
    T*& ptr = ThreadLocalStore<T>::Get();
    delete ptr;
    ptr = nullptr;
  }

 private:
  ThreadLocalPtr(const ThreadLocalPtr&) = delete;
  ThreadLocalPtr& operator=(const ThreadLocalPtr&) = delete;
};

}  // namespace caffe

#endif  // CAFFE_COMPAT_THREAD_LOCAL_HPP_

#ifndef CAFFE_COMPAT_LOGGING_HPP_
#define CAFFE_COMPAT_LOGGING_HPP_

#include <tvm/ffi/error.h>

#include <cstdlib>
#include <cmath>
#include <iostream>
#include <sstream>
#include <string>

namespace caffe {

inline void CaffeLogInit(const char* /*argv0*/ = nullptr) {}

enum LogSeverity {
  LOG_INFO = 0,
  LOG_WARNING = 1,
  LOG_ERROR = 2,
  LOG_FATAL = 3,
};

namespace internal {

inline const char* LogSeverityName(int severity) {
  switch (severity) {
    case LOG_INFO: return "I";
    case LOG_WARNING: return "W";
    case LOG_ERROR: return "E";
    case LOG_FATAL: return "F";
    default: return "?";
  }
}

class LogMessage {
 public:
  LogMessage(const char* file, int line, int severity)
      : severity_(severity), file_(file), line_(line) {
    stream_ << "[" << LogSeverityName(severity) << "] " << file << ":" << line << "] ";
  }

  ~LogMessage() noexcept(false) {
    stream_ << "\n";
    std::string msg = stream_.str();
    std::cerr << msg;
    std::cerr.flush();
    if (severity_ == LOG_FATAL) {
      TVM_FFI_THROW(RuntimeError) << msg;
    }
  }

  std::ostringstream& stream() { return stream_; }

 private:
  int severity_;
  const char* file_;
  int line_;
  std::ostringstream stream_;
};

}  // namespace internal

}  // namespace caffe

#define CAFFE_LOG_SEVERITY_INFO ::caffe::LOG_INFO
#define CAFFE_LOG_SEVERITY_WARNING ::caffe::LOG_WARNING
#define CAFFE_LOG_SEVERITY_ERROR ::caffe::LOG_ERROR
#define CAFFE_LOG_SEVERITY_FATAL ::caffe::LOG_FATAL

#define LOG(severity) \
  ::caffe::internal::LogMessage(__FILE__, __LINE__, CAFFE_LOG_SEVERITY_##severity).stream()

#define LOG_IF(severity, condition) \
  if (condition) LOG(severity)

#define LOG_EVERY_N(severity, n) LOG(severity)
#define LOG_IF_EVERY_N LOG_IF
#define VLOG(level) LOG(INFO)
#define VLOG_IF LOG_IF
#define DLOG LOG
#define DLOG_IF LOG_IF
#define DLOG_EVERY_N LOG_EVERY_N

#define CHECK(cond) TVM_FFI_ICHECK(cond)
#define CHECK_EQ(x, y) TVM_FFI_ICHECK_EQ(x, y)
#define CHECK_NE(x, y) TVM_FFI_ICHECK_NE(x, y)
#define CHECK_LT(x, y) TVM_FFI_ICHECK_LT(x, y)
#define CHECK_LE(x, y) TVM_FFI_ICHECK_LE(x, y)
#define CHECK_GT(x, y) TVM_FFI_ICHECK_GT(x, y)
#define CHECK_GE(x, y) TVM_FFI_ICHECK_GE(x, y)
#define CHECK_NOTNULL(x) TVM_FFI_ICHECK_NOTNULL(x)
#define CHECK_DOUBLE_EQ(x, y) TVM_FFI_ICHECK((x) == (y))
#define CHECK_NEAR(x, y, tol) TVM_FFI_ICHECK(std::fabs((x) - (y)) <= (tol))
#define CHECK_STREQ(a, b) TVM_FFI_ICHECK(std::strcmp((a), (b)) == 0)
#define CHECK_STRNE(a, b) TVM_FFI_ICHECK(std::strcmp((a), (b)) != 0)
#define CHECK_STRCASEEQ(a, b) TVM_FFI_ICHECK(std::strcasecmp((a), (b)) == 0)
#define CHECK_STRCASENE(a, b) TVM_FFI_ICHECK(std::strcasecmp((a), (b)) != 0)

#define DCHECK TVM_FFI_DCHECK
#define DCHECK_EQ TVM_FFI_DCHECK_EQ
#define DCHECK_NE TVM_FFI_DCHECK_NE
#define DCHECK_LT TVM_FFI_DCHECK_LT
#define DCHECK_LE TVM_FFI_DCHECK_LE
#define DCHECK_GT TVM_FFI_DCHECK_GT
#define DCHECK_GE TVM_FFI_DCHECK_GE
#define DCHECK_NOTNULL TVM_FFI_DCHECK_NOTNULL

#define NOT_IMPLEMENTED \
  TVM_FFI_THROW(InternalError) << "Not implemented: " << __FILE__ << ":" << __LINE__

#endif  // CAFFE_COMPAT_LOGGING_HPP_

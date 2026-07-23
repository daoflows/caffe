#ifndef CAFFE_COMPAT_STRING_UTILS_HPP_
#define CAFFE_COMPAT_STRING_UTILS_HPP_

#include <algorithm>
#include <cctype>
#include <sstream>
#include <string>
#include <vector>

namespace caffe {

inline std::string trim(const std::string& s) {
  auto start = s.begin();
  while (start != s.end() && std::isspace(static_cast<unsigned char>(*start))) {
    ++start;
  }
  auto end = s.end();
  do {
    --end;
  } while (std::distance(start, end) > 0 && std::isspace(static_cast<unsigned char>(*end)));
  return std::string(start, end + 1);
}

inline std::vector<std::string> split(const std::string& s, char delimiter) {
  std::vector<std::string> tokens;
  std::string token;
  std::istringstream token_stream(s);
  while (std::getline(token_stream, token, delimiter)) {
    tokens.push_back(token);
  }
  return tokens;
}

inline std::vector<std::string> split(const std::string& s, const std::string& delimiters) {
  std::vector<std::string> tokens;
  size_t start = 0;
  size_t pos = s.find_first_of(delimiters);
  while (pos != std::string::npos) {
    tokens.push_back(s.substr(start, pos - start));
    start = pos + 1;
    pos = s.find_first_of(delimiters, start);
  }
  tokens.push_back(s.substr(start));
  return tokens;
}

template <typename T>
T lexical_cast(const std::string& s) {
  T value;
  std::istringstream iss(s);
  iss >> value;
  return value;
}

template <>
inline std::string lexical_cast<std::string>(const std::string& s) {
  return s;
}

template <>
inline int lexical_cast<int>(const std::string& s) {
  return std::stoi(s);
}

template <>
inline float lexical_cast<float>(const std::string& s) {
  return std::stof(s);
}

template <>
inline double lexical_cast<double>(const std::string& s) {
  return std::stod(s);
}

template <>
inline bool lexical_cast<bool>(const std::string& s) {
  std::string lower = s;
  std::transform(lower.begin(), lower.end(), lower.begin(),
                 [](unsigned char c) { return std::tolower(c); });
  return lower == "true" || lower == "1" || lower == "yes";
}

template <typename T>
inline std::string to_string(const T& value) {
  std::ostringstream oss;
  oss << value;
  return oss.str();
}

}  // namespace caffe

#endif  // CAFFE_COMPAT_STRING_UTILS_HPP_

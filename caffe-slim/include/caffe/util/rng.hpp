#ifndef CAFFE_RNG_HPP_
#define CAFFE_RNG_HPP_

#include <algorithm>
#include <iterator>
#include <random>

#include "caffe/common.hpp"

namespace caffe {

inline rng_t* caffe_rng() {
  return static_cast<caffe::rng_t*>(Caffe::rng_stream().generator());
}

template <class RandomAccessIterator, class RandomGenerator>
inline void shuffle(RandomAccessIterator begin, RandomAccessIterator end,
                    RandomGenerator* gen) {
  typedef typename std::iterator_traits<RandomAccessIterator>::difference_type
      difference_type;

  difference_type length = std::distance(begin, end);
  if (length <= 0) return;

  std::uniform_int_distribution<difference_type> dist(0, 0);
  for (difference_type i = length - 1; i > 0; --i) {
    dist.param(std::uniform_int_distribution<difference_type>::param_type(0, i));
    std::iter_swap(begin + i, begin + dist(*gen));
  }
}

template <class RandomAccessIterator>
inline void shuffle(RandomAccessIterator begin, RandomAccessIterator end) {
  shuffle(begin, end, caffe_rng());
}

}  // namespace caffe

#endif  // CAFFE_RNG_HPP_

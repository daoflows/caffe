#pragma once

#ifdef WIN32
  #define caffex_EXPORT __declspec(dllexport)
#else
  #define caffex_EXPORT
#endif

caffex_EXPORT void caffex();

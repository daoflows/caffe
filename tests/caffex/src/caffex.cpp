#include <iostream>
#include "caffex.h"

void caffex(){
    #ifdef NDEBUG
    std::cout << "caffex/1.0: Hello World Release!\n";
    #else
    std::cout << "caffex/1.0: Hello World Debug!\n";
    #endif
}

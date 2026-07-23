#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq 2>&1
echo "=== Installing ALL boost ==="
apt-get install -y libboost-all-dev 2>&1
echo "=== Search for system library ==="
apt-cache search boost-system
echo "=== Check if header-only ==="
grep -r "BOOST_SYSTEM_NO_LIB\|header.only" /usr/include/boost/system/config.hpp 2>/dev/null || echo "NOT FOUND"
echo "=== Try installing runtime lib ==="
apt-get install -y libboost-system1.90.0 2>&1 || echo "PACKAGE NOT FOUND"
echo "=== Find system .so ==="
find /usr -name "libboost_system*" 2>/dev/null || echo "NOT FOUND .so"
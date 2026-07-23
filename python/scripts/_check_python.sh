#!/bin/bash
source /opt/conda/etc/profile.d/conda.sh
conda activate pycaffe-py314
echo "=== Python version ==="
python --version
echo ""
echo "=== sysconfig ==="
python -c "
import sysconfig
print('INCLUDEPY:', sysconfig.get_config_var('INCLUDEPY'))
print('LDVERSION:', sysconfig.get_config_var('LDVERSION'))
print('VERSION:', sysconfig.get_config_var('VERSION'))
print('Py_GIL_DISABLED:', sysconfig.get_config_var('Py_GIL_DISABLELED'))
print('SOABI:', sysconfig.get_config_var('SOABI'))
print('abiflags:', sysconfig.get_config_var('abiflags'))
"
echo ""
echo "=== Python executable ==="
which python
ls -la $(which python)
echo ""
echo "=== Include directory ==="
ls -la /opt/conda/envs/pycaffe-py314/include/python*
echo ""
echo "=== lib directory ==="
ls -la /opt/conda/envs/pycaffe-py314/lib/libpython*
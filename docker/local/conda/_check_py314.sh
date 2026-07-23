#!/bin/bash
set -e
echo "=== Checking Python 3.14 conda env structure ==="
CONDA_PREFIX_PATH="/opt/conda/envs/py314test"
source /opt/conda/etc/profile.d/conda.sh
conda activate py314test 2>/dev/null || /opt/conda/bin/conda create -y -n py314test python=3.14 >/dev/null 2>&1
conda activate py314test

echo "=== Include dirs ==="
ls -d $CONDA_PREFIX_PATH/include/python* 2>&1 || true
echo ""
echo "=== Python libs ==="
ls $CONDA_PREFIX_PATH/lib/libpython* 2>&1 || true
echo ""
echo "=== sysconfig ==="
python -c "
import sysconfig
for k in ['include', 'platinclude', 'INCLUDEPY']:
    print(f'{k}:', sysconfig.get_path(k) or sysconfig.get_config_var(k))
for k in ['INSTSONAME', 'LDVERSION', 'py_version_nodot', 'SOABI', 'VERSION', 'EXT_SUFFIX']:
    print(f'{k}:', sysconfig.get_config_var(k))
"
echo ""
echo "=== pyconfig.h locations ==="
find $CONDA_PREFIX_PATH/include -name 'pyconfig.h' 2>/dev/null
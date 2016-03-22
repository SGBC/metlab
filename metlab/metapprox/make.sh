#!/bin/bash
# laziness-script to build this as a python module.

if [ `uname` == "Darwin" ]
then
    export CFLAGS=-Qunused-arguments
    export CPPFLAGS=-Qunused-arguments
    export LDFLAGS="-arch x86_64"
fi

python setup.py clean
rm *.so
python setup.py build_ext --inplace

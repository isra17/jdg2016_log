#!/bin/bash

rm -rf build
mkdir -p build
python3 -m py_compile *.py
for fn in __pycache__/*.pyc; do mv $fn ${fn//\.cpython-34/}; done
mv __pycache__ build
cp jdg2016 build
cp tests.json build
cp epreuve.pdf build
cd build
tar zcvf ../jdg2016.tar.gz * -C .

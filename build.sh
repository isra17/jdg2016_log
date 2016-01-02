#!/bin/bash

rm -rf build
mkdir -p build
python3 -m py_compile *.py
for fn in __pycache__/*.pyc; do mv $fn ${fn//\.cpython-3[0-9]/}; done
mv __pycache__ build
cp jdg2016 build
cp tests.json build
cp epreuve.pdf build
cp run.sh build
cp solution.py build
cp solution.java build
cd build
tar zcvf ../jdg2016.tar.gz * -C .

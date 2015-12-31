#!/bin/sh

rm -rf build
mkdir -p build
python -m py_compile *.py
for fn in __pycache__/*.pyc; do mv $fn ${fn//\.cpython-35/}; done
mv __pycache__ build
cp jdg2016 build
cp tests.json build
cp epreuve.pdf build
tar zcvf jdg2016.tar.gz build/*

#!/usr/bin/env bash

python3 -m venv ./env/

source ./env/bin/activate

./env/bin/pip install --upgrade pip

./env/bin/pip install -r ./requirements.txt

cd ./env/

git clone http://github.com/sciserver/SciScript-Python.git

cd ./SciScript-Python/

python Install.py

cd ../..

python domecat.py

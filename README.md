# cyoa-archives

## Requirements

Using python 3.8.2

Tensorflow

## Installation

Via PIP

* pandas
* praw
* PyYAML
* redditcleaner
* grist-api
* strsimpy
* opencv-contrib-pythong
* gallery-dl
* pytesseract
* ImageHash # Not for now
* Keybert

Via github

* https://github.com/KichangKim/DeepDanbooru (and trained model)

Via machine-specific instructions

* Tensorflow
* Keras OCR

Use these installation instructiosn:
https://caffeinedev.medium.com/how-to-install-tensorflow-on-m1-mac-8e9b91d93706

First, install python 3.7.16 with pyenv and switch python versions.

Next start a virtual environment:

`python3 -m venv env

. env/bin/activate`


setup and download model

git clone https://github.com/tensorflow/io.git

cd io

python setup.py -q bdist_wheel

python -m pip install --no-deps dist/tensorflow_io-0.32.0-cp38-cp38-macosx_11_0_arm64.whl

https://medium.com/dive-into-ml-ai/installing-tensorflow-natively-on-mac-m1-in-2022-1357e9b7a201

## Usage

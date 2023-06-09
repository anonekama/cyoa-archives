import argparse
import json
import pathlib
import logging
import pathlib
import shutil
import subprocess
import sys
import os
import math

import cv2
import pandas as pd
import yaml

import keras_ocr
import tensorflow as tf

MAX_WIDTH = 1280
INPUT_SIZE = (512, 512)
SLIDING_WINDOW_DIM = (512, 512)
SLIDING_WINDOW_STEP = 256
PROJECT_PATH = '/Users/jyzhou/src/cyoa/cyoa_parser/deepdanbooru-v3-20211112-sgd-e28'
DD_THRESHOLD = 0.9
DD_REPORT_THRESHOLD = 0.03
KB_THRESHOLD = 0.3

from cyoa_archives.predictor.image import CyoaImage

def main(config):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    tempdir = pathlib.Path('temp/')
    if tempdir.exists():
        logger.info(f'Deleting directory: {tempdir.resolve()}')
        # shutil.rmtree(tempdir.resolve())

    # subprocess.run(['gallery-dl', 'https://imgur.com/gallery/QLfAhNT', '-d', 'temp/'], universal_newlines=True)
    # subprocess.run(['gallery-dl', 'https://www.reddit.com/gallery/12kylsi', '-d', 'temp/'], universal_newlines=True)
    # subprocess.run(['gallery-dl', 'https://imgchest.com/p/9249jkz27nk', '-d', 'temp/'], universal_newlines=True)

    # List files
    imagepaths = []
    for extension in ['*.png', '*.jpg', '*.jpeg']:
        for imagepath in tempdir.rglob(extension):
            imagepaths.append(imagepath)
    # print(imagepaths)

    seen_tags = {}
    rois = []
    for i, image_fn in enumerate(imagepaths):
        image_fn = pathlib.Path('temp/imgur/QLfAhNT - Super CYOA/imgur_QLfAhNT_001_a85tsaH.jpg')
        print(image_fn)

        CyoaImage.load_config(config.get('predictor'))
        cyoa_image = CyoaImage(image_fn)
        logger.info(image_fn)

        # cyoa_image = cv2.imread(str(image_fn.resolve()))
        # img = cv2.resize(cyoa_page, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        # img = cv2.bilateralFilter(img,9,75,75)
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        #cv2.imshow('image', img)
        #cv2.waitKey(0)
        # img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
        # cyoa_text = pytesseract.image_to_string(img, config='--psm 11')
        # with open('tess.txt', 'w') as f:
        #     f.write(cyoa_text)

        #for roi in rois[0:10]:
        #    cyoa_page = cv2.imread(roi)
        #    img = cv2.resize(cyoa_page, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        #    img = cv2.bilateralFilter(img, 9, 75, 75)
        #    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        #    img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
        #    cyoa_text = pytesseract.image_to_string(img, config='--psm 11')
        #    print(cyoa_text)

        """
        predictions = detect_w_keras(rois[0])

        predictions = get_distance(predictions)
        predictions = list(distinguish_rows(predictions, 15))
        # Remove all empty rows
        predictions = list(filter(lambda x: x != [], predictions))
        # Order text detections in human readable format
        ordered_preds = []
        ylst = ['yes', 'y']

        for pr in predictions:
            if True:
                row = sorted(pr, key=lambda x: x['distance_from_origin'])
                for each in row:
                    ordered_preds.append(each['text'])
        print(ordered_preds)
        """

        break



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a subreddit for submissions using praw."
    )
    parser.add_argument("-c", "--config_file", help="Configuration file to use")

    # Parse arguments
    args = parser.parse_args()

    # Load arguments from configuration file if provided
    if args.config_file:
        filepath = pathlib.Path(args.config_file)
        try:
            with open(filepath) as f:
                config = yaml.safe_load(f)
        except OSError:
            print(f"Could not read file: {filepath}")
            sys.exit(1)

    # Pass to main function
    main(
        config,
    )

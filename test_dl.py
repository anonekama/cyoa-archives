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
import pytesseract
import tensorflow as tf

MAX_WIDTH = 1281
INPUT_SIZE = (512, 512)
SLIDING_WINDOW_DIM = (512, 512)
SLIDING_WINDOW_STEP = 256
PROJECT_PATH = '/Users/jyzhou/src/cyoa/cyoa_parser/deepdanbooru-v3-20211112-sgd-e28'
DD_THRESHOLD = 0.9
DD_REPORT_THRESHOLD = 0.03
KB_THRESHOLD = 0.3


def get_distance(predictions):
    """
    Function returns dictionary with (key,value):
        * text : detected text in image
        * center_x : center of bounding box (x)
        * center_y : center of bounding box (y)
        * distance_from_origin : hypotenuse
        * distance_y : distance between y and origin (0,0)
    """

    # Point of origin
    x0, y0 = 0, 0
    # Generate dictionary
    detections = []
    for group in predictions:
        # Get center point of bounding box
        top_left_x, top_left_y = group[1][0]
        bottom_right_x, bottom_right_y = group[1][1]
        center_x = (top_left_x + bottom_right_x) / 2
        center_y = (top_left_y + bottom_right_y) / 2
        # Use the Pythagorean Theorem to solve for distance from origin
        distance_from_origin = math.dist([x0, y0], [center_x, center_y])
        # Calculate difference between y and origin to get unique rows
        distance_y = center_y - y0
        # Append all results
        detections.append({
            'text': group[0],
            'center_x': center_x,
            'center_y': center_y,
            'distance_from_origin': distance_from_origin,
            'distance_y': distance_y
        })
    return detections


def distinguish_rows(lst, thresh=15):
    """Function to help distinguish unique rows"""

    sublists = []
    for i in range(0, len(lst) - 1):
        if lst[i + 1]['distance_y'] - lst[i]['distance_y'] <= thresh:
            if lst[i] not in sublists:
                sublists.append(lst[i])
            sublists.append(lst[i + 1])
        else:
            yield sublists
            sublists = [lst[i + 1]]
    yield sublists


def detect_w_keras(image_path):
    """Function returns detected text from image"""

    # Initialize pipeline
    pipeline = keras_ocr.pipeline.Pipeline()
    # Read in image path
    read_image = keras_ocr.tools.read(image_path)
    # prediction_groups is a list of (word, box) tuples
    prediction_groups = pipeline.recognize([read_image])
    return prediction_groups[0]

def main(config):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    tempdir = pathlib.Path('temp/')
    shutil.rmtree(tempdir.resolve())

    subprocess.run(['gallery-dl', 'https://imgur.com/gallery/QLfAhNT', '-d', 'temp/'], universal_newlines=True)
    # subprocess.run(['gallery-dl', 'https://www.reddit.com/gallery/12kylsi', '-d', 'temp/'], universal_newlines=True)
    # subprocess.run(['gallery-dl', 'https://imgchest.com/p/9249jkz27nk', '-d', 'temp/'], universal_newlines=True)

    # List files
    imagepaths = []
    for extension in ['*.png', '*.jpg', '*.jpeg']:
        for imagepath in tempdir.rglob(extension):
            imagepaths.append(imagepath)
            print(imagepath)
    # print(imagepaths)

    seen_tags = {}
    rois = []
    for i, image_fn in enumerate(imagepaths):
        print(image_fn)
        cyoa_page = cv2.imread(str(image_fn.resolve()))
        img = cv2.resize(cyoa_page, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        img = cv2.bilateralFilter(img,9,75,75)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        #cv2.imshow('image', img)
        #cv2.waitKey(0)
        img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
        cyoa_text = pytesseract.image_to_string(img, config='--psm 11')
        with open('tess.txt', 'w') as f:
            f.write(cyoa_text)

        # Resize tall pages (height > width)
        (H, W) = cyoa_page.shape[:2]
        if H > W and W > MAX_WIDTH:
            scale_percent = MAX_WIDTH / W
            dim = (int(W * scale_percent), int(H * scale_percent))
            cyoa_page = cv2.resize(cyoa_page, dim, interpolation=cv2.INTER_AREA)
            (H, W) = cyoa_page.shape[:2]

        # Sliding window
        for y in range(0, H - SLIDING_WINDOW_DIM[1], SLIDING_WINDOW_STEP):
            for x in range(0, W - SLIDING_WINDOW_DIM[0], SLIDING_WINDOW_STEP):
                x2 = x + SLIDING_WINDOW_DIM[0]
                y2 = y + SLIDING_WINDOW_DIM[1]
                roi = cv2.resize(cyoa_page[y:y2, x:x2], INPUT_SIZE)
                roi_fn = os.path.join(tempdir.resolve(), str(i) + '_' + str(x) + '_' + str(y) + '_' + str(x2) + '_' + str(y2) + '.jpg')
                cv2.imwrite(roi_fn, roi)
                rois.append(roi_fn)

        #for roi in rois[0:10]:
        #    cyoa_page = cv2.imread(roi)
        #    img = cv2.resize(cyoa_page, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        #    img = cv2.bilateralFilter(img, 9, 75, 75)
        #    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        #    img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
        #    cyoa_text = pytesseract.image_to_string(img, config='--psm 11')
        #    print(cyoa_text)

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

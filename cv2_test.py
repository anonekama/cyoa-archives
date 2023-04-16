import argparse
import json
import pathlib
import numpy as np
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

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    image_fn = pathlib.Path('test.jpg')
    print(image_fn)
    image = cv2.imread(str(image_fn.resolve()))

    # Print dimensions
    height, width, channels = image.shape
    print(f'{height} x {width}')

    # Apply grayscale and small blur
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    # apply Otsu's automatic thresholding which automatically determines
    # the best threshold value
    (T, threshInv) = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    cv2.imshow('image', image)
    cv2.waitKey(0)
    # cv2.imshow('image', gray)
    # cv2.waitKey(0)
    # cv2.imshow('image', blurred)
    # cv2.waitKey(0)
    cv2.imshow("Threshold", threshInv)
    cv2.waitKey(0)
    print(threshInv.shape)

    # Save inverted
    invImg = 255 - threshInv

    # Using numpy, get indexes of all 0 or all 1 lines
    zero_rows = np.where(~threshInv.any(axis=1))[0]
    one_rows = np.where(~invImg.any(axis=1))[0]
    print(f'Total Rows: {height} - AllBlack: {len(zero_rows)} - AllWhite: {len(one_rows)}')

    # Get continuous indexes
    results = []
    continuous_row = []
    last_item = -1
    for i in one_rows:
        # If rows were adjacent
        if abs(i - last_item) <= 1:
            continuous_row.append(i)
            if i == len(one_rows):
                # Handle last row
                results.append(continuous_row)
                continuous_row = []
        else:
            if len(continuous_row) > 0:
                results.append(continuous_row)
                continuous_row = []
        last_item = i
    print(f'Chunks: {len(results)}')

    # For each chunk:
    # Filter if tall enough, otherwise return the median
    medians = []
    for chunk in results:
        if len(chunk) > 5: # Threshold
            medians.append(int(np.average(chunk)))
    print(f'Medians: {medians}')

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



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a subreddit for submissions using praw."
    )
    # parser.add_argument("-c", "--config_file", help="Configuration file to use")

    # Parse arguments
    args = parser.parse_args()
    """
    # Load arguments from configuration file if provided
    if args.config_file:
        filepath = pathlib.Path(args.config_file)
        try:
            with open(filepath) as f:
                config = yaml.safe_load(f)
        except OSError:
            print(f"Could not read file: {filepath}")
            sys.exit(1)
    """

    # Pass to main function
    main()

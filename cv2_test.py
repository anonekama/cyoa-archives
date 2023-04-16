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

from cyoa_archives.predictor.image import CyoaImage
from cyoa_archives.predictor.cv import CvChunk


def main():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    #image_fn = pathlib.Path('test.png')
    #image_fn = pathlib.Path('test2.jpeg')
    image_fn = pathlib.Path('test3.jpeg') # pass
    print(image_fn)
    image = cv2.imread(str(image_fn.resolve()))

    image = cv2.resize(image, (300, 1200), interpolation = cv2.INTER_AREA)

    # Print dimensions
    height, width, channels = image.shape
    print(f'{height} x {width}')

    # reduce colors
    #div = 64
    #quantized = image // div * div + div // 2

    # Calculate color space for image
    b, g, r = cv2.split(image)
    shiftet_im = b + 1000 * (g + 1) + 1000 * 1000 * (r + 1)
    # unique_colors = len(np.unique(shiftet_im))

    print(shiftet_im)

    # Run uniqueness kernal
    new_im = np.zeros([height, width])
    kernel = 10
    for i in range(width):
        for j in range(height):
            xmin = i - kernel if i - kernel > 0 else 0
            xmax = i + kernel if i + kernel < width else width
            ymin = j - kernel if j - kernel > 0 else 0
            ymax = j + kernel if j + kernel < height else height
            window = shiftet_im[ymin:ymax, xmin:xmax]
            new_im[j, i] = int(len(np.unique(window)))

    max_unique = np.max(new_im)
    normalized = new_im / max_unique

    print(normalized)

    cv2.imshow("image", normalized)
    cv2.waitKey()



    # Apply preprocessing transformations on the image
   # KERNAL_SIZE = 7
    #gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #blurred = cv2.GaussianBlur(gray, (KERNAL_SIZE, KERNAL_SIZE), 0)

    # Remove margin from image
    #MARGIN = 0.05
    #new_start = int(width * MARGIN / 2)
    #new_end = int(width - width * MARGIN / 2)

    #chunk = CvChunk(blurred[0:height, new_start:new_end], 0, 0)
    #min_size = int(width / 3) # Accept a minimum of 12 columns
    #min_thickness = int(0.02 * width)
    #chunk.generate_subchunks(min_size, min_thickness)

    # ci = CyoaImage.chunk_image(image)


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

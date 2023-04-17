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
    image_fn = pathlib.Path('test0.jpg')

    cyoa_image = CyoaImage(image_fn)
    text = cyoa_image.get_text()
    logger.debug(text)
    # imgs = cyoa_image.get_images()


    # Apply loose chunking for ocr

    # Then apply greedy chunking for (rows, then columns) for

    #cv2.imshow("image", normalized)
    #cv2.waitKey()


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

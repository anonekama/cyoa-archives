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

    bboxes = cyoa_image.get_text_bboxes()
    logger.info(f'Found {len(bboxes)} boxes.')

    chunks = cyoa_image.chunk_image(6)
    for i, chunk in enumerate(chunks):
        cv2.imwrite(f'chunk_{i}.jpg', chunk.cv)


    img = cyoa_image.cv
    for bbox in bboxes:
        start_point = (bbox.xmin, bbox.ymin)
        end_point = (bbox.xmax, bbox.ymax)
        color = (255, 0, 0)
        img = cv2.rectangle(img, start_point, end_point, color, 2)

    cv2.imwrite(f'boundingboxes.jpg', img)



    #cv2.imshow('image', cnts)
    #cv2.waitKey()


    # logger.debug(text)
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

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
    # image_fn = pathlib.Path('test2.jpeg')
    # image_fn = pathlib.Path('test3.jpeg')
    # image_fn = pathlib.Path('test7.jpeg')
    # image_fn = pathlib.Path('test8.png')

    cyoa_image = CyoaImage(image_fn)

    bboxes = cyoa_image.get_text_bboxes()
    logger.info(f'Found {len(bboxes)} boxes.')

    img = cyoa_image.cv

    # chunks = cyoa_image.chunk_image(8, bboxes)
    chunks = cyoa_image.get_img_bboxes(text_bboxes=bboxes)
    for i, chunk in enumerate(chunks):
        logger.debug(f'Chunk: {chunk.x} {chunk.y} {chunk.width} {chunk.height}')
        # cv2.imwrite(f'chunk_{i}.jpg', chunk.cv)

        start_point = (chunk.x, chunk.y)
        end_point = (chunk.xmax, chunk.ymax)
        color = (255, 255, 0)
        img = cv2.rectangle(img, start_point, end_point, color, 2)



    for bbox in bboxes:
        start_point = (bbox.xmin, bbox.ymin)
        end_point = (bbox.xmax, bbox.ymax)
        color = (255, 0, 0)
        img = cv2.rectangle(img, start_point, end_point, color, 2)


    cv2.imwrite(f'{image_fn.stem}_boundingboxes.jpg', img)



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

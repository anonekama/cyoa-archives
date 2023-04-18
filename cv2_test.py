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
    #image_fn = pathlib.Path('test0.jpg')
    # image_fn = pathlib.Path('test2.jpeg')
    #image_fn = pathlib.Path('test3.jpeg')
    #image_fn = pathlib.Path('test7.jpeg')
    #image_fn = pathlib.Path('test8.png')
    image_fn = pathlib.Path('test11.png')

    cyoa_image = CyoaImage(image_fn)

    # 1. Divide CYOA into large row sections
    min_size = cyoa_image.width * 0.10  # Start with a 1:10 aspect ratio minimum
    line_thickness = cyoa_image.width * 0.004  # For a 1200px image, this is 5px
    margin = 0.025  # For a 1200px image, this is a 30px margin
    section_chunks = cyoa_image.as_chunk().generate_subchunks(
        min_size=min_size,
        line_thickness=line_thickness,
        margin=margin
    )

    # 2. Get bbox coordinates for text blocks.
    prelim_bbox_list = []
    for chunk in section_chunks:
        text_bboxes = chunk.get_text_bboxes(level=2, scale=2, minimum_conf=30)  # Text blocks
        prelim_bbox_list.extend(text_bboxes)

    ############ DEBUG PRINT SECTION CHUNKS
    #
    img = cyoa_image.cv
    for i, chunk in enumerate(section_chunks):
        # logger.debug(f'Chunk: {chunk.xmin} {chunk.ymin} {chunk.width} {chunk.height}')
        cv2.imwrite(f'chunk_{i}.jpg', chunk.cv)

        start_point = (chunk.xmin, chunk.ymin)
        end_point = (chunk.xmax, chunk.ymax)
        color = (255, 0, 0)
        img = cv2.rectangle(img, start_point, end_point, color, 5)

    #
    ############ DEBUG PRINT SECTION CHUNKS

    # 3. Perform more aggressive horizontal chunks and use this for ocr
    row_chunks = []
    for chunk in section_chunks:
        chunks = chunk.generate_subchunks(
            min_size=25,
            line_thickness=10,
            margin=0.025,
            bboxes=prelim_bbox_list,
            greedy=False
        )
        row_chunks.extend(chunks)

    text = ""
    bbox_list = []
    img_bbox_list = []
    for chunk in row_chunks:
        row_text = chunk.get_text(scale=2, minimum_conf=70)
        text = text + row_text
        row_bboxes = chunk.get_text_bboxes(scale=2, level=4, minimum_conf=70)  # Line blocks
        bbox_list.extend(row_bboxes)

        # Next also generate image bboxes
        img_bboxes = chunk.get_image_bboxes(
            min_size=10,
            line_thickness=2,
            min_image_size=100,
            color_threshold=10000,
            n_recursions=4
        )
        img_bbox_list.extend(img_bboxes)

    logger.debug(text)

    ############ DEBUG PRINT SECTION CHUNKS
    for i, chunk in enumerate(row_chunks):
        start_point = (chunk.xmin, chunk.ymin)
        end_point = (chunk.xmax, chunk.ymax)
        color = (255, 255, 255)
        img = cv2.rectangle(img, start_point, end_point, color, 3)

    for i, bbox in enumerate(prelim_bbox_list):
        start_point = (bbox.xmin, bbox.ymin)
        end_point = (bbox.xmax, bbox.ymax)
        color = (255, 255, 0)
        img = cv2.rectangle(img, start_point, end_point, color, -1)

    for i, bbox in enumerate(bbox_list):
        start_point = (bbox.xmin, bbox.ymin)
        end_point = (bbox.xmax, bbox.ymax)
        color = (0, 0, 0)
        img = cv2.rectangle(img, start_point, end_point, color, 3)

    for i, bbox in enumerate(img_bbox_list):
        start_point = (bbox.xmin, bbox.ymin)
        end_point = (bbox.xmax, bbox.ymax)
        color = (0, 0, 225)
        img = cv2.rectangle(img, start_point, end_point, color, 5)

    cv2.imwrite(f'{image_fn.stem}_boundingboxes.jpg', img)
    ############ DEBUG PRINT SECTION CHUNKS

    # 3. Chunk aggressively for images, ignoring text boundaries




    """
    for bbox in bboxes:
        start_point = (bbox.xmin, bbox.ymin)
        end_point = (bbox.xmax, bbox.ymax)
        color = (255, 0, 0)
        img = cv2.rectangle(img, start_point, end_point, color, 2)
    """




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

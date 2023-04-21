import argparse
import json
import pathlib
import numpy as np
import logging
import pathlib
import shutil
import subprocess
import sys
import time
import os
import math
from collections import OrderedDict

import imagehash
import cv2
import pandas as pd
import PIL
import yaml

from cyoa_archives.predictor.image import CyoaImage
from cyoa_archives.predictor.deepdanbooru import DeepDanbooru

logger = logging.getLogger(__name__)

dd = DeepDanbooru('deepdanbooru-v3-20211112-sgd-e28', threshold=0.3)

def process_folder_or_file(item_path, data_dir, parent_tag, is_folder=False):
    cyoa_title = item_path.stem
    data_path = pathlib.Path(data_dir)

    # Load images into the path
    image_paths = []
    if is_folder:
        for extension in ['*.png', '*.jpg', '*.jpeg']:
            for imagepath in item_path.rglob(extension):
                image_paths.append(imagepath)
    else:
        image_paths.append(item_path)

    # Load hash table
    if not data_path.exists():
        raise OSError(f"Could not read folder: {data_path}")
    hash_dict = {}
    for item in os.scandir(data_path):
        item_path = pathlib.Path(item)
        if item_path.is_dir():
            hash_file = pathlib.Path.joinpath(item_path, 'hash.txt')
            with open(hash_file, 'r') as f:
                for line in f.readlines():
                    image_hash = line.strip()
                    hash_dict[image_hash] = item_path

    # Compute image hashes for each image
    existing_path = None
    hash_list = []
    for image_path in image_paths:
        image_hash = str(imagehash.average_hash(PIL.Image.open(str(image_path.resolve()))))
        hash_list.append(image_hash)
        if image_hash in hash_dict:
            existing_path = hash_dict[image_hash]


    # If hash was found, we exit and update the tags
    if existing_path:
        tag_file = pathlib.Path.joinpath(existing_path, 'tags.txt')
        with open(tag_file, 'a') as f:
            f.write(f'{pathlib.Path(parent_tag).stem}\n')
        hash_file = pathlib.Path.joinpath(existing_path, 'hash.txt')
        existing_hash_dict = {}
        with open(hash_file, 'r') as f:
            for line in f.readlines():
                image_hash = line.strip()
                existing_hash_dict[image_hash] = True
        with open(hash_file, 'a') as f:
            for image_hash in hash_list:
                if image_hash not in existing_hash_dict:
                    f.write(f'{image_hash}\n')
        return None

    # Otherwise, we process the image
    all_text = ''
    all_data = OrderedDict()
    total_pixels = 0
    page_count = 0
    for i, image_path in enumerate(image_paths):
        # Run processor
        logger.info(f'Processing image {i+1}/{len(image_paths)} in {cyoa_title}...')
        cyoa_image = CyoaImage(image_path)
        #cyoa_image.make_chunks()
        #this_text = cyoa_image.get_text()
        this_dd_data = cyoa_image.run_deepdanbooru_random(dd, 2)
        page_count = page_count + 1
        total_pixels = total_pixels + cyoa_image.area

        # Append data from multiple images
        #all_text = all_text + this_text
        for tag in this_dd_data:
            if tag in all_data:
                all_data[tag].extend(this_dd_data[tag])
            else:
                all_data[tag] = this_dd_data[tag]

    # Print results
    if len(all_data):
        outdir = pathlib.Path.joinpath(data_path, cyoa_title)
        if not outdir.exists():
            os.makedirs(outdir)

        hash_file = pathlib.Path.joinpath(outdir, 'hash.txt')
        tag_file = pathlib.Path.joinpath(outdir, 'tags.txt')
        #text_file = pathlib.Path.joinpath(outdir, 'text.txt')
        data_file = pathlib.Path.joinpath(outdir, 'dd.txt')
        info_file = pathlib.Path.joinpath(outdir, 'info.txt')
        with open(hash_file, 'w') as f:
            for image_hash in hash_list:
                f.write(f'{image_hash}\n')
        with open(tag_file, 'w') as f:
            f.write(f'{parent_tag}\n')
        #with open(text_file, 'w') as f:
        #    f.write(all_text)
        with open(data_file, 'w') as f:
            for tag in all_data:
                f.write(f'{np.average(all_data[tag])}\n')
        with open(info_file, 'w') as f:
            f.write(f'Pages: {page_count}\n')
            f.write(f'Pixels: {total_pixels}\n')
            f.write(f'Coverage: 2\n')
            f.write(f'Timestamp: {time.time()}\n')

    return None

def main(folder, data_dir):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    folder_path = pathlib.Path(folder)
    if not folder_path.exists():
        raise OSError(f"Could not read file: {folder}")

    # Scan directory
    for item in os.scandir(folder_path):
        item_path = pathlib.Path(item)
        # If is directory, then this is a cyoa folder
        if item_path.is_dir():
            process_folder_or_file(item_path, data_dir, parent_tag=folder_path.stem, is_folder=True)
        else:
            extensions = ['.png', '.jpg', '.jpeg']
            if item_path.suffix in extensions:
                process_folder_or_file(item_path, data_dir, parent_tag=folder_path.stem, is_folder=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a subreddit for submissions using praw."
    )
    parser.add_argument("-f", "--folder", help="Folder to process")
    parser.add_argument("-d", "--data_folder", help="Folder containing data")

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
    main(args.folder, args.data_folder)

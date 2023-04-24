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
import pandas
import PIL
import yaml

from PIL import Image
import imagehash

logger = logging.getLogger(__name__)

def process_folder_or_file(item_path, is_folder=False):
    image_paths = []
    if is_folder:
        for extension in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
            for image_path in item_path.rglob(extension):
                image_paths.append(image_path)
    else:
        image_paths = [item_path]

    # Now run hashing algorithm on all images in the directory
    hash_list = []
    for image in image_paths:

        try:
            # Hash the image (Let's use average hash because it's less tolerant)
            img = Image.open(image)
            image_hash = imagehash.average_hash(img)
            color_hash = imagehash.colorhash(img, binbits=3)
            image_hash_str = str(image_hash) + '_' + str(color_hash)
            hash_list.append(image_hash_str)
        except:
            logger.warning(f'Could not hash {image}!')

    return hash_list

def main(folder):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    folder_path = pathlib.Path(folder)
    if not folder_path.exists():
        raise OSError(f"Could not read file: {folder}")

    # Scan directory
    results = []
    for item in os.scandir(folder_path):
        author_path = pathlib.Path(item)
        author = author_path.stem
        logger.info(f'Now hashing: {author}')
        if author_path.is_dir():
            for sub_item in os.scandir(author_path):
                cyoa_path = pathlib.Path(sub_item)
                cyoa_title = cyoa_path.stem

                if cyoa_path.is_dir():
                    hashes = process_folder_or_file(cyoa_path, is_folder=True)
                    results.append({
                        'author': author,
                        'title': cyoa_title,
                        'hashes': ','.join(hashes)
                    })
                else:
                    extensions = ['.png', '.jpg', '.jpeg', '.webp']
                    if cyoa_path.suffix in extensions:
                        hashes = process_folder_or_file(cyoa_path, is_folder=False)
                        results.append({
                            'author': author,
                            'title': cyoa_title,
                            'hashes': ', '.join(hashes)
                        })


    # Print
    pd = pandas.DataFrame(results)
    pd.to_csv('allsync_hashes.csv')



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a subreddit for submissions using praw."
    )
    parser.add_argument("-f", "--folder", help="Folder to process")

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
    main(args.folder)

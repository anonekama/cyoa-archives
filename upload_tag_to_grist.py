"""Scan this directory for image hashes and update grist with the specified tag.

"""

import argparse
import logging
import pathlib
import sys

import imagehash
import yaml

from PIL import Image

from cyoa_archives.grist.api import GristAPIWrapper

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Parse args
parser = argparse.ArgumentParser(
    description="Parse a subreddit for submissions using praw."
)
parser.add_argument("-c", "--config_file", help="Configuration file to use")
parser.add_argument("-d", "--directory", help="Directory to scan for images")
parser.add_argument("-t", "--tag", help="Tag to append")
args = parser.parse_args()

if args.config_file:
    filepath = pathlib.Path(args.config_file)
    try:
        with open(filepath) as f:
            config = yaml.safe_load(f)
    except OSError:
        print(f"Could not read file: {filepath}")
        sys.exit(1)

# List all the images in this directory
directory = pathlib.Path(args.directory)
image_paths = []
for extension in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
    for image_path in directory.rglob(extension):
        image_paths.append(image_path)

# Hash all the images in this directory
image_hashes_dictionary = {}
for image_path in image_paths:
    img = Image.open(image_path)
    image_hash = imagehash.average_hash(img)
    color_hash = imagehash.colorhash(img, binbits=3)
    image_hash_str = str(image_hash) + '_' + str(color_hash)
    image_hashes_dictionary[image_hash_str] = True

# Set up API
api = GristAPIWrapper.from_config(config.get('grist'))
title_pd = api.fetch_table_pd('CYOAs', col_names=['id', 'content_tags'])
grist_pd = api.fetch_table_pd('Records', col_names=['id', 'image_hashes', 'cyoa'])
cyoa_pd = grist_pd.loc[grist_pd['cyoa'] > 0]
logger.debug(len(cyoa_pd))

# Loop through grist hashes
hash_table = {}
for index, row in cyoa_pd.iterrows():
    g_id = row['id']
    cyoa = row['cyoa']
    image_hashes = row['image_hashes']

    if not image_hashes:
        continue

    # Loop through hashes
    for hash_string in image_hashes.split(','):
        trimmed_hash = hash_string.strip()
        if trimmed_hash not in hash_table:
            hash_table[trimmed_hash] = [cyoa]
        else:
            hash_table[trimmed_hash].append(cyoa)
logger.debug(len(hash_table))

# Loop through hashes and save collisions
cyoa_ids = []
for hash_string in image_hashes_dictionary:
    logger.debug(hash_string)
    if hash_string in hash_table:
        logger.debug('FOUND HASH')
        cyoa_ids.extend(hash_table[hash_string])
cyoa_ids = list(set(cyoa_ids))
logger.debug(cyoa_ids)
logger.debug(len(cyoa_ids))

# Loop through cyoa table and save results
result = []
for index, row in title_pd.iterrows():
    g_id = row['id']
    content_tags = row['content_tags']
    if g_id in cyoa_ids:
        if not content_tags:
            content_tags = ['L']
        if int(args.tag) not in content_tags:
            content_tags.append(int(args.tag))
            result.append({
                'id': g_id,
                'content_tags': content_tags
            })

# Submit result to grist
api.update_records('CYOAs', result, mock=False, prompt=True)

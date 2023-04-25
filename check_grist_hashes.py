import argparse
import logging
import pathlib
import sys

import yaml

from cyoa_archives.grist.api import GristAPIWrapper

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Parse args
parser = argparse.ArgumentParser(
    description="Parse a subreddit for submissions using praw."
)
parser.add_argument("-c", "--config_file", help="Configuration file to use")
args = parser.parse_args()

if args.config_file:
    filepath = pathlib.Path(args.config_file)
    try:
        with open(filepath) as f:
            config = yaml.safe_load(f)
    except OSError:
        print(f"Could not read file: {filepath}")
        sys.exit(1)

# Set up API
api = GristAPIWrapper.from_config(config.get('grist'))
title_pd = api.fetch_table_pd('CYOAs', col_names=['uuid', 'official_title'])
grist_pd = api.fetch_table_pd('Records', col_names=[
        'id', 'cyoa_uuid', 'image_hashes', 'cyoa', 'title'
    ])
cyoa_pd = grist_pd.loc[grist_pd['cyoa'] > 0]
logger.debug(len(cyoa_pd))

cyoa_titles = {}
for index, row in title_pd.iterrows():
    uuid = row['uuid']
    cyoa_titles[uuid] = row['official_title']

# Iterate and track hashes
hash_table = {}
for index, row in cyoa_pd.iterrows():
    g_id = row['id']
    cyoa = row['cyoa']
    cyoa_uuid = row['cyoa_uuid']
    image_hashes = row['image_hashes']
    title = row['title']

    if not image_hashes:
        continue

    # Loop through hashes
    for hash_string in image_hashes.split(','):
        trimmed_hash = hash_string.strip()
        if trimmed_hash not in hash_table:
            hash_table[trimmed_hash] = [cyoa_titles[cyoa_uuid]]
        else:
            if cyoa_titles[cyoa_uuid] not in hash_table[trimmed_hash]:
                hash_table[trimmed_hash].append(cyoa_titles[cyoa_uuid])

# Loop through hashes and print collisions
for hash_string, value in hash_table.items():
    if len(value) > 1:
        print(f'{hash_string}\t{value}')
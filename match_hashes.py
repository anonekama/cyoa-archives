import argparse
import logging
import pathlib
import sys

import pandas
import yaml

from cyoa_archives.grist.api import GristAPIWrapper
from cyoa_archives.grist.routine import grist_update_item

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Parse args
parser = argparse.ArgumentParser(
    description="Parse a subreddit for submissions using praw."
)
parser.add_argument("-c", "--config_file", help="Configuration file to use")
parser.add_argument("-x", "--hash_file", help="Hash file to use")
parser.add_argument("-t", "--hash2uuid_file", help="Hash to uuid file to use")
args = parser.parse_args()

if args.config_file:
    filepath = pathlib.Path(args.config_file)
    try:
        with open(filepath) as f:
            config = yaml.safe_load(f)
    except OSError:
        print(f"Could not read file: {filepath}")
        sys.exit(1)

# Open hash files
allsync_hash_pd = pandas.read_csv(args.hash_file)
allsync_2_uuid_pd = pandas.read_csv(args.hash2uuid_file)
print(allsync_hash_pd)
print(allsync_2_uuid_pd)

allsync_2_uuid = {}
for index, row in allsync_2_uuid_pd.iterrows():
    title = row['title']
    uuid = row['uuid']
    allsync_2_uuid[title] = uuid

# Process allsync hashes
allsync_hashes = {}
for index, row in allsync_hash_pd.iterrows():
    title = row['title']
    hashes = str(row['hashes']).split(',')
    for hash_string in hashes:
        if title in allsync_2_uuid:
            allsync_hashes[hash_string.strip()] = allsync_2_uuid[title]

# Now get grist hashes
# Set up API
api = GristAPIWrapper.from_config(config.get('grist'))
grist_pd = api.fetch_table_pd('Records', col_names=[
        'id', 'cyoa_uuid', 'image_hashes', 'cyoa', 'is_cyoa'
    ])
cyoa_pd = api.fetch_table_pd('CYOAs', col_names=[ 'id', 'uuid' ])
main_pd = grist_pd.loc[grist_pd['is_cyoa'].eq('Yes')]


# Set up uuid to cyoa id table
uuid_2_id = {}
for index, row in cyoa_pd.iterrows():
    g_id = row['id']
    uuid = row['uuid']
    uuid_2_id[uuid] = g_id

# Iterate and track hashes
grist_hashes = {}
for index, row in main_pd.iterrows():
    g_id = row['id']
    cyoa = row['cyoa']
    cyoa_uuid = row['cyoa_uuid']
    image_hashes = row['image_hashes']

    if not cyoa or cyoa == 0:
        continue

    if not image_hashes:
        continue

    # Loop through hashes
    for hash_string in image_hashes.split(','):
        trimmed_hash = hash_string.strip()
        if trimmed_hash not in grist_hashes:
            grist_hashes[trimmed_hash] = cyoa_uuid
print(len(grist_hashes))

# Loop through again and assemble update dataframe
results = []
for index, row in main_pd.iterrows():
    g_id = row['id']
    cyoa = row['cyoa']
    cyoa_uuid = row['cyoa_uuid']
    image_hashes = row['image_hashes']

    if cyoa:
        continue

    if not image_hashes:
        continue

    collisions = []
    for hash_string in image_hashes.split(','):
        trimmed_hash = hash_string.strip()
        if trimmed_hash in grist_hashes:
            collisions.append(grist_hashes[trimmed_hash])
        elif trimmed_hash in allsync_hashes:
            collisions.append(allsync_hashes[trimmed_hash])

    # Get the maximum occurance
    if collisions:
        max_uuid = max(set(collisions), key = collisions.count)
        if max_uuid in uuid_2_id:
            result = {
                'id': g_id,
                'cyoa': uuid_2_id[max_uuid]
            }
            results.append(result)

# Update grist
print(len(results))
grist_update_item(config, 'Records', results)
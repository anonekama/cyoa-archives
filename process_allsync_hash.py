import argparse
import json
import pathlib
import numpy as np
import logging
import pathlib

import sys

import pandas
import PIL
import yaml

from cyoa_archives.grist.api import GristAPIWrapper

logger = logging.getLogger(__name__)


def main(config, hashfile):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # folder_path = pathlib.Path(hashfile)
    df = pandas.read_csv(hashfile).dropna()
    print(df)

    # Get grist hashes
    api = GristAPIWrapper.from_config(config.get('grist'))
    title_pd = api.fetch_table_pd('CYOAs', col_names=['uuid', 'official_title'])
    grist_pd = api.fetch_table_pd('Records', col_names=[
        'id', 'cyoa_uuid', 'image_hashes2', 'cyoa', 'title'
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
        image_hashes = row['image_hashes2']
        title = row['title']

        if not image_hashes:
            continue

        # Loop through hashes
        for hash_string in image_hashes.split(','):
            trimmed_hash = hash_string.strip()
            if trimmed_hash not in hash_table:
                hash_table[trimmed_hash] = cyoa_uuid

    # Iterate through hashes
    results = []
    for index, row in df.iterrows():
        author = row['author'].split("'")[0]
        title = row['title']
        hashes = str(row['hashes']).split(",")
        matches = {}
        for hash_string in hashes:
            if hash_string in hash_table:
                uuid = hash_table[hash_string]
                if uuid in matches:
                    matches[uuid] = matches[uuid] + 1
                else:
                    matches[uuid] = 1
        max_uuid_value = 0
        max_uuid = None
        for uuid in matches:
            if matches[uuid] > max_uuid_value:
                max_uuid = uuid
                max_uuid_value = matches[uuid]
        results.append({
            'author': author,
            'title': title,
            'cyoa': cyoa_titles[max_uuid] if max_uuid else '',
            'count': max_uuid_value
        })

    result_df = pandas.DataFrame(results)
    print(result_df)
    result_df.to_csv('all_sync_hash_matches.csv')




if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a subreddit for submissions using praw."
    )
    parser.add_argument("-s", "--hashfile", help="File with allsync hashes")
    parser.add_argument("-c", "--config_file", help="Configuration file to use")

    # Parse arguments
    args = parser.parse_args()
    # Load arguments from configuration file if provided
    if args.config_file:
        filepath = pathlib.Path(args.config_file)
        try:
            with open(filepath) as f:
                config = yaml.safe_load(f)
        except OSError:
            print(f"Could not read file: {filepath}")
            sys.exit(1)

    # Pass to main function
    main(config, args.hashfile)

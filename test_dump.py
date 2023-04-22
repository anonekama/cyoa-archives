import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import yaml
import logging
import time

from PIL import Image
import imagehash

from cyoa_archives.grist.api import GristAPIWrapper

logger = logging.getLogger(__name__)

# Parse args
parser = argparse.ArgumentParser(
    description="Parse a subreddit for submissions using praw."
)
parser.add_argument("-c", "--config_file", help="Configuration file to use")
parser.add_argument("-d", "--database_folder", help="Folder to use as database")
parser.add_argument("-t", "--temporary_folder", help="Folder to use to temporarily keep files")
args = parser.parse_args()

if args.config_file:
    filepath = pathlib.Path(args.config_file)
    try:
        with open(filepath) as f:
            config = yaml.safe_load(f)
    except OSError:
        print(f"Could not read file: {filepath}")
        sys.exit(1)

# If the database folder does not exist, create it
dbdir = pathlib.Path(args.database_folder)
tempdir = pathlib.Path(args.temporary_folder)
if not dbdir.exists():
    logger.info(f'Making database folder at: {dbdir.resolve()}')
    os.makedirs(dbdir)


# Set up API
api = GristAPIWrapper(config.get('grist'))
grist_pd = api.fetch_table_pd('Records', col_names=[
        'id', 'cyoa_uuid', 'is_cyoa', 'static_url', 'broken_link', 'image_hashes', 'created_utc', 'cyoa'
    ])
cyoa_pd = grist_pd.loc[grist_pd['cyoa'] > 0].sort_values(by=['created_utc'], ascending=False)
logger.debug(len(cyoa_pd))


result_list = []
for index, row in cyoa_pd.iterrows():
    g_id = row['id']
    cyoa_uuid = row['cyoa_uuid']
    is_cyoa = row['is_cyoa']
    static_url = row['static_url']
    broken_link = row['broken_link']
    image_hashes = row['image_hashes']

    # Skip irrelevant rows
    if not static_url or broken_link or image_hashes:
        continue

    # Empty temporary directory
    if tempdir.exists():
        logger.info(f'Deleting directory: {tempdir.resolve()}')
        shutil.rmtree(tempdir.resolve())
        os.makedirs(tempdir)

    # Download using gallery-dl
    subprocess.run(['gallery-dl', static_url, '-d', tempdir.resolve()], universal_newlines=True)
    image_paths = []
    for extension in ['*.png', '*.jpg', '*.jpeg']:
        for image_path in tempdir.rglob(extension):
            image_paths.append(image_path)
    logger.debug(image_paths)

    # Now run hashing algorithm on all images in the temporary directory
    hash_list = []
    for image in image_paths:

        # Hash the image (Let's use average hash because it's less tolerant)
        image_hash = imagehash.average_hash(Image.open(image))
        image_hash_str = str(image_hash)
        hash_list.append(image_hash_str)

        # If it's an imgur image, save it
        if 'imgur.' in static_url:
            cyoa_directory = pathlib.Path.joinpath(dbdir, cyoa_uuid)
            if not cyoa_directory.exists():
                logger.info(f'Making database folder at: {dbdir.resolve()}')
                os.makedirs(cyoa_directory)
            image_path_copy = pathlib.Path.joinpath(dbdir, cyoa_uuid, image_hash_str + image.suffix)
            shutil.copyfile(image, image_path_copy)

    # Detect no downloads
    is_broken_link = False
    if not image_paths:
        is_broken_link = True

    # 
    result_list.append({
        'id': g_id,
        'image_hashes': ', '.join(hash_list),
        'broken_link': is_broken_link
    })

    time.sleep(3)

# Update grist
api.update_records('Records', result_list, mock=False, prompt=True)

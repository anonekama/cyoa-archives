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
logging.basicConfig(level=logging.DEBUG)

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
api = GristAPIWrapper.from_config(config.get('grist'))
grist_pd = api.fetch_table_pd('Records', col_names=[
        'id', 'cyoa_uuid', 'is_cyoa', 'static_url', 'interactive_url', 'broken_link', 'image_hashes2', 'created_utc',
        'cyoa', 'link_flair_text', 'title'
    ])
cyoa_pd = grist_pd.loc[grist_pd['is_cyoa'].eq('Yes')].sort_values(by=['created_utc'], ascending=False)
logger.debug(len(cyoa_pd))


result_list = []
count = 0
for index, row in cyoa_pd.iterrows():
    g_id = row['id']
    cyoa_uuid = row['cyoa_uuid']
    is_cyoa = row['is_cyoa']
    static_url = row['static_url']
    interactive_url = row['interactive_url']
    broken_link = row['broken_link']
    image_hashes = row['image_hashes']
    flair = row['link_flair_text']
    title = row['title']

    try:

        # Skip irrelevant rows
        if not static_url or broken_link or image_hashes or interactive_url:
            continue

        # Skip posts flagged as interactive
        if flair and 'Interactive' in flair:
            continue

        # Empty temporary directory
        if tempdir.exists():
            logger.info(f'Deleting directory: {tempdir.resolve()}')
            shutil.rmtree(tempdir.resolve())
            os.makedirs(tempdir)

        # Download using gallery-dl
        subprocess.run(['gallery-dl', static_url, '-d', tempdir.resolve(), '--range', '1-100'], universal_newlines=True)
        image_paths = []
        for extension in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
            for image_path in tempdir.rglob(extension):
                image_paths.append(image_path)
        logger.debug(image_paths)

        # Now run hashing algorithm on all images in the temporary directory
        hash_list = []
        for i, image in enumerate(image_paths):

            # Hash the image (Let's use average hash because it's less tolerant)
            img = Image.open(image)
            image_hash = imagehash.average_hash(img)
            color_hash = imagehash.colorhash(img, binbits=3)
            image_hash_str = str(image_hash) + '_' + str(color_hash)
            hash_list.append(image_hash_str)

            # If it's an imgur image, save it
            if 'imgur.' in static_url:
                if cyoa_uuid:
                    cyoa_directory = pathlib.Path.joinpath(dbdir, cyoa_uuid)
                else:
                    cyoa_directory = pathlib.Path.joinpath(dbdir, title.replace('/', '').strip())
                if not cyoa_directory.exists():
                    logger.info(f'Making database folder at: {cyoa_directory.resolve()}')
                    os.makedirs(cyoa_directory)
                image_path_copy = pathlib.Path.joinpath(cyoa_directory, image.stem + image.suffix)
                shutil.copyfile(image, image_path_copy)

        # Detect no downloads
        is_broken_link = False
        if not image_paths:
            is_broken_link = True

        # Append results
        result_list.append({
            'id': g_id,
            'image_hashes': ', '.join(hash_list),
            'broken_link': is_broken_link
        })

    except:
        logger.warning(f'Unable to has image: {static_url}')

    time.sleep(3)
    count = count + 1
    if count % 25 == 0:
        api.update_records('Records', result_list, mock=False, prompt=False)
        hash_list = []

# Update grist
api.update_records('Records', result_list, mock=False, prompt=False)

import argparse
import logging
import pathlib
import shutil
import subprocess
import os

import imagehash
import pandas
from PIL import Image

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Parse args
parser = argparse.ArgumentParser(
    description="Parse a subreddit for submissions using praw."
)
parser.add_argument("-u", "--url", help="URL to gallery-dl")
parser.add_argument("-x", "--hash_file", help="Hash file to use")
parser.add_argument("-t", "--temporary_folder", help="Folder to use to temporarily keep files")
args = parser.parse_args()
tempdir = pathlib.Path(args.temporary_folder)

# Open hash files
allsync_hash_pd = pandas.read_csv(args.hash_file)
# print(allsync_hash_pd)


# Process allsync hashes
allsync_hashes = {}
for index, row in allsync_hash_pd.iterrows():
    title = row['title']
    hashes = str(row['hashes']).split(',')
    for hash_string in hashes:
        allsync_hashes[hash_string.strip()] = title

# Now download image
# Empty temporary directory
if tempdir.exists():
    logger.info(f'Deleting directory: {tempdir.resolve()}')
    shutil.rmtree(tempdir.resolve())
os.makedirs(tempdir)

# Download using gallery-dl
subprocess.run(['gallery-dl', args.url, '-d', tempdir.resolve()], universal_newlines=True)

# Now run application on all images in the temporary directory
image_paths = []
for extension in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
    for image_path in tempdir.rglob(extension):
        image_paths.append(image_path)
logger.debug(image_paths)

# Hash
hash_list = []
for image in image_paths:
    # Hash the image (Let's use average hash because it's less tolerant)
    img = Image.open(image)
    image_hash = imagehash.average_hash(img)
    color_hash = imagehash.colorhash(img, binbits=3)
    image_hash_str = str(image_hash) + '_' + str(color_hash)
    hash_list.append(image_hash_str)

matches = []
for hash_string in hash_list:
    if hash_string in allsync_hashes:
        matches.append(allsync_hashes[hash_string])

if matches:
    print(matches)
else:
    print('No matches found')
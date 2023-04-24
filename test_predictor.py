import argparse
import logging
import math
import os
import pathlib
import shutil
import subprocess
import sys
import time

from collections import OrderedDict

import numpy as np
import yaml

from cyoa_archives.grist.routine import grist_fetch_deepl, grist_update_item
from cyoa_archives.predictor.deepdanbooru import DeepDanbooru
from cyoa_archives.predictor.image import CyoaImage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main(config, database_folder, temporary_folder):
    # TODO: Assert that configuration file is appropriately formatted

    # Get the list of CYOAs to download
    cyoa_list = grist_fetch_deepl(config)
    logger.debug(cyoa_list)

    # Initialize deepdanbooru
    predictor_config = config.get('predictor')
    dd = DeepDanbooru(predictor_config.get('model_path'), special_tags=predictor_config.get('dd_tags'),
                      threshold=predictor_config.get('dd_threshold'))
    # kw_model = KeyBERT(predictor_config.get('keybert_model'))

    # Run loop
    for index, row in cyoa_list.iterrows():
        g_id = row['id']
        uuid = row['uuid']
        interactive_url = row['interactive_url']
        cyoa_title = row['official_title']
        static_url = row['static_url']

        # Empty temporary directory
        if temporary_folder.exists():
            logger.info(f'Deleting directory: {temporary_folder.resolve()}')
            shutil.rmtree(temporary_folder.resolve())
            os.makedirs(temporary_folder)

        # Download using gallery-dl
        subprocess.run(['gallery-dl', static_url, '-d', temporary_folder.resolve()], universal_newlines=True)

        # Now run application on all images in the temporary directory
        image_paths = []
        for extension in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
            for image_path in temporary_folder.rglob(extension):
                image_paths.append(image_path)
        logger.debug(image_paths)

        # TODO: Consider adding image hash function

        # Run the main processor loop
        all_text = ''
        all_data = OrderedDict()
        total_pixels = 0
        page_count = 0
        for i, image_path in enumerate(image_paths):
            # Run processor
            logger.info(f'Processing image {i + 1}/{len(image_paths)} in {cyoa_title}...')
            cyoa_image = CyoaImage(image_path)
            cyoa_image.make_chunks()
            this_text = cyoa_image.get_text()
            this_dd_data = cyoa_image.run_deepdanbooru_random(dd, coverage=predictor_config.get('coverage'))
            page_count = page_count + 1
            total_pixels = total_pixels + cyoa_image.area

            # Append data from multiple images
            all_text = all_text + " " + this_text
            for tag in this_dd_data:
                if tag in all_data:
                    all_data[tag].extend(this_dd_data[tag])
                else:
                    all_data[tag] = this_dd_data[tag]

        if not len(all_data):
            logger.info('Predictor found no results for this image.')

        # Update record
        timestamp = time.time()
        if len(all_data) == 0 or total_pixels < 4194304:
            # We do not report results for small images (sampling is not accurate)
            dd_sex = [0]
            dd_girl = [0]
            dd_boy = [0]
            dd_other = [0]
            dd_furry = [0]
            dd_bdsm = [0]
            dd_3d = [0]
        else:
            dd_sex = all_data.get('dd_sex')
            dd_girl = all_data.get('dd_girl')
            dd_boy = all_data.get('dd_boy')
            dd_other = all_data.get('dd_other')
            dd_furry = all_data.get('dd_furry')
            dd_bdsm = all_data.get('dd_bdsm')
            dd_3d = all_data.get('dd_3d')
        record = {
            'id': g_id,
            'pages': page_count,
            'pixels': int(math.sqrt(total_pixels)),
            'n_char': len(all_text),
            'text': all_text.replace('\n', ' '),
            'dd_sex': np.average(dd_sex) * 100,
            'dd_girl': np.average(dd_girl) * 100,
            'dd_boy': np.average(dd_boy) * 100,
            'dd_other': np.average(dd_other) * 100,
            'dd_furry': np.average(dd_furry) * 100,
            'dd_bdsm': np.average(dd_bdsm) * 100,
            'dd_3d': np.average(dd_3d) * 100,
            'deepl_timestamp': timestamp
        }
        grist_update_item(config, 'CYOAs', record)

        # Write results to db folder
        outdir = pathlib.Path.joinpath(database_folder, uuid)
        if not outdir.exists():
            os.makedirs(outdir)

        text_file = pathlib.Path.joinpath(outdir, 'text.txt')
        data_file = pathlib.Path.joinpath(outdir, 'dd.txt')
        info_file = pathlib.Path.joinpath(outdir, 'info.txt')
        with open(text_file, 'w') as f:
            f.write(all_text)
        with open(data_file, 'w') as f:
            for tag in all_data:
                f.write(f'{tag}\t{np.average(all_data[tag])}\n')
        with open(info_file, 'w') as f:
            f.write(f'Pages: {page_count}\n')
            f.write(f'Pixels: {total_pixels}\n')
            f.write(f'Coverage: {predictor_config.get("coverage")}\n')
            f.write(f'Threshold: {predictor_config.get("coverage")}\n')
            f.write(f'Timestamp: {timestamp}\n')

        # Delete tempdir
        if tempdir.exists():
            logger.info(f'Deleting directory: {tempdir.resolve()}')
            shutil.rmtree(tempdir.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a subreddit for submissions using praw."
    )
    parser.add_argument("-c", "--config_file", help="Configuration file to use")
    parser.add_argument("-d", "--database_folder", help="Folder to use as database")
    parser.add_argument("-t", "--temporary_folder", help="Folder to use to temporarily keep files")

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

    # If the database folder does not exist, create it
    dbdir = pathlib.Path(args.database_folder)
    tempdir = pathlib.Path(args.temporary_folder)
    if not dbdir.exists():
        logger.info(f'Making database folder at: {dbdir.resolve()}')
        os.makedirs(dbdir)

    # Pass to main function
    main(
        config,
        dbdir,
        tempdir
    )

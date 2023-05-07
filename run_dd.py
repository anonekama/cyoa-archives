"""Run Deepdanbooru script.

Download static and interactive CYOAs from Grist, randomly sample images, and run deep danbooru.

Typical usage:
    python3 run_dd.py -c config.yaml -t temp

"""

__version__ = 0.2

import argparse
import logging
import math
import os
import pathlib
import sys
import time

from collections import OrderedDict
from typing import Dict

import numpy as np
import yaml

from cyoa_archives.grist.api import GristAPIWrapper
from cyoa_archives.grist.routine import grist_update_item
from cyoa_archives.scrapers.download import CyoaDownload
from cyoa_archives.predictor.image import CyoaImage
from cyoa_archives.predictor.deepdanbooru import DeepDanbooru

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keybert gives warnings unless parallelism is disabled
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def main(config: Dict, temporary_folder: pathlib.Path, database_folder: pathlib.Path) -> None:
    """Main method for script.

    :param config: A configuration object.
    :param temporary_folder: Path to the temporary folder to use (warning: will be frequently deleted and replaced).
    """
    # TODO: Assert that configuration file is appropriately formatted

    # Parse configuration file
    grist_config = config.get('grist')
    SERVER_URL = grist_config.get('server_url')
    DOCUMENT_ID = grist_config.get('document_id')
    API_KEY = grist_config.get('api_key')

    predictor_config = config.get('predictor')
    MODEL_PATH = predictor_config.get('model_path')
    DD_TAGS = predictor_config.get('dd_tags')
    DD_THRESHOLD = predictor_config.get('dd_threshold')
    DD_COVERAGE = predictor_config.get('coverage')
    MAX_TALL_WIDTH = predictor_config.get('max_width')
    MAX_WIDE_WIDTH = predictor_config.get('max_wide_width')
    DD_MIN_PIXELS = 4194304

    # Initialize deepdanbooru
    predictor_config = config.get('predictor')
    dd = DeepDanbooru(MODEL_PATH, special_tags=DD_TAGS, threshold=DD_THRESHOLD)
    downloader = CyoaDownload(tempdir=temporary_folder)

    # Fetch CYOAs from Grist
    api = GristAPIWrapper(server_url=SERVER_URL, document_id=DOCUMENT_ID, api_key=API_KEY)
    cyoa_pd = api.fetch_table_pd('CYOAs', col_names=[
        'id', 'uuid', 'deepl', 'deepl_timestamp', 'media', 'static_url', 'interactive_url', 'official_title',
    ])

    # Run loop
    for index, row in cyoa_pd.iterrows():
        g_id = row['id']
        uuid = row['uuid']
        deepl = row['deepl']
        deepl_timestamp = row['deepl_timestamp']
        media = row['media']
        interactive_url = row['interactive_url']
        static_url = row['static_url']
        official_title = row['official_title']

        # Skip records that don't pass criteria
        if not media or media == 'Other':
            continue
        if not static_url and not interactive_url:
            continue
        if deepl_timestamp and not deepl:
            continue

        # Download using gallery-dl or selenium
        # TODO: Handle raw html image scraping
        # TODO: Fail gracefully
        image_paths = []
        logger.info(f'Attempting to download {official_title}...')
        if interactive_url:
            image_paths = downloader.interactive_dl(interactive_url)
        elif static_url:
            image_paths = downloader.gallery_dl(static_url)

        # Run the main processor loop
        all_data = OrderedDict()
        total_pixels = 0
        page_count = 0
        for i, image_path in enumerate(image_paths):
            logger.info(f'Processing image {i + 1}/{len(image_paths)} in {official_title}...')
            cyoa_image = CyoaImage(image_path)
            #cyoa_image.make_chunks()
            this_dd_data = cyoa_image.run_deepdanbooru_random(dd, coverage=DD_COVERAGE)
            page_count = page_count + 1
            total_pixels = total_pixels + cyoa_image.normalized_area(
                max_tall_image=MAX_TALL_WIDTH,
                max_wide_image=MAX_WIDE_WIDTH
            )

            # Append data from multiple images
            for tag in this_dd_data:
                if tag in all_data:
                    all_data[tag].extend(this_dd_data[tag])
                else:
                    all_data[tag] = this_dd_data[tag]

        # Assemble result and update Grist
        timestamp = time.time()
        if len(all_data) == 0 or total_pixels < DD_MIN_PIXELS:
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
        result = {
            'id': g_id,
            'pages': page_count,
            'pixels': int(math.sqrt(total_pixels)),
            'dd_sex': np.average(dd_sex) * 100,
            'dd_girl': np.average(dd_girl) * 100,
            'dd_boy': np.average(dd_boy) * 100,
            'dd_other': np.average(dd_other) * 100,
            'dd_furry': np.average(dd_furry) * 100,
            'dd_bdsm': np.average(dd_bdsm) * 100,
            'dd_3d': np.average(dd_3d) * 100,
            'deepl_timestamp': timestamp,
            'deepl': False
        }
        grist_update_item(config, 'CYOAs', result)

        # Write results to db folder
        outdir = pathlib.Path.joinpath(database_folder, uuid)
        if not outdir.exists():
            os.makedirs(outdir)

        data_file = pathlib.Path.joinpath(outdir, 'dd.txt')
        info_file = pathlib.Path.joinpath(outdir, 'info.txt')
        with open(data_file, 'w') as f:
            for tag in all_data:
                f.write(f'{tag}\t{np.average(all_data[tag])}\n')
        with open(info_file, 'w') as f:
            f.write(f'Pages: {page_count}\n')
            f.write(f'Pixels: {total_pixels}\n')
            f.write(f'Coverage: {predictor_config.get("coverage")}\n')
            f.write(f'Threshold: {predictor_config.get("coverage")}\n')
            f.write(f'Timestamp: {timestamp}\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download CYOA images (static or interactive), run tesseract and keybert."
    )
    parser.add_argument("-c", "--config_file", help="Configuration file to use")
    parser.add_argument("-t", "--temporary_folder", help="Folder to use to temporarily keep files")
    parser.add_argument("-d", "--database_folder", help="Folder to use to store deepdanbooru results")

    # Parse arguments
    args = parser.parse_args()

    # Load arguments from configuration file if provided
    if args.config_file:
        filepath = pathlib.Path(args.config_file)
        try:
            with open(filepath) as f:
                config = yaml.safe_load(f)
        except OSError:
            logger.error(f"Could not read file: {filepath.resolve()}")
            sys.exit(1)

    # Pass to main function
    main(
        config,
        pathlib.Path(args.temporary_folder),
        pathlib.Path(args.database_folder)
    )

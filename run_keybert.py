"""Run Keybert script.

Download static and interactive CYOAs from Grist and perform OCR with Tesseract and keyword extraction with Keybert.
By default, we run this script on every CYOA that lacks an 'ocr_timestamp' on Grist. However, CYOAs that are marked
with 'deepl'=True will also be reprocessed. We skip CYOAs that lack a 'media' attribute or are of "Other" media type.

Typical usage:
    python3 run_keybert.py -c config.yaml -t temp

"""

__version__ = 0.2

import argparse
import logging
import math
import os
import pathlib
import sys
import time

from typing import Dict

from keybert import KeyBERT
import yaml

from cyoa_archives.grist.api import GristAPIWrapper
from cyoa_archives.grist.routine import grist_update_item
from cyoa_archives.scrapers.download import CyoaDownload
from cyoa_archives.predictor.image import CyoaImage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keybert gives warnings unless parallelism is disabled
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def main(config: Dict, temporary_folder: pathlib.Path) -> None:
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
    KEYBERT_MODEL = predictor_config.get('keybert_model')
    MAX_TALL_WIDTH = predictor_config.get('max_width')
    MAX_WIDE_WIDTH = predictor_config.get('max_wide_width')
    KEYBERT_MIN_CHARS = predictor_config.get('keybert_min_chars')
    KEYBERT_THRESHOLD = predictor_config.get('keybert_threshold')

    # Initialize keybert
    kw_model = KeyBERT(KEYBERT_MODEL)
    downloader = CyoaDownload(tempdir=temporary_folder)

    # Fetch CYOAs from Grist
    api = GristAPIWrapper(server_url=SERVER_URL, document_id=DOCUMENT_ID, api_key=API_KEY)
    cyoa_pd = api.fetch_table_pd('CYOAs', col_names=[
        'id', 'deepl', 'ocr_timestamp', 'media', 'static_url', 'interactive_url', 'official_title',
    ])

    # Run loop
    for index, row in cyoa_pd.iterrows():
        g_id = row['id']
        deepl = row['deepl']
        ocr_timestamp = row['ocr_timestamp']
        media = row['media']
        interactive_url = row['interactive_url']
        static_url = row['static_url']
        official_title = row['official_title']

        # Skip records that don't pass criteria
        if not media or media == 'Other':
            continue
        if not static_url and not interactive_url:
            continue
        if ocr_timestamp and not deepl:
            continue

        # Download using gallery-dl or selenium
        # TODO: Handle raw html image scraping
        # TODO: Fail gracefully
        image_paths = []
        if interactive_url:
            image_paths = downloader.interactive_dl(interactive_url)
        elif static_url:
            image_paths = downloader.gallery_dl(static_url)

        # Run the main processor loop
        all_text = ''
        total_pixels = 0
        page_count = 0
        for i, image_path in enumerate(image_paths):
            logger.info(f'Processing image {i + 1}/{len(image_paths)} in {official_title}...')
            cyoa_image = CyoaImage(image_path)
            cyoa_image.make_chunks()
            all_text = all_text + " " + cyoa_image.get_text()
            page_count = page_count + 1
            total_pixels = total_pixels + cyoa_image.normalized_area(
                max_tall_image=MAX_TALL_WIDTH,
                max_wide_image=MAX_WIDE_WIDTH
            )
        logger.info(f'Tesseract found {len(all_text)} characters in {official_title}.')

        # Run keybert
        top_keywords = []
        if len(all_text) < KEYBERT_MIN_CHARS:
            # If not enough words, return nothing
            top_keywords = ['n/a']
        else:
            kb_output = kw_model.extract_keywords(all_text, keyphrase_ngram_range=(1, 1), stop_words=None, top_n=10)
            for keyword in kb_output:
                word = keyword[0]
                conf = keyword[1]
                if conf > KEYBERT_THRESHOLD:
                    top_keywords.append(word)
            logger.info(f'Keybert output: {top_keywords}')

        # Assemble result and update Grist
        timestamp = time.time()
        result = {
            'id': g_id,
            'pages': page_count,
            'pixels': int(math.sqrt(total_pixels)),
            'n_char': len(all_text),
            'text': all_text.replace('\n', ' '),
            'keybert': ', '.join(top_keywords),
            'ocr_timestamp': timestamp,
            'deepl': False
        }
        grist_update_item(config, 'CYOAs', result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download CYOA images (static or interactive), run tesseract and keybert."
    )
    parser.add_argument("-c", "--config_file", help="Configuration file to use")
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
            logger.error(f"Could not read file: {filepath.resolve()}")
            sys.exit(1)

    # Pass to main function
    main(
        config,
        pathlib.Path(args.temporary_folder)
    )

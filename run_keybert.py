import argparse
import json
import logging
import math
import numpy as np
import os
import pathlib
import shutil
import subprocess
import sys
import time

from collections import OrderedDict

from keybert import KeyBERT
import pandas as pd
import yaml

from cyoa_archives.grist.routine import grist_fetch_keybert, grist_update_item
from cyoa_archives.scrapers.interactive import download_interactive

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main(config, database_folder, temporary_folder):
    # TODO: Assert that configuration file is appropriately formatted

    cyoa_list = grist_fetch_keybert(config)
    logger.debug(cyoa_list)

    # Initialize keybert
    predictor_config = config.get('predictor')
    kw_model = KeyBERT(predictor_config.get('keybert_model'))

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
        if interactive_url:
            download_interactive(interactive_url, temporary_folder.resolve())
        elif static_url:
            subprocess.run(['gallery-dl', static_url, '-d', temporary_folder.resolve()], universal_newlines=True)

        # Now run application on all images in the temporary directory
        image_paths = []
        for extension in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
            for image_path in temporary_folder.rglob(extension):
                image_paths.append(image_path)
        logger.debug(image_paths)

    # Run loop on each cyoa
    result_list = []
    for index, row in cyoa_list.iterrows():
        g_id = row['id']
        text = row['text']

        # Run keybert
        kb_output = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 1), stop_words=None, top_n=10)
        top_keywords = []
        for keyword in kb_output:
            word = keyword[0]
            conf = keyword[1]
            if conf > predictor_config.get('keybert_threshold'):
                top_keywords.append(word)
        logger.info(f'Keybert output: {top_keywords}')

        # If not enough words, return nothing
        if len(text) < 1000:
            top_keywords = ['n/a']

        # Assemble result
        result = {
            'id': g_id,
            'keybert': ', '.join(top_keywords)
        }
        result_list.append(result)

    # Run update
    grist_update_item(config, 'CYOAs', result_list)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download CYOA images (static or interactive), run tesseract and keybert."
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
            logger.error(f"Could not read file: {filepath.resolve()}")
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
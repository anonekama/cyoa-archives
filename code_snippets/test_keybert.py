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

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main(config):
    # Get the list of cyoas to run keybert
    cyoa_list = grist_fetch_keybert(config)
    logger.debug(cyoa_list)

    # Initialize keybert
    predictor_config = config.get('predictor')
    kw_model = KeyBERT(predictor_config.get('keybert_model'))

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
        description="Parse a subreddit for submissions using praw."
    )
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
    main(config)

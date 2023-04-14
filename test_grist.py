import argparse
import json
import logging
import pathlib
import sys

import pandas as pd
import yaml
# from strsimpy.metric_lcs import MetricLCS
# from strsimpy.ngram import NGram

from cyoa_archives.grist.routine import praw_fetch_add_update

def main(config, password):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Set up config
    new_config = config
    new_config['reddit_scraper']['password'] = password

    # Run loop
    praw_fetch_add_update(new_config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a subreddit for submissions using praw."
    )
    parser.add_argument("-c", "--config_file", help="Configuration file to use")
    parser.add_argument("-p", "--password", help="Reddit API account password")

    # Parse arguments
    args = parser.parse_args()
    password = args.password

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
    main(
        config,
        args.password,
    )

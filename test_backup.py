import argparse
import json
import logging
import pathlib
import sys

import pandas as pd
import yaml

from cyoa_archives.grist.routine import praw_fetch_add_update

def main(config):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # First we download data from grist and keep backups
    # /backups
    # /backups/D1/date_table.csv
    # /backups/D2/
    # /Backups/D4/
    # /Backups/D7/
    # /Backups/W2/
    # /Backups/M1/

    # Next we compare the current update with backup.
    # For some columns, we want to prevent any deletions (only modifications that make text longer)
    # For other columns, we just want to prevent mass-deletions if the user is anonymous

    # Run loop
    # praw_fetch_add_update(new_config)


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
    main(
        config
    )

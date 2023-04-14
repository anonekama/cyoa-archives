import argparse
import json
import logging
import pathlib
import sys

import pandas as pd
import yaml
# from strsimpy.metric_lcs import MetricLCS
# from strsimpy.ngram import NGram

from cyoa_archives.grist.api import GristAPIWrapper
from cyoa_archives.scrapers.praw import PrawAPIWrapper
from cyoa_archives.scrapers.pulseshift import PulseshiftAPIWrapper


def main(config, password):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Set up config
    pc_config = config.get('reddit_scraper')
    pc_config['password'] = password

    # Set up API
    api = GristAPIWrapper(config.get('grist'))
    pulse = PulseshiftAPIWrapper(pc_config)

    # Fetch data from pulseshift
    pulse_data = pulse.scrape('makeyourchoice', size=300, after=1586842926)
    pulse_pd = pd.DataFrame.from_dict(pulse_data)

    # Fetch data from grist
    grist_pd = api.fetch_table_pd('Records', col_names=['id', 'r_id', 'is_cyoa'])

    # Match the r_id from grist with pulse_id
    inner_merge = pd.merge(
        pulse_pd[
            ['r_id', 'is_cyoa', 'urls', 'static_url', 'interactive_url', 'total_awards_received', 'parser_timestamp']],
        grist_pd[['r_id', 'id']],
        on=['r_id']
    )
    print(inner_merge)

    # Update grist
    update_json = inner_merge.to_json(orient='records', default_handler=str)
    update_object = json.loads(update_json)
    api.update_records('Records', update_object, mock = False)


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

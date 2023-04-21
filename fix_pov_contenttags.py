import argparse
import pathlib
import sys
import yaml
import logging

import pandas as pd
from grist_api import GristDocAPI

from cyoa_archives.grist.api import GristAPIWrapper

logger = logging.getLogger(__name__)

# Parse args
parser = argparse.ArgumentParser(
    description="Parse a subreddit for submissions using praw."
)
parser.add_argument("-c", "--config_file", help="Configuration file to use")
args = parser.parse_args()
if args.config_file:
    filepath = pathlib.Path(args.config_file)
    try:
        with open(filepath) as f:
            config = yaml.safe_load(f)
    except OSError:
        print(f"Could not read file: {filepath}")
        sys.exit(1)


# Set up API
api = GristAPIWrapper(config.get('grist'))

backup_api = GristAPIWrapper(config.get('grist'))
backup_api.document_id = 'CENSORED'
backup_api.api = GristDocAPI(backup_api.document_id, server=backup_api.server_url, api_key=backup_api.api_key)

grist_pd = backup_api.fetch_table_pd('CYOAs', col_names=['id', 'pov', 'content_tags'])
# print(grist_pd)

result_list = []
for index, row in grist_pd.iterrows():
    g_id = row['id']
    pov = row['pov']
    tags = row['content_tags']

    result_list.append({
        'id': g_id,
        'pov': pov,
        'content_tags': tags
    })
# print(result_list)

# Update grist
api.update_records('CYOAs', result_list, mock=False, prompt=True)

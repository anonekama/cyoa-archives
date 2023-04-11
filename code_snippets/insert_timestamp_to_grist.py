import argparse
import os
import pathlib
import json

from grist_api import GristDocAPI
import pandas
import yaml

from cyoa_archives.scrapers.reddit_scraper import scrape_subreddit

def main(config, subreddit, password, limit = None):

    # Get variables from config
    username = config.get('reddit_scraper').get('username')
    clientid = config.get('reddit_scraper').get('clientid')
    clientsecret = config.get('reddit_scraper').get('clientsecret')
    useragent = config.get('reddit_scraper').get('useragent')
    sever = config.get('grist').get('server')
    apikey = config.get('grist').get('apikey')
    documentid = config.get('grist').get('documentid')

    # Get api key from your Profile Settings, and run with GRIST_API_KEY=<key>
    api = GristDocAPI(documentid, server=sever, api_key=apikey)

    archivefile = "RawRecords_20230409_1681073394.csv"
    adf = pandas.read_csv(archivefile)
    adf.fillna('', inplace=True)

    data = api.fetch_table('Records')
    id_dict = {}
    for item in data:
        if item.r_id not in id_dict:
            id_dict[item.r_id] = item.id

    adf['r_id'] = adf['id']
    adf['id'] = adf['r_id'].apply((lambda x: id_dict.get(x)))

    update_df = adf[['id', 'created_utc', 'parser_timestamp']]
    update_json = update_df.to_json(orient='records', default_handler=str)
    update_object = json.loads(update_json)
    api.update_records('Records', update_object)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a subreddit for submissions using praw."
    )
    parser.add_argument("subreddit", help="Name of subreddit to parse (example: makeyourchoice)")
    parser.add_argument("-c", "--config_file", help="Configuration file to use")
    parser.add_argument("-p", "--password", help="Reddit API account password")
    parser.add_argument("-l", "--limit", help="Limit number of submissions to return", default=None)

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
        args.subreddit,
    	args.password,
    	int(args.limit) if args.limit else None
    )

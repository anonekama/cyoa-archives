import argparse
import os
import pathlib
import re
import json

from grist_api import GristDocAPI
import pandas
import yaml
from strsimpy.metric_lcs import MetricLCS
from strsimpy.ngram import NGram

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

    records = api.fetch_table('Records')

    # Convert records into df
    list_id = []
    list_is_cyoa = []
    list_selftext = []
    list_cyoa = []
    list_title = []
    list_num_comments = []
    list_score = []
    list_urls = []
    list_link_flair_text = []
    for record in records:
        new_title = " ".join(record.title.split())
        list_id.append(record.id)
        list_is_cyoa.append(record.is_cyoa)
        list_selftext.append(record.selftext)
        list_cyoa.append(record.cyoa)
        list_title.append(new_title)
        list_num_comments.append(record.num_comments)
        list_score.append(record.score)
        list_urls.append(record.urls)
        list_link_flair_text.append(record.link_flair_text)
    df = pandas.DataFrame()
    df['id'] = list_id
    df['is_cyoa'] = list_is_cyoa
    df['selftext'] = list_selftext
    df['cyoa'] = list_cyoa
    df['title'] = list_title
    df['num_comments'] = list_num_comments
    df['score'] = list_score
    df['urls'] = list_urls
    df['link_flair_text'] = list_link_flair_text

    # Subset dataframe from items with no official cyoa (and is a CYOA) and has no associated cyoa
    #badtext = [ "[removed]", "[deleted]" ]
    # iscyoa_df = df.loc[df['link_flair_text'] == "Jumpchain"]
    # iscyoa_df = df.loc[df['title'].apply(lambda x: x.find('r/JumpChain') > 0)]
    iscyoa_df = df.loc[(df['selftext'].apply(lambda x: len(x) == 0)) & (df['urls'].apply(lambda x: len(x) == 0))]
    print(iscyoa_df)

    # Set found records to is_cyoa false
    update_df = iscyoa_df[['id', 'is_cyoa']]
    update_df['is_cyoa'] = ["No"] * len(iscyoa_df)
    print(update_df)
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

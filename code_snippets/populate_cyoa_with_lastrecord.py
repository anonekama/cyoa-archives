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
    cyoas = api.fetch_table('CYOAs')

    # Convert records into df
    list_id = []
    list_r_id = []
    list_created_utc = []
    list_title = []
    for record in records:
        new_title = re.sub(r'([\(\[]).*?([\)\]])', '', record.title)
        new_title = re.sub(r'[^A-Za-z0-9 ]+', '', new_title)
        new_title = " ".join(new_title.split())
        list_id.append(record.id)
        list_r_id.append(record.r_id)
        list_created_utc.append(record.created_utc)
        list_title.append(new_title)
    df = pandas.DataFrame()
    df['id'] = list_id
    df['r_id'] = list_r_id
    df['created_utc'] = list_created_utc
    df['title'] = list_title



    # loop through cyoas and find nearest match
    metriclcs = MetricLCS()
    fourgram = NGram(4)
    TIME_DELTA = 100000
    df_final = pandas.DataFrame()
    for cyoa in cyoas:
        cyoa_id = cyoa.id
        official_title = cyoa.Official_Title
        last_posted = cyoa.Last_Posted2
        has_data = cyoa.Last_Posted
        if has_data:
            continue
        if last_posted:
            subset = df[df['created_utc'].between(last_posted - TIME_DELTA, last_posted + TIME_DELTA)]
            mlcs = subset['title'].apply(lambda x: metriclcs.distance(official_title, x))
            fg = subset['title'].apply(lambda x: fourgram.distance(official_title, x))
            st = pandas.DataFrame({
                'id': subset['id'],
                'official': [official_title] * len(subset['title']),
                'cyoa': [cyoa_id] * len(subset['title']),
                'title': subset['title'],
                'mlcs': mlcs,
                'fg': fg,
                'avg': (mlcs + fg) / 2
            })
            pst = st[((st['mlcs'] < 0.5) & (st['fg'] < 0.5))]
            min_st = pst[pst.avg == pst.avg.min()]
            df_final = df_final.append(min_st)

    # make update
    update_df = df_final[['id', 'cyoa']]
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

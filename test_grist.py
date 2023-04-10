import argparse
import os
import pathlib
import json

from grist_api import GristDocAPI
import pandas
import yaml

from cyoa_archives.scrapers.reddit_scraper import scrape_subreddit

SERVER = "https://docs.getgrist.com"         # your org goes here
DOC_ID = "4BJRx9uGf3aByrqHzs2TKX"   #  document id goes here

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

    # add some rows to a table
    """
    rows = api.add_records('Test', [
        {'A': 'eggs'},
        {'B': 'beets'}
    ])
    """
    # updatethis = { 'id': 1, 'B': 'Test this' }

    # Think about archiving posts after six months

    # api.update_records('Test', [updatethis])
    # api.update_records('Test', [updatethis])
    #
    data = api.fetch_table('Records')
    id_dict = {}
    for item in data:
        if item.r_id not in id_dict:
            id_dict[item.r_id] = item.id

    df = scrape_subreddit(subreddit, username, password, clientid, clientsecret, useragent, limit)
    # df.loc[df['r_id'].isin(id_dict.keys())] # records in keys
    # df.loc[df['r_id'].isin(id_dict.keys())]
    # print(df['r_id'].isin(id_dict.keys()))
    print(df.loc[df['r_id'].isin(id_dict.keys())])
    newrecords = df.loc[~df['r_id'].isin(id_dict.keys())] # New Records

    addthis = newrecords[["r_id", "is_cyoa", "title", "date_posted", "posted_by", "subreddit", "link_flair_text", "num_comments", "score", "upvote_ratio", "permalink"]]
    thisrecord = addthis.iloc[0]
    print(thisrecord['is_cyoa'])
    print(type(thisrecord['is_cyoa']))
    print(thisrecord['is_cyoa'])
    # pr = addthis.to_json(orient='records', default_handler=str)
    # p = json.loads(pr)
    # api.add_records('Records', p)
    # print(p)

    """
    rid_to_change = "qwerxz12345"
    myrecord = api.fetch_table('Records', filters={"r_id": rid_to_change})
    print(myrecord)
    print(myrecord[0].id)
    updatethis = [
        { 'id': 17193, 'score': 3},
        { 'id': 17192, 'score': 13313}
    ]
    api.update_records('Records', updatethis)
    """
    # api.add_records('Records', [{'title': 'Test999', 'date_posted': "2023-4-10", 'r_id': 'qwerxz12345'}])

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

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

    # Convert cyoas into df
    cyoa_id = {}
    list_official_title = []
    list_cyoa_id = []
    for cyoa in cyoas:
        official_title = cyoa.Official_Title.replace("CYOA", "")
        if official_title not in cyoa_id:
            cyoa_id[official_title] = cyoa.id
            list_official_title.append(cyoa.Official_Title)
            list_cyoa_id.append(cyoa.id)
    cyoa_df = pandas.DataFrame()
    cyoa_df['id'] = list_cyoa_id
    cyoa_df['Official_Title'] = list_official_title

    # Convert records into df
    list_id = []
    list_iscyoa = []
    list_cyoa = []
    list_title = []
    for record in records:
        new_title = re.sub(r'([\(\[]).*?([\)\]])', '', record.title)
        new_title = re.sub(r'[^A-Za-z0-9 ]+', '', new_title)
        new_title = " ".join(new_title.split())
        list_id.append(record.id)
        list_iscyoa.append(record.is_cyoa)
        list_cyoa.append(record.cyoa)
        list_title.append(new_title)
    df = pandas.DataFrame()
    df['id'] = list_id
    df['is_cyoa'] = list_iscyoa
    df['cyoa'] = list_cyoa
    df['is_cyoa'] = df['is_cyoa']
    df['title'] = list_title

    # Subset dataframe from items with no official cyoa (and is a CYOA) and has no associated cyoa
    iscyoa_df = df.loc[(df['is_cyoa'] == 'Yes') | (df['is_cyoa'].isnull())]
    iscyoa_df = iscyoa_df.loc[iscyoa_df['cyoa'] == 0]

    # Loop through records and find nearest match
    metriclcs = MetricLCS()
    fourgram = NGram(4)
    df_final = pandas.DataFrame()
    for index, row in iscyoa_df.iterrows():
        record_id = row.id
        title = re.sub(r'([\(\[]).*?([\)\]])', '', row.title)
        title = re.sub(r'[^A-Za-z0-9 ]+', '', title)
        title = " ".join(title.split()).replace("CYOA", "")
        if title:
            mlcs = cyoa_df['Official_Title'].apply(lambda x: metriclcs.distance(title, x))
            fg = cyoa_df['Official_Title'].apply(lambda x: fourgram.distance(title, x))
            st = pandas.DataFrame({
                'id': [record_id] * len(cyoa_df),
                'title': [title] * len(cyoa_df),
                'cyoa': cyoa_df['id'],
                'official': cyoa_df['Official_Title'],
                'mlcs': mlcs,
                'fg': fg,
                'avg': (mlcs + fg) / 2
            })
            st.sort_values(by=['avg'], ascending=True, inplace = True)
            min_st = st.iloc[0]
            # pst = st[((st['mlcs'] < 0.5) & (st['fg'] < 0.5))]
            min_st2 = st.iloc[1]
            delta = st.iloc[1].avg - st.iloc[0].avg
            #print(min_st)
            #print(min_st2)
            #print(delta)
            #print(title)
            print(f"{index} | {min_st.mlcs:.3f} {min_st.fg:.3f} | {delta:.3f} || {min_st.title} | {min_st.official}")
            if (min_st.mlcs < 0.2) and (min_st.fg < 0.2) and (delta > 0.3):
                print(f":::::TRIGGER:::: {min_st.title} | {min_st.official}")
                update_object = {
                    'id': int(min_st.id),
                    'cyoa': int(min_st.cyoa)
                }
                api.update_records('Records', [update_object])
        

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

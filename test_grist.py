import argparse
import os
import pathlib
import re
import json
import logging

from grist_api import GristDocAPI
import pandas
import yaml
from strsimpy.metric_lcs import MetricLCS
from strsimpy.ngram import NGram

from cyoa_archives.scrapers.reddit_scraper import scrape_subreddit
from cyoa_archives.grist.api import GristAPIWrapper

def main(config, subreddit, password, limit = None):

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Get variables from config
    username = config.get('reddit_scraper').get('username')
    clientid = config.get('reddit_scraper').get('clientid')
    clientsecret = config.get('reddit_scraper').get('clientsecret')
    useragent = config.get('reddit_scraper').get('useragent')
    server = config.get('grist').get('server_url')
    apikey = config.get('grist').get('api_key')
    documentid = config.get('grist').get('document_id')

    api = GristAPIWrapper(server_url=server, document_id=documentid, api_key=apikey)
    api2 = GristAPIWrapper.load_config({
        "server_url": server,
        "document_id": documentid,
        "api_key": apikey
    })
    print(api.document_id)
    print(api2.document_id)

    records_pd = api.fetch_table_pd('CYOAs', colnames=['id', 'uuid', 'Official_Title'])
    print(records_pd)

    # mock = api.add_records('Test', [{'A': 123}])
    # prompt = api.add_records('Test', [{'A': 123}], mock=False)
    # noprompt = api.add_records('Test', [{'A': 931223},{'B': 25492223}], mock=False, prompt=False)
    # print(noprompt)

    # patch = api.update_records('Test', [{'id': 7, 'B': 931255123}], mock=False, prompt=False)
    # print(patch)

    # Get api key from your Profile Settings, and run with GRIST_API_KEY=<key>
    # api = GristDocAPI(documentid, server=sever, api_key=apikey)

    #

    """
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
    #update_json = update_df.to_json(orient='records', default_handler=str)
    #update_object = json.loads(update_json)
    #api.update_records('Records', update_object)
    """

    """
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
            #df_final = df_final.append(min_st)
    #df_final.to_csv('temp.csv')
    """

    """
    # make update
    update_df = df_final[['id', 'cyoa']]
    update_json = update_df.to_json(orient='records', default_handler=str)
    update_object = json.loads(update_json)
    api.update_records('Records', update_object)
    """

    """
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
    """

    # updatethis = { 'id': 1, 'B': 'Test this' }

    # Think about archiving posts after six months

    # api.update_records('Test', [updatethis])
    # api.update_records('Test', [updatethis])
    #


    """
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

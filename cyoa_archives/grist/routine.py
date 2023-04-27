"""Miscellaneous functions for interacting with grist."""

import json
import logging
import os
import pathlib
import re
import shutil
import subprocess

from typing import Dict

import imagehash
import pandas as pd

from PIL import Image
from strsimpy.metric_lcs import MetricLCS
from strsimpy.ngram import NGram

from cyoa_archives.grist.api import GristAPIWrapper
from cyoa_archives.scrapers.praw import PrawAPIWrapper

logger = logging.getLogger(__name__)


def find_closest_cyoa(title, cyoa_df):
    # Loop through records and find nearest match
    metriclcs = MetricLCS()
    fourgram = NGram(4)

    processed_text = re.sub(r'([\(\[]).*?([\)\]])', '', title)
    processed_text = re.sub(r'[^A-Za-z0-9 ]+', '', processed_text)
    processed_text = " ".join(processed_text.split()).replace('CYOA', '')
    if processed_text:
        mlcs = cyoa_df['official_title'].apply(lambda x: metriclcs.distance(processed_text, x))
        fg = cyoa_df['official_title'].apply(lambda x: fourgram.distance(processed_text, x))
        st = pd.DataFrame({
            'cyoa': cyoa_df['id'],
            'mlcs': mlcs,
            'fg': fg,
            'avg': (mlcs + fg) / 2
        })
        st.sort_values(by=['avg'], ascending=True, inplace=True)
        min_st = st.iloc[0]
        delta = st.iloc[1].avg - st.iloc[0].avg
        if (min_st.mlcs < 0.2) and (min_st.fg < 0.2) and (delta > 0.3):
            return int(min_st.cyoa)
    return None

def hash_static_url(static_url, temp_dir):
    if static_url:
        # Empty temporary directory
        tempdir = pathlib.Path(temp_dir)
        if tempdir.exists():
            logger.info(f'Deleting directory: {tempdir.resolve()}')
            shutil.rmtree(tempdir.resolve())
            os.makedirs(tempdir)

        # Download using gallery-dl
        subprocess.run(['gallery-dl', static_url, '-d', tempdir.resolve()], universal_newlines=True)
        image_paths = []
        for extension in ['*.png', '*.jpg', '*.jpeg']:
            for image_path in tempdir.rglob(extension):
                image_paths.append(image_path)
        logger.debug(image_paths)

        # Now run hashing algorithm on all images in the temporary directory
        hash_list = []
        for image in image_paths:
            # Hash the image (Let's use average hash because it's less tolerant)
            img = Image.open(image)
            image_hash = imagehash.average_hash(img)
            color_hash = imagehash.colorhash(img, binbits=3)
            image_hash_str = str(image_hash) + '_' + str(color_hash)
            hash_list.append(image_hash_str)

        return ', '.join(hash_list)
    else:
        return ''


def praw_fetch_add_update(config: Dict) -> None:
    """Fetch recent updates from reddit (praw) and update the Grist Records table.

    :param config: A config dictionary object
    """
    # Parse configuration file
    grist_config = config.get('grist')
    server_url = grist_config.get('server_url')
    document_id = grist_config.get('document_id')
    api_key = grist_config.get('api_key')
    praw_config = config.get('reddit_scraper')

    # Set up API
    api = GristAPIWrapper(server_url=server_url, document_id=document_id, api_key=api_key)
    praw = PrawAPIWrapper(config.get('reddit_scraper'))

    grist_records_pd = api.fetch_table_pd('Records', col_names=['id', 'r_id'])
    grist_cyoa_pd = api.fetch_table_pd('CYOAs', col_names=['id', 'official_title'])

    for subreddit in ['nsfwcyoa', 'makeyourchoice', 'InteractiveCYOA', 'allsync_mirror']:

        # Fetch data from Praw
        praw_data = praw.scrape(subreddit, limit=50)
        praw_pd = pd.DataFrame.from_dict(praw_data)

        # First update old records
        inner_merge = pd.merge(
            praw_pd[
                ['r_id', 'score', 'num_comments', 'upvote_ratio', 'total_awards_received', 'parser_timestamp']
            ],
            grist_records_pd[['r_id', 'id']],
            on=['r_id']
        )
        update_json = inner_merge.to_json(orient='records', default_handler=str)
        update_object = json.loads(update_json)
        api.update_records('Records', update_object, mock=False, prompt=False)

        # TODO: Match CYOAs by their image hashes

        # Next add new records
        new_pd = praw_pd.loc[~praw_pd['r_id'].isin(grist_records_pd['r_id'])]
        new_pd['cyoa'] = new_pd['title'].apply(find_closest_cyoa, cyoa_df=grist_cyoa_pd)
        new_pd['image_hashes'] = new_pd['static_url'].apply(hash_static_url, temp_dir=config.get('project').get('temp_dir'))
        add_pd = new_pd[[
            'author', 'created_utc', 'cyoa', 'r_id', 'is_self', 'link_flair_text', 'num_comments', 'permalink',
            'removed_by_category', 'score', 'selftext', 'subreddit', 'title', 'total_awards_received', 'upvote_ratio',
            'urls', 'static_url', 'interactive_url', 'is_cyoa', 'image_hashes'
        ]]
        add_json = add_pd.to_json(orient='records', default_handler=str)
        add_object = json.loads(add_json)
        api.add_records('Records', add_object, mock=False, prompt=False)


def grist_fetch_deepl(config: Dict) -> pd.DataFrame:
    """Fetch a list of CYOAs from Grist that have been marked for Deep Learning.

    These are CYOAs marked ('deepl') and lack a ('deepl_timestamp').

    :param config: A configuration file (root) for the application.
    :return: A pandas dataframe.
    """
    # Set up API
    api = GristAPIWrapper.from_config(config.get('grist'))

    grist_cyoa_pd = api.fetch_table_pd('CYOAs', col_names=[
        'id', 'uuid', 'official_title', 'deepl', 'deepl_timestamp', 'static_url', 'interactive_url', 'last_posted'
    ])
    deepl_pd = grist_cyoa_pd.loc[grist_cyoa_pd['deepl']].sort_values(by=['last_posted'], ascending=False)
    filter_pd = deepl_pd.loc[deepl_pd['deepl_timestamp'] == 0]
    return filter_pd

def grist_fetch_keybert(config):
    # Set up API
    api = GristAPIWrapper.from_config(config.get('grist'))

    grist_cyoa_pd = api.fetch_table_pd('CYOAs', col_names=['id', 'uuid', 'official_title', 'deepl', 'deepl_timestamp',
                                                           'text', 'keybert'])
    deepl_pd = grist_cyoa_pd.loc[grist_cyoa_pd['deepl']]
    filter_pd = deepl_pd[~(deepl_pd['text'].isnull() | deepl_pd['text'].eq(''))]
    no_keybert_pd = filter_pd[filter_pd['keybert'].isnull() | filter_pd['keybert'].eq('')]
    return no_keybert_pd

def grist_update_item(config, table, item_dict):
    # Check if item_dict is a singleton or a list
    if type(item_dict) is list:
        result = item_dict
    else:
        result = [item_dict]

    # Set up API
    api = GristAPIWrapper.from_config(config.get('grist'))
    api.update_records(table, result, mock=False, prompt=False)
    return None
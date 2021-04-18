from typing import Dict, List, Any
import requests
import os
import json
from os.path import join
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from urllib.parse import urlencode
from pprint import pprint

load_dotenv(verbose=True)
ENV_FILE = '.env.production' if os.environ.get(
    "PYTHON_ENV") == 'production' else '.env.development'
dotenv_path = join(os.getcwd(), ENV_FILE)
load_dotenv(dotenv_path)

REST = 'https://api.twitter.com/2'

# Rate limits https://developer.twitter.com/en/docs/rate-limits
# 450 requests per 15-minute window(app auth)
# 180 requests per 15-minute window(user auth)

# https: // developer.twitter.com /en/docs/twitter-api/tweets/timelines/api-reference/get-users-id-tweets
# 1500 requests per 15-minute window (app auth)
# 900 requests per 15-minute window (user auth)


def auth():
    return os.environ.get("TWITTER_BEARER_TOKEN")


def strftime_back(seconds=0, minutes=0, hours=0, days=0):
    since_date = ""
    td = ""
    utc_date = datetime.now(timezone.utc)
    td = timedelta(days=days, seconds=seconds, minutes=minutes, hours=hours)
    since_date = utc_date - td
    return since_date.strftime("%Y-%m-%dT%H:%M:%SZ")


def create_url(method, endpoint, params={}):
    url = ''
    if method == "GET" and len(params):
        url = endpoint + '?' + urlencode(params)
    else:
        url = endpoint
    return url


def create_headers(bearer_token):
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    return headers


def connect_to_endpoint(method, endpoint, params, headers):
    response: requests.Response = {}
    if method == 'GET':
        url = create_url(method, endpoint, params)
        response = requests.request("GET", url, headers=headers)
        # print(response.status_code)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()


def isunion(a, b):
    return a or b


def isintersect(a, b):
    return a and b


def check_txt(keywords, txt, cond='or'):
    func = isunion if cond == 'or' else isintersect
    is_included = False
    for word in keywords:
        is_included = func((word in txt), is_included)
    return is_included


def mining_txt(keywords, datas: Dict[str, Any], cond='or'):
    matched_data = []
    if datas["meta"]["result_count"] == 0:
        return []
    for data in datas["data"]:
        if check_txt(keywords, data["text"], cond):
            matched_data.append(data)
    return matched_data


def user_timeline(id, exclude=None, start_time=None, end_time=None, tweet_fields=None):
    endpoint = f'{REST}/users/{id}/tweets'
    params = {}
    if exclude is not None:
        params['exclude'] = exclude
    if start_time is not None:
        params['start_time'] = start_time
    if end_time is not None:
        params['end_time'] = end_time
    if tweet_fields is not None:
        params['tweet.fields'] = tweet_fields
    headers = create_headers(auth())
    return connect_to_endpoint('GET', endpoint, params, headers)


def search_recent(query, start_time=None, end_time=None, tweet_fields=None):
    endpoint = f'{REST}/tweets/search/recent'
    params = {'query': query}
    if start_time is not None:
        params['start_time'] = start_time
    if end_time is not None:
        params['end_time'] = end_time
    if tweet_fields is not None:
        params['tweet.fields'] = tweet_fields

    headers = create_headers(auth())
    return connect_to_endpoint('GET', endpoint, params, headers)


def keywords_search(keywords, res, cond='or'):
    matched = mining_txt(keywords, res, cond)
    print("Matched Tweets:", json.dumps(matched, indent=2))
    return matched


if __name__ == "__main__":
    # query = "from:FTX_Official"
    # id = '1101264495337365504'  # ftxofficial
    query = "from:elonmusk"
    id = '44196397'  # elonmusk
    tweet_fields = "author_id"
    start_time = strftime_back(days=5, hours=12, seconds=10)
    keywords = ['doge', 'Doge', 'DOGE']
    # keywords = ['autopilot', 'Autopiot']

    res = search_recent(query, start_time=start_time, tweet_fields=tweet_fields)
    ('data' in res) and pprint(res['data'])
    print("--------")

    res = user_timeline(id=id, start_time=start_time)
    ('data' in res) and pprint(res['data'])
    print("--------")

    keywords_search(keywords, res, 'or')

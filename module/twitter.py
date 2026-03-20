import asyncio
import requests
import json
import os
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup as BS
from collections import deque
import _G
import utils
import timer
from logger import logger
import hashlib
from tweety import Twitter
from tweety.types.twDataTypes import SelfThread, get_running_loop
from tweety.exceptions import TwitterError
import module.tweet_handler as xhandler

TWITTER_LISTENERS = {
    'mist_staff': {
        'webhook': os.getenv('MST_TWT_WEBHOOK'),
        'mention': os.getenv('MST_GAME_ROLE'),
    },
    'monmusu_td': {
        'webhook': os.getenv('MTD_TWT_WEBHOOK'),
        'mention': os.getenv('MTD_GAME_ROLE'),
    },
    'starknights_PR': {
        'webhook': os.getenv('TSK_TWT_WEBHOOK'),
        'mention': os.getenv('TSK_GAME_ROLE'),
    },
    'azurlane_staff': {
        'webhook': os.getenv('AZL_TWT_WEBHOOK'),
        'mention': os.getenv('AZL_GAME_ROLE'),
    },
    'AzurLane_EN': {
        'webhook': os.getenv('AZL_TWT_WEBHOOK'),
        'mention': os.getenv('AZL_GAME_ROLE'),
    },
    'ff_xiv_jp': {
        'webhook': os.getenv('FFXIV_TWT_WEBHOOK'),
        'mention': os.getenv('FFXIV_GAME_ROLE'),
        'handler': xhandler.filter_ffxiv_recruits,
    },
}

ACTIVE_HOURS    = []
LAZY_HOURS      = [range(20, 24), range(0, 9)]
ACTIVE_INTERVAL = 1
NORMAL_INTERVAL = 5
LAZY_INTERVAL   = 30

Agent:Twitter = None
AgentLoop:asyncio.AbstractEventLoop = None
ErrorCnt = 0

TIMER_UPDATE_KEY = 'twitter_update'

TweetHistory = {k:deque(maxlen=10) for k in TWITTER_LISTENERS}

def parse_tweet(tweet):
    ret = {}
    if not tweet.created_on:
        return None
    ret['id'] = int(tweet.id)
    ret['postedAt'] = int(tweet.created_on.timestamp())
    ret['message'] = tweet.text
    ret['account'] = tweet.author.username
    return ret


def parse_tweet_threads(tweets):
    ret = []
    for t in tweets:
        # only interpret first Thread level
        if type(t) == SelfThread:
            for t2 in t:
                pt = parse_tweet(t2)
                if pt:
                    ret.append(pt)
        else:
            pt = parse_tweet(t)
            if pt:
                ret.append(pt)
    return ret

def get_new_tweets(account:str):
    global Agent
    ret = []
    try:
        tweets = arun(Agent.get_tweets(account))
        ret = parse_tweet_threads(tweets)
    except TwitterError:
        arun(connect_twitter())
        tweets = arun(Agent.get_tweets(account))
        ret = parse_tweet_threads(tweets)
    except Exception as err:
        utils.handle_exception(err)
        return []
    ret = sorted(ret, key=lambda o: o['id'], reverse=True)
    return ret

def get_old_tweets(account, prev_file):
    ret = []
    if not os.path.exists(prev_file):
        ret = get_new_tweets(account)
        if not ret:
            return []
        save_tweets(account, ret)
    try:
        with open(prev_file, 'r') as fp:
            ret = json.load(fp)
    except Exception:
        ret = []
    ret = sorted(ret, key=lambda o: o['id'], reverse=True)
    return ret

def is_same_message(a, b):
    ha = hashlib.md5(a.encode()).hexdigest()
    hb = hashlib.md5(b.encode()).hexdigest()
    return ha == hb

def update_tweets(account):
    global Agent
    data = TWITTER_LISTENERS[account]
    webhook = data['webhook']
    dc_role_id = data['mention']
    logger.debug(f"Getting tweets from {account}")
    prev_file = f"{_G.CACHE_DIR}/{account}_prevtweets.json"
    news = []
    try:
        news = get_new_tweets(account)
        news = sorted(news, key=lambda o: o['id'], reverse=True)
    except Exception as err:
        utils.handle_exception(err)
        return
    if not news:
        logger.error("Unable to get new tweets")
        return
    olds = get_old_tweets(account, prev_file)
    o_cksum = 0
    if olds:
        o_cksum = olds[0]['postedAt']
    else:
        logger.warning(f"{prev_file} does not exists")
    n_cksum = int(news[0]['postedAt'])
    o_cksum = int(o_cksum)
    if o_cksum > n_cksum:
        logger.warning(f"Old news newer than latest news ({o_cksum} > {n_cksum})")
    if o_cksum == n_cksum:
        logger.debug("No news, skip")
        return True

    logger.info(f"Gathering {account} new tweets")
    ar = []
    for n in news:
        ok = False
        if not olds:
            ok = True
            logger.debug("Boardcast news, reason: no old news")
        elif n['id'] > olds[0]['id']:
            ok = True
            logger.debug("Boardcast news, reason: newer id than old news")
        elif n['id'] == olds[0]['id'] and not is_same_message(n['message'], olds[0]['message']):
            ok = True
            logger.debug("Boardcast news, reason: latest post updated")
        else:
            break
        if n['id'] in TweetHistory[account] and any([n['id'] == o['id'] for o in olds]):
            logger.info(f"Skip {account}/{n['id']}, reason: duplicated id in history")
            continue
        if ok and ('handler' not in data or data['handler'](n)):
            TweetHistory[account].append(n['id'])
            ar.insert(0, n)

    urls = []
    if webhook:
        urls = webhook.split(',')
    try:
        if ar and dc_role_id:
            roles = dc_role_id.split(',')
            for i,role in enumerate(roles):
                if i >= len(urls):
                    break
                if not role:
                    continue
                requests.post(
                    urls[i],
                    json={
                        'content': f"<@&{role}>"
                    },
                    timeout=_G.REQUEST_TIMEOUT
                )
        for a in ar:
            for u in urls:
                send_message(u, a)
    except Exception as err:
        utils.handle_exception(err)
    save_tweets(account, news)
    return True

def update():
    global Agent, ErrorCnt
    if not Agent:
        if ErrorCnt < 0:
            utils.restart()
        return
    if not timer.is_expired(TIMER_UPDATE_KEY):
        return
    if ErrorCnt >= len(TWITTER_LISTENERS):
        logger.warning("Trying to reconnect Twitter due to errors")
        Agent = None
        connect_twitter()
    for account in TWITTER_LISTENERS:
        no_err = update_tweets(account)
        if not no_err:
            ErrorCnt += 1
        else:
            ErrorCnt = max(0, ErrorCnt - 1)
    if any(datetime.now().hour in t for t in LAZY_HOURS):
        timer.delay(TIMER_UPDATE_KEY, minutes=LAZY_INTERVAL)
    elif any(datetime.now().hour in t for t in ACTIVE_HOURS):
        timer.delay(TIMER_UPDATE_KEY, minutes=ACTIVE_INTERVAL)
    else:
        timer.delay(TIMER_UPDATE_KEY, minutes=NORMAL_INTERVAL)


def send_message(url, obj):
    return requests.post(
        url,
        json={
            'content': f"https://fixupx.com/{obj['account']}/status/{obj['id']}"
        },
        timeout=_G.REQUEST_TIMEOUT
    )

async def connect_twitter():
    global Agent, ErrorCnt
    Agent = Twitter('session')
    try:
        a = await Agent.connect()
        if not a:
            a = await Agent.sign_in(os.getenv('TWITTER_USERNAME'), os.getenv('TWITTER_PASSWORD'))
        logger.info(f"Twitter connected: {a}")
    except Exception as err:
        utils.handle_exception(err)
        if ErrorCnt >= len(TWITTER_LISTENERS)*2:
            msg = "Disable twitter module due to successive errors"
            logger.warning(msg)
            utils.send_critical_message(f"{msg}\bError: {err}")
            Agent = None
            ErrorCnt = -1
            return
        logger.info(f"Try using username/pwd to sign in again, depth={ErrorCnt}")
        await Agent.sign_in(os.getenv('TWITTER_USERNAME'), os.getenv('TWITTER_PASSWORD'))

def save_tweets(account, tweets):
    prev_file = f"{_G.CACHE_DIR}/{account}_prevtweets.json"
    # only keeps latest 100 tweets
    with open(prev_file, 'w') as fp:
        json.dump(sorted(tweets, key=lambda x: x['id'], reverse=True)[:100], fp)

def arun(coro):
    global AgentLoop
    if not AgentLoop:
        AgentLoop = get_running_loop()
    if asyncio.iscoroutine(coro):
        return AgentLoop.run_until_complete(coro)
    return coro

def init():
    arun(connect_twitter())
    timer.set_timer(TIMER_UPDATE_KEY, timedelta(seconds=10))

def reload():
    pass

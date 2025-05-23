import requests
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup as BS
import _G
from logger import logger
import utils
import warnings
warnings.simplefilter("ignore")

PREV_NEWS_FILE = f"{_G.CACHE_DIR}/.aa_prevnews.json"

NEWS_URL    = os.getenv('AA_NEWS_URL')
WEBHOOK_URL = os.getenv('AA_WEBHOOK_URL')

AA_TAG_MAP = {
    1: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/g6YYKpKcmwayayE6r1NzuajDNBbNlgmqloBM887n.png',
    2: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/l6hNGLymu3xLxeiteEa9BN6NvISlomlbeSeDNlXr.png',
    3: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/g6eJW2EO2z1bbE0EVsrRbH9DjxpbUyTGkGIQUKdP.png',
    4: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/cE8PMgnMwRNJwEsgtrmbn7zpi2SUmSybrixzMNiP.png',
    5: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/x0D2uRHUoq63ubJ1PZmnhGN8p9E0KdvCz3WE9gGL.png',
    6: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/CgGLgT69zSh3puuo6nLC5o2mBvcheZrfrBFJJsuK.png',
    7: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/VZax2h8g6RCltUuD5kHm8Mup8GOMOeKpgJHCgIYT.png',
    8: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/oMP7Kmbrt03kOkeyJlzskPqIMH8WmCr3x4SSgw5h.png'
}

AA_NEWS_TAG = {
    1: 'MAINTENANCE',
    2: 'UPDATE',
    3: 'BUG',
    4: 'CAMPAIGN',
    5: 'EVENT',
    6: 'GACHA',
    7: 'MISC',
    8: 'IMPORTANT',
    9: 'MISC',
}

AA_NEWS_ICON = {
    1: 'https://cdn-icons-png.flaticon.com/512/777/777081.png', # MAINTENANCE
    2: 'https://cdn.icon-icons.com/icons2/1508/PNG/512/updatemanager_104426.png', # UPDATE
    3: 'https://www.iconsdb.com/icons/preview/red/error-7-xxl.png', # BUG
    4: 'https://cdn-icons-png.flaticon.com/512/3867/3867424.png', # CAMPAIGN
    5: 'https://cdn-icons-png.flaticon.com/512/4285/4285436.png', # EVENT
    6: 'https://cdn-icons-png.flaticon.com/512/4230/4230567.png', # GACHA
    7: 'https://cdn-icons-png.flaticon.com/512/1827/1827301.png', # MISC
    8: 'https://www.iconsdb.com/icons/preview/red/error-7-xxl.png', # IMPORTANT
    9: 'https://cdn-icons-png.flaticon.com/512/1827/1827301.png', # MISC
}

AA_NEWS_COLOR = {
    1: 0xfc3aef, # MAINTENANCE
    2: 0x5299f7, # UPDATE
    3: 0xdb043e, # BUG
    4: 0xff5cb0, # CAMPAIGN
    5: 0x50faf4, # EVENT
    6: 0xfad73c, # GACHA
    7: 0xcccccc, # MISC
    8: 0xdb043e, # IMPORTANT
    9: 0xcccccc, # MISC
}

AA_VOCAB_JP = {
    'NEWS_TAG': {
    1: 'メンテナンス',
    2: 'アップデート',
    3: '不具合',
    4: 'キャンペーン',
    5: 'イベント',
    6: 'ガチャ',
    7: 'その他',
    8: '重要',
    9: 'その他',
    }
}

def get_webhook_url():
    global WEBHOOK_URL
    return WEBHOOK_URL

def get_news_data():
    ret = {}
    try:
        res = requests.get(NEWS_URL, timeout=_G.REQUEST_TIMEOUT)
        ret = []
        for a in res.json():
            id = int(a['id'])
            ret.append({
                'id': id,
                'title': a['title'],
                'postedAt': a['updatedAt'],
                'tag': a['tag'],
                'message': a['message']
            })
    except Exception as err:
        utils.handle_exception(err)
    return ret

def get_old_news():
    ret = {}
    if not os.path.exists(PREV_NEWS_FILE):
        ret = get_news_data()
        ret = sorted(ret, key=lambda o: -o['id'])
        with open(PREV_NEWS_FILE, 'w') as fp:
            json.dump(ret, fp)
    else:
        with open(PREV_NEWS_FILE, 'r') as fp:
            ret = json.load(fp)
    return ret


def update():
    news = {}
    try:
        news = get_news_data()
        news = sorted(news, key=lambda o: -o['id'])
    except Exception as err:
        utils.handle_exception(err)
        return
    if not news or 'service unavailable' in news[0]['message'].lower():
        logger.warning("News data endpoint failure:")
        if news:
            logger.warning(news[0]['message'])
        return
    olds = get_old_news()
    o_cksum = 0
    logger.debug("Checking AA news")
    if olds:
        o_cksum = int(datetime.fromisoformat(olds[0]['postedAt']).timestamp())
    n_cksum = int(datetime.fromisoformat(news[0]['postedAt']).timestamp())
    if o_cksum > n_cksum:
        logger.warning(f"Old news newer than latest news ({o_cksum} > {n_cksum})")
    elif o_cksum == n_cksum and news[0]['message'] == olds[0]['message']:
        logger.debug("No news, skip")
        return

    logger.info("Gathering AA news")
    ar = []
    for n in news:
        if not olds or n['id'] > olds[0]['id'] or (n['id'] == olds[0]['id'] and n['message'] != olds[0]['message']):
            ar.insert(0, n)
        else:
            break
    for a in ar:
        try:
            send_message(a)
        except Exception as err:
            utils.handle_exception(err)
    with open(PREV_NEWS_FILE, 'w') as fp:
        json.dump(news, fp)


def send_message(obj):
    payload = {}
    payload['embeds'] = [{
        'author': {
            'name': AA_VOCAB_JP['NEWS_TAG'][obj['tag']],
            'icon_url': AA_NEWS_ICON[obj['tag']],
        },
        'title': f"**{obj['title']}**",
        'description': f"<t:{int(datetime.fromisoformat(obj['postedAt']).timestamp())}>",
        'color': AA_NEWS_COLOR[obj['tag']],
        'fields': []
    }]
    # this will fail if total length is over 6000
    for msg in utils.chunk(obj['message'], 1000):
        payload['embeds'][0]['fields'].append({
            'name': " \u200b", # zero-width space
            'value': msg
        })
    return requests.post(get_webhook_url(), json=payload, timeout=_G.REQUEST_TIMEOUT)

def init():
    pass

def reload():
    pass

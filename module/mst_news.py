import requests
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup as BS
import _G
import utils
from logger import logger

PREV_NEWS_FILE = f"{_G.CACHE_DIR}/.mst_prevnews.json"

NEWS_URL    = os.getenv('MST_NEWS_URL')
WEBHOOK_URL = os.getenv('MST_WEBHOOK_URL')

MST_NEWS_TAG = {
    1: 'MAINTENANCE',
    2: 'UPDATE',
    3: 'GACHA',
    4: 'EVENT',
    5: 'CAMPAIGN',
    6: 'BUG',
    7: 'MISC',
    8: 'IMPORTANT',
    9: 'SELL'
}

MST_NEWS_ICON = {
    1: 'https://cdn-icons-png.flaticon.com/512/777/777081.png',
    2: 'https://cdn.icon-icons.com/icons2/1508/PNG/512/updatemanager_104426.png',
    3: 'https://cdn-icons-png.flaticon.com/512/4230/4230567.png',
    4: 'https://cdn-icons-png.flaticon.com/512/4285/4285436.png',
    5: 'https://cdn-icons-png.flaticon.com/512/3867/3867424.png',
    6: 'https://www.iconsdb.com/icons/preview/red/error-7-xxl.png',
    7: 'https://cdn-icons-png.flaticon.com/512/1827/1827301.png',
    8: 'https://www.iconsdb.com/icons/preview/red/error-7-xxl.png',
    9: 'https://cdn-icons-png.flaticon.com/512/4021/4021642.png'
}

MST_NEWS_COLOR = {
    1: 0xfc3aef,
    2: 0x5299f7,
    3: 0xfad73c,
    4: 0x50faf4,
    5: 0xff5cb0,
    6: 0xdb043e,
    7: 0xcccccc,
    8: 0xdb043e,
    9: 0xfad73c,
}

TSK_VOCAB_JP = {
    'NEWS_TAG': {
        1: 'メンテナンス',
        2: 'アップデート',
        3: 'ガチャ',
        4: 'イベント',
        5: 'キャンペーン',
        6: '不具合',
        7: 'その他',
        8: '重要',
        9: '販売'
    }
}

def get_webhook_url():
    global WEBHOOK_URL
    return WEBHOOK_URL or ''

def get_news_detail(id):
    ret = ''
    try:
        res = requests.get(f"{NEWS_URL}?id={id}", timeout=_G.REQUEST_TIMEOUT)
        doc = BS(res.content, features='lxml')
        ret = doc.text
    except Exception as err:
        utils.handle_exception(err)
        return ''
    return BS(ret, features='lxml').text

def get_news_data():
    ret = {}
    try:
        res = requests.get(NEWS_URL, timeout=_G.REQUEST_TIMEOUT)
        ret = []
        for a in res.json()['articles']:
            id = int(a['articleUrl'])
            ret.append({
                'id': id,
                'title': a['title'],
                'postedAt': a['date'],
                'tag': next((i for i,v in MST_NEWS_TAG.items() if a['type'].upper() == v), 7),
                'message': get_news_detail(id)
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
    logger.debug("Checking MST news")
    if olds:
        o_cksum = int(datetime.fromisoformat(olds[0]['postedAt']).timestamp())
    n_cksum = int(datetime.fromisoformat(news[0]['postedAt']).timestamp())
    if o_cksum > n_cksum:
        logger.warning(f"Old news newer than latest news ({o_cksum} > {n_cksum})")
    elif o_cksum == n_cksum and news[0]['message'] == olds[0]['message']:
        logger.debug("No news, skip")
        return

    logger.info("Gathering MST news")
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
            'name': TSK_VOCAB_JP['NEWS_TAG'][obj['tag']],
            'icon_url': MST_NEWS_ICON[obj['tag']],
        },
        'title': f"**{obj['title']}**",
        'description': f"<t:{int(datetime.fromisoformat(obj['postedAt']).timestamp())}>",
        'color': MST_NEWS_COLOR[obj['tag']],
        'fields': []
    }]
    # this will fail if total length is over 6000
    for msg in utils.chunk(obj['message'], 1000):
        payload['embeds'][0]['fields'].append({
            'name': " \u200b", # zero-width space
            'value': msg
        })
    urls = get_webhook_url().split(',')
    for url in urls:
        requests.post(url, json=payload, timeout=_G.REQUEST_TIMEOUT)

def init():
    pass

def reload():
    pass

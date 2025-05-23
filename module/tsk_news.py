import requests
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup as BS
import _G
import utils
from logger import logger
import warnings
warnings.simplefilter("ignore")

PREV_NEWS_FILE = f"{_G.CACHE_DIR}/.tsk_prevnews.json"

NEWS_URL    = os.getenv('TSK_NEWS_URL')
WEBHOOK_URL = os.getenv('TSK_WEBHOOK_URL')

TSK_TAG_MAP = {
    1: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/g6YYKpKcmwayayE6r1NzuajDNBbNlgmqloBM887n.png',
    2: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/l6hNGLymu3xLxeiteEa9BN6NvISlomlbeSeDNlXr.png',
    3: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/g6eJW2EO2z1bbE0EVsrRbH9DjxpbUyTGkGIQUKdP.png',
    4: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/cE8PMgnMwRNJwEsgtrmbn7zpi2SUmSybrixzMNiP.png',
    5: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/x0D2uRHUoq63ubJ1PZmnhGN8p9E0KdvCz3WE9gGL.png',
    6: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/CgGLgT69zSh3puuo6nLC5o2mBvcheZrfrBFJJsuK.png',
    7: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/VZax2h8g6RCltUuD5kHm8Mup8GOMOeKpgJHCgIYT.png',
    8: 'https://dz87n5pasv7ep.cloudfront.net/common/img/info/flag/oMP7Kmbrt03kOkeyJlzskPqIMH8WmCr3x4SSgw5h.png'
}

TSK_NEWS_TAG = {
    1: 'MAINTENANCE',
    2: 'UPDATE',
    3: 'GACHA',
    4: 'EVENT',
    5: 'CAMPAIGN',
    6: 'BUG',
    7: 'MISC',
    8: 'IMPORTANT'
}

TSK_NEWS_ICON = {
    1: 'https://cdn-icons-png.flaticon.com/512/777/777081.png', # MAINTENANCE
    2: 'https://cdn.icon-icons.com/icons2/1508/PNG/512/updatemanager_104426.png', # UPDATE
    3: 'https://cdn-icons-png.flaticon.com/512/4230/4230567.png', # GACHA
    4: 'https://cdn-icons-png.flaticon.com/512/4285/4285436.png', # EVENT
    5: 'https://cdn-icons-png.flaticon.com/512/3867/3867424.png', # CAMPAIGN
    6: 'https://www.iconsdb.com/icons/preview/red/error-7-xxl.png', # BUG
    7: 'https://cdn-icons-png.flaticon.com/512/1827/1827301.png', # MISC
    8: 'https://www.iconsdb.com/icons/preview/red/error-7-xxl.png', # IMPORTANT
}

TSK_NEWS_COLOR = {
    1: 0xfc3aef, # MAINTENANCE
    2: 0x5299f7, # UPDATE
    3: 0xfad73c, # GACHA
    4: 0x50faf4, # EVENT
    5: 0xff5cb0, # CAMPAIGN
    6: 0xdb043e, # BUG
    7: 0xcccccc, # MISC
    8: 0xdb043e  # IMPORTANT
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
        8: '重要'
    }
}

def get_webhook_url():
    global WEBHOOK_URL
    return WEBHOOK_URL

def get_news_detail(id):
    ret = ''
    try:
        res = requests.get(
            f"https://prod-dmmclientr.twinkle-star-knights.com/api/info/detail?info_id={id}",
            timeout=_G.REQUEST_TIMEOUT
        )
        doc = BS(res.content, features='lxml')
        for p in doc.findAll('p'):
            ret += p.decode_contents().replace('<br/>', '\n') + '\n\n'
    except Exception as err:
        utils.handle_exception(err)
        return ''
    return BS(ret, features='lxml').text

def parse_news_index(doc):
    ret = []
    ul = doc.find('ul', {'class': 'navi_info_inner_list'})
    for li in ul.children:
        txt = [s.strip() for s in li.text.split('\n') if s.strip()]
        if len(txt) < 2:
            continue
        obj = {}
        try:
            obj['title'] = txt[1]
            obj['postedAt'] = txt[0].replace('/', '-')
            tag_img = li.find('img')['src']
            obj['tag'] = next((i for i in TSK_TAG_MAP if TSK_TAG_MAP[i] == tag_img), 7)
            id = re.search(r"info_id=(\d+)", li.find('div', 'navi_info_inner_list_card')['data-detail_url']).group(1)
            dh = datetime.fromisoformat(obj['postedAt'])
            obj['id'] = (dh.year * 10**12) + (dh.month * 10**10) + (dh.day * 10**8) + int(id)
            obj['message'] = get_news_detail(id)
            ret.append(obj)
        except Exception as err:
            logger.error("Malformed news post object: ", txt)
            utils.handle_exception(err)
    return ret

def get_news_data():
    ret = {}
    try:
        res = requests.get(NEWS_URL, timeout=_G.REQUEST_TIMEOUT)
        ret = parse_news_index(BS(res.content, features='lxml'))
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
    logger.debug("Checking TSK news")
    if olds:
        o_cksum = int(datetime.fromisoformat(olds[0]['postedAt']).timestamp())
    n_cksum = int(datetime.fromisoformat(news[0]['postedAt']).timestamp())
    if o_cksum > n_cksum:
        logger.warning(f"Old news newer than latest news ({o_cksum} > {n_cksum})")
    elif o_cksum == n_cksum and news[0]['message'] == olds[0]['message']:
        logger.debug("No news, skip")
        return

    logger.info("Gathering TSK news")
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
            'icon_url': TSK_NEWS_ICON[obj['tag']],
        },
        'title': f"**{obj['title']}**",
        'description': f"<t:{int(datetime.fromisoformat(obj['postedAt']).timestamp())}>",
        'color': TSK_NEWS_COLOR[obj['tag']],
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

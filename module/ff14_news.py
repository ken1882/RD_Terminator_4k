import requests
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup as BS
from urllib.parse import urljoin
import _G
import utils
from logger import logger

PREV_NEWS_FILE = f"{_G.CACHE_DIR}/.ffxiv_prevnews.json"

NEWS_URL    = "https://www.ffxiv.com.tw/web/news/news_list.aspx?page="
WEBHOOK_URL = os.getenv('FFXIV_WEBHOOK_URL')

FFXIV_NEWS_TAG = {
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

FFXIV_NEWS_ICON = {
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

FFXIV_NEWS_COLOR = {
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

FFXIV_VOCAB_TW = {
    'NEWS_TAG': {
        1: '維護',
        2: '更新',
        3: '其他',
        4: '活動',
        5: '活動',
        6: '其他',
        7: '其他',
        8: '其他',
        9: '其他'
    }
}

def get_webhook_url():
    global WEBHOOK_URL
    return WEBHOOK_URL or ''

def get_news_detail(url):
    ret = ''
    try:
        res = requests.get(url, timeout=_G.REQUEST_TIMEOUT)
        doc = BS(res.content, features='lxml')
        content = doc.find('div', {'class':'article'})
        author  = doc.find('div', {'class':'publisher'})
        if author:
            ret += f"發布者: {author.text.strip()}\n"
        published = doc.find('div', {'class':'Date'}) # YYYY-MM-DD HH:mm
        if published:
            ret += f"發布時間: <t:{int(datetime.strptime(published.text.strip(), '%Y-%m-%d %H:%M').timestamp())}>\n"
        ret += "\n"
        if not content:
            logger.warning(f"Failed to get news detail from {url}")
        ret += content.text.strip()
    except Exception as err:
        utils.handle_exception(err)
        return ''
    return ret

def get_news_data():
    ret = {}
    try:
        res = requests.get(NEWS_URL, timeout=_G.REQUEST_TIMEOUT)
        ret = []
        doc = BS(res.content, features='lxml')
        table = doc.find('div', {'class': 'news_list'})
        entries = table.findAll('div', {'class': 'item'})
        for entry in entries:
            block = entry.find('div', {'class': 'title new'})
            if not block:
                continue
            id = int(entry.find('div', {'class': 'news_id'}).text.strip())
            title = block.text.strip()
            link = block.find('a')['href']
            link = urljoin(NEWS_URL, link)
            posted_at = datetime.now().isoformat()
            published = entry.find('div', {'class': 'publish_date'})
            if published:
                published = published.text.strip() # YYYY/MM/DD
                posted_at = datetime.strptime(published, '%Y/%m/%d').isoformat()
            tag = 7 # default to misc
            if entry.find('div', {'class': 'type event'}):
                tag = 4
            elif entry.find('div', {'class': 'type update'}):
                tag = 2
            elif entry.find('div', {'class': 'type maintain'}):
                tag = 1
            ret.append({
                'id': id,
                'title': title,
                'postedAt': posted_at,
                'tag': tag,
                'message': get_news_detail(link),
                'link': link,
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
    logger.debug("Checking FFXIV-TW news")
    if olds:
        o_cksum = int(datetime.fromisoformat(olds[0]['postedAt']).timestamp())
    n_cksum = int(datetime.fromisoformat(news[0]['postedAt']).timestamp())
    if o_cksum > n_cksum:
        logger.warning(f"Old news newer than latest news ({o_cksum} > {n_cksum})")
    elif o_cksum == n_cksum and news[0]['message'] == olds[0]['message']:
        logger.debug("No news, skip")
        return

    logger.info("Gathering FFXIV-TW news")
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
    desc = f"原始連結: {obj['link']}\n"
    payload['embeds'] = [{
        'author': {
            'name': FFXIV_VOCAB_TW['NEWS_TAG'][obj['tag']],
            'icon_url': FFXIV_NEWS_ICON[obj['tag']],
        },
        'title': f"**{obj['title']}**",
        'description': desc,
        'color': FFXIV_NEWS_COLOR[obj['tag']],
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

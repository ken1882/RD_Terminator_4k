import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup as BS
import _G
import utils
from logger import logger
import warnings
warnings.simplefilter("ignore")

PREV_NEWS_FILE = f"{_G.CACHE_DIR}/.das_prevnews.json"

NEWS_URL    = 'https://api.abyss-prod-r18.dotabyss.dmmgames.com/information/index?device=Player_R18'
DETAIL_URL  = 'https://api.abyss-prod-r18.dotabyss.dmmgames.com/information/detail'
WEBHOOK_URL = os.getenv('DAS_WEBHOOK_URL')

DAS_TAG_CLASS_MAP = {
    'textTagMaintenance': 1,
    'textTagUpdate': 2,
    'textTagGacha': 3,
    'textTagEvent': 4,
    'textTagCamp': 5,
    'textTagCampaign': 5,
    'textTagBug': 6,
    'textTagInfo': 7,
    'textTagImportant': 8,
}

DAS_NEWS_TAG = {
    1: 'MAINTENANCE',
    2: 'UPDATE',
    3: 'GACHA',
    4: 'EVENT',
    5: 'CAMPAIGN',
    6: 'BUG',
    7: 'MISC',
    8: 'IMPORTANT'
}

DAS_NEWS_ICON = {
    1: 'https://cdn-icons-png.flaticon.com/512/777/777081.png', # MAINTENANCE
    2: 'https://cdn.icon-icons.com/icons2/1508/PNG/512/updatemanager_104426.png', # UPDATE
    3: 'https://cdn-icons-png.flaticon.com/512/4230/4230567.png', # GACHA
    4: 'https://cdn-icons-png.flaticon.com/512/4285/4285436.png', # EVENT
    5: 'https://cdn-icons-png.flaticon.com/512/3867/3867424.png', # CAMPAIGN
    6: 'https://www.iconsdb.com/icons/preview/red/error-7-xxl.png', # BUG
    7: 'https://cdn-icons-png.flaticon.com/512/1827/1827301.png', # MISC
    8: 'https://www.iconsdb.com/icons/preview/red/error-7-xxl.png', # IMPORTANT
}

DAS_NEWS_COLOR = {
    1: 0xfc3aef, # MAINTENANCE
    2: 0x5299f7, # UPDATE
    3: 0xfad73c, # GACHA
    4: 0x50faf4, # EVENT
    5: 0xff5cb0, # CAMPAIGN
    6: 0xdb043e, # BUG
    7: 0xcccccc, # MISC
    8: 0xdb043e  # IMPORTANT
}

DAS_VOCAB_JP = {
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
    return WEBHOOK_URL or ''

def clean_text(elm):
    if not elm:
        return ''
    for unwanted in elm.find_all(['script', 'style']):
        unwanted.decompose()
    for br in elm.find_all('br'):
        br.replace_with('\n')
    for block in elm.find_all(['div', 'p', 'h1', 'h2', 'h3', 'li', 'tr']):
        block.insert_before('\n')
        block.append('\n')
    lines = [line.strip() for line in elm.get_text().splitlines()]
    return '\n'.join(line for line in lines if line)

def parse_tag(elm):
    if not elm:
        return 7
    classes = elm.get('class', [])
    return next((DAS_TAG_CLASS_MAP[cls] for cls in classes if cls in DAS_TAG_CLASS_MAP), 7)

def get_news_detail(id):
    try:
        res = requests.get(
            DETAIL_URL,
            params={
                'information_id': id,
                'is_webview': 0,
                'token': ''
            },
            timeout=_G.REQUEST_TIMEOUT
        )
        doc = BS(res.content, features='lxml')
        return clean_text(doc.find('div', {'class': 'infoDetailBody'}))
    except Exception as err:
        utils.handle_exception(err)
        return ''

def parse_news_index(doc):
    ret = []
    seen = set()
    for a in doc.select('a.infoList[data-info-id]'):
        obj = {}
        try:
            id = int(a['data-info-id'])
            if id in seen:
                continue
            seen.add(id)

            list_data = a.find('div', {'class': 'listData'})
            obj['title'] = clean_text(list_data.find('h1'))
            obj['postedAt'] = clean_text(list_data.find('p')).replace('/', '-')
            obj['tag'] = parse_tag(list_data.find('span', {'class': 'listLabel'}))

            dh = datetime.fromisoformat(obj['postedAt'])
            obj['id'] = (dh.year * 10**12) + (dh.month * 10**10) + (dh.day * 10**8) + int(id)
            obj['message'] = get_news_detail(id)
            ret.append(obj)
        except Exception as err:
            logger.error("Malformed DAS news post object: %s", clean_text(a))
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
        ret = sorted(ret, key=lambda o: o['id'], reverse=True)
        save_news(ret)
    else:
        with open(PREV_NEWS_FILE, 'r') as fp:
            ret = json.load(fp)
    return ret

def save_news(news):
    with open(PREV_NEWS_FILE, 'w') as fp:
        json.dump(sorted(news, key=lambda o: o['id'], reverse=True)[:100], fp)

def update():
    news = {}
    try:
        news = get_news_data()
        news = sorted(news, key=lambda o: o['id'], reverse=True)
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
    logger.debug("Checking DAS news")
    if olds:
        o_cksum = int(datetime.fromisoformat(olds[0]['postedAt']).timestamp())
    n_cksum = int(datetime.fromisoformat(news[0]['postedAt']).timestamp())
    if o_cksum > n_cksum:
        logger.warning(f"Old news newer than latest news ({o_cksum} > {n_cksum})")
    elif o_cksum == n_cksum and news[0]['message'] == olds[0]['message']:
        logger.debug("No news, skip")
        return

    logger.info("Gathering DAS news")
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
    save_news(news)

def send_message(obj):
    payload = {}
    payload['embeds'] = [{
        'author': {
            'name': DAS_VOCAB_JP['NEWS_TAG'][obj['tag']],
            'icon_url': DAS_NEWS_ICON[obj['tag']],
        },
        'title': f"**{obj['title']}**",
        'description': f"<t:{int(datetime.fromisoformat(obj['postedAt']).timestamp())}>",
        'color': DAS_NEWS_COLOR[obj['tag']],
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

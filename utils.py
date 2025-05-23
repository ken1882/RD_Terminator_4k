import _G
import traceback
import requests
import os
from datetime import datetime
from logger import logger

def handle_exception(err):
    errinfo = traceback.format_exc()
    logger.error(f"An error occured!\n{str(err)}\n{errinfo}")

def chunk(it, n):
  return [it[i * n:(i + 1) * n] for i in range((len(it) + n - 1) // n )]

def send_critical_message(*messages, sep=' '):
    webhook_url = os.getenv('DEBUG_WEBHOOK')
    message = sep.join(messages)
    if not webhook_url:
        logger.warning(f"Debug webhook is not set, message to send:\n{message}")
        return
    payload = {}
    payload['content'] = '@here'
    payload['embeds'] = [{
        'title': f"**Critical Error!**",
        'description': f"<t:{int(datetime.now().timestamp())}>",
        'color': 0xff1111,
        'fields': []
    }]
    # this will fail if total length is over 6000
    for msg in chunk(message, 1000):
        payload['embeds'][0]['fields'].append({
            'name': " \u200b", # zero-width space
            'value': msg
        })
    return requests.post(os.getenv('DEBUG_WEBHOOK'), json=payload)

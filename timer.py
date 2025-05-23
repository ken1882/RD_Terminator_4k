from datetime import datetime, timedelta
from logger import logger
from typing import Callable, Dict

TimerMap: Dict[str, Dict] = {}

def set_timer(name: str, interval: timedelta, func: Callable=None, *args, **kwargs):
    global TimerMap
    TimerMap[name] = {
        'interval': interval,
        'func': func,
        'args': args,
        'kwargs': kwargs,
        'interval': interval,
        'next_run': datetime.now() + interval
    }

def is_expired(name: str) -> bool:
    global TimerMap
    if name not in TimerMap:
        logger.warning(f"Timer '{name}' does not exist.")
        return False
    return datetime.now() >= TimerMap[name]['next_run']

def delay(name: str, seconds: int=0, minutes: int=0, hours: int=0, future: datetime=None) -> datetime:
    global TimerMap
    if name not in TimerMap:
        logger.warning(f"Timer '{name}' does not exist.")
        return
    if future:
        TimerMap[name]['next_run'] = future
    else:
        future = datetime.now() + timedelta(seconds=seconds, minutes=minutes, hours=hours)
    TimerMap[name]['next_run'] = future
    logger.debug(f"Next run for '{name}' expected around {future}")
    return future

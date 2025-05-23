import os, sys
import json
import traceback

from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

ENCODING = 'utf-8'
sys.stdout.reconfigure(encoding=ENCODING)
sys.stderr.reconfigure(encoding=ENCODING)

IS_WIN32 = False
IS_LINUX = False

if sys.platform == 'win32':
    IS_WIN32 = True
elif sys.platform == 'linux':
    IS_LINUX = True

ARGV:dict[str] = {}

PRODUCTION = ((os.getenv('FLASK_ENV') or '').lower() == 'production')

# 0:NONE 1:ERROR 2:WARNING 3:INFO 4:DEBUG
VerboseLevel = 3
VerboseLevel = 4 if ('--verbose' in sys.argv) else VerboseLevel

FlagRunning = True
FlagPaused  = False
FlagWorking = False
FlagReady   = False

CACHE_DIR = './cache'

ERRNO_OK          = 0x0
ERRNO_LOCKED      = 0x1
ERRNO_UNAUTH      = 0x2
ERRNO_BADDATA     = 0x3
ERRNO_MAINTENANCE = 0x10
ERRNO_DAYCHANGING = 0x11
ERRNO_FAILED      = 0xfe
ERRNO_UNAVAILABLE = 0xff

SERVER_TICK_INTERVAL = 60
REQUEST_TIMEOUT = 30
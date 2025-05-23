import logging
from logging.handlers import TimedRotatingFileHandler
import sys
from pathlib import Path

log_dir = Path('./log')
log_dir.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ #
# Get / create logger                                                #
# ------------------------------------------------------------------ #
logger = logging.getLogger('rdt4k')
logger.setLevel(logging.DEBUG)
logger.propagate = False  # avoid double-logging via the root logger

# Clear existing handlers so repeated calls don't duplicate output
if logger.handlers:
    logger.handlers.clear()

# ------------------------------------------------------------------ #
# Common formatter                                                   #
# ------------------------------------------------------------------ #
fmt = '%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s'
datefmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

# ------------------------------------------------------------------ #
# 1) STDOUT handler                                                  #
# ------------------------------------------------------------------ #
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

# ------------------------------------------------------------------ #
# 2) Timed rotating file handler                                     #
# ------------------------------------------------------------------ #
file_path = log_dir / f"rdt4k.log"
file_handler = TimedRotatingFileHandler(
    filename=file_path,
    when='midnight',
    interval=1,
    backupCount=30,
    encoding="utf-8",
    utc=False,
)
# Add a date suffix to rotated files, e.g. app.log.2025-05-23
file_handler.suffix = "%Y-%m-%d"
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

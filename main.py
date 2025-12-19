import _G
import utils
from logger import logger
from time import sleep
from threading import Thread
from types import ModuleType

LOADED_MODULES: list[ModuleType] = []
Workers: list[Thread] = []

FLAG_MULTITHREAD = False # not recommended to enable due to Elon's API rate limit

def import_modules():
    global LOADED_MODULES
    import module.tsk_news as tsk_news
    import module.mst_news as mst_news
    import module.mtd_news as mtd_news
    import module.aa_news as aa_news
    import module.ff14_news as ff14_news
    import module.twitter as twitter
    LOADED_MODULES.extend([
        tsk_news,
        mst_news,
        mtd_news,
        aa_news,
        ff14_news,
        twitter
    ])

def init_modules():
    global LOADED_MODULES
    for module in LOADED_MODULES:
        try:
            logger.info(f"Initializing {module.__name__}")
            module.init()
        except Exception as err:
            utils.handle_exception(err)
            logger.warning(f"Failed to initialize {module.__name__}: {err}")

def main_loop():
    global LOADED_MODULES
    while _G.FlagRunning:
        workers: list[Thread] = []
        for module in LOADED_MODULES:
            try:
                if FLAG_MULTITHREAD:
                    worker = Thread(target=module.update)
                    worker.start()
                    workers.append(worker)
                else:
                    module.update()
            except Exception as err:
                utils.handle_exception(err)
                logger.warning(f"Failed to update {module.__name__}: {err}")
        sleep(_G.SERVER_TICK_INTERVAL)
        [w.join() for w in workers]

def main():
    import_modules()
    init_modules()
    main_loop()

if __name__ == '__main__':
    logger.info("App Start")
    try:
        main()
    finally:
        _G.FlagRunning = False
        logger.info("App Stop")

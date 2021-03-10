from logging import INFO, getLogger, StreamHandler, Formatter, FileHandler, DEBUG


def setup_logger(log_folder, modname=__name__):
    logger = getLogger(modname)
    logger.setLevel(DEBUG)

    sh = StreamHandler()
    sh.setLevel(DEBUG)
    formatter = Formatter(
        '%(levelname)s:%(filename)s:%(lineno)d:%(message)s')
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    fh = FileHandler(log_folder)
    fh.setLevel(INFO)
    fh_formatter = Formatter(
        '%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d:%(message)s')
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)
    return logger


if __name__ == '__main__':
    logger = setup_logger('log/logger_test.log')
    logger.debug('Log test')
    listed_markets = [{'name': 'BTC-PERP', 'ask': 100}]
    logger.info(listed_markets)

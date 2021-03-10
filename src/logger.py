from logging import INFO, getLogger, StreamHandler, Formatter, FileHandler, DEBUG
import os


def setup_logger(file_name, modname=__name__):
    dir = os.path.dirname(file_name)
    if not os.path.isdir(dir):
        os.makedirs(dir)

    logger = getLogger(modname)
    logger.setLevel(DEBUG)

    sh = StreamHandler()
    sh.setLevel(DEBUG)
    formatter = Formatter(
        '%(levelname)s:%(filename)s:%(lineno)d:%(message)s')
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    fh = FileHandler(file_name)
    fh.setLevel(INFO)
    fh_formatter = Formatter(
        '%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d:%(message)s')
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)
    return logger


if __name__ == '__main__':
    filepath = 'log/test/mkdir_test.log'
    logger = setup_logger(filepath)
    logger.debug('Log test')
    listed_markets = [{'name': 'BTC-PERP', 'ask': 100}]
    logger.info(listed_markets)

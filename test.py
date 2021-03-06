import os
import configparser
from dotenv import load_dotenv

# @TODO  環境変数か各々のボットの定数から使うコンフィグを選択するIDを渡して，confを読む
load_dotenv(verbose=True)
PYTHON_ENV = os.environ.get("PYTHON_ENV")
ENV_FILE = '.production.env' if PYTHON_ENV == 'production' else '.development.env'
dotenv_path = os.path.join(os.getcwd(), ENV_FILE)
load_dotenv(dotenv_path)

config = configparser.ConfigParser()
conf_path = f"./setting/{os.path.basename(__file__)}".replace('.py', '.ini')
try:
    if not os.path.isfile(conf_path):
        raise FileNotFoundError
except FileNotFoundError as e:
    print(f"FILE_NO_FOUND:{conf_path}にconfファイルを置いてください")
    exit(1)

conf_path = './setting/tweet_long.ini'
config.read(conf_path)

print("conf_path :>>", conf_path)
print("os.path.basename(__file__) :>>", os.path.basename(__file__))
print("PYTHON_ENV :>>", PYTHON_ENV)
# print(config["DEFAULT"])

CONFIG_SECTION = 'DEFAULT' if PYTHON_ENV == 'production' else 'DEVELOPMENT'
for item in config[CONFIG_SECTION]:
    print("item :>>", config[CONFIG_SECTION][item])

import os
from dotenv import load_dotenv

# @TODO  環境変数か各々のボットの定数から使うコンフィグを選択するIDを渡して，confを読む
load_dotenv(verbose=True)
PYTHON_ENV = os.environ.get("PYTHON_ENV")
ENV_FILE = '.production.env' if PYTHON_ENV == 'production' else '.development.env'
dotenv_path = os.path.join(os.getcwd(), ENV_FILE)
load_dotenv(dotenv_path)

TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_SECERT = os.environ.get("TWITTER_API_SECERT")
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN")

FTX_API_KEY = os.environ.get("FTX_API_KEY")
FTX_API_SECRET = os.environ.get("FTX_API_SECRET")

BOT_NAME = os.environ.get("BOT_NAME")
MARKET = os.environ.get("MARKET")
SUBACCOUNT = os.environ.get("SUBACCOUNT")
MAX_SIZE = os.environ.get("MAX_SIZE")
TRADABLE = os.environ.get("TRADABLE")

LINE_USER_ID = os.environ.get("LINE_USER_ID")
LINE_BEARER_TOKEN = os.environ.get("LINE_BEARER_TOKEN")

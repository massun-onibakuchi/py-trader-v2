import os
import configparser
from sys import argv
from dotenv import load_dotenv

load_dotenv(verbose=True)
PYTHON_ENV = os.environ.get("PYTHON_ENV")
ENV_FILE = '.production.env' if PYTHON_ENV == 'production' else '.development.env'
dotenv_path = os.path.join(os.getcwd(), ENV_FILE)
load_dotenv(dotenv_path)
print(".env path :>>" + dotenv_path)

API_PREFIX = ""
key_name = "FTX_API_KEY"
secret_name = "FTX_API_SECRET"
config = configparser.ConfigParser()
conf_path = f"./src/setting/{os.path.basename(argv[0])}".replace('.py', '.ini')
try:
    if not os.path.isfile(conf_path):
        raise FileNotFoundError
    else:
        config.read(conf_path)
except FileNotFoundError as e:
    print(f"FILE_NO_FOUND:{conf_path}にconfファイルを置いてください")
    exit(1)

try:
    API_PREFIX = config['DEFAULT']['API_PREFIX']
    if len(API_PREFIX.lstrip()) > 0:
        key_name = f"{API_PREFIX}_{key_name}".upper()
        secret_name = f"{API_PREFIX}_{secret_name}".upper()
except KeyError as e:
    print("IGNORE API_PREFIX AND USE DEFAULT API_KEYs")

SECTION = 'DEFAULT' if PYTHON_ENV == 'production' else 'DEVELOPMENT'
config = config[SECTION]
FTX_API_KEY = os.environ.get(key_name)
FTX_API_SECRET = os.environ.get(secret_name)
SUBACCOUNT = os.environ.get("SUBACCOUNT")
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_SECERT = os.environ.get("TWITTER_API_SECERT")
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")
LINE_BEARER_TOKEN = os.environ.get("LINE_BEARER_TOKEN")

try:
    if FTX_API_KEY is None or FTX_API_SECRET is None:
        raise ValueError(FTX_API_KEY, FTX_API_SECRET, "API_KEY_OR_API_SECRET_ARE_NONE")
except ValueError as e:
    print("e :>>", e)
    exit(1)

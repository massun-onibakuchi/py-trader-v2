# PyTrader

A python bot that trade a cryptocurrency based on some strategies.

## Strategy

- ミスプライスロング `catch_miss_price.py`
- トークンのリバランスを利用したエントリー `rebalance_entry.py`
- 上場ロング `listed_and_buy.py`
- ツイッター監視ロング `tweet_long.py`
- 精算時に積立てる

## How it works

- `setting` set config and env variable
- `ftx` ftx api wrapper
- `twitter` twitter recent reseach
- `ftx_bot_base` ボットの基底クラス

## How to install

MacOSX/Linux

First install Poetry, then
`poetry -V`

If fail,run
`apt-get install python3-venv`

To install dependencies,
`poetry install `

To run the bot,
` poetry run python file.py`

## How to use

Prepare `.production.env` beforehand,and then run
`python3 file.py`

ボットの設定をマニュアルで変更するためには，bot の実行ファイル`some-bot.py`名と同名の INI ファイルを`setting/some-bot.ini`を変更する．

To make the bot reboot automatically when it crashes due to errors, use the forever.py script provided:

```
chmod +x forever.py
./forever.py file.py
```

INI ファイルで記す必要のある変数は，

```
[DEFAULT]
# 必須の設定
BOT_NAME=IEO_FTT_LONG
MARKET=FTT-PERP
MARKET_TYPE=future
API_PREFIX=
TRADABLE=True
SEC_TO_EXPIRE=420
MAX_ORDER_NUMBER=10
MAX_POSITION_SIZE=1000
VERBOSE=True
PUSH_NOTIF=True
```

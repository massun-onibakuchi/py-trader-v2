# PyTrader
A python bot that trade a cryptocurrency based on some strategies.
## Strategy
 - ミスプライスロング `catch_miss_price.py`
 - トークンのリバランスを利用したエントリー `rebalance_entry.py`
 - 上場ロング `listed_and_buy.py`
 - ツイッター監視ロング `tweet_long.py`

## How it works
 - `setting`  set config and env variable
 - `ftx`    ftx api wrapper
 - `twitter`  twitter recent reseach
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

ボットの設定をマニュアルで変更するためには，botの実行ファイル`some-bot.py`名と同名のINIファイルを`setting/some-bot.ini`を変更する．

To make the bot reboot automatically when it crashes due to errors, use the forever.py script provided:
```
chmod +x forever.py
./forever.py file.py
```

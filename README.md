# PyTrader
A python bot that trade a cryptocurrency based on some strategies.
## Strategy
 - 上場ロング `listed_and_buy.py`
 - ツイッター監視ロング `tweet_long.py`

## How it works
 - `setting`
  set env variable
 - `ftx`
  ftx api wrapper
 - `twitter`
   twitter recent reseach

## How to install
MacOSX/Linux

To install Poetry, run
`curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python3`

`source $HOME/.poetry/env`

And then, `poetry -V`

If fail,run
`apt-get install python3-venv`

To install dependencies,

`poetry install `

To run the bot,  
` poetry run python file.py`

## How to use
Prepare `.production.env` beforehand,and then run
`python3 file.py`

To make the bot reboot automatically when it crashes due to errors, use the forever.py script provided:
```
chmod +x forever.py
./forever.py file.py
```

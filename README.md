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

## How to use
Prepare `.production.env` beforehand,and then run
`python3 file.py`

To make the bot reboot automatically when it crashes due to errors, use the forever.py script provided:
```
chmod +x forever.py
./forever.py file.py
```

If you use `poetry` ,run
` poetry run python file.py`

For convenience,
```
alias po='poetry run'
alias pp='poetry run python'

function pdev () {
  poetry add -D black flake8 pytest
}
```

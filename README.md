
## Strategy
 - 上場ロング `./listed_and_buy.py`
 - ツイッター監視ロング `./tweet_long.py`

## Folders
 - `setting`
  set env variable
 - `ftx`
  ftx api wrapper
 - `twitter_search`
   twitter recent reseach

## How to use
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

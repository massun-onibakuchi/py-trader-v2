import asyncio
from typing import Dict, List, Union
from ftx.ftx import FTX
from line import push_message
from setting.settting import FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT, PYTHON_ENV, config
import json

TRADABLE = config.getboolean('TRADABLE')
BOT_NAME = config["BOT_NAME"]
VERBOSE = config.getboolean("VERBOSE")


class Bot:
    DEFAULT_USD_SIZE = float(config['DEFAULT_USD_SIZE'])
    SPECIFIC_NAMES = config['SPECIFIC_NAMES']
    SPECIFIC_USD_SIZE = float(config['SPECIFIC_USD_SIZE'])

    prev_markets: List[Dict[str, Union[str, float]]] = []

    def __init__(self, api_key, api_secret):
        self.ftx = FTX(
            "",
            api_key=api_key,
            api_secret=api_secret,
            subaccount=SUBACCOUNT)

        print(f"PYTHON_ENV:{PYTHON_ENV}\nSUBACCOUNT:{SUBACCOUNT}")
        # タスクの設定およびイベントループの開始
        loop = asyncio.get_event_loop()
        tasks = [self.run()]
        loop.run_until_complete(asyncio.wait(tasks))

    # ---------------------------------------- #
    # bot main
    # ---------------------------------------- #
    async def run(self):
        while True:
            try:
                await self.main(10)
                await asyncio.sleep(0)
            except Exception as e:
                print('An exception occurred', e)
                push_message(e)
                exit(1)

    async def main(self, interval):
        # main処理
        listed = []
        new_listed = []

        self.ftx.market()
        response = await self.ftx.send()
        # print(json.dumps(response[0]['result'], indent=2, sort_keys=False))
        # 引数に与えた条件に当てはまる上場銘柄をリストに抽出する
        listed = self.extract_markets(markets=response[0]['result'], include=["spot"])
        if VERBOSE:
            print(json.dumps(listed, indent=2, sort_keys=False))
        # 前回の上場銘柄リストがあるならば，現在の上場リストと比較して新規上場銘柄があるか調べる
        if len(self.prev_markets) > 0:
            # 新規上場銘柄を抽出する
            new_listed = self.extract_new_listed(self.prev_markets, listed)
            print(
                "\nNew Listed...",
                json.dumps(
                    new_listed,
                    indent=2,
                    sort_keys=False))

            for new in new_listed:
                # SNS通知
                push_message(f"NEW LISTED:\n {json.dumps(new)}")

                usd = self.SPECIFIC_USD_SIZE if str(
                    new["baseCurrency"]).upper() in self.SPECIFIC_NAMES else self.DEFAULT_USD_SIZE
                size = usd / float(new["bid"])
                await asyncio.sleep(0)

                if TRADABLE:
                    if PYTHON_ENV == 'production':
                        self.ftx.place_order(
                            type='market',
                            market=new["name"],
                            side='buy',
                            price='',
                            size=size,
                            postOnly=False)
                    else:
                        self.ftx.place_order(
                            type='limit',
                            market='ETH-PERP',
                            side='buy',
                            price=1000,
                            size=size,
                            postOnly=False)
                    response = await self.ftx.send()
                    print(response[0])
                    orderId = response[0]['result']['id']
                    push_message(
                        f"ENV:{PYTHON_ENV}\nBOT:{BOT_NAME}\nOrdered :\norderId:{orderId}\n{new['name']}\nSIZE:{size}")
                    print(f"ENV:{PYTHON_ENV}\nMARKET:{new['name']}\nSIZE:{size}")

        # ---------共通の処理----------
        await asyncio.sleep(interval)

        # 最新の上場のリストを更新
        self.prev_markets = listed
        listed = []
        print("Snapshot markets...")

        await asyncio.sleep(0)

    def extract_markets(
            self,
            markets,
            include=["spot", "future"],
            exclude=["HEDGE", "BULL", "BEAR", "HALF", "BVOL"]):
        satsfied = []
        has_spot = "spot" in include
        has_future = "future" in include
        for market in markets:
            if market["enabled"]:
                if has_spot and market['type'] == "spot" and market["quoteCurrency"] == 'USD':
                    is_excluded = True
                    for keyword in exclude:
                        is_excluded = is_excluded and keyword not in market["baseCurrency"]
                    if is_excluded:
                        satsfied.append(market)
                if has_future and market["type"] == 'future':
                    satsfied.append(market)
        return satsfied

    def extract_new_listed(
            self,
            prev_markets: List[Dict[str, Union[str, float]]],
            current_markets: List[Dict[str, Union[str, float]]]) -> List[Dict[str, Union[str, float]]]:
        new_listed = []
        if len(current_markets) == 0:
            return new_listed
        prev_market_names = [prev_market["name"] for prev_market in prev_markets]
        for current_market in current_markets:
            if current_market["name"] not in prev_market_names:
                new_listed.append(current_market)
        return new_listed


if __name__ == "__main__":

    Bot(api_key=FTX_API_KEY, api_secret=FTX_API_SECRET)

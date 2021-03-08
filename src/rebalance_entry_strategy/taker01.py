import asyncio
from typing import Dict, List, Union
from enum import IntEnum
from ftx.ftx import FTX
from line import push_message
from setting.settting import FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT, PYTHON_ENV, config
from pprint import pprint

TRADABLE = config.getboolean('TRADABLE')
BOT_NAME = config["BOT_NAME"]
VERBOSE = config.getboolean("VERBOSE")


class Color(IntEnum):
    ETNTRY = 1
    ORDER_AWAIT = 2
    AWAIT = 3

# 01分にtakeするクラス
# 01分にcatchhigeのmake注文だすクラス
# 03分にポジションを持っていたら，全ての新規ポジション増やす注文をキャンセルして01分の始値にtp指値か即take決済，
# crontabで00:00に起動
# main botクラスでchangebodでperpsをスクリーニングして，対象を決定
# main botクラスはそれらを操作取り扱う


class Bot:
    DEFAULT_USD_SIZE = float(config['DEFAULT_USD_SIZE'])
    SPECIFIC_NAMES = config['SPECIFIC_NAMES']
    SPECIFIC_USD_SIZE = float(config['SPECIFIC_USD_SIZE'])

    def __init__(self, ftx, market):
        print(f"ENV:{PYTHON_ENV}\nSUBACCOUNT:{SUBACCOUNT}")
        self.prev_markets: List[Dict[str, Union[str, float]]] = []
        self.ftx = ftx
        self.market = market
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
                await self.main(5)
                await asyncio.sleep(0)
            except Exception as e:
                print('An exception occurred', e)
                push_message(e)
                exit(1)

    async def main(self, interval):
        # main処理

        # self.ftx.positions()
        # response = await self.ftx.send()

        # if len(response[0]["result"]) > 0:
        #     self.phase = 'position'

        self.ftx.futures()
        response = await self.ftx.send()
        # 引数に与えた条件に当てはまる上場銘柄をリストに抽出する
        perpetual_markets = self.extract_markets(
            markets=response[0]['result'],
            market_type=["perpetual"],
            exclude_keywords=["BTC", "ETH", "XRP"],
        )
        if VERBOSE:
            pprint.pprint(perpetual_markets)
        # 新規上場銘柄を抽出する
        perpetuals = self.extract_change_bod(perpetual_markets, grater_than=0.03)

        for new in perpetuals:
            usd = self.SPECIFIC_USD_SIZE if str(new["baseCurrency"]).upper(
            ) in self.SPECIFIC_NAMES else self.DEFAULT_USD_SIZE
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

        await asyncio.sleep(0)

    def extract_markets(self, markets, market_type=["spot", "future", "move", "perpetual"], exclude_keywords=[
            "/HEDGE", "/BULL", "/BEAR", "/HALF", "BVOL"]) -> List[Dict[str, Union[str, float]]]:
        """引数で指定した条件を満たしたマーケットを返す関数

        FTX REST APIのfutures/marketsレスポンスを満たす型を受け取り，引数で指定した条件を満たしたマーケットを返す

        Args:
            markets ( List[Dict[str, Union[str, float]]] ): FTX REST APIのfuturesとmarketsのレスポンスの型
            market_type (List[str], optional) : 結果に含めるマーケットのタイプ
            exclude_keywords (List[str], optional) : マーケット名に含まれるとき結果から除外するキーワード

        Returns:
            [List[Dict[str, Union[str,float]]]]: [market_typeを満たし，exclude_keywordsが銘柄名に部分文字列として含まれるものを除外したmarkets]
        """
        satsfied = []
        has_spot = "spot" in market_type
        has_future = "future" in market_type
        has_move = "move" in market_type
        has_perpetual = "perpetual" in market_type
        for market in markets:
            if market["enabled"]:
                for keyword in exclude_keywords:
                    if keyword in market["name"]:
                        continue
                if has_spot and market['type'] == "spot" and market["quoteCurrency"] == 'USD':
                    satsfied.append(market)
                if has_future and market["type"] == 'future':
                    satsfied.append(market)
                if has_move and market['type'] == "move":
                    satsfied.append(market)
                if has_perpetual and market["type"] == 'perpetual':
                    satsfied.append(market)
        return satsfied

    def extract_change_bod(self, markets, grater_than=0.03):
        satsfied = []
        for market in markets:
            if grater_than <= abs(market["changeBod"]):
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

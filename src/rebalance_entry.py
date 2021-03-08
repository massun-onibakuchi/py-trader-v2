import asyncio
from typing import Dict, List, Union
from enum import IntEnum
from ftx.ftx import FTX
from line import push_message
from setting.settting import FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT, PYTHON_ENV, config
from pprint import pprint
from datetime import timezone, datetime

TRADABLE = config.getboolean('TRADABLE')
BOT_NAME = config["BOT_NAME"]
MARKET = config["MARKET"]
VERBOSE = config.getboolean("VERBOSE")
SINGLE = config.getboolean("SINGLE")


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
    FRONTRUN_USD_SIZE = float(config['DEFAULT_USD_SIZE'])
    PLACE_MISS_PRICE_USD_SIZE = float(config['DEFAULT_USD_SIZE'])
    SPECIFIC_NAMES = config['SPECIFIC_NAMES']
    SPECIFIC_USD_SIZE = float(config['SPECIFIC_USD_SIZE'])

    def __init__(self, api_key, api_secret):
        self.ftx = FTX(
            market=MARKET,
            api_key=api_key,
            api_secret=api_secret,
            subaccount=SUBACCOUNT)
        self.prev_markets: List[Dict[str, Union[str, float]]] = []

        print(f"ENV:{PYTHON_ENV}\nSUBACCOUNT:{SUBACCOUNT}")
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
        # position確認
        position = {}
        self.ftx.positions()
        response = await self.ftx.send()
        for pos in response[0]["result"]:
            if pos["future"] == MARKET:
                position = pos
                break
        print("\nPOSITION :>>")
        pprint(position)

        self.phase = self.update(self.phase, position)

        # perps = []
        if self.phase == 'fetch':
            self.ftx.future()
            response = await self.ftx.send()
            perps = self.extract_markets(
                markets=[response[0]['result']],
                market_type=["perpetual"],
                exclude_keywords=["BTC", "ETH", "XRP"],
            )
            perps = self.extract_change_bod(perps, grater_than=0.03)
            if VERBOSE:
                pprint.pprint(perps)
            if len(perps[0]) > 0:
                self.phase = 'frontrun'
                self.perp = perps[0]
            return await asyncio.sleep(5)

        side, size = self.order_conf(self.phase, self.perp)
        if self.phase == 'frontrun':
            success = await self.frontrun(market=MARKET, side=side, size=size, ord_type='market')
            if success:
                self.phase = 'prepare_miss_price'
            await asyncio.sleep(5)

        if self.phase == 'prepare_miss_price':
            success = await self.catch_miss_price(market=MARKET, side=side, size=size)
            if success:
                self.phase = 'settle'
            await asyncio.sleep(5)

        if self.phase == 'settle':
            success = await self.catch_miss_price(market=MARKET, side=side, size=size)
            if success:
                self.phase = 'waiting'
                self.perp = {}
            await asyncio.sleep(5)

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

    def extract_change_bod(self, markets, grater_than=0.03, smaller_than=0.0):
        satsfied = []
        for market in markets:
            if grater_than <= abs(market["changeBod"]):
                satsfied.append(market)
        return satsfied

    async def frontrun(self, market, side, size, ord_type='limit'):
        if PYTHON_ENV == 'production':
            self.ftx.place_order(
                type=ord_type,
                market=market,
                side=side,
                price='',
                size=size,
                postOnly=False)
        else:
            self.ftx.place_order(
                type=ord_type,
                market=market,
                side=side,
                price=1000,
                size=size,
                postOnly=False)
        response = await self.ftx.send()
        print(f"ENV:{PYTHON_ENV}\nMARKET:{market}\nSIZE:{size}\nSIDE:{side}")
        print(response[0])
        push_message(
            f"ENV:{PYTHON_ENV}\nBOT:{BOT_NAME}\nOrdered\nMARKET:{market}\nSIZE:{size}\nSIDE:{side}")

    async def catch_miss_price(self, market, side, size):
        return await self.frontrun(market, side, size, 'limit')

    def update(self, phase, position):
        utc_date = datetime.now(timezone.utc)
        hour = utc_date.hour
        min = utc_date.min
        if hour == 0 and min == 1 and phase == 'wait':
            return 'fetch'
        if hour == 0 and min == 1 and phase == 'fetch':
            return 'frontrun'
        if hour == 0 and min == 3 and abs(position["size"]) > 0:
            return 'settle'
        else:
            return 'waiting'

    def order_conf(self, phase, perp):
        side = ''
        size = 0.0
        if phase == 'fetch':
            side = ''
            size = 0.0
        if phase == 'frontrun':
            side = 'buy' if perp["changeBod"] > 0 else 'sell'
            size = self.FRONTRUN_USD_SIZE / float(perp["bid"])
        if phase == 'prepare_miss_price':
            side = 'sell' if perp["changeBod"] < 0 else 'buy'  # inverse_side
            size = self.PLACE_MISS_PRICE_USD_SIZE / float(perp["bid"])
        if phase == 'settle':
            side = 'sell' if perp["changeBod"] < 0 else 'buy'  # inverse_side
            size = - perp['size']
        return side, size


if __name__ == "__main__":

    Bot(api_key=FTX_API_KEY, api_secret=FTX_API_SECRET)

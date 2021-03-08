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
    FRONTRUN_USD_SIZE = float(config['DEFAULT_USD_SIZE'])
    CATCH_MISS_PRICE_USD_SIZE = float(config['DEFAULT_USD_SIZE'])

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
        """
         - positionを取ってくる
         - futureからデータとる
        if hour minが01-03ではないとき
            if positionがあるなら，決済
            if 閾値に達したなら....
        else:
            if 01 and 十分な価格変化:
                成り行き
                catch_miss_price
            if 03 あたり:
                if positionあるなら，決済
        """
        position = {}
        self.ftx.positions()
        response = await self.ftx.send()
        for pos in response[0]["result"]:
            if pos["future"] == MARKET:
                position = pos
                break
        print("\nPOSITION :>>")
        pprint(position)

        self.ftx.future()
        response = await self.ftx.send()

        utc_date = datetime.now(timezone.utc)
        hour = utc_date.hour
        min = utc_date.minute
        if hour == 0 and min >= 1 and min <= 3:
            perps = self.extract_change_bod([response[0]["result"]], floor_bod=0.03)
            pprint(perps)
            perp = perps[0]
            if min == 1:
                # positionを持っているならば，
                if abs(position["size"]):
                    return
                # positionを持っていなくて，bodが基準値以上ならば
                # bod>0ならば，perpを買い増しリバランスなのでtakerで順方向エントリー
                side = 'buy' if perp["changeBod"] > 0 else 'sell'
                size = self.FRONTRUN_USD_SIZE / float(perp["bid"])
                await self.taker_frontrun(MARKET, side, size)

                await asyncio.sleep(10)
                # miss priceを狙って逆張りの指値
                price = float(perp["bid"]) * 1.004
                inverse_side = 'buy' if perp["changeBod"] < 0 else 'sell'
                size = self.CATCH_MISS_PRICE_USD_SIZE / float(perp["bid"])
                await self.maker_frontrun(MARKET, price, inverse_side, size,)

                await asyncio.sleep(interval)
            if min == 3:
                if abs(position["size"]) > 0:
                    side = 'buy' if position["size"] < 0 else 'sell'
                    size = abs(position["size"])
                    self.ftx.place_order(MARKET, side, 'market', size)
                    response = await self.ftx.send()
                    print(response[0]["result"])
        else:
            # if hour minが01-03ではないとき
            # positionがあるなら決済
            if abs(position["size"]) > 0:
                side = 'buy' if position["size"] < 0 else 'sell'
                size = abs(position["size"])
                self.ftx.place_order(MARKET, side, 'market', size)
                await self.ftx.send()
                print(response[0]["result"])

            perps = self.extract_change_bod([response[0]["result"]], floor_bod=0.03)
            # if リバランスの閾値に達しているなら...
            if len(perps) > 0:
                pass

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

    def extract_change_bod(
            self,
            markets,
            floor_bod=0.0,
            grater_than=0.0,
            smaller_than=0.0):
        satsfied = []
        if floor_bod > 0:
            for market in markets:
                if floor_bod <= abs(market["changeBod"]):
                    satsfied.append(market)
            return satsfied
        if grater_than > 0 and smaller_than < 0:
            for market in markets:
                if grater_than <= market["changeBod"]:
                    satsfied.append(market)
                if smaller_than >= market["changeBod"]:
                    satsfied.append(market)
        return satsfied

    async def _entry(self, market, side, price, size, ord_type='limit', postOnly=False):
        if PYTHON_ENV == 'production':
            self.ftx.place_order(
                type=ord_type,
                market=market,
                side=side,
                price=price,
                size=size,
                postOnly=postOnly)
        else:
            self.ftx.place_order(
                type=ord_type,
                market=market,
                side=side,
                price=price,
                size=size,
                postOnly=True)
        response = await self.ftx.send()
        print(f"ENV:{PYTHON_ENV}\nMARKET:{market}\nSIZE:{size}\nSIDE:{side}")
        print(response[0])
        push_message(
            f"ENV:{PYTHON_ENV}\nBOT:{BOT_NAME}\nOrdered\nMARKET:{market}\nSIZE:{size}\nSIDE:{side}")

    async def taker_frontrun(self, market, side, size):
        await self._entry(market, side, '', size, 'market', False)

    async def maker_frontrun(self, market, price, side, size):
        await self._entry(market, side, price, size, 'limit', True)


if __name__ == "__main__":

    Bot(api_key=FTX_API_KEY, api_secret=FTX_API_SECRET)

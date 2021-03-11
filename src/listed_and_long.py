import asyncio
from configparser import Error
from typing import Dict, List, Union
import time
from ftx.ftx import FTX
from line import push_message
from setting.settting import FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT, PYTHON_ENV, config
from logger import setup_logger

TRADABLE = config.getboolean('TRADABLE')
BOT_NAME = config["BOT_NAME"]
VERBOSE = config.getboolean("VERBOSE")


class Bot:
    DEFAULT_USD_SIZE = config.getfloat('DEFAULT_USD_SIZE')
    SPECIFIC_NAMES = config['SPECIFIC_NAMES']
    SPECIFIC_USD_SIZE = config.getfloat('SPECIFIC_USD_SIZE')

    def __init__(self, api_key, api_secret):
        self.ftx = FTX(
            "",
            api_key=api_key,
            api_secret=api_secret,
            subaccount=SUBACCOUNT)
        self.logger = setup_logger("log/listed_and_long.log")
        self.prev_markets: List[Dict[str, Union[str, float]]] = []
        self.positions = []
        self.HODL_TIME = config.getfloat('HODL_TIME')
        self.TARGET_PRICE_CHANGE = config.getfloat('TARGET_PRICE_CHANGE')

        self.logger.info(f"BOT:{BOT_NAME} ENV:{PYTHON_ENV} SUBACCOUNT:{SUBACCOUNT}")
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
            except KeyError as e:
                push_message("KeyError: {}".format(e))
                self.logger.error('An exception occurred', str(e))
            except Exception as e:
                push_message(str(e))
                self.logger.error('An exception occurred' + str(e))
                exit(1)

    async def main(self, interval):
        # main処理
        listed = []
        new_listed = []

        self.ftx.market()
        response = await self.ftx.send()
        # print(json.dumps(response[0]['result'], indent=2, sort_keys=False))
        # 引数に与えた条件に当てはまる上場銘柄をリストに抽出する
        listed = self.extract_markets(
            markets=response[0]['result'],
            include=["spot", "future"],
            exclude=[
                'HEDGE', 'BULL', 'BEAR', 'HALF', 'BVOL', '-0326', 'BTC-', 'ETH-', "MOVE"
            ])
        VERBOSE and self.logger.debug(listed)
        # 前回の上場銘柄リストがあるならば，現在の上場リストと比較して新規上場銘柄があるか調べる
        if len(self.prev_markets) > 0:
            # 新規上場銘柄を抽出する
            new_listed = self.extract_new_listed(self.prev_markets, listed)
            for new in new_listed:
                # SNS通知
                msg = f"New Listing: {new['name']}"
                self.logger.info(msg)
                push_message(msg)
                await asyncio.sleep(0)
                # トレードを許可しているならば，エントリー
                if TRADABLE:
                    ord_type = 'market'
                    market = new['name']
                    price = ''
                    key = 'underlying' if new['type'] == 'future' else 'baseCurrency'
                    usd = self.SPECIFIC_USD_SIZE if str(
                        new[key]).upper() in self.SPECIFIC_NAMES else self.DEFAULT_USD_SIZE
                    size = usd / (float(new['bid']) + float(new['ask'])) / 2
                    if PYTHON_ENV != 'production':
                        price = 1000
                        market = 'ETH-PERP'
                        size = 0.001
                        ord_type = 'limit'
                    responce, _ = await self.entry(market, size, ord_type, 'buy', price)
                    self.positions.append({'orderTime': time.time(),
                                           'market': market,
                                           'size': size,
                                           'side': 'buy',
                                           'price': responce[0]['result']['price']})
        # ---------共通の処理----------
        # 最新の上場のリストを更新
        self.prev_markets = listed
        listed = []
        self.logger.debug("Snapshot markets...")
        if len(self.positions) > 0:
            self.logger.info("Current positions :>>")
            self.logger.info(self.positions)
            await self.settle(market_type=["future"])
        await asyncio.sleep(interval)

    def extract_markets(
            self,
            markets,
            include=["spot", "future"],
            exclude=["HEDGE", "BULL", "BEAR", "HALF", "BVOL", "-0326"]):
        satsfied = []
        has_spot = "spot" in include
        has_future = "future" in include
        for market in markets:
            if market["enabled"]:
                if has_spot and market['type'] == "spot" and market["quoteCurrency"] == 'USD':
                    is_excluded = True
                    for keyword in exclude:
                        is_excluded = is_excluded and keyword not in market["name"]
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

    async def entry(self, market, size, ord_type, side, price="", postOnly=False, reduceOnly=False):
        try:
            self.ftx.place_order(
                type=ord_type,
                market=market,
                side=side,
                price=price,
                size=size,
                postOnly=postOnly,
                reduceOnly=reduceOnly
            )
            response = await self.ftx.send()
            if response[0]['success']:
                msg = f"BOT:{BOT_NAME}\nOrdered\n{market}\nSIZE:{size}"
                self.logger.info(msg)
                push_message(msg)
                return response, True
            else:
                raise Exception(response[0])
        except Exception as e:
            msg = f"BOT:{BOT_NAME}\nERROR: {str(e)}"
            self.logger.error(msg)
            push_message(msg)
            return {}, False

    async def settle(self, market_type=["future"]):
        has_future = "future" in market_type
        for pos in self.positions:
            if has_future and ("-PERP" in pos["market"]):
                try:
                    if time.time() - pos["orderTime"] >= self.HODL_TIME:
                        price = ""
                        ord_type = 'market'
                        _, success = await self.entry(
                            market=pos["market"],
                            size=pos["size"],
                            ord_type=ord_type,
                            price=price,
                            side='sell',
                            reduceOnly=True
                        )
                        if success:
                            self.positions.remove(pos)
                except KeyError as e:
                    self.logger.error("KeyError" + str(e))
                except Exception as e:
                    self.logger.error("Exception: " + str(e))


if __name__ == "__main__":

    Bot(api_key=FTX_API_KEY, api_secret=FTX_API_SECRET)

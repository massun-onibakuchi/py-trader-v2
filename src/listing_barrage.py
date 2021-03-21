"""How to use
    上場時間直前にスクリプトを実行して，上場即買いを行う．(IEO)
    高値を掴まないように`BUY_ORDER_PRICES`で指定した価格にpostOnly=Falseで指値をばらまく
    注文サイズは`SIZE`で一定
    # 成功した買い注文のレスポンスがあれば，売り指値を`SELL_PRICES`で指定した価格に売り指値をばらまく
    # → レスポンスがTrueが買えたことを意味していないのでダメ
"""
import asyncio
from ftx_bot_base import BotBase
from setting.settting import PYTHON_ENV, config, FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT
from pprint import pprint
import json


class Bot(BotBase):
    def __init__(self, market, market_type, api_key, api_secret, subaccount):
        super().__init__(market, market_type, api_key, api_secret, subaccount)

        self.interval = 10
        # タスクの設定およびイベントループの開始
        loop = asyncio.get_event_loop()
        tasks = [
            # self.run(10),
            self.run_strategy()
        ]
        loop.run_until_complete(asyncio.wait(tasks))

    async def run_strategy(self):
        while True:
            try:
                self.logger.debug('strategy....')
                await self.strategy(10)
                await asyncio.sleep(0)
            except Exception as e:
                self.logger.error('An exception occurred', e)
                exit(1)

    async def strategy(self, interval):
        res_result = []
        for price in BUY_ORDER_PRICES:
            _, success = await self.place_order(
                side='buy',
                ord_type='limit',
                size=SIZE,
                price=price,
                ioc=False,
                reduceOnly=False,
                postOnly=False,
                sec_to_expire=10
            )
            res_result.append(success)

        # if True in res_result:
        #     for sell_price in SELL_ORDER_PRICES:
        #         _, success = await self.place_order(
        #             side='sell',
        #             ord_type='limit',
        #             size=SIZE,
        #             price=sell_price,
        #             ioc=False,
        #             reduceOnly=True,
        #             postOnly=True,
        #             sec_to_expire=10
        #         )
        await asyncio.sleep(interval)


MARKET = config['MARKET']
BOT_NAME = config["BOT_NAME"]
TRADABLE = config.getboolean('TRADABLE')
VERBOSE = config.getboolean("VERBOSE")
MARKET_TYPE = config["MARKET_TYPE"]

SIZE = config["SIZE"]
BUY_ORDER_PRICES = json.loads(config["BUY_ORDER_PRICES"])
SELL_ORDER_PRICES = json.loads(config["SELL_ORDER_PRICES"])

bot = Bot(MARKET, MARKET_TYPE, FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT)

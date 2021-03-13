import asyncio
from typing import List
from ftx_bot_base import BotBase
from line import push_message
from setting.settting import PYTHON_ENV, FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT, config
import json

MARKET = config['MARKET']
MARKET_TYPE = config["MARKET_TYPE"]
TARGET_PRICE_CHANGES: List[float] = json.loads(config['TARGET_PRICE_CHANGES'])
USD_SIZES: List[float] = json.loads(config['USD_SIZES'])
SEC_TO_EXPIRE = config.getfloat('SEC_TO_EXPIRE')


class Bot(BotBase):
    def __init__(self, market, market_type, api_key, api_secret, subaccount):
        super().__init__(market, market_type, api_key, api_secret, subaccount)

        self.interval = 10
        # タスクの設定およびイベントループの開始
        loop = asyncio.get_event_loop()
        tasks = [self.run(10), self.run_strategy()]
        # tasks = [self.run_strategy()]
        loop.run_until_complete(asyncio.wait(tasks))

    async def run_strategy(self):
        while True:
            try:
                await self.strategy(10)
                await asyncio.sleep(0)
            except Exception as e:
                self.logger.error(f'An exception occurred {str(e)}')
                push_message(f'Unhandled Error :strategy  {str(e)}')
                exit(1)

    async def strategy_demo(self, interval):
        self.logger.debug('strategy....')
        if self.interval == 10:
            _, success = await self.place_order(
                side='buy', ord_type='limit', size=0.01, price=1000, reduceOnly=False, postOnly=True, sec_to_expire=60)
            if success:
                self.logger.debug('new order')
            self.interval = 11

    async def strategy(self, interval):
        self.logger.debug('strategy....')
        market, success = await self.get_single_market()
        if success and len(self.open_orders) == 0:
            price = float(market['ask'])
            if len(USD_SIZES) != len(TARGET_PRICE_CHANGES):
                raise Exception('USD_SIZES TARGET_PRICE_CHANGES の長さが違います')

            for i in range(len(USD_SIZES)):
                target_price = price * (1.0 - TARGET_PRICE_CHANGES[i])
                size = USD_SIZES[i] / price
                await self.place_order(
                    side='buy',
                    ord_type='limit',
                    size=size,
                    price=target_price,
                    sec_to_expire=SEC_TO_EXPIRE)
        await asyncio.sleep(interval)


bot = Bot(MARKET, MARKET_TYPE, FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT)

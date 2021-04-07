import asyncio
from typing import List
from ftx_bot_base import BotBase
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
        self.validate()
        # タスクの設定およびイベントループの開始
        loop = asyncio.get_event_loop()
        # tasks = [self.run_strategy()]
        tasks = [self.run(10), self.run_strategy()]
        loop.run_until_complete(asyncio.wait(tasks))

    async def run_strategy(self):
        while True:
            try:
                await self.strategy(10)
                await asyncio.sleep(10)
            except Exception as e:
                self.logger.error(f'Unhandled Error :strategy {str(e)}')
                self.push_message(f'Unhandled Error :strategy {str(e)}')

    async def strategy_demo(self, interval):
        self.logger.debug('strategy....')
        if self.interval == 10:
            _, success = await self.place_order(
                side='buy', ord_type='limit', size=0.01, price=1000, reduceOnly=False, postOnly=True, sec_to_expire=60)
            if success:
                self.logger.debug('new order')
            self.interval = 11

    def validate(self):
        if len(USD_SIZES) != len(TARGET_PRICE_CHANGES):
            raise Exception('USD_SIZES TARGET_PRICE_CHANGES の長さが違います')

    async def strategy(self, interval):
        self.logger.debug('strategy....')
        # ---現在価格を取得---
        market, success = await self.get_single_market()
        if not success:
            return await asyncio.sleep(interval)
        price = float(market['ask'])

        # ---- 方法2：quantZoneで決済する----
        # 閾値でsizeを変更する
        if self.has_position():
            size = self.position['size'] if self.position['size'] * \
                price < 3 * USD_SIZES[0] else self.position['openSize'] * 0.3
            # ---positionを持っていて，まだsettleを出してないとき，positonを決済する---
            if self.isvalid_reduce_only(size):
                # 通知
                self.push_message(self.position)
                # ---settle---
                await self.place_order(
                    side='sell',
                    ord_type='limit',
                    size=size,
                    price=price * 1.04,
                    reduceOnly=True,
                    postOnly=True,
                    sec_to_expire=SEC_TO_EXPIRE
                )

        # ---- 方法2：quantZoneで決済する----

        # ---オープンオーダーがない時---
        if len(self.open_orders) == 0:
            # ---place---
            # 与えれた変化率に従って指値をばら撒く
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

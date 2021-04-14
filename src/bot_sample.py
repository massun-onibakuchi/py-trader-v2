import asyncio
from ftx_bot_base import BotBase
from setting.settting import PYTHON_ENV, config, FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT
from pprint import pprint


class Bot(BotBase):
    def __init__(self, market, market_type, api_key, api_secret, subaccount):
        super().__init__(market, market_type, api_key, api_secret, subaccount)

        self.flag = 1
        # タスクの設定およびイベントループの開始
        loop = asyncio.get_event_loop()
        tasks = [self.run(10), self.run_strategy()]
        # tasks = [self.run_strategy()]
        loop.run_until_complete(asyncio.wait(tasks))

    async def run_strategy(self):
        while True:
            try:
                await self.strategy(10)
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.error('An exception occurred', e)
                exit(1)

    async def strategy(self, interval):
        self.logger.debug('strategy....')
        # --position--
        # self.ftx.positions()
        # res = await self.ftx.send()
        # if res[0]['success']:
        #     data = res[0]['result']
        #     for pos in data:
        #         print(pos['future'])
        #     return
        if self.flag:
            # _, success = await self.get_single_market()
            res, success = await self.place_order(
                side='buy',
                ord_type='limit',
                size=0.01,
                price=55000,
                reduceOnly=False,
                postOnly=True,
                sec_to_expire=60)
            if success:
                pprint(res)
                # self.logger.debug('new order')
            self.flag = 0
        await asyncio.sleep(interval)


MARKET = config['MARKET']
BOT_NAME = config["BOT_NAME"]
TRADABLE = config.getboolean('TRADABLE')
VERBOSE = config.getboolean("VERBOSE")
MARKET_TYPE = config["MARKET_TYPE"]

bot = Bot(MARKET, MARKET_TYPE, FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT)

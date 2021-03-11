import asyncio
from ftx_bot_base import BotBase
from setting.settting import PYTHON_ENV, config, FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT


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
                self.logger.error('An exception occurred', e)
                exit(1)

    async def strategy(self, interval):
        self.logger.debug('strategy....')
        if self.interval == 10:
            _, success = await self.place_order('buy', 'limit', 0.001, 1000, False, True, 15)
            if success:
                self.logger.debug('new order')
            self.interval = 11
        print('hoge')
        await asyncio.sleep(interval)


MARKET = config['MARKET']
BOT_NAME = config["BOT_NAME"]
TRADABLE = config.getboolean('TRADABLE')
VERBOSE = config.getboolean("VERBOSE")
MARKET_TYPE = config["MARKET_TYPE"]

bot = Bot(MARKET, MARKET_TYPE, FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT)

import asyncio
from ftx_bot_base import BotBase
from setting.settting import PYTHON_ENV, config, FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT


class Bot(BotBase):
    def __init__(self, market, api_key, api_secret, subaccount):
        super().__init__(market, api_key, api_secret, subaccount)
        loop = asyncio.get_event_loop()
        tasks = [self.run()]
        loop.run_until_complete(asyncio.wait(tasks))

    async def run(self):
        while True:
            try:
                await self.strategy(10)
                await asyncio.sleep(0)
            except Exception as e:
                self.logger.error('An exception occurred', e)
                exit(1)

    async def strategy(self, interval):
        _, success = await self.place_order('buy', 'limit', 0.001, 1000, False, True, 1000)
        if success:
            self.logger.debug('new order')


MARKET = config['MARKET']
BOT_NAME = config["BOT_NAME"]
TRADABLE = config.getboolean('TRADABLE')
VERBOSE = config.getboolean("VERBOSE")

bot = Bot(MARKET, FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT)

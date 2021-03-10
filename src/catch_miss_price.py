import asyncio
from typing import Dict, List, Union
from ftx.ftx import FTX
from line import push_message
from setting.settting import FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT, PYTHON_ENV, config
from datetime import datetime as dt
from logger import setup_logger
import json

TRADABLE = config.getboolean('TRADABLE')
BOT_NAME = config["BOT_NAME"]
MARKET = config["MARKET"]
VERBOSE = config.getboolean("VERBOSE")
TARGET_PRICE_CHANGES: List[float] = json.loads(config['TARGET_PRICE_CHANGES'])
USD_SIZES: List[float] = json.loads(config['USD_SIZES'])
VALIDITY_PERIOD = config.getfloat('VALIDITY_PERIOD')


class Bot:
    DEFAULT_USD_SIZE = float(config['DEFAULT_USD_SIZE'])
    SPECIFIC_NAMES = config['SPECIFIC_NAMES']
    SPECIFIC_USD_SIZE = float(config['SPECIFIC_USD_SIZE'])

    def __init__(self, api_key, api_secret):
        self.ftx = FTX(
            market=MARKET,
            api_key=api_key,
            api_secret=api_secret,
            subaccount=SUBACCOUNT)
        self.logger = setup_logger("log/listed_and_long.log")
        self.positions = []
        self.prev_market: Dict[str, Union[str, float]] = {}
        self.open_orders = []

        self.prev_markets: List[Dict[str, Union[str, float]]] = []
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
            except Exception as e:
                self.logger.error('An exception occurred', e)
                push_message(e)
                exit(1)

    async def market(self) -> Dict[str, Union[str, float]]:
        self.ftx.market()
        try:
            res = await self.ftx.send()
            return res[0]["result"]
        except Exception as e:
            self.logger.error(e)
            return {}

    async def place_order(self, side, ord_type, size, price='', reduceOnly=False, postOnly=False, period=0):
        try:
            self.ftx.place_order(side, ord_type, size, price, reduceOnly, postOnly)
            res = await self.ftx.send()
            if res[0]["success"]:
                data = res[0]["result"]
                self.open_orders.append({
                    'orderId': data['id'],
                    'side': data['side'],
                    'type': data['type'],
                    'size': data['size'],
                    'price': data['price'],
                    'status': data['status'],
                    'orderTime': dt.now(),
                    'expireTime': dt.now() + period,
                    'cancelTime': None,
                    'excutedSize': data['filledSize'],
                })
                return data, True
            else:
                return {}, False
        except Exception as e:
            self.logger.error(e)
            return {}, False

    async def cancel_expired_orders(self):
        for order in self.open_orders:
            if order['status'] != 'closed' and order['expireTime'] > dt.now():
                try:
                    return self.cancel_order(order)
                except Exception as e:
                    self.logger.error(e)
                    return {}, False

    async def update_orders_status(self):
        for order in self.open_orders:
            if order['status'] != 'closed' and order['expireTime'] < dt.now():
                self.ftx.order_status(order['orderId'])
                res = await self.ftx.send()
                if res[0]['success']:
                    data = res[0]['result']
                    self._update_order_status(data, order)
                await asyncio.sleep(0)

    def _update_order_status(self, data, order):
        if data['id'] == 'closed':
            self.open_orders.remove(order)
        if data['id'] == 'canceled':
            self.open_orders.remove(order)
        else:
            order['status'] = data['id']
            order['excutedSize'] = data['filledSize']

    async def cancel_order(self, order):
        self.ftx.cancel_order(order["orderId"])
        res = await self.ftx.send()
        if res[0]['success']:
            data = res[0]['result']
            self._update_order_status(data, order)
            return res[0]['result'], True
        else:
            return {}, False

    async def main(self, interval):

        market = await self.market()
        if market != {}:
            if len(self.open_orders) == 0:
                price = float(market['ask'])
                for price_change, usd in TARGET_PRICE_CHANGES, USD_SIZES:
                    target_price = price * (1.0 - price_change)
                    size = usd / price
                    await self.place_order('buy', 'limit', size, target_price, period=VALIDITY_PERIOD)


if __name__ == "__main__":

    Bot(api_key=FTX_API_KEY, api_secret=FTX_API_SECRET)

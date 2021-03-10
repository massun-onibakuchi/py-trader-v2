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


class BotBase:
    def __init__(self, api_key, api_secret):
        self.ftx = FTX(
            market=MARKET,
            api_key=api_key,
            api_secret=api_secret,
            subaccount=SUBACCOUNT)
        self.logger = setup_logger("log/listed_and_long.log")
        self.position = {}
        self.open_orders = []

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

    async def cancel_expired_orders(self, interval=1):
        for order in self.open_orders:
            if order['status'] != 'closed' and order['expireTime'] > dt.now():
                try:
                    await self.cancel_order(order)
                    await asyncio.sleep(1)
                except Exception as e:
                    self.logger.error(e)

    async def update_orders_status(self, interval=1):
        for order in self.open_orders:
            if order['status'] != 'closed' and order['expireTime'] < dt.now():
                self.ftx.order_status(order['orderId'])
                res = await self.ftx.send()
                data = res[0]['result']
                if res[0]['success']:
                    self._update_order_status(data, order)
                else:
                    self.logger.error(data)
                await asyncio.sleep(interval)

    def _update_order_status(self, data, order):
        order['status'] = data['status']
        order['excutedSize'] = data['filledSize']
        if data['status'] == 'cancelled':
            order['cancelTime'] = dt.now()

    async def cancel_order(self, order):
        self.ftx.cancel_order(order["orderId"])
        res = await self.ftx.send()
        if res[0]['success']:
            data = res[0]['result']
            self._update_order_status(data, order)
            return data, True
        else:
            return {}, False

    def remove_not_open_orders(self):
        for order in self.open_orders:
            if order['status'] == 'closed':
                self.open_orders.remove(order)
            if order['status'] == 'cancelled':
                self.open_orders.remove(order)
            if order['status'] == 'open' or order['status'] == 'new':
                pass
            else:
                self.logger.warn(f"Unexpected Order status{order['status']}")

    def _update_position(self, order):
        size = order['filledSize'] if order['side'] == 'buy' else -order['filledSize']
        self.position['size'] += size
        self.position['netSize'] = abs(self.position['size'])
        self.position['side'] = 'buy' if self.position['size'] > 0 else 'sell'

    async def sync_position(self, market):
        self.ftx.positions()
        res = await self.ftx.send()
        if res[0]['success']:
            all_poss = res[0]['result']
            for pos in all_poss:
                key = 'future' if 'future' in pos else 'name'
                if market in pos[key]:
                    self.position['cost'] = pos['cost']
                    self.position['entryPrice'] = pos['entryPrice']
                    self.position['side'] = pos['side']
                    self.position['size'] = pos['size']
                    self.position['netSize'] = pos['netSize']
                    self.position['openSize'] = pos['openSize']
                    self.position['realizedPnl'] = pos['realizedPnl']
                    break
        else:
            self.logger.error('Fail get_position')

    async def main(self, interval):
        try:
            await self.update_orders_status()
            await self.cancel_expired_orders()
            self.remove_not_open_orders()
        except Exception as e:
            pass


if __name__ == "__main__":

    Bot(api_key=FTX_API_KEY, api_secret=FTX_API_SECRET)

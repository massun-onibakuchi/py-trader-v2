import asyncio
from typing import Dict, Union
from ftx.ftx import FTX
from line import push_message
from setting.settting import PYTHON_ENV, config
from datetime import datetime as dt
from logger import setup_logger

TRADABLE = config.getboolean('TRADABLE')
BOT_NAME = config["BOT_NAME"]
VERBOSE = config.getboolean("VERBOSE")


class BotBase:
    def __init__(self, _market, api_key, api_secret, subaccount):
        self.ftx = FTX(
            market=_market,
            api_key=api_key,
            api_secret=api_secret,
            subaccount=subaccount)
        self.logger = setup_logger(f"log/{BOT_NAME.lower()}.log")
        self.MARKET = _market
        self.position = {}
        self.open_orders = []

        self.logger.info(
            f"BOT:{BOT_NAME} started... ENV:{PYTHON_ENV} SUBACCOUNT:{subaccount}")
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
                await self.main(10)
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

    async def place_order(self, side, ord_type, size, price='', reduceOnly=False, postOnly=False, sec_to_expire=0):
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
                    'expireTime': dt.now() + sec_to_expire,
                    'cancelTime': None,
                    'excutedSize': data['filledSize'],
                })
                push_message(f'Bot{BOT_NAME}:ordered \nmarket:{self.MARKET}')
                return data, True
            else:
                return {}, False
        except Exception as e:
            self.logger.error(e)
            return {}, False

    async def cancel_expired_orders(self, interval=1):
        self.logger.debug('Cancel expired orders...')
        for order in self.open_orders:
            if order['status'] != 'closed' and order['expireTime'] > dt.now():
                try:
                    await self.cancel_order(order)
                    await asyncio.sleep(1)
                except Exception as e:
                    self.logger.error(e)

    async def update_orders_status(self, interval=1):
        self.logger.debug('Updating orders status...')
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
        if data['status'] == 'closed':
            self._update_position(order)

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
        self.logger.debug('Remove not open orders...')
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

    async def sync_position(self):
        self.logger.debug('Sync position...')
        self.ftx.positions()
        res = await self.ftx.send()
        if res[0]['success']:
            all_poss = res[0]['result']
            for pos in all_poss:
                key = 'future' if 'future' in pos else 'name'
                if self.MARKET in pos[key]:
                    self.position['cost'] = pos['cost']
                    self.position['entryPrice'] = pos['entryPrice']
                    self.position['side'] = pos['side']
                    self.position['size'] = pos['size']
                    self.position['netSize'] = pos['netSize']
                    self.position['openSize'] = pos['openSize']
                    self.position['realizedPnl'] = pos['realizedPnl']
                    break
        else:
            self.logger.error('Fail get_position' + res[0]['result'])

    async def main(self, interval):
        try:
            self.remove_not_open_orders()
            await self.update_orders_status()
            await self.cancel_expired_orders()
            await self.sync_position()
            await asyncio.sleep(interval)
        except Exception as e:
            pass


if __name__ == "__main__":

    BotBase('ETH-PERP', api_key='', api_secret='', subaccount='')

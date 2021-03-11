import asyncio
from typing import Dict, Union, List, Any
from ftx.ftx import FTX
from line import push_message
from setting.settting import PYTHON_ENV, config
import time
from logger import setup_logger

TRADABLE = config.getboolean('TRADABLE')
BOT_NAME = config["BOT_NAME"]
MARKET = config["MARKET"]
VERBOSE = config.getboolean("VERBOSE")


class BotBase:
    def __init__(self, _market, market_type, api_key, api_secret, subaccount):
        self.ftx = FTX(
            market=_market,
            api_key=api_key,
            api_secret=api_secret,
            subaccount=subaccount)
        self.logger = setup_logger(f"log/{BOT_NAME.lower()}.log")
        self.MARKET: str = _market
        self.MARKET_TYPE: str = market_type
        self.position: Dict[str, Any] = {}
        self.open_orders: List[Dict[str, Union[str, float]]] = []

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
                self.logger.error(f'An exception occurred: {str(e)}')
                push_message(str(e))
                exit(1)

    async def market(self):
        try:
            self.ftx.market()
            res = await self.ftx.send()
            if res[0]['success']:
                return res[0]["result"]
            else:
                raise Exception('API_REQUEST_FAILED', res[0])
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
                    'orderTime': time.time(),
                    'expireTime': time.time() + sec_to_expire,
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

    async def cancel_expired_orders(self, delay=1):
        self.logger.debug('Cancel expired orders...')
        for order in self.open_orders:
            if order['status'] != 'closed' and float(order['expireTime']) > time.time():
                _ = await self.cancel_order(order)
                await asyncio.sleep(delay)

    async def update_orders_status(self, delay=1):
        self.logger.debug('Updating orders status...')
        for order in self.open_orders:
            if order['status'] != 'closed' and float(order['expireTime']) < time.time():
                self.ftx.order_status(order['orderId'])
                res = await self.ftx.send()
                if res[0]['success']:
                    data = res[0]['result']
                    self._update_order_status(data, order)
                else:
                    self.logger.error(res[0])
                await asyncio.sleep(delay)

    def _update_order_status(self, data, order):
        order['status'] = data['status']
        order['excutedSize'] = data['filledSize']
        if data['status'] == 'cancelled':
            order['cancelTime'] = time.time()
        if data['status'] == 'closed':
            self._update_position_by(order)

    async def cancel_order(self, order):
        try:
            self.ftx.cancel_order(order["orderId"])
            res = await self.ftx.send()
            if res[0]['success']:
                data = res[0]['result']
                self._update_order_status(data, order)
                return data, True
            else:
                raise Exception('API_REQUEST_FAILED', res[0])
        except Exception as e:
            self.logger.error(str(e))
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

    def _update_position_by(self, order):
        size = order['filledSize'] if order['side'] == 'buy' else -order['filledSize']
        self.position['size'] += size
        self.position['netSize'] = abs(float(self.position['size']))
        self.position['side'] = 'buy' if float(self.position['size']) > 0 else 'sell'

    def _update_position(self, pos):
        try:
            self.position['cost'] = pos['cost']
            self.position['entryPrice'] = pos['entryPrice']
            self.position['side'] = pos['side']
            self.position['size'] = pos['size']
            self.position['netSize'] = pos['netSize']
            self.position['openSize'] = pos['openSize']
            self.position['realizedPnl'] = pos['realizedPnl']
        except Exception as e:
            self.logger.error(str(e))
            self.position = pos

    async def sync_position(self, delay=0):
        self.logger.debug('Sync position...')
        self.ftx.positions()
        res = await self.ftx.send()
        await asyncio.sleep(delay)
        if res[0]['success']:
            correct_pos = {}
            for pos in res[0]['result']:
                key = 'future' if 'future' in pos else 'name'
                if self.MARKET in pos[key]:
                    correct_pos = pos
                    break
            if self.position == {}:
                self.position = correct_pos
            else:
                self._update_position(correct_pos)
            VERBOSE and self.logger.info(f'self.position :>> {self.position}')
        else:
            self.logger.error('Fail get_position' + res[0]['error'])

    async def main(self, interval):
        try:
            await self.update_orders_status(delay=5)
            await self.cancel_expired_orders(delay=5)
            self.remove_not_open_orders()
            if self.MARKET_TYPE.lower() == 'future':
                await self.sync_position()
            await asyncio.sleep(interval)
        except Exception as e:
            self.logger.error(f'ERROR: {str(e)}')

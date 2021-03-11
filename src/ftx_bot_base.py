import asyncio
from typing import Dict, Union, List, Any
from ftx.ftx import FTX
from line import push_message
from setting.settting import PYTHON_ENV, config
import time
from logger import setup_logger

TRADABLE = config.getboolean('TRADABLE')
BOT_NAME = config['BOT_NAME']
MARKET = config['MARKET']
VERBOSE = config.getboolean('VERBOSE')
PUSH_NOTIF = config.getboolean('PUSH_NOTIF')


class BotBase:
    def __init__(self, _market, market_type, api_key, api_secret, subaccount):
        self.ftx = FTX(
            market=_market,
            api_key=api_key,
            api_secret=api_secret,
            subaccount=subaccount)
        self.logger = setup_logger(f'log/{BOT_NAME.lower()}.log')
        self.MARKET: str = _market
        self.MARKET_TYPE: str = market_type
        self.position: Dict[str, Any] = {}
        self.open_orders: List[Dict[str, Union[str, float]]] = []

        self.logger.info(
            f'BOT:{BOT_NAME} started... ENV:{PYTHON_ENV} SUBACCOUNT:{subaccount}')
        # タスクの設定およびイベントループの開始
        # loop = asyncio.get_event_loop()
        # tasks = [self.run()]
        # loop.run_until_complete(asyncio.wait(tasks))

    # ---------------------------------------- #
    # bot main
    # ---------------------------------------- #
    async def run(self, interval):
        while True:
            try:
                await self.main(interval)
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
                return res[0]['result']
            else:
                raise Exception('API_REQUEST_FAILED', res[0])
        except Exception as e:
            self.logger.error(e)
            return {}

    async def place_order(self, side, ord_type, size, price='', reduceOnly=False, postOnly=False, sec_to_expire=0):
        try:
            self.ftx.place_order(
                self.MARKET,
                side,
                ord_type,
                size,
                price,
                reduceOnly,
                postOnly)
            res = await self.ftx.send()
            if res[0]['success']:
                data = res[0]['result']
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
                self.logger.info(
                    f'Place_order :>> orderId:{data["id"]},market:{self.MARKET},side:{data["side"]},price:{data["price"]}')
                push_message(
                    f'{BOT_NAME}:place_order\nmarket:{self.MARKET}\nside:{data["side"]}\nprice:{data["price"]}')
                return data, True
            else:
                raise Exception(f'PLACE_ORDER_FAILED:{res[0]["error"]}')
        except Exception as e:
            self.logger.error(str(e))
            return {}, False

    async def cancel_expired_orders(self, delay=1):
        # self.logger.debug('Cancel expired orders...')
        for order in self.open_orders:
            if order['status'] in ['new', 'open'] and float(order['expireTime']) > time.time():
                _, success = await self.cancel_order(order)
                if not success:
                    self.logger.error('CANCEL_EXPIRED_ORDERS: cancel_order failed')
                await asyncio.sleep(delay)

    async def update_orders_status(self, delay=1):
        self.logger.debug('Updating orders status...')
        for order in self.open_orders:
            try:
                if order['status'] == 'open' and float(order['expireTime']) < time.time():
                    self.ftx.order_status(order['orderId'])
                    res = await self.ftx.send()
                    if res[0]['success']:
                        data = res[0]['result']
                        self._update_order_status(data, order)
                    else:
                        raise Exception('UPDATE_ORDERS_STATUS_FAILED', res[0])
                    await asyncio.sleep(delay)
            except Exception as e:
                self.logger.error(f'UPDATE_ORDERS_STATUS_FAILED {str(e)}')

    def _update_order_status(self, data, order):
        order['status'] = data['status']
        order['excutedSize'] = data['filledSize']
        if data['status'] == 'cancelled':
            order['cancelTime'] = time.time()
        elif data['status'] == 'closed':
            self._update_position_by(order)
        return self.remove_not_open_orders()

    async def cancel_order(self, order):
        try:
            self.ftx.cancel_order(order['orderId'])
            res = await self.ftx.send()
            if res[0]['success']:
                data = res[0]['result']
                self._update_order_status(data, order)
                self.logger.debug(f'Order cancelled :>> orderId:{order["orderId"]}')
                return data, True
            else:
                raise Exception(f'API_REQUEST_FAILED orderId:{order["orderId"]}', res[0])
        except Exception as e:
            self.logger.error(str(e))
            push_message(str(e))
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
                self.logger.warn(f'Unexpected Order status{order["status"]}')

    def _update_position_by(self, order):
        try:
            size = order['filledSize'] if order['side'] == 'buy' else -order['filledSize']
            self.position['size'] += size
            self.position['netSize'] = abs(float(self.position['size']))
            self.position['side'] = 'buy' if float(self.position['size']) > 0 else 'sell'
        except KeyError as e:
            raise KeyError('KeyError', order)
        except Exception as e:
            self.logger.error(str(e))
            # def _update_position(self, pos):
            #     try:
            #         self.position['cost'] = pos['cost']
            #         self.position['entryPrice'] = pos['entryPrice']
            #         self.position['side'] = pos['side']
            #         self.position['size'] = pos['size']
            #         self.position['netSize'] = pos['netSize']
            #         self.position['openSize'] = pos['openSize']
            #         self.position['realizedPnl'] = pos['realizedPnl']
            #     except KeyError as e:
            #         self.logger.error('KeyError _update_position', str(e))
            #         self.position = pos
            #     except Exception as e:
            #         self.logger.error(str(e))
            #         self.position = pos

    async def get_position(self):
        self.ftx.positions()
        res = await self.ftx.send()
        if res[0]['success']:
            for pos in res[0]['result']:
                key = 'future' if 'future' in pos else 'name'
                if self.MARKET in pos[key]:
                    return pos, True
            else:
                raise Exception('Response result is iterable', res[0])
        else:
            self.logger.error(f'Failed to get position {res[0]}')
            return {}, False

    async def sync_position(self, delay=0):
        self.logger.debug('Sync position...')
        pos, success = await self.get_position()
        if success:
            self.position = pos
            # if self.position == {}:
            # self.position = pos
            # else:
            #     self._update_position(pos)
        else:
            self.logger.error('Fail SyncPosition...')
        await asyncio.sleep(delay)

    def log_status(self):
        if VERBOSE:
            # self.logger.debug(f'self.position :>> {self.position}')
            self.logger.info(f'self.open_orders :>> {self.open_orders}')

    async def main(self, interval):
        try:
            await self.cancel_expired_orders(delay=1)
            # await self.update_orders_status(delay=1)
            # self.remove_not_open_orders()
            # if self.MARKET_TYPE.lower() == 'future':
            #     await self.sync_position()
            # elif self.MARKET_TYPE.lower() == 'spot':
            #     pass
            self.log_status()
            await asyncio.sleep(interval)
        except Exception as e:
            self.logger.error(f'ERROR: {str(e)}')

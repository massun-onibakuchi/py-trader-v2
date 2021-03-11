import asyncio
from typing import Dict, Union, List, Any
from ftx.ftx import FTX
from setting.settting import PYTHON_ENV, FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT
import time

VERBOSE = True
market = 'CBSE'


class BotBase:
    def __init__(self, _market, market_type, api_key, api_secret, subaccount):
        self.ftx = FTX(
            market=_market,
            api_key=api_key,
            api_secret=api_secret,
            subaccount=subaccount)
        self.MARKET: str = _market
        self.MARKET_TYPE: str = market_type
        self.position: Dict[str, Any] = {}
        self.open_orders: List[Dict[str, Union[str, float]]] = []

        # タスクの設定およびイベントループの開始
        loop = asyncio.get_event_loop()
        tasks = [self.run()]
        loop.run_until_complete(asyncio.wait(tasks))

    # ---------------------------------------- #
    # bot main
    # ---------------------------------------- #
    async def run(self):
        try:
            res, success = await self.get_markets()
            if success:
                print(res)
                for market in res:
                    if 'CBSE' in market['name']:
                        print(market)
            else:
                print('fail')
            await asyncio.sleep(0)
        except Exception as e:
            print(e)
            exit(1)

    async def place_order(self,
                          side,
                          ord_type,
                          size,
                          price='',
                          ioc=False, reduceOnly=False, postOnly=False, sec_to_expire=0):
        try:
            self.ftx.place_order(
                self.MARKET,
                side,
                ord_type,
                size,
                price,
                ioc,
                reduceOnly,
                postOnly)
            res = await self.ftx.send()
            if res[0]['success']:
                data = res[0]['result']
                if data['status'] != 'cancelled':
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
                return data, True
            else:
                raise Exception(f'PLACE_ORDER_FAILED:{res[0]["error"]}')
        except Exception as e:
            print(e)
            return {}, False

    async def cancel_expired_orders(self, delay=1):
        for order in self.open_orders:
            if (order['status'] in ['new', 'open']) and float(
                    order['expireTime']) > time.time() and order['cancelTime'] is None:
                _, success = await self.cancel_order(order)
                if not success:
                    print('CANCEL_EXPIRED_ORDERS')
                await asyncio.sleep(delay)

    async def update_orders_status(self, delay=1):
        for order in self.open_orders:
            try:
                if order['status'] in ['open', 'new'] and float(
                        order['expireTime']) < time.time():
                    self.ftx.order_status(order['orderId'])
                    res = await self.ftx.send()
                    if res[0]['success']:
                        data = res[0]['result']
                        self._update_order_status(data, order)
                    else:
                        raise Exception('API_REQUEST_FAILED UPDATE_ORDERS_STATUS', res[0])
                    await asyncio.sleep(delay)
            except Exception as e:
                print(e)

    def _update_order_status(self, data, order):
        try:
            if isinstance(data, Dict):
                order['status'] = data['status']
                order['excutedSize'] = data['filledSize']
            # new
            if order['status'] == 'new':  # FTXではcancelledかfilledはclosedとして表わされる.
                pass
            # open
            if order['status'] == 'open':
                pass
            # cancelled
            if order['cancelTime'] is not None:  # orderがキューに入ってstatusが更新されていないとき
                order['status'] = 'cancelled'
            if order['status'] == 'cancelled':
                pass
            # filled or cancelled
            if order['status'] == 'closed' and order['cancelTime'] is not None:  # cancelされた注文はcancelTimeが数値になる
                pass
            if order['status'] == 'closed' and order['cancelTime'] is None:
                self._update_position_by(order)
            if order['status'] == 'filled' and order['cancelTime'] is None:
                self._update_position_by(order)
            return self._update_open_order_by(order)
        except Exception as e:
            print(e)

    async def cancel_order(self, order):
        try:
            self.ftx.cancel_order(order['orderId'])
            res = await self.ftx.send()
            if res[0]['success']:
                data = res[0]['result']
                order['cancelTime'] = time.time()
                if not isinstance(data, Dict):
                    data = None
                self._update_order_status(data, order)
                return data, True
            else:
                raise Exception(f'API_REQUEST_FAILED orderId:{order["orderId"]}', res[0])
        except Exception as e:
            return {}, False

    def _update_open_order_by(self, order):
        try:
            # cancelled
            if order['status'] == 'cancelled':
                self.open_orders.remove(order)
            # cancelled
            elif order['status'] == 'closed' and order['cancelTime'] is not None:
                self.open_orders.remove(order)
            # filled
            elif order['status'] == 'closed' and order['cancelTime'] is None:
                self.open_orders.remove(order)
            elif order['status'] == 'filled' and order['cancelTime'] is None:
                self.open_orders.remove(order)
            elif order['status'] == 'open' or order['status'] == 'new':
                pass
            else:
                print(f'Unexpected Order status{order["status"]}')
        except Exception as e:
            print(e)
            raise Exception(f'UPDATE_OPEN_ORDER_BY_STATUS {str(e)}')

    def remove_not_open_orders(self):
        print('Remove not open orders...')
        for order in self.open_orders:
            self._update_open_order_by(order)

    def _update_position_by(self, order):
        try:
            size = order['excutedSize'] if order['side'] == 'buy' else - \
                order['excutedSize']
            self.position['size'] += size
            self.position['netSize'] = abs(float(self.position['size']))
            self.position['side'] = 'buy' if float(self.position['size']) > 0 else 'sell'
        except KeyError as e:
            raise KeyError('KeyError', order)
        except Exception as e:
            print(e)

    async def get_position(self):
        self.ftx.positions()
        res = await self.ftx.send()
        try:
            if res[0]['success']:
                for pos in res[0]['result']:
                    key = 'future' if 'future' in pos else 'name'
                    if self.MARKET in pos[key]:
                        return pos, True
                else:
                    raise Exception('ERROR res[0] :>> ', res[0]['result'])
            else:
                raise Exception('API_REQUEST_FAILED get_position', res[0])
        except Exception as e:
            print(e)
            return {}, False

    async def get_single_market(self):
        try:
            self.ftx.single_market()
            res = await self.ftx.send()
            if res[0]['success']:
                return res[0]['result'], True
            else:
                raise Exception('API_REQUEST_FAILED get_single_market', res[0])
        except Exception as e:
            print(e)
            return {}, False

    async def get_markets(self):
        try:
            self.ftx.market()
            res = await self.ftx.send()
            if res[0]['success']:
                return res[0]['result'], True
            else:
                raise Exception('API_REQUEST_FAILED', res[0])
        except Exception as e:
            print(e)
            return {}, False

    async def sync_position(self, delay=0):
        print('Sync position...')
        pos, success = await self.get_position()
        if success:
            self.position = pos
        else:
            print('Fail SyncPosition...')
        await asyncio.sleep(delay)

    def log_status(self):
        if VERBOSE:
            # print(f'self.position :>> {self.position}')
            print(f'self.open_orders :>> {self.open_orders}')


if __name__ == "__main__":
    BotBase(market, 'future', FTX_API_KEY, FTX_API_SECRET, SUBACCOUNT)

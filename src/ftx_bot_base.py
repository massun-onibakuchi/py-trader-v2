from typing import Dict, Union, List, Any
import asyncio
import inspect
import time
from ftx.ftx import FTX
from line import push_message
from setting.settting import PYTHON_ENV, config
from logger import setup_logger

BOT_NAME = config['BOT_NAME']
MARKET = config['MARKET']
TRADABLE = config.getboolean('TRADABLE')
VERBOSE = config.getboolean('VERBOSE')
PUSH_NOTIF = config.getboolean('PUSH_NOTIF')


def _message(data='', msg_type=''):
    text = ''
    if isinstance(data, str):
        text = data
    elif isinstance(data, Dict):
        # dataがpositionデータの時
        if 'netSize' in data and 'side' in data:
            base = f'Position netSize:{data["netSize"]} side:{data["side"]} '
            if msg_type.lower() == 'update':
                text = 'Update' + base
            elif msg_type.lower() == 'sync':
                text = 'Sync' + base
        # dataがオーダーデータの時
        if 'orderId' in data and 'status' in data:
            base = f'order:{data["orderId"]} status:{data["status"]} '
            if msg_type.lower() == 'new':
                text = 'New' + base
            elif msg_type.lower() == 'update':
                text = 'Update' + base
            elif msg_type.lower() == 'cancel':
                text = 'Cancel' + base
            elif 'side' in data and 'price' in data and 'type' in data:
                text = base + f'price:{data["price"]} type:{data["type"]} side:{data["side"]}'
            else:
                text = base
    if text == '':
        text = '_unexpexted_data_type_'
    return text


class CycleError(Exception):
    def __init__(self, expression, msg_type=''):
        self.expression = expression
        self.msg_type = msg_type

    def __str__(self):
        if self.error_name == '':
            self.error_name = 'CycleError'
        return self._error_message()

    def _error_message(self):
        return f'{self.error_name}:{inspect.stack()[1].function} {_message(self.expression,self.msg_type)}'


class OrderCycleError(CycleError):
    def __init__(self, order, msg_type):
        super().__init__(order, msg_type)
        self.error_name = 'OrderCycleError'


class PositionCycleError(CycleError):
    def __init__(self, data, msg_type):
        super().__init__(data, msg_type)
        self.error_name = 'PositionCycleError'


class APIRequestError(Exception):
    def __init__(self, expression, msg=""):
        self.expression = expression
        self.msg = msg

    def __str__(self):
        return f'APIRequestError:{inspect.stack()[1].function} {self.expression}:{self.msg}'


class BotBase:
    def __init__(self, _market, market_type, api_key, api_secret, subaccount):
        self.ftx = FTX(
            market=_market,
            api_key=api_key,
            api_secret=api_secret,
            subaccount=subaccount)
        self.logger = setup_logger(f'log/{BOT_NAME.lower()}.log')
        self.BOT_NAME: str = BOT_NAME
        self.SUBACCOUNT = subaccount
        self.MARKET: str = _market
        self.MARKET_TYPE: str = market_type
        self.position: Dict[str, Any] = {}
        self.open_orders: List[Dict[str, Any]] = []

        self.logger.info(f'ENV:{PYTHON_ENV} {self.SUBACCOUNT} {self.BOT_NAME} {self.MARKET}')
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
                self.push_message(str(e))

    async def get_single_market(self):
        try:
            self.ftx.single_market()
            res = await self.ftx.send()
            if res[0]['success']:
                return res[0]['result'], True
            else:
                raise APIRequestError(res[0]['error'])
        except Exception as e:
            self.logger.error(str(e))
            return {}, False

    async def get_markets(self):
        try:
            self.ftx.market()
            res = await self.ftx.send()
            if res[0]['success']:
                return res[0]['result'], True
            else:
                raise APIRequestError(res[0]['error'])
        except Exception as e:
            self.logger.error(str(e))
            return {}, False

    async def place_order(self,
                          side,
                          ord_type,
                          size,
                          price='',
                          ioc=False,
                          reduceOnly=False,
                          postOnly=False,
                          sec_to_expire=0,
                          delay=5):
        """ place_order
        新規オーダーを置く.オーダーの成功・失敗を通知する
        レスポンスのオーダー情報とリクエストの可否のタプルを返す．
        """
        try:
            self.ftx.place_order(
                market=self.MARKET,
                side=side,
                ord_type=ord_type,
                size=size,
                price=price,
                ioc=ioc,
                reduceOnly=reduceOnly,
                postOnly=postOnly)
            res = await self.ftx.send()
            if res[0]['success']:
                data = res[0]['result']
                new_order = {}
                if data['status'] != 'cancelled':
                    new_order = {
                        'orderId': data['id'],
                        'side': data['side'],
                        'type': data['type'],
                        'size': data['size'],
                        'price': data['price'],
                        'status': data['status'],
                        'orderTime': time.time(),
                        'expireTime': time.time() + float(sec_to_expire),
                        'cancelTime': None,
                        'excutedSize': data['filledSize'],
                    }
                    self.open_orders.append(new_order)
                self.logger.info(self._message(new_order))
                if PUSH_NOTIF:
                    self.push_message(data)
                await asyncio.sleep(delay)
                return data, True
            else:
                raise APIRequestError(res[0]['error'])
        except Exception as e:
            self.logger.error(str(e))
            self.push_message(str(e))
            return {}, False

    async def cancel_expired_orders(self, delay=1):
        self.logger.debug('Cancel expired orders...')
        for order in self.open_orders:
            if (order['status'] in ['new', 'open']) and float(
                    order['expireTime']) < time.time() and order['cancelTime'] is None:
                _, success = await self.cancel_order(order)
                try:
                    if not success:
                        raise OrderCycleError(order, 'cancel')
                        # self.logger.error('CANCEL_EXPIRED_ORDERS: cancel_order failed')
                except Exception as e:
                    self.logger.error(str(e))
                await asyncio.sleep(delay)

    async def update_orders_status(self, delay=1):
        """
            オープンオーダーリストの`status`がopenまたはnewのオーダーのステータスをリクエストして更新する．
            約定済み，キャンセルになったオーダーはリストから削除し，ポジションを自炊更新する．
        """
        self.logger.debug('[Cycle] Updating orders status...')
        for order in self.open_orders:
            try:
                if order['status'] in ['open', 'new']:
                    self.ftx.order_status(order['orderId'])
                    res = await self.ftx.send()
                    if res[0]['success']:
                        if 'result' in res[0]:
                            data = res[0]['result']
                            self._update_per_order(data, order)
                        else:
                            self.logger.warn(f'key `result` not in {res[0]}')
                    else:
                        self.logger.error(res[0])
                        raise APIRequestError(res[0]['error'])
                    await asyncio.sleep(delay)
            except Exception as e:
                self.logger.error(f'[Cycle] UPDATE_ORDERS_STATUS_ERROR {str(e)}')

    def _update_per_order(self, data, order):
        """
            `data`で`order`の情報を更新する，および
            `order`の情報で現在ポジションとオープンオーダーのリストを更新する．
        """
        try:
            if isinstance(data, Dict):
                if 'status' in data and 'filledSize' in data:
                    order['status'] = data['status']
                    order['excutedSize'] = data['filledSize']
                    if order['status'] == 'closed':
                        self.logger.debug(self._message(order, 'update'))
                else:
                    self.logger.warn(f'`No valid key in data`:{data}')
            else:
                self.logger.warn(f'Expected type [Dict] `data`:{data}')
            # new
            if order['status'] == 'new':  # FTXではcancelledかfilledはclosedとして表わされる.
                pass
            # open
            if order['status'] == 'open':
                pass
            # cancelled
            if order['cancelTime'] is not None:  # orderがキューに入ってstatusが更新されていないときcancelledとみなす
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
            self.logger.error(f'_update_open_order_status {str(e)}')
            raise

    async def cancel_order(self, order):
        """ オーダーをキャンセルをリクエストする
            キャンセルリクエストのタイムスタンプをオーダーに追加する.および，オープンオーダーのリストから削除する．
            リクエストが失敗した時のみ，通知する
        """
        try:
            self.ftx.cancel_order(order['orderId'])
            res = await self.ftx.send()
            if res[0]['success']:
                data = res[0]['result']
                self.logger.info(self._message(data, 'cancel'))
                order['cancelTime'] = time.time()
                self._update_per_order(data, order)
                return data, True
            else:
                raise APIRequestError(res[0]['error'], f'orderId {order["orderId"]}')
        except Exception as e:
            self.logger.error(str(e))
            self.push_message(str(e))
            return {}, False

    def _update_open_order_by(self, order):
        """ `order`でオープンオーダーリストを更新する
            ステータスがキャンセルまたは，約定済みならばリストから削除する
        """
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
                self.logger.warn(f'Unexpected Order status{order["status"]}')
        except Exception as e:
            self.logger.error(str(e))
            raise OrderCycleError(order, 'update')
            # raise Exception(f'UPDATE_OPEN_ORDER_BY_STATUS {str(e)}')

    def remove_not_open_orders(self):
        """ オープンオーダーリストのオーダーでステータスがキャンセルのものを全て削除する
        """
        self.logger.debug('[Cycle] Removec canceled orders...')
        for order in self.open_orders:
            self._update_open_order_by(order)

    def _update_position_by(self, order):
        """ `order`でポジションを自炊更新する
        """
        try:
            size = order['excutedSize'] if order['side'] == 'buy' else - \
                order['excutedSize']
            self.position['size'] += size
            self.position['netSize'] = abs(float(self.position['size']))
            self.position['side'] = 'buy' if float(self.position['size']) > 0 else 'sell'
        except KeyError as e:
            raise KeyError('KeyError', order)
        except Exception as e:
            self.logger.error(str(e))
            raise PositionCycleError(order, 'update')

    async def get_position(self):
        self.ftx.positions()
        res = await self.ftx.send()
        try:
            if res[0]['success']:
                data = res[0]['result']
                for pos in data:
                    key = 'future' if 'future' in pos else 'name'
                    if self.MARKET in pos[key]:
                        return pos, True
                else:
                    raise Exception('ERROR res[0] :>> ', res[0]['result'])
            else:
                raise APIRequestError(res[0]['error'])
        except Exception as e:
            self.logger.error(str(e))
            return {}, False

    async def sync_position(self, delay=0):
        """ ポジションをリクエストして最新の状態に同期させる．
        """
        self.logger.debug('Sync position...')
        pos, success = await self.get_position()
        if success:
            self.position = pos
        else:
            self.logger.error('[Cycle] SYNC_POSITION_ERROR')
        await asyncio.sleep(delay)

    def log_status(self):
        if VERBOSE:
            # self.logger.debug(f'self.position :>> {self.position}')
            self.logger.debug(f'self.open_orders :>> {self.open_orders}')

    def has_position(self):
        return self.position != {} and self.position['netSize'] > 0

    def _message(self, data='', msg_type=''):
        return _message(data, msg_type)

    def push_message(self, data):
        """ ボットの基本情報＋引数のデータ型に応じたテキストを追加して送信する．
             - `data`がstrなら，そのまま送信
             - `position`なら，sizeとsideを送信
             - `order`ならpriceとtype,sideを送信
        """
        bot_info = f'{self.SUBACCOUNT}:{self.BOT_NAME}\n{self.MARKET}'
        text = self._message(data)
        push_message(f'{bot_info}\n{text}')

    async def main(self, interval):
        try:
            await self.update_orders_status(delay=2)
            await self.cancel_expired_orders(delay=2)
            self.remove_not_open_orders()
            if self.MARKET_TYPE.lower() == 'future':
                await self.sync_position(delay=5)
            elif self.MARKET_TYPE.lower() == 'spot':
                pass
            self.log_status()
            await asyncio.sleep(interval)
        except Exception as e:
            self.logger.error(f'ERROR: {str(e)}')

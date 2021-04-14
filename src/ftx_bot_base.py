from typing import Dict, Union, List, Any
import asyncio
import time
from ftx.ftx import FTX
from bot_base_error import APIRequestError, CycleError, PositionCycleError, OrderCycleError, _message
from line import push_message
from setting.settting import PYTHON_ENV, config
from logger import setup_logger

BOT_NAME = config['BOT_NAME']
MARKET = config['MARKET']
TRADABLE = config.getboolean('TRADABLE')
SEC_TO_EXPIRE = config.getfloat('SEC_TO_EXPIRE')
VERBOSE = config.getboolean('VERBOSE')
PUSH_NOTIF = config.getboolean('PUSH_NOTIF')
MAX_POSITION_SIZE = config.getfloat('MAX_POSITION_SIZE')
MAX_ORDER_NUMBER = config.getint('MAX_ORDER_NUMBER')


class BotBase:
    def __init__(self, _market, market_type, api_key, api_secret, subaccount):
        self.ftx = FTX(
            market=_market,
            api_key=api_key,
            api_secret=api_secret,
            subaccount=subaccount)
        self.logger = setup_logger(f'log/{BOT_NAME.lower()}.log')
        self.BOT_NAME: str = BOT_NAME
        self.MAX_ORDER_NUMBER: int = MAX_ORDER_NUMBER
        self.SUBACCOUNT = subaccount
        self.MARKET: str = _market
        self.MARKET_TYPE: str = market_type
        self.MAX_POSITION_SIZE = MAX_POSITION_SIZE
        self.position: Dict[str, Any] = {}
        self.open_orders: List[Dict[str, Any]] = []
        self.error_tracking = {'count': 0, 'error_message': '', 'timestamp': 0}
        self.next_update_time = time.time()

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
                self.logger.error(f'RUN_CYCLE_ERROR: {str(e)}')
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

    async def get_open_orders(self):
        try:
            self.ftx.open_orders()
            res = await self.ftx.send()
            if res[0]['success']:
                return res[0]['result'], True
            else:
                raise APIRequestError(res[0]['error'])
        except Exception as e:
            self.push_message(str(e))
            self.logger.error(str(e))
            return {}, False

    async def require_num_open_orders_within(self, max_order_number):
        """
            オープンオーダーが与えられたオーダー数なら，`CycleError`エラーを投げる
        """
        open_orders, success = await self.get_open_orders()
        if success:
            if len(open_orders) >= max_order_number:
                msg = f'TOO_MANY_OPEN_ORDERS: {len(open_orders)}'
                self.logger.warn(msg)
                self.push_message(msg)
                raise CycleError(msg)

    def isvalid_reduce_only(self, size):
        reduce_only_size = 0.0
        pos = self.position
        if not self.has_position():
            return False
        for op_ord in self.open_orders:
            if op_ord['reduceOnly']:
                reduce_only_size += op_ord['size']
        if reduce_only_size + size >= pos['size']:
            self.logger.warn('Invalid ResuceOnly order')
            self.push_message('Invalid ResuceOnly order')
            return False
        else:
            return True

    def isvalid_size(self, size):
        return ('size' in self.position) and (self.MAX_POSITION_SIZE >= self.position['size'])

    async def place_order(self,
                          side,
                          ord_type,
                          size,
                          price='',
                          ioc=False,
                          reduceOnly=False,
                          postOnly=False,
                          sec_to_expire=SEC_TO_EXPIRE,
                          delay=5):
        """ place_order
        新規オーダーを置く.オーダーの成功・失敗を通知する
        レスポンスのオーダー情報とリクエストの可否のタプルを返す．
        """
        try:
            # if self.isvalid_size(size):
            #     return {}, False
            if reduceOnly:
                if not self.isvalid_reduce_only(size):
                    return {}, False
            if not sec_to_expire:
                sec_to_expire = SEC_TO_EXPIRE
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
                self.logger.info(self._message(new_order, 'new'))
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
        """ 期限切れの全てのオーダーをキャンセルする．
            ステータスがopenまたはnewではない時に限る.
        """
        self.logger.debug('[Cycle] Cancel expired orders...')
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
                raise APIRequestError(f'ERROR:{res[0]["error"]}:orderId {order["orderId"]}')
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
            net_excuted = order['excutedSize'] if order['side'] == 'buy' else - order['excutedSize']
            self.position['size'] += abs(net_excuted)  # sizeは絶対値
            self.position['netSize'] += net_excuted
            self.position['side'] = 'buy' if float(self.position['size']) > 0 else 'sell'
        except KeyError as e:
            raise KeyError('KeyError', order)
        except Exception as e:
            self.logger.error(str(e))
            raise PositionCycleError(order, 'update')

    async def get_position(self, market=None):
        if market is None:
            market = self.MARKET

        self.ftx.positions()
        res = await self.ftx.send()
        try:
            if res[0]['success']:
                data = res[0]['result']
                for pos in data:
                    key = 'future' if 'future' in pos else 'name'
                    if market in pos[key]:
                        return pos, True
                else:
                    raise Exception('ERROR res[0] :>> ', res[0]['result'])
            else:
                raise APIRequestError(res[0]['error'])
        except Exception as e:
            self.logger.error(str(e))
            return {}, False

    async def sync_position(self, delay=0):
        """
            ポジションをリクエストして最新の状態に同期させる．
        """
        try:
            self.logger.debug('[Cycle] Sync position...')
            pos, success = await self.get_position()
            await asyncio.sleep(delay)
            if success:
                self.position = pos
            else:
                raise PositionCycleError('SYNC_POSITION_ERROR', '')
        except PositionCycleError as e:
            self.logger.error(str(e))

    def log_status(self):
        if VERBOSE:
            self.logger.debug(f'self.position :>> {self.position["netSize"]}')
            self.logger.debug(f'self.open_orders lenth :>> {len(self.open_orders)}')

    def has_position(self):
        return self.position != {} and self.position['size'] > 0

    def _message(self, data='', msg_type=''):
        return _message(data, msg_type)

    def push_message(self, data, msg_type=''):
        """ ボットの基本情報＋引数のデータ型に応じたテキストを追加して送信する．
             - `data`がstrなら，そのまま送信
             - `position`なら，sizeとsideを送信
             - `order`ならpriceとtype,sideを送信
        """
        bot_info = f'{self.SUBACCOUNT}:{self.BOT_NAME}\n{self.MARKET}'
        text = self._message(data, msg_type)
        push_message(f'{bot_info}\n{text}')

    def _update(self, interval):
        if time.time() > self.next_update_time:
            self.next_update_time += interval
            return True
        else:
            return False

    async def main(self, interval):
        try:
            if self._update(60):
                await self.require_num_open_orders_within(self.MAX_ORDER_NUMBER)

            await self.update_orders_status(delay=2)

            await asyncio.sleep(5)

            await self.cancel_expired_orders(delay=2)
            self.remove_not_open_orders()
            if self.MARKET_TYPE.lower() == 'future':
                await self.sync_position(delay=5)
            elif self.MARKET_TYPE.lower() == 'spot':
                pass
            self.log_status()
            await asyncio.sleep(interval)
        except CycleError as e:
            self.ftx.cancel_all_orders()
            res = await self.ftx.send()
            print("res[0] :>>", res[0])
            if res[0]['success'] and 'result' in res[0]:
                msg = '[Cycle] CANCEL_ALL_ORDERS'
                self.logger.info(msg)
                self.push_message(msg)
            else:
                raise APIRequestError(res[0]['error'])
        except Exception as e:
            self.logger.error(str(e))
            self.push_message(str(e))

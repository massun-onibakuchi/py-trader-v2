from typing import Dict
import inspect


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

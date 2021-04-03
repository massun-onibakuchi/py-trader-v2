from typing import Dict


def _message(data='', msg_type=''):
    text = ''
    if isinstance(data, str):
        text = data
    elif isinstance(data, Dict):
        if 'netSize' in data and 'side' in data:
            text = f'Position netSize:{data["netSize"]} side:{data["side"]}'
        if 'orderId' in data and 'price' in data and 'status' in data and 'side' in data:
            base = f'order:{data["orderId"]} status:{data["status"]}'
            if msg_type.lower() == 'new':
                text = 'New' + base
            elif msg_type.lower() == 'update':
                text = 'Update' + base
            elif msg_type.lower() == 'cancel':
                text = 'Cancel' + base
            else:
                text = base + f'price:{data["price"]} type:{data["type"]} side:{data["side"]}'
    if text == '':
        text = '_unexpexted_data_type_'
    return text


position = {'netSize': 12, 'side': 212}
order = {'orderId': 21}
print("_message('test') :>>", _message("test"))
print("_message(position) :>>", _message(position))
print("_message(order) :>>", _message(order))

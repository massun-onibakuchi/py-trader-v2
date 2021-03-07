import requests
from setting.settting import LINE_BEARER_TOKEN, LINE_USER_ID
import json


def create_headers(bearer_token):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(bearer_token)
    }
    return headers


def push_message(text):
    headers = create_headers(LINE_BEARER_TOKEN)
    pay_load = {
        'to': LINE_USER_ID,
        'messages': [{
            "type": "text",
            "text": text
        }]
    }
    # "https://api.line.me/v2/bot/message/push",
    response = requests.request(
        method="POST",
        url="https://api.line.me/v2/bot/message/broadcast",
        headers=headers,
        data=json.dumps(pay_load))
    print(response.status_code)
    try:
        if response.status_code != 200:
            raise Exception(response.status_code, response.text)
        else:
            return response.json()
    except Exception as e:
        print(e)
        return {}


if __name__ == "__main__":
    push_message("TEST_PUSH_MESSAGE")

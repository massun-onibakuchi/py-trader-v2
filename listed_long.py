import asyncio
from datetime import datetime, timezone
from ftx.ftx import FTX
from line import push_message
from setting.settting import FTX_API_KEY, FTX_API_SECRET, PYTHON_ENV, SUBACCOUNT, TRADABLE
import json


class Bot:
    prev_markets = []
    default_size = 100
    SPECIFIC_NAME = ["SPACEX", "STARLINK", "STAR", "STRLK"]
    SPECIFIC_SIZE = 900

    def __init__(self, api_key, api_secret):
        self.ftx = FTX(
            "",
            api_key=api_key,
            api_secret=api_secret,
            subaccount=SUBACCOUNT)

        print(
            "\nENV:%s \nSUBACCOUNT: %s"
            % (
                PYTHON_ENV,
                SUBACCOUNT
            ))
        # タスクの設定およびイベントループの開始
        loop = asyncio.get_event_loop()
        tasks = [self.run()]
        loop.run_until_complete(asyncio.wait(tasks))

    # ---------------------------------------- #
    # bot main
    # ---------------------------------------- #
    async def run(self):
        while True:
            await self.main(5)
            await asyncio.sleep(0)

    async def main(self, interval):
        # main処理
        """
        """
        listed = []
        new_listed = []

        self.ftx.market()
        response = await self.ftx.send()
        # print(json.dumps(response[0]['result'], indent=2, sort_keys=False))
        listed = self.extract_name(markets=response[0]['result'])
        print(json.dumps(listed, indent=2, sort_keys=False))

        if self.prev_markets == []:
            self.prev_markets = listed
            print("Snapshot markets...")
        else:
            # 新規上場を検知
            new_listed = self.extract_new_listed(self.prev_markets, listed)
            print(
                "New Listed...",
                json.dumps(
                    new_listed,
                    indent=2,
                    sort_keys=False))

            if TRADABLE:
                for new in new_listed:
                    size = self.default_size / new["bid"]
                    if new["baseCurrency"] in self.SPECIFIC_NAME:
                        size = self.SPECIFIC_SIZE
                    if PYTHON_ENV == 'production':
                        self.ftx.place_order(
                            type='market',
                            market=new["name"],
                            side='buy',
                            price='',
                            size=size,
                            postOnly=False)
                        response = await self.ftx.send()
                        print(response[0])
                        orderId = response[0]['result']['id']
                        push_message(f"Ordered :\norderId:{orderId}")
                    else:
                        # テスト
                        print(
                            f"DEVELOPMENT:>>\nMARKET:{new['name']}\nSIZE:{size}"
                        )

            # SNSに通知する
        for new in new_listed:
            push_message(f"NEW LISTED: {json.dumps(new)}")

        await asyncio.sleep(interval)
        # Update...
        self.prev_markets = listed
        listed = []

        await asyncio.sleep(0)

    def extract_name(
            self, markets,
            include=["spot"],
            exclude=["HEDGE", "BULL", "BEAR", "HALF", "BVOL"]):
        satsfied = []
        for market in markets:
            if not market["enabled"]:
                continue
            if "spot" in include and market['type'] == "spot" and market["quoteCurrency"] == 'USD':
                is_excluded = True
                for token in exclude:
                    is_excluded = is_excluded and not (
                        token in market["baseCurrency"])
                if is_excluded:
                    satsfied.append(market)
            if "future" in include and market["type"] == 'future':
                satsfied.append(market)
        return satsfied

    def extract_new_listed(self, prev_markets, current_markets):
        new_listed = []
        if len(current_markets) == 0:
            return new_listed
        for market in prev_markets:
            name = market["name"]
            for current_market in current_markets:
                if name == current_market["name"]:
                    break
            else:
                new_listed.append(current_market)
        return new_listed


if __name__ == "__main__":

    Bot(api_key=FTX_API_KEY, api_secret=FTX_API_SECRET)

import asyncio
from datetime import datetime, timezone, timedelta
from ftx.ftx import FTX
from twitter.recent_research import recent_research
from line import push_message
from setting.settting import FTX_API_KEY, FTX_API_SECRET, PYTHON_ENV, MARKET, SUBACCOUNT, MAX_SIZE, BOT_NAME
from pprint import pprint


class Bot:
    MAX_POSITION_SIZE: float = 0.0
    order_list = []
    # ---------------------------------------- #
    # init
    # ---------------------------------------- #

    def __init__(self, api_key, api_secret):
        if MAX_SIZE is not None:
            self.MAX_POSITION_SIZE = float(MAX_SIZE)
        else:
            raise ValueError("MAX_SIZE is neither int nor float")
        self.ftx = FTX(
            MARKET,
            api_key=api_key,
            api_secret=api_secret,
            subaccount=SUBACCOUNT)

        print(
            "BOT_NAME: %s \nENV:%s \nMARKET %s \nSUBACCOUNT: %s"
            % (BOT_NAME,
                PYTHON_ENV,
                MARKET,
                SUBACCOUNT))
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
                await self.main(5)
                await asyncio.sleep(0)
            except Exception as e:
                print('An exception occurred', e)
                push_message(e)
                exit(1)

    def create_time_fields(self, sec=10):
        since_date = ""
        td = ""
        utc_date = datetime.now(timezone.utc)
        if PYTHON_ENV != 'production':  # テストの時
            td = timedelta(days=3)
            since_date = utc_date - td
        else:  # 本番のとき 検索開始期間を10s前に設定
            td = timedelta(seconds=sec)
            since_date = utc_date - td
        start_time_fields = "start_time=" + \
            since_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        return start_time_fields

    async def main(self, interval):
        # main処理

        self.ftx.positions()
        response = await self.ftx.send()
        # print(json.dumps(response[0], indent=2, sort_keys=False))
        position = {}
        for pos in response[0]["result"]:
            if pos["future"] == MARKET:
                position = pos
        print("\nPOSITION :>>")
        pprint(position)

        await asyncio.sleep(5)

        # 現在のポジションが規定のサイズを超えていたらエントリーしない
        if position["netSize"] > float(self.MAX_POSITION_SIZE):
            print("\n[Info]: MAX_POSITION_SIZE")
        else:
            query = "query=from:elonmusk -is:retweet"
            tweet_fields = "tweet.fields=author_id"
            start_time_fields = self.create_time_fields(sec=12)
            queries = [query, tweet_fields, start_time_fields]
            keywords = ['doge', 'Doge', 'DOGE']

            result = recent_research(keywords, queries)

            if len(result) > 0:
                push_message(f"Detect events:\nkeywords:{keywords}\n{result}")
                if PYTHON_ENV == 'production':
                    self.ftx.place_order(
                        type='market',
                        market=MARKET,
                        side='buy',
                        price='',
                        size=3800,
                        postOnly=False)
                else:
                    self.ftx.place_order(
                        type='limit',
                        market=MARKET,
                        side='buy',
                        price=1111,
                        size=0.001,
                        postOnly=True)
                response = await self.ftx.send()
                pprint(response[0])
                orderId = response[0]['result']['id']
                self.order_list.append({
                    "timestamp": datetime.now(timezone.utc),
                    "orderId": orderId
                })
                push_message(
                    f"[Order]{PYTHON_ENV}\nMARKET:{MARKET}\norderId:{orderId}"
                )
        await asyncio.sleep(interval)

    async def sample(self, interval):
        self.ftx.positions()
        response = await self.ftx.send()
        position = {}
        for pos in response[0]["result"]:
            if pos["future"] == MARKET:
                position = pos
        print("POSITION :>>")
        pprint(position)

        await asyncio.sleep(5)

        if position["size"] > float(self.MAX_POSITION_SIZE):
            print("[Info]: MAX_ENTRY_SIZE")

        query = "query=from:elonmusk -is:retweet"
        tweet_fields = "tweet.fields=author_id"
        start_time_fields = self.create_time_fields(sec=10)
        queries = [query, tweet_fields, start_time_fields]
        keywords = ['doge', 'Doge', 'DOGE']

        result = recent_research(keywords, queries)

        if len(result) > 0:
            push_message(f"Detect events:\nkeywords:{keywords}\n{result}")
            self.ftx.place_order(
                type='limit',
                market=MARKET,
                side='buy',
                price=1111,
                size=0.001,
                postOnly=True)
            response = await self.ftx.send()
            pprint(response[0])
            orderId = response[0]['result']['id']
            push_message(f"Ordered :\norderId:{orderId}")

        await asyncio.sleep(interval)


if __name__ == "__main__":

    Bot(api_key=FTX_API_KEY, api_secret=FTX_API_SECRET)

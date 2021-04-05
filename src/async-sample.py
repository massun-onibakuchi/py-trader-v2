import asyncio
import time


async def g(i):
    print('print 1', i)
    await asyncio.sleep(3)
    # print('print 2', i)
    return "hello"


async def f():
    print(await g(1))
    await asyncio.sleep(3)
    print(await g(2))
    return await g(3)


async def main(interval):
    await f()
    # await asyncio.sleep(interval)


async def run():
    while True:
        try:
            print('start')
            time.sleep(10)
            await main(5)
            print('end')
            # await asyncio.sleep(0)
        except Exception as e:
            print(e)
            exit(1)


async def run2():
    while True:
        print(await g(4))
        print(await g(5))
    # task1 = asyncio.create_task(g(1))
    # task2 = asyncio.create_task(g(2))
    # return await asyncio.gather(task1, task2)
# print(asyncio.run(f()))

loop = asyncio.get_event_loop()
# tasks = [run()]
tasks = [run(), run2()]
loop.run_until_complete(asyncio.wait(tasks))

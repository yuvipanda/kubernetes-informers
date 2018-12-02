import asyncio
import pytest
from kubernetes_informers import CoalescingQueue


@pytest.mark.asyncio
async def test_simple_coalesce():
    """
    Simple, almost synchronous enqueue & dequeue
    """
    q = CoalescingQueue()
    q.put_nowait(('a', 'first-a-value'))
    q.put_nowait(('b', 'first-b-value'))
    q.put_nowait(('a', 'second-a-value'))

    assert 2 == q.qsize()

    assert 'first-b-value' == (await q.get())
    assert 'second-a-value' == (await q.get())


@pytest.mark.asyncio
async def test_async_coalesce():
    """
    Asynchronously insert large number of items into queue
    """
    q = CoalescingQueue()

    keys = ('a', 'b', 'c', 'd', 'e', 'f')
    async def add_to_q(key, value):
        await q.put((key, value))

    # The +1 shifts the queue ordering, so put for 'a' happens last
    # This makes 'b' be front of queue, rather than 'a'
    total_inserts = (len(keys) * 1000) + 1
    put_futures = []
    for i in range(total_inserts):
        key = keys[i % len(keys)]
        value = f'{key}-{i}'
        put_futures.append(asyncio.ensure_future(add_to_q(key, value)))

    await asyncio.gather(*put_futures)

    final_values = [
        'b-5995',
        'c-5996',
        'd-5997',
        'e-5998',
        'f-5999',
        'a-6000'
    ]

    for i in final_values:
        assert i == await(q.get())

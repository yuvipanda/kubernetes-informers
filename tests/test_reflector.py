from kubernetes_informers import Reflector, CoalescingQueue
from kubernetes_informers.reflector import Delta
import asyncio
import pytest
from kubernetes_asyncio import client

def make_pod(ns, name, rv):
    return client.V1Pod(
        metadata=client.V1ObjectMeta(namespace=ns, resource_version=rv, name=name),
    )

@pytest.mark.asyncio
async def test_single_changes():
    """
    Validate deltas with single object changes only
    """
    states = [
        # Initial state is empty
        [],
        # Add pod1
        [make_pod('ns', 'pod1', 1) ],
        # Add pod2
        [
            make_pod('ns', 'pod1', 1),
            make_pod('ns', 'pod2', 1)
        ],
        # Change pod1
        [
            make_pod('ns', 'pod1', 2),
            make_pod('ns', 'pod2', 1)
        ],
        # Delete pod1
        [
            make_pod('ns', 'pod2', 1)
        ],
        # Change pod2
        [
            make_pod('ns', 'pod2', 2)
        ],
        # Delete pod2
        [],
    ]

    deltas = [
        Delta(type='added', old=None, new=make_pod('ns', 'pod1', 1)),
        Delta(type='added', old=None, new=make_pod('ns', 'pod2', 1)),
        Delta(type='changed', old=make_pod('ns', 'pod1', 1), new=make_pod('ns', 'pod1', 2)),
        Delta(type='deleted', old=make_pod('ns', 'pod1', 2), new=None),
        Delta(type='changed', old=make_pod('ns', 'pod2', 1), new=make_pod('ns', 'pod2', 2)),
        Delta(type='deleted', old=make_pod('ns', 'pod2', 2), new=None),
    ]

    yield_states = iter(states)

    async def fake_list_method(namespace, *args, **kwargs):
        assert namespace == 'ns'
        state = next(yield_states)
        return client.V1PodList(items=state)

    q = CoalescingQueue()
    r = Reflector(q, fake_list_method, 'ns', resync_period=0.1)
    reflect_future = asyncio.ensure_future(r.reflect())

    for expected_delta in deltas:
        delta = await q.get()

        assert delta == expected_delta

    reflect_future.cancel()


@pytest.mark.asyncio
async def test_multiple_changes():
    """
    Validate deltas with single object changes only
    """
    states = [
        # Initial state is empty
        [],
        # Add two pods
        [
            make_pod('ns', 'pod1', 1),
            make_pod('ns', 'pod2', 1)
        ],
        # Change pod1
        [
            make_pod('ns', 'pod1', 2),
            make_pod('ns', 'pod2', 1)
        ],
        # Delete pod1
        [
            make_pod('ns', 'pod2', 1)
        ],
        # Change pod2
        [
            make_pod('ns', 'pod2', 2)
        ],
        # Add pod3 and pod4
        [
            make_pod('ns', 'pod2', 2),
            make_pod('ns', 'pod3', 1),
            make_pod('ns', 'pod4', 1),
        ],
        # Change pod3 and pod4
        [
            make_pod('ns', 'pod2', 2),
            make_pod('ns', 'pod3', 2),
            make_pod('ns', 'pod4', 2),
        ],
        # Delete all pods
        [],
    ]

    delta_batches = [
        [
            Delta(type='added', old=None, new=make_pod('ns', 'pod1', 1)),
            Delta(type='added', old=None, new=make_pod('ns', 'pod2', 1)),
        ],
        [
            Delta(type='changed', old=make_pod('ns', 'pod1', 1), new=make_pod('ns', 'pod1', 2)),
        ],
        [
            Delta(type='deleted', old=make_pod('ns', 'pod1', 2), new=None),
        ],
        [
            Delta(type='changed', old=make_pod('ns', 'pod2', 1), new=make_pod('ns', 'pod2', 2)),
        ],
        [
            Delta(type='added', old=None, new=make_pod('ns', 'pod3', 1)),
            Delta(type='added', old=None, new=make_pod('ns', 'pod4', 1)),
        ],
        [
            Delta(type='changed', old=make_pod('ns', 'pod3', 1), new=make_pod('ns', 'pod3', 2)),
            Delta(type='changed', old=make_pod('ns', 'pod4', 1), new=make_pod('ns', 'pod4', 2)),
        ],
        [
            Delta(type='deleted', old=make_pod('ns', 'pod2', 2), new=None),
            Delta(type='deleted', old=make_pod('ns', 'pod3', 2), new=None),
            Delta(type='deleted', old=make_pod('ns', 'pod4', 2), new=None),
        ]
    ]

    yield_states = iter(states)

    async def fake_list_method(namespace, *args, **kwargs):
        assert namespace == 'ns'
        state = next(yield_states)
        return client.V1PodList(items=state)

    q = CoalescingQueue()
    r = Reflector(q, fake_list_method, 'ns', resync_period=0.1)
    reflect_future = asyncio.ensure_future(r.reflect())

    for delta_batch in delta_batches:
        while len(delta_batch) != 0:
            delta = await q.get()
            assert delta in delta_batch
            delta_batch.remove(delta)

    reflect_future.cancel()



from collections import namedtuple
import asyncio
import logging

from kubernetes_asyncio import client, config, watch

from .coalesce import CoalescingQueue

Delta = namedtuple('Delta', ['type', 'old', 'new'])


class Reflector:
    """
    Reliably watch for changes to Kubernetes objects
    """
    def __init__(self, q, list_method, namespace, labels=None, fields=None, resync_period=60, request_timeout=10):
        self.q = q
        self.list_method = list_method
        self.labels = labels if labels else {}
        self.fields = fields if fields else {}
        self.namespace = namespace
        # FIXME: Jitter this time period
        self.resync_period = resync_period
        self.request_timeout = request_timeout

        self.resources = {}
        # FIXME: Make this configurable
        self.log = logging.getLogger()

        # FIXME: Protect against malicious labels?
        self.label_selector = ','.join(['{}={}'.format(k, v) for k, v in self.labels.items()])
        self.field_selector = ','.join(['{}={}'.format(k, v) for k, v in self.fields.items()])

    async def reflect(self):
        while True:
            resp = await self.list_method(
                self.namespace,
                label_selector=self.label_selector,
                field_selector=self.field_selector,
                _request_timeout=self.request_timeout,
            )

            new_resources = {
                (r.metadata.namespace, r.metadata.name): r
                for r in resp.items
            }

            for key in new_resources:
                new_resource = new_resources[key]
                if key in self.resources:
                    # Check if we have changed
                    old_resource = self.resources[key]
                    if old_resource.metadata.resource_version != new_resource.metadata.resource_version:
                        self.resources[key] = new_resource
                        self.q.put_nowait((key, Delta(
                            type='changed',
                            old=old_resource,
                            new=new_resource
                        )))
                else:
                    # Object has been added
                    self.resources[key] = new_resource
                    self.q.put_nowait((key, Delta(
                        type='added',
                        new=new_resource,
                        old=None
                    )))

            deleted_keys = set(self.resources.keys()) - set(new_resources.keys()) 
            for key in deleted_keys:
                old = self.resources[key]
                del self.resources[key]
                self.q.put_nowait((key, Delta(
                    type='deleted',
                    old=old,
                    new=None
                )))

            # FIXME: resync every resync_period, *not* resync_period after last resync
            await asyncio.sleep(self.resync_period)


async def main():
    await config.load_kube_config()
    v1api = client.CoreV1Api()
    q = CoalescingQueue()
    r = Reflector(q, v1api.list_namespaced_pod, 'binder-test', {}, {}, resync_period=1)
    asyncio.ensure_future(r.reflect())
    while True:
        delta = await q.get()
        if delta.type == 'added' or delta.type == 'changed':
            print(delta.type, delta.new.metadata.name)
        elif delta.type == 'deleted':
            print(delta.type, delta.old.metadata.name)
        await asyncio.sleep(5)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
    asyncio.get_event_loop().close()

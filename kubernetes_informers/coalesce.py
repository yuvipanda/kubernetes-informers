from asyncio.queues import Queue


class CoalescingQueue(Queue):
    """
    Coalescing wrapper around asyncio.Queue

    When putting a value into this queue, a key is also required.
    If another value with this key already exists in this queue,
    the value is overwritten with new value (while still maintaining
    its place in the queue).

    This primarily helps write code that is 'level triggered' rather
    than 'edge triggered'. When a `get` returns, it returns the value
    that contains the *last* event that has happened to this key
    since the last time it was processed. 

    Items are expected to be in the form (key, value)
    """
    # Only override functions marked as 'overridable' in the base class's source
    def _put(self, item):
        key, value = item
        try:
            # If key already exists in queue, remove it
            # This makes sure we coalesce into the *last* inserted position
            # for the key, rather than the first.
            self._queue.remove(key)
        except ValueError:
            pass
        self._store[key] = value
        self._queue.append(key)

    def _init(self, maxsize):
        super()._init(maxsize)
        self._store = {}

    def _get(self):
        # Return only the value, never the key
        return self._store[super()._get()]
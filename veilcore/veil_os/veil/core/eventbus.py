class EventBus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type, handler):
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type, payload=None):
        for handler in self._subscribers.get(event_type, []):
            handler(event_type, payload)

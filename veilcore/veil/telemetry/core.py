class TelemetryBus:
    def __init__(self):
        self.metrics = []
        self.events = []

    def record_metric(self, organ, name, value, tags=None):
        self.metrics.append({
            "organ": organ,
            "name": name,
            "value": value,
            "tags": tags or {}
        })

    def record_event(self, organ, event_type, payload=None):
        self.events.append({
            "organ": organ,
            "type": event_type,
            "payload": payload or {}
        })


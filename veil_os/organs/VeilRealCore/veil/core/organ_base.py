class BaseOrgan:
    def __init__(self, name, eventbus, telemetry, security):
        self.name = name
        self.eventbus = eventbus
        self.telemetry = telemetry
        self.security = security

    def start(self):
        """
        Start the organ. Override in subclasses.
        """
        raise NotImplementedError

    def stop(self):
        """
        Stop the organ. Override in subclasses.
        """
        raise NotImplementedError

    def emit_metric(self, metric_name, value, tags=None):
        if self.telemetry is not None:
            self.telemetry.record_metric(self.name, metric_name, value, tags or {})

    def emit_event(self, event_type, payload=None):
        if self.eventbus is not None:
            self.eventbus.publish(event_type, {"organ": self.name, "payload": payload})

    def record_security_event(self, event_type, details=None):
        if self.security is not None:
            self.security.record_event(self.name, event_type, details or {})

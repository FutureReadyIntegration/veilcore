class SecurityBus:
    def __init__(self):
        self.events = []
        self.lockdown = False

    def record_event(self, organ, event_type, details=None):
        self.events.append({
            "organ": organ,
            "type": event_type,
            "details": details or {}
        })

    def activate_lockdown(self, reason=None):
        self.lockdown = True
        self.record_event("system", "lockdown", {"reason": reason})

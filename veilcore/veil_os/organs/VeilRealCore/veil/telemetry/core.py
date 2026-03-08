class SecurityBus:
    def __init__(self):
        self._events = []
        self._lockdown_active = False

    def record_event(self, organ, event_type, details=None):
        entry = {
            "organ": organ,
            "type": event_type,
            "details": details or {},
        }
        self._events.append(entry)
        return entry

    def activate_lockdown(self, reason=None):
        self._lockdown_active = True
        self.record_event("system", "lockdown_activated", {"reason": reason})

    def deactivate_lockdown(self, reason=None):
        self._lockdown_active = False
        self.record_event("system", "lockdown_deactivated", {"reason": reason})

    def is_lockdown_active(self):
        return self._lockdown_active

    def get_events(self):
        return list(self._events)

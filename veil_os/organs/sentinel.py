import time
from veil.organ_base import OrganBase, OrganConfig
from veil.hybrid import organ_display_name, organ_feeds


class SentinelOrgan(OrganBase):
    def run(self):
        display = organ_display_name(self.config.name)
        feeds = organ_feeds(self.config.name)

        self.start_health_loop()
        self.logger.info("%s online. Watching activity...", display)

        if feeds:
            self.logger.info("Attached feeds: %s", ", ".join(feeds))

        while not self.killer.stop:
            # Hybrid behavior: clinical role + mythic narrative
            self.logger.info("%s: observing system activity and intrusion signals", display)
            time.sleep(15)


def create_organ(config: OrganConfig) -> SentinelOrgan:
    return SentinelOrgan(config)

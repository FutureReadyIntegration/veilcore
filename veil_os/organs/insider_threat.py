import time
from veil.organ_base import OrganBase, OrganConfig


class InsiderThreatOrgan(OrganBase):
    def run(self):
        self.start_health_loop()
        self.logger.info("Insider Threat organ online. Monitoring behavior...")

        while not self.killer.stop:
            # Placeholder: analyze recent activity, score risk, emit alerts
            self.logger.info("InsiderThreat: analyzing behavior for risk signals")
            time.sleep(30)


def create_organ(config: OrganConfig) -> InsiderThreatOrgan:
    return InsiderThreatOrgan(config)

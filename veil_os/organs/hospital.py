import time
from veil.organ_base import OrganBase, OrganConfig
from veil.hybrid import organ_display_name


class HospitalOrgan(OrganBase):
    def run(self):
        display = organ_display_name(self.config.name)

        self.start_health_loop()
        self.logger.info("%s online. Hospital subsystem active.", display)

        while not self.killer.stop:
            self.logger.info("%s: performing internal system health stabilization", display)
            time.sleep(30)


def create_organ(config: OrganConfig) -> HospitalOrgan:
    return HospitalOrgan(config)

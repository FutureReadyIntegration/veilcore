import yaml
from dataclasses import dataclass

@dataclass
class Organ:
    name: str
    tier: str
    glyph: str
    affirmation: str

    @staticmethod
    def from_yaml(path):
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return Organ(**data)

    def activate(self):
        print(f"⚡ Organ '{self.name}' activated.")

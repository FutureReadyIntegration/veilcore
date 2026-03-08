import yaml
from pathlib import Path

DATA_ROOT = Path("backend/data")

def load_yaml(filename: str):
    path = DATA_ROOT / filename
    if not path.exists():
        return {"error": f"{filename} not found"}
    with open(path, "r") as f:
        return yaml.safe_load(f)

def load_yaml_from_folder(folder: str, filename: str):
    path = DATA_ROOT / folder / filename
    if not path.exists():
        return {"error": f"{folder}/{filename} not found"}
    with open(path, "r") as f:
        return yaml.safe_load(f)

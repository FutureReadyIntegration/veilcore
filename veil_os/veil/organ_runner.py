import importlib
import sys

from veil.organ_base import OrganConfig


def load_organ_module(organ_name: str):
    module_name = f"veil.organs.{organ_name}"
    return importlib.import_module(module_name)


def build_config(organ_name: str) -> OrganConfig:
    log_file = f"/var/log/veil/{organ_name}.log"
    storage_path = f"/var/lib/veil/{organ_name}"
    # Default health interval; organs can override internally if needed
    return OrganConfig(
        name=organ_name,
        log_file=log_file,
        storage_path=storage_path,
        health_interval=30,
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m veil.organ_runner <organ_name>")
        sys.exit(1)

    organ_name = sys.argv[1]
    config = build_config(organ_name)

    module = load_organ_module(organ_name)
    if not hasattr(module, "create_organ"):
        print(f"Organ module {module.__name__} missing create_organ(config) factory")
        sys.exit(1)

    organ = module.create_organ(config)
    organ.main()


if __name__ == "__main__":
    main()

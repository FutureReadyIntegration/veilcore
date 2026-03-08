import importlib
import pkgutil

from veil.registry import OrganRegistry


def load_organs(package, eventbus, telemetry, security):
    registry = OrganRegistry()

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package.__name__}.{module_name}")
        organ_cls = getattr(module, "Organ", None)
        if organ_cls is None:
            continue
        organ = organ_cls(eventbus=eventbus, telemetry=telemetry, security=security)
        registry.register(organ)

    return registry

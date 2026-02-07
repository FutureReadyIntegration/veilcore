from typing import Optional
from veil.aliases import registry


def organ_display_name(organ_name: str) -> str:
    """
    Return a human / mythic display name for an organ,
    falling back to the raw organ name.
    """
    reg = registry()
    for alias, data in reg.all().items():
        if data.get("organ") == organ_name:
            return data.get("display_name") or organ_name
    return organ_name


def organ_feeds(organ_name: str) -> list:
    """
    Return any legacy / external feeds associated with this organ.
    """
    reg = registry()
    feeds = []
    for alias, data in reg.all().items():
        if data.get("organ") == organ_name:
            feeds.extend(data.get("feeds") or [])
    return feeds


def alias_for_organ(organ_name: str) -> Optional[str]:
    reg = registry()
    for alias, data in reg.all().items():
        if data.get("organ") == organ_name:
            return alias
    return None

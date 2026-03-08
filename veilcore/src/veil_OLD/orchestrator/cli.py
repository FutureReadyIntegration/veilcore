from __future__ import annotations

from typing import Optional

from .runtime import start, stop, status, list_status


def cmd_start(name: str, module: Optional[str] = None) -> int:
    st = start(name, module=module)
    print(f"OK start: {st.name} running={st.running} pid={st.pid} log={st.log_path}")
    return 0


def cmd_stop(name: str, force: bool = False) -> int:
    st = stop(name, force=force)
    print(f"OK stop: {st.name} running={st.running} pid={st.pid} log={st.log_path}")
    return 0


def cmd_status(name: str) -> int:
    st = status(name)
    print(f"{st.name} running={st.running} pid={st.pid} log={st.log_path}")
    return 0 if st.running else 1


def cmd_list() -> int:
    allst = list_status()
    for n, st in allst.items():
        print(f"{n} running={st.running} pid={st.pid} log={st.log_path}")
    return 0

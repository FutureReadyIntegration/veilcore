import sys
import traceback
from typing import Callable, List, Tuple


def _try(label: str, fn: Callable[[], int], errors: List[str]) -> int | None:
    try:
        code = fn()
        print(f"✅ GUI started: {label}", file=sys.stderr)
        return int(code)
    except Exception as e:
        # Keep a short, readable trail of failures
        tb = "".join(traceback.format_exception_only(type(e), e)).strip()
        errors.append(f"{label}: {tb}")
        return None

def main() -> int:
    # QML-only GUI (no Tkinter/Qt-widgets fallbacks)
    from hospital_gui_qml import main as qml_main
    return int(qml_main())

    """
    Stable GUI entrypoint.

    CLI command: `veil-gui`
    Internally, we route to whichever GUI implementation is available.
    """
    errors: List[str] = []

    backends: List[Tuple[str, Callable[[], int]]] = [
        ("organs v3", lambda: _start_organs_v3()),
        ("organs v2", lambda: _start_organs_v2()),
        ("organs v1", lambda: _start_organs_v1()),
        ("qt",       lambda: _start_qt()),
    ]

    for label, fn in backends:
        result = _try(label, fn, errors)
        if result is not None:
            return result

    print("❌ No GUI backend could start.", file=sys.stderr)
    print("Tried:", ", ".join([b[0] for b in backends]), file=sys.stderr)
    print("Failure details:", file=sys.stderr)
    for msg in errors:
        print(" -", msg, file=sys.stderr)
    return 1


def _start_organs_v3() -> int:
    from .hospital_gui_organs_v3 import VeilHospitalGUIOrgansV3
    VeilHospitalGUIOrgansV3().mainloop()
    return 0


def _start_organs_v2() -> int:
    from .hospital_gui_organs_v2 import VeilHospitalGUIOrgansV2
    VeilHospitalGUIOrgansV2().mainloop()
    return 0


def _start_organs_v1() -> int:
    from .hospital_gui_organs import VeilHospitalGUIOrgans
    VeilHospitalGUIOrgans().mainloop()
    return 0


def _start_qt() -> int:
    from .hospital_gui_qt import main as qt_main
    return int(qt_main())


if __name__ == "__main__":
    raise SystemExit(main())

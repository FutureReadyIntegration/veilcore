import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, Property, QSettings
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


class SettingsBridge(QObject):
    def __init__(self) -> None:
        super().__init__()
        QSettings.setDefaultFormat(QSettings.IniFormat)
        self._s = QSettings("Veil", "HospitalGUI")

    @Slot(str, "QVariant", result="QVariant")
    def get(self, key: str, default=None):
        return self._s.value(key, default)

    @Slot(str, "QVariant")
    def set(self, key: str, value):
        self._s.setValue(key, value)


class Backend(QObject):
    patientsChanged = Signal()
    searchChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._search = ""
        self._all = [
            {"id": 1, "name": "Ava Johnson", "age": 34, "status": "Admitted"},
            {"id": 2, "name": "Noah Smith", "age": 52, "status": "Discharged"},
            {"id": 3, "name": "Mia Chen", "age": 28, "status": "Admitted"},
        ]

    def _filtered(self):
        s = (self._search or "").strip().lower()
        if not s:
            return list(self._all)
        out = []
        for p in self._all:
            if (
                s in str(p["id"]).lower()
                or s in p["name"].lower()
                or s in str(p["age"]).lower()
                or s in p["status"].lower()
            ):
                out.append(p)
        return out

    @Property("QVariantList", notify=patientsChanged)
    def patients(self):
        return self._filtered()

    @Property(str, notify=searchChanged)
    def search(self):
        return self._search

    @Slot(str)
    def set_search(self, text: str) -> None:
        self._search = text or ""
        self.searchChanged.emit()
        self.patientsChanged.emit()

    @Slot(str, int, str)
    def add_patient(self, name: str, age: int, status: str) -> None:
        name = (name or "").strip()
        status = (status or "Admitted").strip()
        if not name:
            return
        try:
            age = int(age)
        except Exception:
            age = 0

        new_id = (max([p["id"] for p in self._all]) + 1) if self._all else 1
        self._all.append({"id": new_id, "name": name, "age": age, "status": status})
        self.patientsChanged.emit()


def main() -> int:
    app = QGuiApplication(sys.argv)

    backend = Backend()
    settings = SettingsBridge()

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("settings", settings)

    qml_path = Path(__file__).with_name("qt_ui").joinpath("Main.qml")
    engine.load(qml_path.as_uri())

    if not engine.rootObjects():
        print(f"❌ Failed to load QML: {qml_path}", file=sys.stderr)
        return 1

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

# Small helpers to call internal APIs or read sentinel logs.
def read_sentinel_log(path="/var/log/veil/sentinel.log", lines=200):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().splitlines()[-lines:]
    except Exception:
        return []

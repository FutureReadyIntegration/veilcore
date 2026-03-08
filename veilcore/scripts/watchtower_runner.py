#!/usr/bin/env python3
import asyncio, sys

sys.path.insert(0, ".")
from core.mobile.api import MobileAPI

async def main():
    api = MobileAPI(port=9444)
    await api.start()
    print("Watchtower running on :9444", flush=True)
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())

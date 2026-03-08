#!/usr/bin/env python3
import time
import signal
import sys

running = True

def shutdown(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

print("Veil Core Engine started (stub)")

while running:
    time.sleep(1)

print("Veil Core Engine stopped cleanly")
sys.exit(0)

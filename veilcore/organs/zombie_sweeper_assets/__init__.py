"""
Zombie Sweeper Organ - Veil OS Security
========================================
"I hunt the dead. I clean the forgotten."

This organ handles cleanup of stale resources:
- Orphan process detection and termination
- Stale session cleanup
- Dead connection sweeping
- Resource leak detection
"""

from .sweeper import (
    ZombieSweeper,
    SweeperConfig,
    ZombieProcess,
    StaleSession,
    DeadConnection,
    SweepResult,
)

__all__ = [
    "ZombieSweeper",
    "SweeperConfig",
    "ZombieProcess",
    "StaleSession",
    "DeadConnection",
    "SweepResult",
]

__version__ = "1.0.0"
__affirmation__ = "I hunt the dead. I clean the forgotten."

from .runner import start, stop, status

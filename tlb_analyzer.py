"""
TLB Performance Analyzer
=========================
Simulates Translation Lookaside Buffer behavior and analyzes
its effect on memory access time. Supports FIFO and LRU
replacement policies, step-by-step tracing, performance
metrics (hit rate, miss rate, EMAT), and matplotlib graphs.

Run with:  python tlb_analyzer.py
"""

from __future__ import annotations

import os
import sys
import random
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Constants
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

TLB_ACCESS_TIME = 1    # time units
MEMORY_ACCESS_TIME = 10  # time units


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Enums & Data Classes
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ReplacementPolicy(Enum):
    FIFO = "FIFO"
    LRU = "LRU"


@dataclass
class AccessResult:
    virtual_address: int
    page_number: int
    offset: int
    frame_number: int
    hit: bool
    tlb_snapshot: dict[int, int]


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Page Table
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class PageTable:
    """Simple flat page table mapping virtual page to physical frame."""

    def __init__(self, num_pages: int):
        self.num_pages = num_pages
        self._table: dict[int, int] = {}
        self._next_frame = 0
        for page in range(num_pages):
            self._table[page] = self._next_frame
            self._next_frame += 1

    def lookup(self, page_number: int) -> Optional[int]:
        return self._table.get(page_number)

    def __repr__(self) -> str:
        entries = ", ".join(f"{p}->{f}" for p, f in sorted(self._table.items()))
        return f"PageTable({entries})"

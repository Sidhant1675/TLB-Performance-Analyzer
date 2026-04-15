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

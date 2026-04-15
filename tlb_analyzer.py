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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  TLB
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TLB:
    """Translation Lookaside Buffer with configurable size and replacement policy."""

    def __init__(self, size: int, policy: ReplacementPolicy = ReplacementPolicy.FIFO):
        self.size = size
        self.policy = policy

        if policy == ReplacementPolicy.LRU:
            self._cache: OrderedDict[int, int] = OrderedDict()
        else:
            self._cache: dict[int, int] = {}
            self._order: deque[int] = deque()

    def lookup(self, page_number: int) -> Optional[int]:
        if page_number in self._cache:
            if self.policy == ReplacementPolicy.LRU:
                self._cache.move_to_end(page_number)
            return self._cache[page_number]
        return None

    def insert(self, page_number: int, frame_number: int) -> None:
        if page_number in self._cache:
            self._cache[page_number] = frame_number
            if self.policy == ReplacementPolicy.LRU:
                self._cache.move_to_end(page_number)
            return

        if len(self._cache) >= self.size:
            self._evict()

        self._cache[page_number] = frame_number
        if self.policy == ReplacementPolicy.FIFO:
            self._order.append(page_number)

    def _evict(self) -> None:
        if self.policy == ReplacementPolicy.FIFO:
            victim = self._order.popleft()
            del self._cache[victim]
        else:
            self._cache.popitem(last=False)

    def snapshot(self) -> dict[int, int]:
        return dict(self._cache)

    def reset(self) -> None:
        self._cache.clear()
        if self.policy == ReplacementPolicy.FIFO:
            self._order.clear()

    def __repr__(self) -> str:
        entries = ", ".join(f"{p}->{f}" for p, f in self._cache.items())
        return f"TLB[{self.policy.value}]({entries})"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Simulator
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class SimulationConfig:
    num_pages: int = 10
    page_size: int = 10
    tlb_size: int = 3
    policy: ReplacementPolicy = ReplacementPolicy.FIFO
    addresses: list[int] = field(default_factory=list)


class Simulator:
    """Drives the full TLB simulation and collects metrics."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.page_table = PageTable(config.num_pages)
        self.tlb = TLB(config.tlb_size, config.policy)
        self.results: list[AccessResult] = []
        self.hits = 0
        self.misses = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return self.hits / self.total if self.total else 0.0

    @property
    def miss_rate(self) -> float:
        return self.misses / self.total if self.total else 0.0

    @property
    def emat(self) -> float:
        hr = self.hit_rate
        mr = self.miss_rate
        return (hr * TLB_ACCESS_TIME) + (mr * (TLB_ACCESS_TIME + MEMORY_ACCESS_TIME))

    def run(self) -> list[AccessResult]:
        self.results.clear()
        self.hits = 0
        self.misses = 0
        self.tlb.reset()

        for addr in self.config.addresses:
            page_num = addr // self.config.page_size
            offset = addr % self.config.page_size

            frame = self.tlb.lookup(page_num)
            if frame is not None:
                hit = True
                self.hits += 1
            else:
                hit = False
                self.misses += 1
                frame = self.page_table.lookup(page_num)
                if frame is None:
                    frame = -1
                else:
                    self.tlb.insert(page_num, frame)

            self.results.append(AccessResult(
                virtual_address=addr,
                page_number=page_num,
                offset=offset,
                frame_number=frame,
                hit=hit,
                tlb_snapshot=self.tlb.snapshot(),
            ))

        return self.results


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Pretty Printing
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
MAGENTA = "\033[95m"

DIVIDER = f"{DIM}{chr(9472) * 72}{RESET}"
THICK_DIVIDER = f"{DIM}{chr(9552) * 72}{RESET}"


def print_banner() -> None:
    print(f"""
{THICK_DIVIDER}
{BOLD}{CYAN}  {chr(9556)}{chr(9552)*51}{chr(9559)}
  {chr(9553)}         TLB  PERFORMANCE  ANALYZER                {chr(9553)}
  {chr(9562)}{chr(9552)*51}{chr(9565)}{RESET}
{THICK_DIVIDER}
""")


def print_config(cfg: SimulationConfig) -> None:
    print(f"{BOLD}Configuration{RESET}")
    print(DIVIDER)
    print(f"  Pages          : {cfg.num_pages}")
    print(f"  Page size      : {cfg.page_size}")
    print(f"  TLB size       : {cfg.tlb_size}")
    print(f"  Policy         : {cfg.policy.value}")
    print(f"  Addresses ({len(cfg.addresses)})  : {cfg.addresses}")
    print(f"  TLB access time: {TLB_ACCESS_TIME} unit(s)")
    print(f"  Memory access  : {MEMORY_ACCESS_TIME} unit(s)")
    print(DIVIDER)
    print()


def print_step(idx: int, r: AccessResult) -> None:
    status = f"{GREEN}HIT{RESET}" if r.hit else f"{RED}MISS{RESET}"
    tlb_str = ", ".join(f"{p}->{f}" for p, f in r.tlb_snapshot.items()) or "empty"
    print(
        f"  {BOLD}[{idx+1:>3}]{RESET}  "
        f"VA={r.virtual_address:<6}  "
        f"Page={r.page_number:<4}  "
        f"Offset={r.offset:<4}  "
        f"Frame={r.frame_number:<4}  "
        f"{status:<14}  "
        f"{DIM}TLB {{ {tlb_str} }}{RESET}"
    )


def print_summary(sim: Simulator) -> None:
    print()
    print(THICK_DIVIDER)
    print(f"{BOLD}{MAGENTA}  RESULTS SUMMARY{RESET}")
    print(THICK_DIVIDER)
    print(f"  Total accesses : {sim.total}")
    print(f"  TLB hits       : {GREEN}{sim.hits}{RESET}")
    print(f"  TLB misses     : {RED}{sim.misses}{RESET}")
    print(f"  Hit rate       : {YELLOW}{sim.hit_rate:.2%}{RESET}")
    print(f"  Miss rate      : {YELLOW}{sim.miss_rate:.2%}{RESET}")
    print(f"  EMAT           : {CYAN}{sim.emat:.2f} time units{RESET}")
    print()

    no_tlb_time = MEMORY_ACCESS_TIME
    speedup = no_tlb_time / sim.emat if sim.emat else float("inf")
    print(f"  Without TLB    : {no_tlb_time:.2f} time units per access")
    print(f"  With TLB       : {sim.emat:.2f} time units per access")
    print(f"  Speedup        : {CYAN}{speedup:.2f}x{RESET}")
    print(THICK_DIVIDER)
    print()

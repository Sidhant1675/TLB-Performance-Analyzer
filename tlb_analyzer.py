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

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Visualization
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def plot_cumulative_hit_rate(results: list[AccessResult]) -> None:
    hits_so_far = 0
    x_vals: list[int] = []
    y_vals: list[float] = []

    for i, r in enumerate(results, 1):
        if r.hit:
            hits_so_far += 1
        x_vals.append(i)
        y_vals.append(hits_so_far / i * 100)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(x_vals, y_vals, color="#333333", linewidth=2, marker="o",
            markersize=5, markerfacecolor="#555555", markeredgecolor="#333333")
    ax.set_xlabel("Memory Access #", fontsize=12)
    ax.set_ylabel("Cumulative Hit Rate (%)", fontsize=12)
    ax.set_title("Cumulative TLB Hit Rate Over Time", fontsize=14, fontweight="bold")
    ax.set_ylim(-5, 105)
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig("cumulative_hit_rate.png", dpi=150)
    print("  [graph]  Saved:  cumulative_hit_rate.png")


def plot_tlb_size_vs_hit_rate(config: SimulationConfig) -> None:
    sizes = list(range(1, config.num_pages + 1))
    hit_rates: list[float] = []

    for sz in sizes:
        cfg = SimulationConfig(
            num_pages=config.num_pages,
            page_size=config.page_size,
            tlb_size=sz,
            policy=config.policy,
            addresses=list(config.addresses),
        )
        sim = Simulator(cfg)
        sim.run()
        hit_rates.append(sim.hit_rate * 100)

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(sizes, hit_rates, color="#555555", edgecolor="#333333", linewidth=0.8)

    for bar, rate in zip(bars, hit_rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                f"{rate:.0f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")

    ax.set_xlabel("TLB Size (entries)", fontsize=12)
    ax.set_ylabel("Hit Rate (%)", fontsize=12)
    ax.set_title("TLB Size vs Hit Rate", fontsize=14, fontweight="bold")
    ax.set_ylim(0, 115)
    ax.set_xticks(sizes)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig("tlb_size_vs_hit_rate.png", dpi=150)
    print("  [graph]  Saved:  tlb_size_vs_hit_rate.png")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Interactive CLI
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def cli_get_config() -> SimulationConfig:
    print(f"{BOLD}Select mode:{RESET}")
    print(f"  {CYAN}1{RESET}) Manual input")
    print(f"  {CYAN}2{RESET}) Auto-generated random addresses")
    print(f"  {CYAN}3{RESET}) Run built-in example test case")
    choice = input(f"\n  Enter choice [{CYAN}1-3{RESET}]: ").strip()

    if choice == "3":
        return SimulationConfig(
            num_pages=10,
            page_size=10,
            tlb_size=3,
            policy=ReplacementPolicy.FIFO,
            addresses=[10, 22, 15, 10, 45, 22],
        )

    num_pages = int(input("  Number of pages  [10]: ").strip() or 10)
    page_size = int(input("  Page size        [10]: ").strip() or 10)
    tlb_size = int(input("  TLB size          [3]: ").strip() or 3)

    pol_in = input("  Policy (FIFO/LRU) [FIFO]: ").strip().upper() or "FIFO"
    policy = ReplacementPolicy[pol_in]

    if choice == "1":
        raw = input("  Enter addresses (comma-separated): ").strip()
        addresses = [int(a.strip()) for a in raw.split(",")]
    else:
        count = int(input("  Number of accesses [20]: ").strip() or 20)
        max_addr = num_pages * page_size - 1
        addresses = [random.randint(0, max_addr) for _ in range(count)]

    return SimulationConfig(num_pages, page_size, tlb_size, policy, addresses)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Main
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main() -> None:
    print_banner()
    config = cli_get_config()

    print()
    print_config(config)

    sim = Simulator(config)
    results = sim.run()

    print(f"{BOLD}Step-by-Step Trace{RESET}")
    print(DIVIDER)
    for i, r in enumerate(results):
        print_step(i, r)
    print(DIVIDER)

    print_summary(sim)

    print(f"{BOLD}Generating graphs ...{RESET}")
    try:
        plot_cumulative_hit_rate(results)
        plot_tlb_size_vs_hit_rate(config)
        print(f"\n  {DIM}Open the PNG files to view graphs.{RESET}")
    except Exception as exc:
        print(f"  Could not render plots: {exc}")

    print(f"\n{DIM}Done.{RESET}\n")


if __name__ == "__main__":
    main()

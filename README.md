# TLB Performance Analyzer

Simulates the behavior of a Translation Lookaside Buffer (TLB) and analyzes its effect on memory access time. Available as a Python CLI/GUI, C++ CLI, and a web-based interface.

## Features

- Virtual to physical address translation simulation
- **FIFO** and **LRU** replacement policies
- Configurable TLB size, page size, and number of pages
- Step-by-step simulation trace with colored output
- Performance metrics: hit rate, miss rate, EMAT, speedup
- **FIFO vs LRU comparison** with side-by-side analysis
- Matplotlib visualizations (cumulative hit rate, TLB size vs hit rate)
- Tkinter GUI with dark minimalist theme
- **Web interface** with interactive charts and premium dark UI

## Requirements

- Python 3.10+
- matplotlib

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Python CLI / GUI

```bash
python tlb_analyzer.py
```

#### Modes
1. **Manual input** — Enter virtual addresses manually
2. **Auto-generated** — Random address sequence
3. **Built-in test** — Pre-configured example test case
4. **GUI** — Launch Tkinter graphical interface

### C++ CLI

```bash
g++ -o tlb_out tlb_analyzer.cpp
./tlb_out
```

Runs a multi-size TLB analysis with FIFO and LRU policies across TLB sizes 2, 4, and 8.

### Web Interface

Open `index.html` in any modern browser, or visit the deployed version on Vercel.

Features:
- Configure simulation parameters (pages, page size, TLB size, policy)
- Run single simulation with animated results
- Compare FIFO vs LRU policies side-by-side
- Interactive Chart.js visualizations

## Example Test Case

```
Page size = 10, TLB size = 3, Policy = FIFO
Addresses = [10, 22, 15, 10, 45, 22]

Results:
  Hits: 3, Misses: 3
  Hit Rate: 50%
  EMAT: 6.00 time units
  Speedup: 1.67x over no-TLB baseline
```

## Performance Metrics

| Metric | Formula |
|--------|---------|
| Hit Rate | hits / total accesses |
| Miss Rate | misses / total accesses |
| EMAT | (Hit Rate × TLB Access Time) + (Miss Rate × (TLB + Memory Access Time)) |

Default timing: TLB access = 1 unit, Memory access = 10 units

## Project Structure

```
tlb_analyzer.py     # Python simulation (CLI + Tkinter GUI)
tlb_analyzer.cpp    # C++ simulation (CLI, multi-size analysis)
index.html          # Web interface (Chart.js, standalone)
vercel.json         # Vercel deployment config
requirements.txt    # Python dependencies
README.md           # This file
```

## License

This project is for educational purposes.

# TLB Performance Analyzer

Simulates the behavior of a Translation Lookaside Buffer (TLB) and analyzes its effect on memory access time.

## Features

- Virtual to physical address translation simulation
- FIFO and LRU replacement policies
- Configurable TLB size, page size, and number of pages
- Step-by-step simulation trace
- Performance metrics: hit rate, miss rate, EMAT
- Matplotlib visualizations
- Tkinter GUI

## Requirements

- Python 3.10+
- matplotlib (`pip install matplotlib`)

## Usage

```bash
python tlb_analyzer.py
```

### Modes
1. **Manual input** - Enter addresses manually
2. **Auto-generated** - Random address sequence
3. **Built-in test** - Example test case
4. **GUI** - Launch Tkinter interface

## Example Test Case

- Page size = 10, TLB size = 3
- Addresses = [10, 22, 15, 10, 45, 22]
- Result: 50% hit rate, EMAT = 6.00 time units

## Performance Metrics

- **Hit Rate** = hits / total accesses
- **Miss Rate** = misses / total accesses
- **EMAT** = (Hit Rate x TLB Access Time) + (Miss Rate x (TLB Access Time + Memory Access Time))

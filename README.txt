# MOS - Multiprogramming Operating System Simulator

A Python simulator of a small Multiprogramming Operating System (MOS). It builds a virtual computer (CPU, memory, input and output files) and an OS on top of it that loads jobs, runs them, handles input/output and interrupts, and writes the results.

The project has two phases. Phase 2 is built on top of Phase 1.

| | Phase 1 | Phase 2 |
|---|---|---|
| Memory | 100 words (10 blocks) | 300 words (30 frames) |
| Program storage | Sequential, from address 0 | Random frames through a page table (paging) |
| Jobs | Error-free | May contain errors |
| Interrupts | SI | SI, TI, PI |
| End of a job | Two blank lines | 6-line report (job id, error, IC, IR, TTC, LLC) + two blank lines |

## Features

**Phase 1**
- Virtual machine: IR, R, IC, C registers and 100 x 4 memory
- 7 instructions: `GD`, `PD`, `LR`, `SR`, `CR`, `BT`, `H`
- LOAD, EXECUTE USER PROGRAM and MOS (READ, WRITE, TERMINATE)
- Job analytics: turnaround, waiting and CPU time, operation counts, timeline

**Phase 2**
- Paging: page table, `ADDRESS_MAP` (virtual to real address), random `ALLOCATE`
- Interrupts: SI (service), TI (time limit), PI (opcode, operand, page fault)
- Detects and reports: out of data, line limit, time limit, opcode error, operand error, invalid page fault, and time limit combined with opcode or operand error
- Valid page faults (`GD`, `SR`) are served by the OS; invalid ones end the job
- Analytics extended with page faults, frames used and how each job ended

## Project structure

```
MOS-Multiprogramming-OS-Simulator/
├── README.md
├── OS_Phase1/
│   ├── mos_analytics.py          Phase 1 simulator + analytics
│   ├── input_Phase1.txt          sample jobs
│   ├── output.txt                output of the sample jobs
│   ├── analytics_report.txt      analytics report
│   ├── timeline.csv              tick-by-tick event log
│   └── OS_Phase1_Easy_Guide.pdf  easy guide
└── OS_Phase2/
    ├── mos_phase2.py                 Phase 2 simulator
    ├── mos_phase2_analytics.py       Phase 2 simulator + analytics
    ├── input_phase2.txt              sample jobs (with errors)
    ├── output_phase2.txt             output of the sample jobs
    ├── analytics_report_phase2.txt   analytics report
    ├── timeline_phase2.csv           tick-by-tick event log
    ├── OS_Phase2_Easy_Guide.pdf      easy guide
    └── MOS_Project_Report.pdf        project report and viva Q&A
```

## Requirements

Python 3. No extra packages are needed.

## How to run

**Phase 1**
```
cd OS_Phase1
python3 mos_analytics.py -i input_Phase1.txt -o output.txt
```

**Phase 2**
```
cd OS_Phase2
python3 mos_phase2.py -i input_phase2.txt -o output_phase2.txt
python3 mos_phase2_analytics.py            # also writes the report and timeline
```

Phase 2 options:

| Option | What it does |
|---|---|
| `--seed N` | Same random frames every run |
| `--trace` | Print every instruction (`mos_phase2.py`) |
| `--dump` | Print each job's page table (`mos_phase2.py`) |
| `--arrival-gap N` | Jobs arrive N ticks apart (analytics version) |
| `--quiet` | No live per-job lines (analytics version) |

## Job format

```
$AMJ020200250004      job id 0202, time limit 0025, line limit 0004
GD20PD20LR20...       program cards (10 instructions per line)
$DTA
*                     data cards
$END0202
```

Jobs follow each other in the input file with no separator. In the output file, each job is followed by two blank lines.

## Phase 2 error messages

| EM | Message | Cause |
|---|---|---|
| 0 | NO ERROR | Job ended normally |
| 1 | OUT OF DATA | `GD` but no data card left |
| 2 | LINE LIMIT EXCEEDED | More `PD` lines than the limit |
| 3 | TIME LIMIT EXCEEDED | More instructions than the limit |
| 4 | OPERATION CODE ERROR | Unknown opcode |
| 5 | OPERAND ERROR | Operand is not a two-digit number |
| 6 | INVALID PAGE FAULT | `LR`, `CR`, `BT` or `PD` used a page that was never allocated |
| 7 / 8 | Time limit with opcode / operand error | Both at once (3 + 4, 3 + 5) |

Example report written at the end of a job:
```
JOB ID   :  202
 LINE LIMIT EXCEEDED
IC       :  15
IR       :  PD60
TTC      :  15
LLC      :  4
```

## Documentation

- `OS_Phase1/OS_Phase1_Easy_Guide.pdf` and `OS_Phase2/OS_Phase2_Easy_Guide.pdf` explain each phase with pictures.
- `OS_Phase2/MOS_Project_Report.pdf` explains what the whole project does, function by function, with test results and viva questions.

## Notes

- Phase 2's LOAD function follows the algorithm document, since no separate lecture covered it.
- The sample `output_phase2.txt` has the same text as the expected output. The expected file shows empty memory cells as NUL characters and starts with an extra blank line, which this Python version does not write.
- A Phase 1 job that jumps with `BT` to an address in a page that was never loaded gives an invalid page fault in Phase 2.

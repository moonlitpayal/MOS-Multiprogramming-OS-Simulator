<div align="center">

# 🖥️ MOS — Multiprogramming Operating System Simulator

**A tiny computer and a tiny operating system, built from scratch in Python.**

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Phase 1](https://img.shields.io/badge/Phase%201-Complete-brightgreen)
![Phase 2](https://img.shields.io/badge/Phase%202-Complete-brightgreen)
![Dependencies](https://img.shields.io/badge/Dependencies-None-blue)
![Type](https://img.shields.io/badge/Type-College%20Project-orange)

[Overview](#-overview) •
[Features](#-features) •
[How it works](#-how-it-works) •
[Quick start](#-quick-start) •
[Errors](#-phase-2-error-handling) •
[Structure](#-project-structure) •
[Docs](#-documentation)

</div>

---

## 📖 Overview

MOS simulates a small computer: a **virtual CPU**, **main memory**, and an **input / output file** that act as a card reader and a printer. On top of it runs a mini **operating system** that loads user jobs, runs them instruction by instruction, performs I/O on their behalf, and ends them cleanly or with an error message.

The goal is to **see how a real OS works inside**: loading, the fetch–decode–execute cycle, interrupts, paging and error handling.

| | 🟦 Phase 1 | 🟧 Phase 2 |
|---|---|---|
| **Memory** | 100 words (10 blocks) | 300 words (30 frames) |
| **Program storage** | Sequential, from address 0 | Random frames via a **page table** |
| **Jobs** | Error-free | May contain **6 kinds of errors** |
| **Interrupts** | `SI` | `SI` · `TI` · `PI` |
| **End of job** | Two blank lines | 6-line **report** + two blank lines |

> Phase 2 is built **on top of** Phase 1.

---

## ✨ Features

<table>
<tr>
<td width="50%" valign="top">

### 🟦 Phase 1
- Virtual machine: `IR`, `R`, `IC`, `C` and 100 × 4 memory
- 7 instructions: `GD` `PD` `LR` `SR` `CR` `BT` `H`
- `LOAD`, `EXECUTE USER PROGRAM`, and `MOS` (`READ` `WRITE` `TERMINATE`)
- Job analytics: turnaround, waiting time, CPU use, timeline

</td>
<td width="50%" valign="top">

### 🟧 Phase 2
- **Paging**: page table, `ADDRESS_MAP`, random `ALLOCATE`
- **Interrupts**: SI (service), TI (time), PI (program)
- **Error detection** with termination reports
- Valid page faults served by the OS
- Analytics with page faults, frames used and job outcomes

</td>
</tr>
</table>

---

## 🧠 How it works

```mermaid
flowchart LR
    A[📥 Input file<br/>jobs] --> B[LOAD<br/>page table + program pages]
    B --> C[START EXECUTION<br/>IC = 0]
    C --> D[EXECUTE USER PROGRAM<br/>fetch · map address · decode · execute]
    D -->|GD / PD / H<br/>or an error| E[MOS<br/>READ · WRITE · TERMINATE]
    E -->|continue| D
    E -->|job ended| B
    E --> F[📤 Output file<br/>results + report]
```

### 📄 Paging in one picture

```mermaid
flowchart LR
    VA["Virtual address<br/>VA = 37"] --> P["page = 3<br/>offset = 7"]
    P --> PT[("Page table<br/>entry for page 3")]
    PT -->|"valid: frame 9"| RA["Real address<br/>9 × 10 + 7 = 97"]
    PT -->|"empty"| PF{{"Page fault<br/>PI = 3"}}
    PF -->|"GD or SR"| AL["Allocate a random frame,<br/>update table, re-run"]
    PF -->|"LR · CR · BT · PD"| ER["Terminate<br/>INVALID PAGE FAULT"]
```

<details>
<summary><b>🔔 Interrupts (click to expand)</b></summary>

| Interrupt | Value | Raised when |
|---|---|---|
| `SI` | 1 / 2 / 3 | `GD` / `PD` / `H` |
| `TI` | 2 | Time limit exceeded |
| `PI` | 1 | Opcode error |
| `PI` | 2 | Operand error |
| `PI` | 3 | Page fault |

</details>

<details>
<summary><b>📦 Memory layout (click to expand)</b></summary>

- 300 words = **30 frames × 10 words**. One frame holds exactly one 40-character card.
- Each job gets **one frame for its page table** and one frame per program page, all chosen at random.
- Data pages get their frames later, when `GD` or `SR` first uses them.

</details>

---

## 🚀 Quick start

**Requirements:** Python 3. No extra packages.

```bash
# Phase 1
cd OS_Phase1
python3 mos_analytics.py -i input_Phase1.txt -o output.txt

# Phase 2
cd OS_Phase2
python3 mos_phase2.py -i input_phase2.txt -o output_phase2.txt
python3 mos_phase2_analytics.py        # also writes the report and timeline
```

<details>
<summary><b>⚙️ Phase 2 options (click to expand)</b></summary>

| Option | What it does |
|---|---|
| `--seed N` | Same random frames every run |
| `--trace` | Print every instruction (`mos_phase2.py`) |
| `--dump` | Print each job's page table (`mos_phase2.py`) |
| `--arrival-gap N` | Jobs arrive N ticks apart (analytics version) |
| `--quiet` | No live per-job lines (analytics version) |

</details>

<details>
<summary><b>🧾 Job format (click to expand)</b></summary>

```text
$AMJ020200250004      job id 0202 · time limit 0025 · line limit 0004
GD20PD20LR20...       program cards (10 instructions per line)
$DTA
*                     data cards
$END0202
```

Jobs follow each other in the input file with no separator. In the output file each job is followed by two blank lines.

</details>

---

## 🚨 Phase 2 error handling

When a job goes wrong, the OS stops it and writes a report like this:

```text
JOB ID   :  202
 LINE LIMIT EXCEEDED
IC       :  15
IR       :  PD60
TTC      :  15
LLC      :  4
```

| EM | Message | Cause |
|:--:|---|---|
| 0 | ✅ NO ERROR | Job ended normally |
| 1 | 📭 OUT OF DATA | `GD` but no data card left |
| 2 | 📏 LINE LIMIT EXCEEDED | More `PD` lines than the limit |
| 3 | ⏱️ TIME LIMIT EXCEEDED | More instructions than the limit |
| 4 | ❓ OPERATION CODE ERROR | Unknown opcode |
| 5 | 🔢 OPERAND ERROR | Operand is not a two-digit number |
| 6 | 📄 INVALID PAGE FAULT | `LR` `CR` `BT` `PD` used a page that was never allocated |
| 7 · 8 | ⏱️➕ Time limit with opcode / operand error | Both at once (3 + 4, 3 + 5) |

<details>
<summary><b>🔍 What do IC, IR, TTC and LLC mean?</b></summary>

- **IC** — instruction counter when the job stopped
- **IR** — the instruction that was being handled
- **TTC** — instructions completed so far (time counter)
- **LLC** — lines printed so far (line counter)

</details>

---

## 📊 Analytics

Both phases come with an analytics version that measures itself on a virtual clock (ticks) and writes a report and a tick-by-tick timeline.

| Measured | Phase 1 | Phase 2 |
|---|:--:|:--:|
| Turnaround, waiting and service time | ✅ | ✅ |
| CPU use and I/O wait | ✅ | ✅ |
| Reads / writes / executes | ✅ | ✅ |
| ASCII timeline (Gantt chart) | ✅ | ✅ |
| Page faults and frames used | – | ✅ |
| How each job ended | – | ✅ |

---

## 📁 Project structure

```text
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

---

## 📚 Documentation

| Document | What it covers |
|---|---|
| `OS_Phase1/OS_Phase1_Easy_Guide.pdf` | Phase 1 explained with pictures |
| `OS_Phase2/OS_Phase2_Easy_Guide.pdf` | Phase 2 explained with pictures |
| `OS_Phase2/MOS_Project_Report.pdf` | The whole project function by function, test results, viva questions |

---

## 📝 Notes

- Phase 2's `LOAD` follows the algorithm document, since no separate lecture covered it.
- `output_phase2.txt` has the same text as the expected output. The expected file shows empty memory cells as NUL characters and starts with an extra blank line, which this Python version does not write.
- A Phase 1 job that jumps with `BT` to a page that was never loaded gives an invalid page fault in Phase 2.

---

<div align="center">

Made for the Operating Systems course project · ⭐ Star the repo if it helped you

</div>

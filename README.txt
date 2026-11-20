# 🖥️ MOS — Multiprogramming Operating System Simulator

<p align="center">
  <strong>A Computer. An Operating System. Built from Scratch.</strong>
  <br/>
  A Python-based simulation of a multiprogramming operating system featuring virtual memory, paging, interrupts, process execution, error handling, and system analytics.
  <br/><br/>

  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Phase%201-Complete-2ea44f?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Phase%202-Complete-2ea44f?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Dependencies-None-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Project-Operating%20Systems-orange?style=for-the-badge" />

  <br/><br/>

  **Designed to understand how an operating system actually works — one instruction at a time.**
</p>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Project Highlights](#-project-highlights)
- [System Architecture](#-system-architecture)
- [Development Phases](#-development-phases)
- [Core Concepts Implemented](#-core-concepts-implemented)
- [How the Simulator Works](#-how-the-simulator-works)
- [Virtual Memory and Paging](#-virtual-memory-and-paging)
- [Interrupt Handling](#-interrupt-handling)
- [Error Handling](#-error-handling)
- [System Analytics](#-system-analytics)
- [Quick Start](#-quick-start)
- [Input File Format](#-input-file-format)
- [Project Structure](#-project-structure)
- [Documentation](#-documentation)
- [Learning Outcomes](#-learning-outcomes)

---

## 📖 Overview

**MOS (Multiprogramming Operating System Simulator)** is a lightweight simulation of a computer system and its operating system, developed entirely in Python using standard language features without external dependencies.

The project recreates the fundamental components of a computer:

- **Virtual CPU:** Fetches, decodes, and executes machine instructions.
- **Main Memory:** Stores instructions, data, and page tables.
- **Operating System:** Controls job loading, execution, I/O operations, interrupts, and termination.
- **Input System:** Reads program cards and data cards from an input file.
- **Output System:** Writes execution results and termination reports to an output file.

Rather than treating an operating system as a collection of theoretical concepts, MOS demonstrates how these concepts interact during actual program execution.

### What makes this project interesting?

It implements two progressively developed versions of the simulator:

| Capability | Phase 1 | Phase 2 |
|---|---|---|
| Memory | 100 words | 300 words |
| Memory organization | 10 blocks | 30 frames |
| Program loading | Sequential | Page-based |
| Address translation | Direct | Page table |
| Memory allocation | Sequential | Random frame allocation |
| Interrupt handling | SI | SI, TI, PI |
| Error handling | Basic | 8 termination conditions |
| Page fault handling | Not implemented | Implemented |
| Execution analytics | Yes | Yes |
| Job reports | Basic | Detailed |

> **Phase 2 extends the original Phase 1 simulator by introducing paging, address translation, program interrupts, time interrupts, and structured error handling.**

---

## ✨ Project Highlights

<table>
<tr>
<td width="50%" valign="top">

### 🧠 Virtual Machine

- Virtual CPU registers: `IR`, `R`, `IC`, `C`
- Instruction fetch-decode-execute cycle
- Memory management
- Conditional branching
- Register-to-memory operations
- Instruction-level execution

</td>
<td width="50%" valign="top">

### 💾 Memory Management

- 100-word memory in Phase 1
- 300-word memory in Phase 2
- 10-word memory frames
- Page table implementation
- Virtual-to-physical address translation
- Dynamic frame allocation

</td>
</tr>
<tr>
<td width="50%" valign="top">

### ⚡ Interrupt System

- Service Interrupt (`SI`)
- Time Interrupt (`TI`)
- Program Interrupt (`PI`)
- Centralized interrupt handling
- OS-level service routines

</td>
<td width="50%" valign="top">

### 📊 System Analytics

- Turnaround time
- Waiting time
- Service time
- CPU utilization
- I/O waiting time
- Page fault statistics
- Frame utilization
- Tick-by-tick execution timeline

</td>
</tr>
</table>

---

## 🏗️ System Architecture

MOS follows a simplified computer-system architecture in which the operating system manages the interaction between the CPU, memory, and I/O devices.

```mermaid
flowchart TB
    A["Input File<br/>Program Cards + Data Cards"]

    subgraph OS["Operating System"]
        B["LOAD<br/>Job Initialization"]
        C["Memory Management<br/>Allocation + Page Table"]
        D["EXECUTE USER PROGRAM"]
        E["MOS<br/>Interrupt Handling"]
        F["READ / WRITE / TERMINATE"]
    end

    subgraph VM["Virtual Machine"]
        G["Virtual CPU<br/>IR · R · IC · C"]
        H["Main Memory<br/>300 Words · 30 Frames"]
    end

    I["Output File<br/>Results + Termination Reports"]

    A --> B
    B --> C
    C --> D
    D --> G
    G <--> H
    G --> E
    E --> F
    F --> D
    F --> I
```

### Major Components

| Component | Responsibility |
|---|---|
| CPU | Executes instructions |
| IR | Stores the current instruction |
| R | General-purpose register |
| IC | Tracks the next instruction |
| C | Stores the comparison condition |
| Memory | Stores program instructions and data |
| Page Table | Maps virtual pages to physical frames |
| MOS | Handles OS services and interrupts |
| Input File | Supplies jobs and data |
| Output File | Stores results and execution reports |

---

## 🔄 Development Phases

### 🟦 Phase 1 — Foundation of the Virtual Operating System

Phase 1 establishes the basic virtual machine and operating system execution environment.

**Implemented features:**

1. Virtual CPU with four registers.
2. 100-word main memory.
3. Instruction loading and execution.
4. Fetch-decode-execute cycle.
5. Seven machine instructions.
6. Basic input/output operations.
7. Job termination.
8. Execution analytics.

**Instruction Set**

| Instruction | Operation |
|---|---|
| `GD` | Get Data |
| `PD` | Put Data |
| `LR` | Load Register |
| `SR` | Store Register |
| `CR` | Compare Register |
| `BT` | Branch if True |
| `H` | Halt |

**Phase 1 execution flow:**

```mermaid
flowchart TD
    A["Read Input File"] --> B["LOAD"]
    B --> C["Initialize Memory and Registers"]
    C --> D["Fetch Instruction"]
    D --> E["Decode Instruction"]
    E --> F["Execute Instruction"]
    F --> G{"Halt or I/O?"}
    G -->|Continue| D
    G -->|I/O or Halt| H["MOS Service Routine"]
    H --> I{"Job Terminated?"}
    I -->|No| D
    I -->|Yes| J["Write Output"]
```

### 🟧 Phase 2 — Paging, Interrupts and Advanced Error Handling

Phase 2 builds on the original execution engine and introduces more advanced operating-system concepts.

**Implemented features:**

1. 300-word main memory.
2. 30 physical memory frames.
3. Page-based program loading.
4. Page table management.
5. Random frame allocation.
6. Virtual-to-physical address translation.
7. Service, time, and program interrupts.
8. Page fault handling.
9. Structured job termination reports.
10. Extended execution analytics.

**The major upgrade:** Programs no longer rely on sequential physical memory placement. Virtual addresses are translated through page tables into physical memory addresses.

---

## ⚙️ Core Concepts Implemented

### 1. Instruction Execution Cycle

Every instruction follows the fundamental CPU execution process:

```mermaid
flowchart LR
    A["FETCH"] --> B["DECODE"]
    B --> C["EXECUTE"]
    C --> D["UPDATE"]
    D --> A
```

- **Fetch:** Retrieve the instruction using the Instruction Counter.
- **Decode:** Identify the opcode and operand.
- **Execute:** Perform the required operation.
- **Update:** Update registers, memory, counters, and execution state.

### 2. Paging and Memory Management

Phase 2 divides the physical memory into fixed-size frames.

| Property | Value |
|---|---:|
| Total memory | 300 words |
| Frame size | 10 words |
| Total frames | 30 |
| Page size | 10 words |
| Page table | One frame per job |

Each job receives:
- One frame for its page table.
- One frame for every program page.
- Additional data frames when required.

### 3. Virtual Address Translation

A virtual address is divided into two components:

- Page Number
- Offset

**Example:**

Consider virtual address `37`.

```text
Virtual Address = 37

Page Number = 37 / 10 = 3
Offset      = 37 % 10 = 7
```

Suppose page 3 is mapped to physical frame 9.

```text
Physical Address = (Frame Number × Frame Size) + Offset

                 = (9 × 10) + 7

                 = 97
```

**Address Translation Flow**

```mermaid
flowchart TD
    A["Virtual Address: 37"] --> B["Page: 3 | Offset: 7"]
    B --> C["Check Page Table"]
    C --> D{"Page Allocated?"}
    D -->|Yes| E["Frame 9"]
    E --> F["Physical Address: 97"]
    D -->|No| G["Page Fault"]
    G --> H{"Instruction Type?"}
    H -->|GD / SR| I["Allocate Frame"]
    I --> J["Update Page Table"]
    J --> K["Retry Instruction"]
    H -->|LR / CR / BT / PD| L["Invalid Page Fault"]
    L --> M["Terminate Job"]
```

### 4. Dynamic Frame Allocation

Physical frames are allocated dynamically rather than assigning every job a fixed sequential memory region.

The allocation process:

1. Identify an available physical frame.
2. Allocate the frame to the required page.
3. Update the corresponding page table entry.
4. Continue program execution.

The simulator also supports deterministic random allocation using a seed.

---

## 🔔 Interrupt Handling

Phase 2 implements three major interrupt categories.

| Interrupt | Value | Trigger |
|---|---:|---|
| SI | 1 | `GD` instruction |
| SI | 2 | `PD` instruction |
| SI | 3 | `H` instruction |
| TI | 2 | Time limit exceeded |
| PI | 1 | Opcode error |
| PI | 2 | Operand error |
| PI | 3 | Page fault |

### Interrupt Processing

```mermaid
flowchart TD
    A["Instruction Execution"] --> B{"Interrupt Raised?"}
    B -->|No| C["Continue Execution"]
    B -->|Yes| D["Transfer Control to MOS"]
    D --> E{"Interrupt Type"}
    E -->|SI| F["Perform I/O or Termination"]
    E -->|TI| G["Handle Time Limit"]
    E -->|PI| H["Handle Program Error"]
    F --> I["Resume or Terminate"]
    G --> I
    H --> I
```

Interrupt handling allows the operating system to respond to events that require services beyond normal user-program execution.

---

## 🚨 Error Handling

Phase 2 includes structured error detection and termination reporting.

The simulator identifies different execution errors and associates them with corresponding termination codes.

### Error Code Reference

| EM | Error | Description |
|---:|---|---|
| 0 | NO ERROR | Normal job termination |
| 1 | OUT OF DATA | Data requested but unavailable |
| 2 | LINE LIMIT EXCEEDED | Output line limit exceeded |
| 3 | TIME LIMIT EXCEEDED | Execution time limit exceeded |
| 4 | OPERATION CODE ERROR | Unknown instruction opcode |
| 5 | OPERAND ERROR | Invalid operand |
| 6 | INVALID PAGE FAULT | Invalid memory access through an unallocated page |
| 7 | TIME + OPCODE ERROR | Time and opcode errors together |
| 8 | TIME + OPERAND ERROR | Time and operand errors together |

### Sample Termination Report

```text
JOB ID   :  202
LINE LIMIT EXCEEDED
IC       :  15
IR       :  PD60
TTC      :  15
LLC      :  4
```

### Report Fields

| Field | Meaning |
|---|---|
| JOB ID | Unique job identifier |
| IC | Instruction Counter |
| IR | Instruction Register |
| TTC | Total Time Counter |
| LLC | Line Limit Counter |

This reporting mechanism makes it easier to identify why a job terminated and which instruction was being processed.

---

## 📊 System Analytics

Both phases include an analytics-enabled simulator.

Instead of only producing program output, the analytics versions maintain a virtual execution clock and record system activity.

### Metrics Tracked

| Metric | Description |
|---|---|
| Turnaround Time | Total time from arrival to completion |
| Waiting Time | Time spent waiting |
| Service Time | Time spent receiving service |
| CPU Utilization | Proportion of time CPU remains active |
| I/O Waiting Time | Time spent waiting for I/O |
| Instruction Count | Number of instructions executed |
| Read Operations | Number of input operations |
| Write Operations | Number of output operations |
| Page Faults | Number of page faults |
| Frames Used | Physical frames allocated |
| Job Outcome | Normal or abnormal termination |

### Execution Timeline

The analytics module also generates a tick-by-tick execution log.

```text
Tick    Job     Event
--------------------------------
0       0201    JOB ARRIVAL
1       0201    LOAD
2       0201    CPU EXECUTION
3       0201    CPU EXECUTION
4       0201    I/O REQUEST
5       0201    I/O WAIT
6       0201    CPU EXECUTION
7       0201    JOB TERMINATED
```

*Illustrative timeline showing the type of events recorded by the analytics system.*

Generated analytics files include:

- `analytics_report.txt`
- `timeline.csv`
- `analytics_report_phase2.txt`
- `timeline_phase2.csv`

---

## 🚀 Quick Start

### Prerequisites

- Python 3.x
- Git
- A terminal or command prompt

**No third-party Python packages are required.**

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd MOS-Multiprogramming-OS-Simulator
```

### 2. Run Phase 1

```bash
cd OS_Phase1

python3 mos_analytics.py \
    -i input_Phase1.txt \
    -o output.txt
```

### 3. Run Phase 2

```bash
cd ../OS_Phase2

python3 mos_phase2.py \
    -i input_phase2.txt \
    -o output_phase2.txt
```

### 4. Run Phase 2 with Analytics

```bash
python3 mos_phase2_analytics.py
```

The analytics version generates the execution report and timeline.

### Windows Users

If `python3` is not recognized, use:

```bash
python
```

### Optional Phase 2 Arguments

| Argument | Description |
|---|---|
| `--seed N` | Reproduce random frame allocation |
| `--trace` | Display instruction-by-instruction execution |
| `--dump` | Display page tables |
| `--arrival-gap N` | Set job arrival intervals in analytics mode |
| `--quiet` | Disable live per-job analytics output |

---

## 🧾 Input File Format

MOS uses a card-based job format.

A typical job consists of:

1. Job initialization card (`$AMJ`)
2. Program cards
3. Data separator (`$DTA`)
4. Data cards
5. Job termination card (`$END`)

### Example

```text
$AMJ020200250004
GD20PD20LR20...
$DTA
*
$END0202
```

### Job Header Structure

```text
$AMJ020200250004

0202 = Job ID
0025 = Time Limit
0004 = Line Limit
```

Jobs can be placed sequentially in the input file without additional separators.

Each job's output is followed by two blank lines.

---

## 📁 Project Structure

```text
MOS-Multiprogramming-OS-Simulator/
│
├── README.md
│
├── OS_Phase1/
│   ├── mos_analytics.py
│   ├── input_Phase1.txt
│   ├── output.txt
│   ├── analytics_report.txt
│   ├── timeline.csv
│   └── OS_Phase1_Easy_Guide.pdf
│
└── OS_Phase2/
    ├── mos_phase2.py
    ├── mos_phase2_analytics.py
    ├── input_phase2.txt
    ├── output_phase2.txt
    ├── analytics_report_phase2.txt
    ├── timeline_phase2.csv
    ├── OS_Phase2_Easy_Guide.pdf
    └── MOS_Project_Report.pdf
```

---

## 📚 Documentation

Detailed supporting documentation is included in the repository.

| Document | Contents |
|---|---|
| `OS_Phase1_Easy_Guide.pdf` | Phase 1 concepts and implementation explained with diagrams |
| `OS_Phase2_Easy_Guide.pdf` | Phase 2 paging, interrupts and error handling |
| `MOS_Project_Report.pdf` | Complete project explanation, implementation details, test results and viva questions |

---

## 🎯 Learning Outcomes

Through MOS, the following operating-system concepts are implemented and explored practically:

- Understanding the internal structure of a virtual computer.
- Implementing a CPU instruction execution cycle.
- Understanding registers and instruction processing.
- Exploring memory organization and allocation.
- Implementing paging and page tables.
- Understanding virtual and physical address translation.
- Handling interrupts and operating-system services.
- Detecting program execution errors.
- Generating execution statistics and performance reports.
- Understanding how CPU execution, memory management and I/O interact.

The project connects theoretical operating-system concepts with a working software implementation.

---

## 📝 Implementation Notes

- Phase 2's `LOAD` follows the supplied algorithm document.
- The Phase 2 output differs from the reference output in its representation of empty memory cells: this implementation does not write NUL characters or the additional leading blank line.
- A Phase 1 job that branches using `BT` to an unloaded page is treated as an invalid page fault in Phase 2.

---

## 👨‍💻 Project Information

**Project:** MOS — Multiprogramming Operating System Simulator

**Domain:** Operating Systems / Computer Systems

**Language:** Python 3

**Dependencies:** Python Standard Library

**Development:** Two-phase implementation

**Project Type:** Academic / Educational Software Project

---

<p align="center">
  <strong>Built to understand the machine beneath the software.</strong>
  <br/><br/>
  ⭐ If you find this project useful, consider giving the repository a star!
  <br/>
  <sub>Made with Python | Operating Systems Project</sub>
</p>

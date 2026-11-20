# 🖥️ MOS — Multiprogramming Operating System Simulator

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Phase_1-Complete-00C853?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Phase_2-Complete-00BFA5?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Dependencies-None-7C4DFF?style=for-the-badge" />
</p>

<p align="center">
  <b>A tiny computer. A tiny operating system. Built from scratch in Python.</b>
  <br/>
  Simulating how an operating system loads, executes, manages memory, handles interrupts, and terminates jobs.
</p>

---

## ✨ What is MOS?

**MOS** is a Python-based Multiprogramming Operating System Simulator that brings core OS concepts to life through a virtual CPU, main memory, and a mini operating system.

From instruction execution to paging and interrupt handling, everything is simulated step by step.

## 🚀 Features

| 🟦 Phase 1 | 🟪 Phase 2 |
|:---|:---|
| Virtual CPU & registers | Virtual memory & paging |
| 100-word memory | 300-word memory |
| 7 machine instructions | Page table & address mapping |
| Fetch–Decode–Execute | Dynamic frame allocation |
| Basic I/O operations | SI, TI & PI interrupts |
| Job execution & termination | Advanced error handling |
| Execution analytics | Page fault analytics |

## 🧠 How It Works

```mermaid
flowchart LR
    A["📥 Input"] --> B["LOAD"]
    B --> C["🧠 CPU"]
    C <--> D["💾 Memory"]
    C --> E["⚡ MOS"]
    E --> C
    E --> F["📤 Output"]
```

## ⚙️ Core Concepts

- **CPU Simulation** — IR, R, IC, C and instruction execution.
- **Memory Management** — Memory allocation, frames and page tables.
- **Paging** — Virtual-to-physical address translation.
- **Interrupts** — Service, Time and Program Interrupts.
- **Error Handling** — 8 termination conditions.
- **Analytics** — CPU utilization, turnaround time, waiting time and execution timelines.

## 🛠️ Tech Stack

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Mermaid-FF3670?style=flat-square&logo=mermaid&logoColor=white" />
  <img src="https://img.shields.io/badge/Standard_Library-6A5ACD?style=flat-square" />
</p>

## ⚡ Quick Start

**1. Clone the repository**

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd MOS-Multiprogramming-OS-Simulator
```

**2. Run Phase 1**

```bash
cd OS_Phase1
python3 mos_analytics.py -i input_Phase1.txt -o output.txt
```

**3. Run Phase 2**

```bash
cd ../OS_Phase2
python3 mos_phase2.py -i input_phase2.txt -o output_phase2.txt
```

**4. Run Phase 2 Analytics**

```bash
python3 mos_phase2_analytics.py
```

> Requirements: Python 3.x · No external dependencies.

## 📊 Analytics

Both phases include analytics modules that track:

- ⏱️ Turnaround, waiting and service time
- 🖥️ CPU utilization and I/O waiting
- 📈 Instruction execution statistics
- 📄 Page faults and frame utilization (Phase 2)
- 📊 Tick-by-tick execution timelines

## 📁 Project Structure

```text
MOS/
├── README.md
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

## 📚 Documentation

| Document | Description |
|:---|:---|
| Phase 1 Guide | Fundamentals and execution |
| Phase 2 Guide | Paging, interrupts and errors |
| Project Report | Implementation, results and viva Q&A |

## 🎯 Built With Purpose

Created as an Operating Systems course project to explore the internal working of computers and operating systems through practical implementation.

---

<p align="center">
  <b>💻 Built with Python. Powered by curiosity.</b>
  <br/><br/>
  ⭐ If you find MOS interesting, consider starring the repository!
</p>

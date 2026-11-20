#!/usr/bin/env python3
"""
MOS Phase 1  +  Stream Job Analytics
====================================
A Phase-1 MOS simulator (virtual machine, LOAD, EXECUTE USER PROGRAM, MOS with
READ / WRITE / TERMINATE) that also *measures itself* while it runs:

  * job turnaround time      (arrival -> completion, plus wait / service split)
  * CPU utilization          (per job and for the whole system)
  * I/O operations           R = reads (GD), W = writes (PD), E = executes (LR/SR/CR/BT)
  * execution timeline       tick-by-tick event log + ASCII Gantt chart

Naming style (as in the lecture): notation variables and main functions are
UPPER case (M, IR, R, C, IC, SI, BUFFER, LOAD, MOS, READ ...). Our own extra
variables and helper functions are lower case.

Time is measured on a *virtual clock* (ticks), so results are deterministic.
Default cost model (change it with the command-line options):
    reading a card in LOAD ........ 1 tick   (OS work)
    LR / SR / CR / BT ............. 1 tick   (user CPU work)
    GD / PD (READ / WRITE) ........ 5 ticks  (I/O work, CPU waits)
    H -> TERMINATE ................ 2 ticks  (OS work)

Usage:
    python3 mos_analytics.py -i input_Phase1.txt -o output.txt
    python3 mos_analytics.py -i input_Phase1.txt --arrival-gap 40   # jobs arrive as a stream
"""

import argparse
import csv
import sys

# ----------------------------------------------------------------------------
# VIRTUAL MACHINE  (notation from the guide)
# ----------------------------------------------------------------------------
M = [""] * 100          # main memory: 100 words of (up to) 4 characters
IR = ""                 # instruction register  (4 chars)
R = ""                  # general purpose register (4 chars)
C = False               # toggle
IC = 0                  # instruction counter
SI = 0                  # service interrupt: 1 = read, 2 = write, 3 = terminate
BUFFER = ""             # 40-character card / block buffer
m = 0                   # memory pointer used by LOAD

# ----------------------------------------------------------------------------
# OUR OWN VARIABLES  (lower case)
# ----------------------------------------------------------------------------
cost = {"card": 1, "cpu": 1, "io": 5, "term": 2}
arrival_gap = 0         # ticks between job arrivals (0 = whole batch arrives at t=0)
max_steps = 10000       # safety stop for runaway programs
live = True

clock = 0               # virtual clock (ticks)
events = []             # (start, end, job_seq, job_id, kind, detail)
jobs = []               # finished job records
job = None              # record of the job currently in the machine
job_count = 0
skipping = False        # True while LOAD skips the rest of an aborted job
infile = None
outfile = None

KINDS = ("LOAD", "EXEC", "READ", "WRITE", "TERM")


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
def operand(word):
    """Turn the 2 operand characters of an instruction into a number."""
    digits = word[2:4]
    return int(digits) if len(digits) == 2 and digits.isdigit() else 0


def read_card():
    """Read the next card (line) from the input file; None at end of file."""
    line = infile.readline()
    if line == "":
        return None
    return line.rstrip("\r\n")


def tick(kind, ticks, detail=""):
    """Advance the virtual clock and log the event for the analytics."""
    global clock
    start = clock
    clock += ticks
    seq = job["seq"] if job else 0
    jid = job["id"] if job else "----"
    events.append((start, clock, seq, jid, kind, detail))
    if job is not None and kind in job["ticks"]:
        job["ticks"][kind] += ticks


# ----------------------------------------------------------------------------
# job bookkeeping (the analytics part)
# ----------------------------------------------------------------------------
def begin_job(card):
    global job, job_count, m, skipping
    if job is not None:                       # previous job never saw its $END
        end_job("INCOMPLETE (no $END)")
    INIT()
    m = 0
    skipping = False
    arrival = job_count * arrival_gap
    if clock < arrival:                       # CPU sits idle until the job arrives
        tick("IDLE", arrival - clock, "waiting for next job to arrive")
    job_count += 1
    job = {
        "seq": job_count, "id": card[4:8],
        "decl_instr": card[8:12], "decl_pd": card[12:16],
        "static_instr": 0, "static_pd": 0,
        "arrival": arrival, "start": clock, "end": None,
        "R": 0, "W": 0, "E": 0, "instr": 0,
        "ticks": {k: 0 for k in KINDS},
        "status": "OK", "aborted": False,
    }


def note_static():
    """At $DTA: count the instructions that were actually loaded."""
    words = [w for w in M[:m] if w]
    job["static_instr"] = len(words)
    job["static_pd"] = sum(1 for w in words if w[:2] == "PD")


def end_job(status=None):
    global job
    if job is None:
        return
    if status and job["status"] == "OK":
        job["status"] = status
    job["end"] = clock
    job["tat"] = job["end"] - job["arrival"]        # turnaround time
    job["wait"] = job["start"] - job["arrival"]     # time spent waiting
    job["service"] = job["end"] - job["start"]      # time inside the machine
    jobs.append(job)
    if live:
        print_live(job)
    job = None


def abort_job(reason):
    job["status"] = "ABORT: " + reason
    job["aborted"] = True
    sys.stderr.write("job %s aborted: %s\n" % (job["id"], reason))
    TERMINATE()


def print_live(j):
    """Streaming output: one analytics line the moment a job completes."""
    cpu = 100.0 * j["ticks"]["EXEC"] / j["service"] if j["service"] else 0.0
    print("[t=%5d] J%02d (%s) done | TAT=%4d wait=%4d svc=%4d | R=%d W=%d E=%-3d | CPU=%5.1f%% | %s"
          % (clock, j["seq"], j["id"], j["tat"], j["wait"], j["service"],
             j["R"], j["W"], j["E"], cpu, j["status"]))


# ----------------------------------------------------------------------------
# MAIN PROGRAM, INIT, LOAD
# ----------------------------------------------------------------------------
def INIT():
    global M, IR, R, C, IC, SI, BUFFER
    M = [""] * 100
    IR = ""
    R = ""
    C = False
    IC = 0
    SI = 0
    BUFFER = ""


def LOAD():
    global m, BUFFER, skipping
    m = 0
    while True:
        BUFFER = read_card()
        if BUFFER is None:                          # end of file
            break
        if BUFFER.strip() == "":
            continue
        tag = BUFFER[:4]
        if skipping and tag != "$END":
            continue
        if tag == "$AMJ":                           # new job begins
            begin_job(BUFFER)
            tick("LOAD", cost["card"], "$AMJ")
        elif tag == "$DTA":                         # program is loaded, run it
            tick("LOAD", cost["card"], "$DTA")
            note_static()
            START_EXECUTION()
        elif tag == "$END":                         # job is over
            tick("LOAD", cost["card"], "$END")
            skipping = False
            end_job()
        else:                                       # program card
            if m >= 100:
                abort_job("memory exceeded")
                skipping = True
            else:
                BUFFER = BUFFER[:40]
                for i in range(10):
                    M[m + i] = BUFFER[i * 4:(i + 1) * 4]
                tick("LOAD", cost["card"], "program card -> M[%02d..%02d]" % (m, m + 9))
                m += 10


def START_EXECUTION():
    global IC
    IC = 0
    EXECUTE_USER_PROGRAM()


# ----------------------------------------------------------------------------
# EXECUTE USER PROGRAM  (slave mode)
# ----------------------------------------------------------------------------
def EXECUTE_USER_PROGRAM():
    global IR, R, C, IC, SI
    steps = 0
    while True:
        IR = M[IC] if 0 <= IC < 100 else ""         # fetch
        IC = IC + 1
        steps += 1
        if steps > max_steps:
            abort_job("step limit exceeded (possible endless loop)")
            return
        job["instr"] += 1
        op = IR[:2]                                 # decode
        addr = operand(IR)

        if op == "LR":
            R = M[addr]
            job["E"] += 1
            tick("EXEC", cost["cpu"], IR)
        elif op == "SR":
            M[addr] = R
            job["E"] += 1
            tick("EXEC", cost["cpu"], IR)
        elif op == "CR":
            C = (R == M[addr])
            job["E"] += 1
            tick("EXEC", cost["cpu"], IR + (" (equal)" if C else " (not equal)"))
        elif op == "BT":
            if C:
                IC = addr
            job["E"] += 1
            tick("EXEC", cost["cpu"], IR + (" (jump)" if C else " (no jump)"))
        elif op == "GD":
            SI = 1
            MOS()
            if job["aborted"]:
                return
        elif op == "PD":
            SI = 2
            MOS()
        elif IR[:1] == "H":
            SI = 3
            MOS()
            return
        else:                                       # empty / unknown instruction
            job["status"] = "HALT-IMPLICIT (empty instruction at M[%02d])" % (IC - 1)
            SI = 3
            MOS()
            return


# ----------------------------------------------------------------------------
# MOS  (master mode)
# ----------------------------------------------------------------------------
def MOS():
    if SI == 1:
        READ()
    elif SI == 2:
        WRITE()
    elif SI == 3:
        TERMINATE()


def READ():                                         # for GD
    global IR, BUFFER
    IR = IR[:3] + "0"                               # IR[4] <- 0 (block base address)
    addr = operand(IR)
    BUFFER = read_card()
    tick("READ", cost["io"], "GD%02d -> M[%02d..%02d]" % (addr, addr, addr + 9))
    job["R"] += 1
    if BUFFER is None or BUFFER[:4] == "$END":      # out of data
        abort_job("out of data")
        return
    BUFFER = BUFFER[:40]
    for i in range(10):
        M[addr + i] = BUFFER[i * 4:(i + 1) * 4]


def WRITE():                                        # for PD
    global IR, BUFFER
    IR = IR[:3] + "0"
    addr = operand(IR)
    BUFFER = "".join(M[addr:addr + 10])
    outfile.write(BUFFER + "\n")
    tick("WRITE", cost["io"], "PD%02d <- M[%02d..%02d]" % (addr, addr, addr + 9))
    job["W"] += 1


def TERMINATE():                                    # for H
    outfile.write("\n\n")                           # 2 blank lines between job outputs
    tick("TERM", cost["term"], "H")


# ----------------------------------------------------------------------------
# REPORT
# ----------------------------------------------------------------------------
def pct(a, b):
    return 100.0 * a / b if b else 0.0


def gantt(width=80):
    """ASCII Gantt chart: one row per job + one 'whole system' row."""
    if clock == 0:
        return []
    ch_of = {"LOAD": "L", "EXEC": "E", "READ": "R", "WRITE": "W", "TERM": "T", "IDLE": "."}
    prio = "RWELT."
    bucket = max(1, -(-clock // width))
    ncols = -(-clock // bucket)
    rows = {}
    system = [dict() for _ in range(ncols)]
    for (s, e, seq, jid, kind, det) in events:
        row = rows.setdefault(seq, [dict() for _ in range(ncols)])
        ch = ch_of[kind]
        for t in range(s, e):
            b = t // bucket
            row[b][ch] = row[b].get(ch, 0) + 1
            system[b][ch] = system[b].get(ch, 0) + 1

    def render(cells):
        out = []
        for d in cells:
            if not d:
                out.append(" ")
            else:
                out.append(max(d.items(), key=lambda kv: (kv[1], -prio.index(kv[0])))[0])
        return "".join(out)

    ids = {j["seq"]: j["id"] for j in jobs}
    lines = []
    for seq in sorted(rows):
        label = "IDLE      " if seq == 0 else "J%02d %-5s " % (seq, ids.get(seq, "?"))
        lines.append("  " + label + "|" + render(rows[seq]) + "|")
    lines.append("  " + "SYSTEM    " + "|" + render(system) + "|")
    axis = [" "] * (ncols + 12)
    for c in range(0, ncols, 10):
        for i, chh in enumerate(str(c * bucket)):
            axis[c + i] = chh
    lines.append("  " + " " * 11 + "".join(axis).rstrip())
    lines.append("  (1 column = %d tick%s)   L=LOAD  E=execute  R=read(GD)  W=write(PD)  "
                 "T=terminate  .=idle" % (bucket, "" if bucket == 1 else "s"))
    return lines


def build_report():
    L = []
    n = len(jobs)
    total = clock
    tsum = {k: sum(j["ticks"][k] for j in jobs) for k in KINDS}
    idle = sum(e - s for (s, e, seq, jid, kind, det) in events if kind == "IDLE")
    io_ticks = tsum["READ"] + tsum["WRITE"]
    os_ticks = tsum["LOAD"] + tsum["TERM"]
    R_tot = sum(j["R"] for j in jobs)
    W_tot = sum(j["W"] for j in jobs)
    E_tot = sum(j["E"] for j in jobs)
    tats = [j["tat"] for j in jobs]

    L.append("=" * 100)
    L.append("MOS PHASE 1 - STREAM JOB ANALYTICS REPORT")
    L.append("=" * 100)
    L.append("Cost model (ticks): card read=%d  CPU instr=%d  I/O (GD/PD)=%d  terminate=%d  | arrival gap=%d"
             % (cost["card"], cost["cpu"], cost["io"], cost["term"], arrival_gap))
    L.append("")

    # ---- per job table
    L.append("1. PER-JOB METRICS")
    L.append("-" * 100)
    L.append("%3s %-5s %6s %6s %6s %6s %6s %6s %4s %4s %5s %7s  %s"
             % ("Seq", "JobID", "Arrive", "Start", "End", "Wait", "Svc", "TAT",
                "R", "W", "E", "CPU%", "Status"))
    for j in jobs:
        L.append("%3d %-5s %6d %6d %6d %6d %6d %6d %4d %4d %5d %6.1f%%  %s"
                 % (j["seq"], j["id"], j["arrival"], j["start"], j["end"], j["wait"],
                    j["service"], j["tat"], j["R"], j["W"], j["E"],
                    pct(j["ticks"]["EXEC"], j["service"]), j["status"]))
    if n:
        L.append("-" * 100)
        L.append("%3s %-5s %6s %6s %6s %6.1f %6.1f %6.1f %4d %4d %5d %6.1f%%"
                 % ("", "AVG", "", "", "", sum(j["wait"] for j in jobs) / n,
                    sum(j["service"] for j in jobs) / n, sum(tats) / n,
                    R_tot, W_tot, E_tot, pct(tsum["EXEC"], sum(j["service"] for j in jobs))))
        L.append("    (R/W/E columns in the AVG row are totals)")
    L.append("    TAT = End - Arrive | Wait = Start - Arrive | Svc = End - Start | CPU% = execute ticks / Svc")
    L.append("")

    # ---- system summary
    L.append("2. SYSTEM PERFORMANCE")
    L.append("-" * 100)
    L.append("Jobs completed ........... %d" % n)
    L.append("Total time (makespan) .... %d ticks" % total)
    if n:
        L.append("Turnaround time .......... avg %.1f | min %d | max %d" % (sum(tats) / n, min(tats), max(tats)))
        L.append("Waiting time ............. avg %.1f" % (sum(j["wait"] for j in jobs) / n))
        L.append("Throughput ............... %.2f jobs per 100 ticks" % (100.0 * n / total if total else 0))
    L.append("")
    L.append("Where did the time go?")
    for label, v in (("User CPU (execute LR/SR/CR/BT)", tsum["EXEC"]),
                     ("OS work (LOAD cards + TERMINATE)", os_ticks),
                     ("I/O  - read  (GD)", tsum["READ"]),
                     ("I/O  - write (PD)", tsum["WRITE"]),
                     ("Idle (waiting for arrivals)", idle)):
        L.append("  %-34s %6d ticks  %5.1f%%  %s" % (label, v, pct(v, total), "#" * int(pct(v, total) / 2.5)))
    L.append("")
    L.append("CPU utilization (user work only) ....... %5.1f%%" % pct(tsum["EXEC"], total))
    L.append("CPU utilization (user + OS work) ....... %5.1f%%" % pct(tsum["EXEC"] + os_ticks, total))
    L.append("CPU waiting on I/O ..................... %5.1f%%" % pct(io_ticks, total))
    L.append("")

    # ---- I/O operations
    L.append("3. OPERATION COUNTS (R / W / E)")
    L.append("-" * 100)
    all_ops = R_tot + W_tot + E_tot
    L.append("R  (reads  = GD) ........ %4d   (%.1f%% of ops)" % (R_tot, pct(R_tot, all_ops)))
    L.append("W  (writes = PD) ........ %4d   (%.1f%% of ops)" % (W_tot, pct(W_tot, all_ops)))
    L.append("E  (execute: LR/SR/CR/BT) %4d   (%.1f%% of ops)" % (E_tot, pct(E_tot, all_ops)))
    L.append("I/O operations (R + W) .. %4d   | avg per job %.1f | avg I/O cost %.1f ticks per op"
             % (R_tot + W_tot, (R_tot + W_tot) / n if n else 0,
                io_ticks / (R_tot + W_tot) if (R_tot + W_tot) else 0))
    L.append("Instructions fetched .... %4d   (R + W + E + one H per halted job)"
             % sum(j["instr"] for j in jobs))
    L.append("")

    # ---- timeline
    L.append("4. EXECUTION TIMELINE")
    L.append("-" * 100)
    L.extend(gantt())
    L.append("  Full tick-by-tick log: see the timeline CSV file.")
    L.append("")

    # ---- observations
    L.append("5. OBSERVATIONS")
    L.append("-" * 100)
    if n:
        worst = max(jobs, key=lambda j: j["tat"])
        heavy = max(jobs, key=lambda j: pct(j["ticks"]["READ"] + j["ticks"]["WRITE"], j["service"]))
        L.append("- Longest turnaround: J%02d (%s) with %d ticks (waited %d, ran %d)."
                 % (worst["seq"], worst["id"], worst["tat"], worst["wait"], worst["service"]))
        L.append("- Most I/O-bound job: J%02d (%s), %.1f%% of its time in I/O."
                 % (heavy["seq"], heavy["id"],
                    pct(heavy["ticks"]["READ"] + heavy["ticks"]["WRITE"], heavy["service"])))
        L.append("- Only one job is in memory at a time, so the CPU stalls during every GD/PD: "
                 "%.1f%% of all time is I/O wait vs %.1f%% user CPU." % (pct(io_ticks, total), pct(tsum["EXEC"], total)))
        seen = {}
        for j in jobs:
            seen.setdefault(j["id"], []).append(j["seq"])
        for jid, seqs in seen.items():
            if len(seqs) > 1:
                L.append("- Job ID %s appears %d times (J%s); metrics are tracked by sequence number."
                         % (jid, len(seqs), ", J".join("%02d" % s for s in seqs)))
        for j in jobs:
            if (j["decl_instr"] != "%04d" % j["static_instr"]) or (j["decl_pd"] != "%04d" % j["static_pd"]):
                L.append("- J%02d (%s): $AMJ header says %s instr / %s PD, loaded program has %d / %d."
                         % (j["seq"], j["id"], j["decl_instr"], j["decl_pd"], j["static_instr"], j["static_pd"]))
        for j in jobs:
            if j["status"] != "OK":
                L.append("- J%02d (%s) status: %s" % (j["seq"], j["id"], j["status"]))
    L.append("")
    return "\n".join(L)


def write_timeline(path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["start", "end", "duration", "job_seq", "job_id", "phase", "detail"])
        for (s, e, seq, jid, kind, det) in events:
            w.writerow([s, e, e - s, seq, jid, kind, det])


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    global infile, outfile, arrival_gap, live
    ap = argparse.ArgumentParser(description="MOS Phase 1 simulator with stream job analytics")
    ap.add_argument("-i", "--input", default="input_Phase1.txt")
    ap.add_argument("-o", "--output", default="output.txt")
    ap.add_argument("--report", default="analytics_report.txt")
    ap.add_argument("--timeline", default="timeline.csv")
    ap.add_argument("--card-cost", type=int, default=1, help="ticks to read a card in LOAD")
    ap.add_argument("--cpu-cost", type=int, default=1, help="ticks for LR/SR/CR/BT")
    ap.add_argument("--io-cost", type=int, default=5, help="ticks for GD/PD")
    ap.add_argument("--term-cost", type=int, default=2, help="ticks for H / TERMINATE")
    ap.add_argument("--arrival-gap", type=int, default=0,
                    help="ticks between job arrivals (0 = all jobs submitted at t=0)")
    ap.add_argument("--quiet", action="store_true", help="no live per-job lines")
    args = ap.parse_args()

    cost.update(card=args.card_cost, cpu=args.cpu_cost, io=args.io_cost, term=args.term_cost)
    arrival_gap = args.arrival_gap
    live = not args.quiet

    infile = open(args.input, "r", encoding="utf-8")
    outfile = open(args.output, "w", encoding="utf-8")
    INIT()
    if live:
        print("--- live job stream ---")
    LOAD()
    end_job("INCOMPLETE (no $END)")                 # only acts if a job is still open
    infile.close()
    outfile.close()

    report = build_report()
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(report)
    write_timeline(args.timeline)
    print()
    print(report)
    print("Files written: %s, %s, %s" % (args.output, args.report, args.timeline))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
MOS Phase 2  +  Stream Job Analytics
====================================
The Phase-2 MOS simulator (paging, TI/PI/SI interrupts, error messages) that also
*measures itself* while it runs - the Phase 2 twin of mos_analytics.py (Phase 1).
The output file it writes is identical to the one written by mos_phase2.py.

Measured per job and for the whole system:
  * turnaround / waiting / service time    (arrival -> completion)
  * CPU utilisation, I/O wait, OS work
  * R = reads (GD), W = writes (PD), E = executes (LR/SR/CR/BT)
  * NEW in Phase 2: page faults served, frames used, how each job ended (error)
  * execution timeline (tick by tick CSV + ASCII Gantt chart)

Time is a *virtual clock* (ticks), so results are repeatable.  Default cost model:
    reading a card in LOAD ........ 1 tick   (OS work)
    LR / SR / CR / BT ............. 1 tick   (user CPU work)
    GD / PD (READ / WRITE) ........ 5 ticks  (I/O work, CPU waits)
    serving a valid page fault .... 2 ticks  (OS work: ALLOCATE + page table update)
    TERMINATE (H or any error) .... 2 ticks  (OS work)

Naming style (as in the lecture): notation variables and main functions are UPPER case,
our own extra variables and helpers are lower case.

Usage
    python3 mos_phase2_analytics.py -i input_phase2.txt -o output_phase2.txt
    python3 mos_phase2_analytics.py --arrival-gap 40      # jobs arrive as a stream
    python3 mos_phase2_analytics.py --seed 7 --quiet
"""

import argparse
import csv
import random
import sys

# ----------------------------------------------------------------------------
# VIRTUAL MACHINE  (notation from the algorithm)
# ----------------------------------------------------------------------------
M = [""] * 300          # 300 words = 30 frames x 10 words
IR = ""
R = ""
C = False
IC = 0
SI = 0
TI = 0
PI = 0
PTR = 0
VA = 0
RA = 0
EM = 0
TTC = 0
LLC = 0
TTL = 0
TLL = 0
PCB = None              # [job id, TTL, TLL]
BUFFER = ""

MESSAGES = {
    0: " NO ERROR",
    1: " OUT OF DATA",
    2: " LINE LIMIT EXCEEDED",
    3: " TIME LIMIT EXCEEDED",
    4: " OPERATION CODE ERROR",
    5: " OPERAND ERROR",
    6: " INVALID PAGE FAULT",
    7: " TIME LIMIT EXCEEDED  And OPERATION CODE ERROR",
    8: " TIME LIMIT EXCEEDED And OPERAND ERROR",
}

# ----------------------------------------------------------------------------
# OUR OWN VARIABLES (lower case)
# ----------------------------------------------------------------------------
used_frames = set()
page_count = 0
job_done = False
end_seen = False
pending = None
infile = None
outfile = None

cost = {"card": 1, "cpu": 1, "io": 5, "term": 2, "fault": 2}
arrival_gap = 0
live = True

clock = 0               # virtual clock (ticks)
events = []             # (start, end, job_seq, job_id, kind, detail)
jobs = []               # finished job records
job = None              # record of the job currently in the machine
job_count = 0

KINDS = ("LOAD", "EXEC", "READ", "WRITE", "FAULT", "TERM")


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
def read_card():
    global pending
    if pending is not None:
        card, pending = pending, None
        return card
    line = infile.readline()
    if line == "":
        return None
    return line.rstrip("\r\n")


def push_back(card):
    global pending
    pending = card


def to_number(text):
    return int(text) if text.isdigit() else 0


def split_words(card):
    card = card[:40]
    return [card[i:i + 4] for i in range(0, len(card), 4)]


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
    global job, job_count
    if job is not None:                       # previous job never reached its $END
        end_job("INCOMPLETE (no $END)")
    arrival = job_count * arrival_gap
    if clock < arrival:                       # CPU sits idle until the job arrives
        tick("IDLE", arrival - clock, "waiting for next job to arrive")
    job_count += 1
    job = {
        "seq": job_count, "id": card[4:8],
        "ttl": to_number(card[8:12]), "tll": to_number(card[12:16]),
        "static_instr": 0, "static_pd": 0,
        "arrival": arrival, "start": clock, "end": None,
        "R": 0, "W": 0, "E": 0, "instr": 0, "pf": 0,
        "pages": 0, "frames": 0, "em": None,
        "ttc": 0, "llc": 0,
        "ticks": {k: 0 for k in KINDS},
        "status": "OK",
    }


def note_static():
    """At $DTA: count the instructions that were actually loaded."""
    words = []
    for p in range(page_count):
        frame = pt_get(p)
        words += [w for w in M[frame * 10:frame * 10 + 10] if w]
    job["static_instr"] = len(words)
    job["static_pd"] = sum(1 for w in words if w[:2] == "PD")
    job["pages"] = page_count


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


def print_live(j):
    cpu = 100.0 * j["ticks"]["EXEC"] / j["service"] if j["service"] else 0.0
    print("[t=%5d] J%02d (%s) done | TAT=%4d wait=%4d svc=%4d | R=%d W=%d E=%-3d PF=%d | CPU=%5.1f%% | %s"
          % (clock, j["seq"], j["id"], j["tat"], j["wait"], j["service"],
             j["R"], j["W"], j["E"], j["pf"], cpu, j["status"]))


# ----------------------------------------------------------------------------
# INIT / ALLOCATE / page table
# ----------------------------------------------------------------------------
def INIT():
    global M, IR, R, C, IC, SI, TI, PI, PTR, VA, RA, EM, TTC, LLC, BUFFER
    M = [""] * 300
    IR = R = BUFFER = ""
    C = False
    IC = SI = TI = PI = PTR = VA = RA = EM = TTC = LLC = 0
    used_frames.clear()


def ALLOCATE():
    free = [f for f in range(30) if f not in used_frames]
    if not free:
        raise RuntimeError("main memory is full")
    frame = random.choice(free)
    used_frames.add(frame)
    return frame


def pt_init():
    for i in range(10):
        M[PTR + i] = "0 **"


def pt_set(page, frame):
    M[PTR + page] = "1 %02d" % frame


def pt_get(page):
    word = M[PTR + page]
    if word[0] != "1":
        return None
    return int(word[2:4])


# ----------------------------------------------------------------------------
# LOAD
# ----------------------------------------------------------------------------
def LOAD():
    global PCB, PTR, TTC, LLC, TTL, TLL, page_count, job_done, end_seen
    while True:
        card = read_card()
        if card is None:
            break
        if card.strip() == "":
            continue
        if card.startswith("$AMJ"):                      # a new job begins
            begin_job(card)
            INIT()
            PCB = [card[4:8], to_number(card[8:12]), to_number(card[12:16])]
            TTL, TLL = PCB[1], PCB[2]
            TTC = LLC = 0
            page_count = 0
            job_done = end_seen = False
            PTR = ALLOCATE() * 10
            pt_init()
            tick("LOAD", cost["card"], "$AMJ  page table -> frame %d" % (PTR // 10))
        elif card.startswith("$DTA"):
            if PCB is None:
                continue
            tick("LOAD", cost["card"], "$DTA")
            note_static()
            START_EXECUTION()
            skip_rest_of_job()
            end_job()
            PCB = None
        elif card.startswith("$END"):
            if PCB is not None:
                tick("LOAD", cost["card"], "$END")
                end_job()
            PCB = None
        else:                                            # a PROGRAM card
            if PCB is None:
                continue
            if page_count >= 10:
                sys.stderr.write("job %s: too many program cards, card ignored\n" % PCB[0])
                continue
            frame = ALLOCATE()
            pt_set(page_count, frame)
            for i, word in enumerate(split_words(card)):
                M[frame * 10 + i] = word
            tick("LOAD", cost["card"], "program card -> page %d, frame %d (M[%03d..%03d])"
                 % (page_count, frame, frame * 10, frame * 10 + 9))
            page_count += 1


def skip_rest_of_job():
    """Unread data cards (and the $END) are still read by the card reader."""
    if end_seen:
        return
    while True:
        card = read_card()
        if card is None:
            return
        if card.startswith("$END"):
            tick("LOAD", cost["card"], "$END")
            return
        if card.startswith("$AMJ"):
            push_back(card)
            return
        tick("LOAD", cost["card"], "skip unused card")


def START_EXECUTION():
    global IC, TI
    IC = 0
    TI = 2 if TTC >= TTL else 0
    EXECUTE_USER_PROGRAM()


# ----------------------------------------------------------------------------
# ADDRESS MAP
# ----------------------------------------------------------------------------
def ADDRESS_MAP(arg):
    global PI, VA
    if isinstance(arg, str):
        if len(arg) != 2 or not all(ch in "0123456789" for ch in arg):
            PI = 2
            return None
        arg = int(arg)
    VA = arg
    if VA < 0 or VA > 99:
        PI = 3
        return None
    frame = pt_get(VA // 10)
    if frame is None:
        PI = 3
        return None
    return frame * 10 + VA % 10


# ----------------------------------------------------------------------------
# EXECUTE USER PROGRAM  (slave mode)
# ----------------------------------------------------------------------------
def EXECUTE_USER_PROGRAM():
    global IR, IC, R, C, SI, PI, RA
    while not job_done:
        SI = PI = 0
        fetch_ra = ADDRESS_MAP(IC)
        if PI != 0:
            IR = ""
            TERMINATE(6)
            return
        IR = M[fetch_ra]
        IC = IC + 1
        job["instr"] += 1

        op = IR[:2]
        if IR.rstrip() == "H":
            SI = 3
        elif op in ("GD", "PD", "LR", "SR", "CR", "BT"):
            RA = ADDRESS_MAP(IR[2:4])
            if PI == 0 and op in ("GD", "PD") and VA % 10 != 0:
                PI = 2
            if PI == 0 and op == "GD":
                SI = 1
            elif PI == 0 and op == "PD":
                SI = 2
        else:
            PI = 1

        if SI == 0 and PI == 0 and TI == 0:
            if op == "LR":
                R = M[RA]
                tick("EXEC", cost["cpu"], IR)
            elif op == "SR":
                M[RA] = R
                tick("EXEC", cost["cpu"], IR)
            elif op == "CR":
                C = (R == M[RA])
                tick("EXEC", cost["cpu"], IR + (" (equal)" if C else " (not equal)"))
            elif op == "BT":
                if C:
                    IC = VA
                tick("EXEC", cost["cpu"], IR + (" (jump)" if C else " (no jump)"))
            job["E"] += 1
            SIMULATION()
            continue
        MOS()


def SIMULATION():
    global TTC, TI
    TTC = TTC + 1
    if TTC >= TTL:
        TI = 2


# ----------------------------------------------------------------------------
# MOS  (master mode)
# ----------------------------------------------------------------------------
def MOS():
    global IC
    ti = TI
    if SI == 1:
        READ() if ti == 0 else TERMINATE(3)
    elif SI == 2:
        SIMULATION()
        WRITE()
        if ti == 2 and not job_done:
            TERMINATE(3)
    elif SI == 3:
        SIMULATION()
        TERMINATE(0)
    elif PI == 1:
        TERMINATE(4) if ti == 0 else TERMINATE(3, 4)
    elif PI == 2:
        TERMINATE(5) if ti == 0 else TERMINATE(3, 5)
    elif PI == 3:
        if ti == 2:
            TERMINATE(3)
        elif IR[:2] in ("GD", "SR"):                     # valid page fault
            frame = ALLOCATE()
            pt_set(VA // 10, frame)
            IC = IC - 1
            job["pf"] += 1
            tick("FAULT", cost["fault"], "%s page %d -> frame %d" % (IR[:2], VA // 10, frame))
        else:
            TERMINATE(6)
    elif ti == 2:
        TERMINATE(3)


def READ():
    global BUFFER, end_seen
    card = read_card()
    tick("READ", cost["io"], "GD%02d -> M[%03d..%03d]" % (VA, RA, RA + 9))
    job["R"] += 1
    if card is None or card.startswith("$"):
        if card is not None and card.startswith("$END"):
            end_seen = True
        elif card is not None:
            push_back(card)
        TERMINATE(1)
        return
    BUFFER = card[:40]
    for i in range(10):
        M[RA + i] = ""
    for i, word in enumerate(split_words(BUFFER)):
        M[RA + i] = word
    SIMULATION()


def WRITE():
    global LLC
    if LLC >= TLL:
        TERMINATE(2)
        return
    LLC = LLC + 1
    outfile.write("".join(M[RA:RA + 10]) + "\n")
    tick("WRITE", cost["io"], "PD%02d <- M[%03d..%03d]" % (VA, RA, RA + 9))
    job["W"] += 1


def TERMINATE(*errors):
    global EM, job_done
    EM = sum(errors)
    try:
        job_id = str(int(PCB[0]))
    except (TypeError, ValueError):
        job_id = PCB[0] if PCB else "?"
    outfile.write("%-9s:  %s\n" % ("JOB ID", job_id))
    outfile.write(MESSAGES[EM] + "\n")
    outfile.write("%-9s:  %d\n" % ("IC", IC))
    outfile.write("%-9s:  %s\n" % ("IR", IR.rstrip()))
    outfile.write("%-9s:  %d\n" % ("TTC", TTC))
    outfile.write("%-9s:  %d\n" % ("LLC", LLC))
    outfile.write("\n\n")
    tick("TERM", cost["term"], "EM=%d %s" % (EM, MESSAGES[EM].strip()))
    # remember how the job ended (for the analytics)
    job["em"], job["ttc"], job["llc"] = EM, TTC, LLC
    job["frames"] = len(used_frames)
    job["status"] = "OK" if EM == 0 else " ".join(MESSAGES[EM].split())
    job_done = True


# ----------------------------------------------------------------------------
# REPORT
# ----------------------------------------------------------------------------
def pct(a, b):
    return 100.0 * a / b if b else 0.0


def gantt(width=80):
    """ASCII Gantt chart: one row per job + one 'whole system' row."""
    if clock == 0:
        return []
    ch_of = {"LOAD": "L", "EXEC": "E", "READ": "R", "WRITE": "W", "FAULT": "F", "TERM": "T", "IDLE": "."}
    prio = "RWEFLT."
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
    lines.append("  (1 column = %d tick%s)   L=LOAD  E=execute  R=read(GD)  W=write(PD)  F=page fault  "
                 "T=terminate  .=idle" % (bucket, "" if bucket == 1 else "s"))
    return lines


def build_report():
    L = []
    n = len(jobs)
    total = clock
    tsum = {k: sum(j["ticks"][k] for j in jobs) for k in KINDS}
    idle = sum(e - s for (s, e, seq, jid, kind, det) in events if kind == "IDLE")
    io_ticks = tsum["READ"] + tsum["WRITE"]
    os_ticks = tsum["LOAD"] + tsum["TERM"] + tsum["FAULT"]
    R_tot = sum(j["R"] for j in jobs)
    W_tot = sum(j["W"] for j in jobs)
    E_tot = sum(j["E"] for j in jobs)
    PF_tot = sum(j["pf"] for j in jobs)
    tats = [j["tat"] for j in jobs]
    svc_sum = sum(j["service"] for j in jobs)

    L.append("=" * 110)
    L.append("MOS PHASE 2 - STREAM JOB ANALYTICS REPORT")
    L.append("=" * 110)
    L.append("Cost model (ticks): card read=%d  CPU instr=%d  I/O (GD/PD)=%d  page fault=%d  terminate=%d  | arrival gap=%d"
             % (cost["card"], cost["cpu"], cost["io"], cost["fault"], cost["term"], arrival_gap))
    L.append("")

    # ---- per job table
    L.append("1. PER-JOB METRICS")
    L.append("-" * 110)
    L.append("%3s %-5s %6s %6s %6s %6s %6s %6s %3s %3s %4s %3s %7s  %s"
             % ("Seq", "JobID", "Arrive", "Start", "End", "Wait", "Svc", "TAT",
                "R", "W", "E", "PF", "CPU%", "How the job ended"))
    for j in jobs:
        L.append("%3d %-5s %6d %6d %6d %6d %6d %6d %3d %3d %4d %3d %6.1f%%  %s"
                 % (j["seq"], j["id"], j["arrival"], j["start"], j["end"], j["wait"],
                    j["service"], j["tat"], j["R"], j["W"], j["E"], j["pf"],
                    pct(j["ticks"]["EXEC"], j["service"]), j["status"]))
    if n:
        L.append("-" * 110)
        L.append("%3s %-5s %6s %6s %6s %6.1f %6.1f %6.1f %3d %3d %4d %3d %6.1f%%"
                 % ("", "AVG", "", "", "", sum(j["wait"] for j in jobs) / n,
                    svc_sum / n, sum(tats) / n, R_tot, W_tot, E_tot, PF_tot,
                    pct(tsum["EXEC"], svc_sum)))
        L.append("    (R/W/E/PF columns in the AVG row are totals)")
    L.append("    TAT = End - Arrive | Wait = Start - Arrive | Svc = End - Start | CPU% = execute ticks / Svc")
    L.append("    PF = valid page faults served (GD/SR touching a page for the first time)")
    L.append("")

    # ---- system summary
    L.append("2. SYSTEM PERFORMANCE")
    L.append("-" * 110)
    L.append("Jobs completed ........... %d" % n)
    L.append("Total time (makespan) .... %d ticks" % total)
    if n:
        L.append("Turnaround time .......... avg %.1f | min %d | max %d" % (sum(tats) / n, min(tats), max(tats)))
        L.append("Waiting time ............. avg %.1f" % (sum(j["wait"] for j in jobs) / n))
        L.append("Throughput ............... %.2f jobs per 100 ticks" % (100.0 * n / total if total else 0))
    L.append("")
    L.append("Where did the time go?")
    for label, v in (("User CPU (execute LR/SR/CR/BT)", tsum["EXEC"]),
                     ("OS work (LOAD cards + TERMINATE)", tsum["LOAD"] + tsum["TERM"]),
                     ("OS work (page-fault service)", tsum["FAULT"]),
                     ("I/O  - read  (GD)", tsum["READ"]),
                     ("I/O  - write (PD)", tsum["WRITE"]),
                     ("Idle (waiting for arrivals)", idle)):
        L.append("  %-34s %6d ticks  %5.1f%%  %s" % (label, v, pct(v, total), "#" * int(pct(v, total) / 2.5)))
    L.append("")
    L.append("CPU utilization (user work only) ....... %5.1f%%" % pct(tsum["EXEC"], total))
    L.append("CPU utilization (user + OS work) ....... %5.1f%%" % pct(tsum["EXEC"] + os_ticks, total))
    L.append("CPU waiting on I/O ..................... %5.1f%%" % pct(io_ticks, total))
    L.append("")

    # ---- operation counts
    L.append("3. OPERATION COUNTS (R / W / E)")
    L.append("-" * 110)
    all_ops = R_tot + W_tot + E_tot
    L.append("R  (reads  = GD) ........ %4d   (%.1f%% of ops)" % (R_tot, pct(R_tot, all_ops)))
    L.append("W  (writes = PD) ........ %4d   (%.1f%% of ops)" % (W_tot, pct(W_tot, all_ops)))
    L.append("E  (execute: LR/SR/CR/BT) %4d   (%.1f%% of ops)" % (E_tot, pct(E_tot, all_ops)))
    L.append("I/O operations (R + W) .. %4d   | avg per job %.1f | avg I/O cost %.1f ticks per op"
             % (R_tot + W_tot, (R_tot + W_tot) / n if n else 0,
                io_ticks / (R_tot + W_tot) if (R_tot + W_tot) else 0))
    L.append("Instructions fetched .... %4d   (includes the re-fetch after each valid page fault)"
             % sum(j["instr"] for j in jobs))
    L.append("")

    # ---- paging and errors (new in phase 2)
    L.append("4. PAGING AND ERROR STATISTICS (new in Phase 2)")
    L.append("-" * 110)
    L.append("%3s %-5s %7s %7s %7s %7s %6s %6s  %s"
             % ("Seq", "JobID", "ProgPg", "DataPg", "Frames", "Mem%", "TTC", "LLC", "Limits (TTL / TLL) and program size"))
    for j in jobs:
        data_pg = max(0, j["frames"] - 1 - j["pages"])
        L.append("%3d %-5s %7d %7d %7d %6.1f%% %6d %6d  TTL=%d TLL=%d | program: %d instr, %d PD"
                 % (j["seq"], j["id"], j["pages"], data_pg, j["frames"], pct(j["frames"], 30),
                    j["ttc"], j["llc"], j["ttl"], j["tll"], j["static_instr"], j["static_pd"]))
    L.append("    Frames = 1 page table + program pages + data pages;  Mem% = share of the 30 frames used")
    L.append("")
    L.append("How the %d jobs ended:" % n)
    by_em = {}
    for j in jobs:
        by_em.setdefault(j["em"], []).append(j)
    for em in sorted(k for k in by_em if k is not None):
        names = ", ".join("J%02d" % j["seq"] for j in by_em[em])
        L.append("  EM %d  %-46s %2d job(s)  %s" % (em, " ".join(MESSAGES[em].split()), len(by_em[em]), names))
    if None in by_em:
        L.append("  --   %-46s %2d job(s)" % ("did not terminate normally", len(by_em[None])))
    ok = len(by_em.get(0, []))
    L.append("  Success rate: %d of %d jobs ended with NO ERROR (%.1f%%)" % (ok, n, pct(ok, n)))
    L.append("  Page faults: %d valid (served by the OS), %d invalid (job terminated with EM 6)"
             % (PF_tot, len(by_em.get(6, []))))
    L.append("")

    # ---- timeline
    L.append("5. EXECUTION TIMELINE")
    L.append("-" * 110)
    L.extend(gantt())
    L.append("  Full tick-by-tick log: see the timeline CSV file.")
    L.append("")

    # ---- observations
    L.append("6. OBSERVATIONS")
    L.append("-" * 110)
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
        L.append("- Paging cost: %d valid page faults used %d ticks (%.1f%% of all time)."
                 % (PF_tot, tsum["FAULT"], pct(tsum["FAULT"], total)))
        seen = {}
        for j in jobs:
            seen.setdefault(j["id"], []).append(j["seq"])
        for jid, seqs in seen.items():
            if len(seqs) > 1:
                L.append("- Job ID %s appears %d times (J%s); metrics are tracked by sequence number."
                         % (jid, len(seqs), ", J".join("%02d" % s for s in seqs)))
        for j in jobs:
            if j["status"] != "OK":
                L.append("- J%02d (%s) ended with: %s  [TTC=%d of TTL=%d, LLC=%d of TLL=%d]"
                         % (j["seq"], j["id"], j["status"], j["ttc"], j["ttl"], j["llc"], j["tll"]))
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
    ap = argparse.ArgumentParser(description="MOS Phase 2 simulator with stream job analytics")
    ap.add_argument("-i", "--input", default="input_phase2.txt")
    ap.add_argument("-o", "--output", default="output_phase2.txt")
    ap.add_argument("--report", default="analytics_report_phase2.txt")
    ap.add_argument("--timeline", default="timeline_phase2.csv")
    ap.add_argument("--card-cost", type=int, default=1, help="ticks to read a card in LOAD")
    ap.add_argument("--cpu-cost", type=int, default=1, help="ticks for LR/SR/CR/BT")
    ap.add_argument("--io-cost", type=int, default=5, help="ticks for GD/PD")
    ap.add_argument("--fault-cost", type=int, default=2, help="ticks to serve a valid page fault")
    ap.add_argument("--term-cost", type=int, default=2, help="ticks for TERMINATE")
    ap.add_argument("--arrival-gap", type=int, default=0,
                    help="ticks between job arrivals (0 = all jobs submitted at t=0)")
    ap.add_argument("--seed", type=int, default=None, help="seed for the random frame generator")
    ap.add_argument("--quiet", action="store_true", help="no live per-job lines")
    args = ap.parse_args()

    cost.update(card=args.card_cost, cpu=args.cpu_cost, io=args.io_cost,
                fault=args.fault_cost, term=args.term_cost)
    arrival_gap = args.arrival_gap
    live = not args.quiet
    if args.seed is not None:
        random.seed(args.seed)

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

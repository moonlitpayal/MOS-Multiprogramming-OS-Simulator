#!/usr/bin/env python3
"""
MOS PHASE 2  -  Multiprogramming Operating System simulator (built on Phase 1)
==============================================================================
What is new compared with Phase 1
  * Jobs may contain errors  -> out of data, line limit, time limit,
                                opcode error, operand error, page fault
  * Paging                   -> 300 words of memory = 30 frames of 10 words.
                                Every job gets a PAGE TABLE; its program cards and
                                data blocks are stored in RANDOM frames.
  * New interrupts           -> TI (timer) and PI (program), besides SI (service)
  * Termination message     -> every job ends with a 6-line report (job id, error,
                                IC, IR, TTC, LLC) followed by two blank lines.

Naming style (as in the lecture): notation variables and the main functions are
UPPER case (M, IR, R, C, IC, SI, TI, PI, PTR, PCB, VA, RA, TTC, LLC, TTL, TLL, EM,
LOAD, ALLOCATE, START_EXECUTION, EXECUTE_USER_PROGRAM, ADDRESS_MAP, SIMULATION,
MOS, READ, WRITE, TERMINATE).  Our own extra variables / helpers are lower case.

Usage
    python3 mos_phase2.py -i input_phase2.txt -o output_phase2.txt
    python3 mos_phase2.py -i input_phase2.txt -o out.txt --seed 7      # repeatable frames
    python3 mos_phase2.py -i input_phase2.txt -o out.txt --trace       # show every instruction
    python3 mos_phase2.py -i input_phase2.txt -o out.txt --dump        # show page table at the end of each job
(--trace and --dump print to the screen (stderr); the output file stays clean.)
"""

import argparse
import random
import sys

# ----------------------------------------------------------------------------
# VIRTUAL MACHINE  (notation from the algorithm)
# ----------------------------------------------------------------------------
M = [""] * 300      # main memory: 300 words (30 frames x 10 words). A word = up to 4 chars
IR = ""             # instruction register (4 chars): IR[0:2] = opcode, IR[2:4] = operand
R = ""              # general purpose register (one word)
C = False           # toggle (set by CR, read by BT)
IC = 0              # instruction counter (a VIRTUAL address 0..99)
SI = 0              # service interrupt : 1 = GD, 2 = PD, 3 = H
TI = 0              # timer interrupt   : 2 = time limit exceeded
PI = 0              # program interrupt : 1 = opcode error, 2 = operand error, 3 = page fault
PTR = 0             # page table register: real address of the job's page table
VA = 0              # virtual address  (0..99)
RA = 0              # real address     (0..299)
EM = 0              # error message number (see MESSAGES)
TTC = 0             # total time counter  (instructions executed so far)
LLC = 0             # line limit counter  (lines printed so far)
TTL = 0             # total time limit    (from the $AMJ card)
TLL = 0             # total line limit    (from the $AMJ card)
PCB = None          # process control block: [job id, TTL, TLL]
BUFFER = ""         # 40-character card buffer

# error messages printed at termination (EM -> text). EM 7 = 3+4, EM 8 = 3+5
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
used_frames = set()     # frames already given out to the current job
page_count = 0          # how many program pages the current job has loaded
job_done = False        # True once TERMINATE has been called for the current job
end_seen = False        # True if READ already consumed the job's $END card
pending = None          # one card "pushed back" so LOAD can read it again
infile = None
outfile = None
trace = False
dump = False


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
def read_card():
    """Next card (line) of the input file, or None at end of file."""
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
    """'0025' -> 25  (0 if the text is not a number)."""
    return int(text) if text.isdigit() else 0


def split_words(card):
    """Cut a card (max 40 chars) into words of 4 characters (the last may be shorter)."""
    card = card[:40]
    return [card[i:i + 4] for i in range(0, len(card), 4)]


def log(text):
    if trace:
        sys.stderr.write(text + "\n")


# ----------------------------------------------------------------------------
# INIT / ALLOCATE / page table helpers
# ----------------------------------------------------------------------------
def INIT():
    """Clear memory, registers, counters and interrupts (called for every new job)."""
    global M, IR, R, C, IC, SI, TI, PI, PTR, VA, RA, EM, TTC, LLC, BUFFER
    M = [""] * 300
    IR = R = BUFFER = ""
    C = False
    IC = SI = TI = PI = PTR = VA = RA = EM = TTC = LLC = 0
    used_frames.clear()


def ALLOCATE():
    """Return a RANDOM free frame number (0..29) and mark it as used."""
    free = [f for f in range(30) if f not in used_frames]
    if not free:
        raise RuntimeError("main memory is full")
    frame = random.choice(free)
    used_frames.add(frame)
    return frame


def pt_init():
    """Every entry of a new page table = 'not allocated yet'  ('0 **')."""
    for i in range(10):
        M[PTR + i] = "0 **"


def pt_set(page, frame):
    """Entry layout: char 0 = valid bit, chars 2-3 = frame number  ->  '1 17'."""
    M[PTR + page] = "1 %02d" % frame


def pt_get(page):
    """Frame number of a page, or None if the page has no frame yet."""
    word = M[PTR + page]
    if word[0] != "1":
        return None
    return int(word[2:4])        # frame = tens digit * 10 + units digit


# ----------------------------------------------------------------------------
# LOAD  -  reads the cards, builds the page table, stores program cards
# ----------------------------------------------------------------------------
def LOAD():
    global PCB, PTR, TTC, LLC, TTL, TLL, page_count, job_done, end_seen
    while True:
        card = read_card()
        if card is None:                                 # end of file
            break
        if card.startswith("$AMJ"):                      # control card: a new job begins
            INIT()
            PCB = [card[4:8], to_number(card[8:12]), to_number(card[12:16])]
            TTL, TLL = PCB[1], PCB[2]
            TTC = LLC = 0
            page_count = 0
            job_done = end_seen = False
            PTR = ALLOCATE() * 10                        # frame for the page table
            pt_init()
        elif card.startswith("$DTA"):                    # program is loaded: run it
            if PCB is None:
                continue
            START_EXECUTION()
            skip_rest_of_job()                           # ignore unused data cards up to $END
            PCB = None
        elif card.startswith("$END"):                    # job over
            PCB = None
        else:                                            # a PROGRAM card
            if PCB is None:
                continue
            if page_count >= 10:
                sys.stderr.write("job %s: too many program cards, card ignored\n" % PCB[0])
                continue
            frame = ALLOCATE()                           # frame for this program page
            pt_set(page_count, frame)                    # update the page table
            for i, word in enumerate(split_words(card)):
                M[frame * 10 + i] = word                 # load the page in its frame
            page_count += 1


def skip_rest_of_job():
    """After TERMINATE the rest of the job's cards must not be run: skip to $END."""
    if end_seen:
        return
    while True:
        card = read_card()
        if card is None or card.startswith("$END"):
            return
        if card.startswith("$AMJ"):                      # job without $END: do not lose next job
            push_back(card)
            return


def START_EXECUTION():
    global IC, TI
    IC = 0
    TI = 2 if TTC >= TTL else 0                          # (only matters when TTL = 0)
    EXECUTE_USER_PROGRAM()


# ----------------------------------------------------------------------------
# ADDRESS MAP  (virtual address -> real address)
# ----------------------------------------------------------------------------
def ADDRESS_MAP(arg):
    """
    arg is either the IC (an int) or the operand characters of IR (a 2-char string).
    Returns the real address, or None after setting PI:
        PI = 2  operand is not a 2-digit number
        PI = 3  the page has no frame yet (page fault)
    """
    global PI, VA
    if isinstance(arg, str):
        if len(arg) != 2 or not all(ch in "0123456789" for ch in arg):
            PI = 2
            return None
        arg = int(arg)
    VA = arg
    if VA < 0 or VA > 99:                                # can only happen for IC running off the end
        PI = 3
        return None
    frame = pt_get(VA // 10)                             # page number = VA / 10
    if frame is None:
        PI = 3
        return None
    return frame * 10 + VA % 10                          # RA = frame * 10 + offset


# ----------------------------------------------------------------------------
# EXECUTE USER PROGRAM  (slave mode)
# ----------------------------------------------------------------------------
def EXECUTE_USER_PROGRAM():
    global IR, IC, R, C, SI, PI, RA
    while not job_done:
        SI = PI = 0

        # ---- FETCH -------------------------------------------------------
        fetch_ra = ADDRESS_MAP(IC)
        if PI != 0:                                      # instruction page is missing
            IR = ""
            TERMINATE(6)
            return
        IR = M[fetch_ra]
        IC = IC + 1

        # ---- DECODE (find out what this instruction needs) ----------------
        op = IR[:2]
        if IR.rstrip() == "H":                           # H has no operand
            SI = 3
        elif op in ("GD", "PD", "LR", "SR", "CR", "BT"):
            RA = ADDRESS_MAP(IR[2:4])                    # may set PI = 2 or PI = 3
            if PI == 0 and op in ("GD", "PD") and VA % 10 != 0:
                PI = 2                                   # GD / PD work on a whole block
            if PI == 0 and op == "GD":
                SI = 1
            elif PI == 0 and op == "PD":
                SI = 2
        else:
            PI = 1                                       # unknown opcode

        log("IC=%02d IR=%-4s SI=%d PI=%d TI=%d TTC=%d LLC=%d RA=%s"
            % (IC - 1, IR, SI, PI, TI, TTC, LLC, RA if PI == 0 else "-"))

        # ---- EXECUTE -------------------------------------------------------
        if SI == 0 and PI == 0 and TI == 0:              # LR / SR / CR / BT done by the CPU
            if op == "LR":
                R = M[RA]
            elif op == "SR":
                M[RA] = R
            elif op == "CR":
                C = (R == M[RA])
            elif op == "BT":
                if C:
                    IC = VA
            SIMULATION()
            continue
        MOS()                                            # some interrupt is pending: master mode


def SIMULATION():
    """Called after an instruction completes: count it, and arm TI when time is used up."""
    global TTC, TI
    TTC = TTC + 1
    if TTC >= TTL:
        TI = 2                                           # the NEXT instruction exceeds the limit


# ----------------------------------------------------------------------------
# MOS  (master mode)
# ----------------------------------------------------------------------------
def MOS():
    global IC
    ti = TI                                              # time status when this instruction started

    if SI == 1:                                          # GD
        if ti == 0:
            READ()
        else:
            TERMINATE(3)
    elif SI == 2:                                        # PD
        SIMULATION()
        WRITE()
        if ti == 2 and not job_done:                     # WRITE, THEN TERMINATE(3)
            TERMINATE(3)
    elif SI == 3:                                        # H
        SIMULATION()
        TERMINATE(0)
    elif PI == 1:                                        # opcode error
        TERMINATE(4) if ti == 0 else TERMINATE(3, 4)
    elif PI == 2:                                        # operand error
        TERMINATE(5) if ti == 0 else TERMINATE(3, 5)
    elif PI == 3:                                        # page fault
        if ti == 2:
            TERMINATE(3)
        elif IR[:2] in ("GD", "SR"):                     # VALID page fault: give the page a frame
            pt_set(VA // 10, ALLOCATE())
            IC = IC - 1                                  # run the same instruction again
        else:                                            # LR, CR, BT, PD: INVALID page fault
            TERMINATE(6)
    elif ti == 2:                                        # nothing but TI
        TERMINATE(3)


def READ():
    """GD: read the next data card into M[RA .. RA+9]."""
    global BUFFER, end_seen
    card = read_card()
    if card is None or card.startswith("$"):             # no data card left
        if card is not None and card.startswith("$END"):
            end_seen = True                              # we consumed the job's $END
        elif card is not None:
            push_back(card)                              # $AMJ / $DTA: leave it for LOAD
        TERMINATE(1)                                     # OUT OF DATA (GD is NOT counted)
        return
    BUFFER = card[:40]
    for i in range(10):                                  # clear the block, then fill it
        M[RA + i] = ""
    for i, word in enumerate(split_words(BUFFER)):
        M[RA + i] = word
    SIMULATION()                                         # GD finished: count it


def WRITE():
    """PD: print the block M[RA .. RA+9] as one line."""
    global LLC
    if LLC >= TLL:                                       # this line would be one too many
        TERMINATE(2)
        return
    LLC = LLC + 1
    outfile.write("".join(M[RA:RA + 10]) + "\n")


def TERMINATE(*errors):
    """
    End the job. Overloaded like in the lecture:
        TERMINATE(3)      single error
        TERMINATE(3, 4)   two errors at once (EM = 3 + 4 = 7)
    Writes the 6-line report and two blank lines.
    """
    global EM, job_done
    EM = sum(errors)
    try:
        job_id = str(int(PCB[0]))                        # '0202' -> '202'
    except (TypeError, ValueError):
        job_id = PCB[0] if PCB else "?"
    outfile.write("%-9s:  %s\n" % ("JOB ID", job_id))
    outfile.write(MESSAGES[EM] + "\n")
    outfile.write("%-9s:  %d\n" % ("IC", IC))
    outfile.write("%-9s:  %s\n" % ("IR", IR.rstrip()))
    outfile.write("%-9s:  %d\n" % ("TTC", TTC))
    outfile.write("%-9s:  %d\n" % ("LLC", LLC))
    outfile.write("\n\n")
    if dump:
        dump_job()
    job_done = True


def dump_job():
    """--dump: show the page table of the job that just finished."""
    rows = []
    for page in range(10):
        frame = pt_get(page)
        if frame is not None:
            rows.append("page %d -> frame %02d (real %03d-%03d)" % (page, frame, frame * 10, frame * 10 + 9))
    sys.stderr.write("--- job %s: EM=%d  PTR=%d (frame %d)\n    %s\n"
                     % (PCB[0], EM, PTR, PTR // 10, "\n    ".join(rows) or "no pages"))


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    global infile, outfile, trace, dump
    parser = argparse.ArgumentParser(description="MOS Phase 2 simulator")
    parser.add_argument("-i", "--input", default="input_phase2.txt")
    parser.add_argument("-o", "--output", default="output_phase2.txt")
    parser.add_argument("--seed", type=int, default=None, help="seed for the random frame generator")
    parser.add_argument("--trace", action="store_true", help="print every instruction to stderr")
    parser.add_argument("--dump", action="store_true", help="print the page table of each job to stderr")
    args = parser.parse_args()
    trace, dump = args.trace, args.dump
    if args.seed is not None:
        random.seed(args.seed)
    infile = open(args.input, "r")
    outfile = open(args.output, "w")
    INIT()
    LOAD()
    infile.close()
    outfile.close()


if __name__ == "__main__":
    main()

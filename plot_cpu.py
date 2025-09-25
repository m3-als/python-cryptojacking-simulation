#!/usr/bin/env python3
# plot_cpu.py
# يرسم استهلاك CPU عبر الزمن من ملف top_log.txt
# يدعم رسم: (A) Cpu overall (Cpu(s) line) (B) CPU% لعملية باسم محدد

import re
import argparse
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def parse_top_overall(lines):
    # يبحث عن سطور Cpu(s) أو %Cpu(s)
    cpu_vals = []
    times = []
    t0 = datetime.utcnow()
    for idx, line in enumerate(lines):
        m = re.search(r'Cpu\(s\):\s*([0-9.]+)\s*us', line) or re.search(r'%Cpu\(s\):\s*([0-9.]+)\s*us', line)
        if m:
            val = float(m.group(1))
            cpu_vals.append(val)
            times.append(t0 + timedelta(seconds=idx))  # approximate spacing (index-based)
    return times, cpu_vals

def parse_top_by_process(lines, proc_name):
    # يحاول التقاط خطوط العمليات: شكل السطر في top: USER PID ... %CPU ... COMMAND
    cpu_vals = []
    times = []
    tindex = 0
    # split into "frames" by occurrences of "top -"
    frames = []
    current = []
    for line in lines:
        if line.strip().startswith("top -") and current:
            frames.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        frames.append(current)
    for idx, frame in enumerate(frames):
        # find process line matching proc_name (by substring in the line)
        found = False
        for line in frame:
            if proc_name in line and '%' in line:
                # try to extract %CPU (column with decimal)
                parts = line.split()
                # find the first part that looks like a percentage number
                for p in parts:
                    if re.match(r'^[0-9]+\.[0-9]+$', p) or re.match(r'^[0-9]+$', p):
                        # crude guess: CPU usually around column after PID, but we'll try to locate by header
                        pass
                # better: regex to find float before COMMAND at end
                m = re.search(r'\s([0-9]+\.[0-9]+)\s+[0-9]+\s+.*$', line)
                if not m:
                    # try simpler: find first float in line
                    m2 = re.search(r'([0-9]+\.[0-9]+)', line)
                    if m2:
                        val = float(m2.group(1))
                    else:
                        continue
                else:
                    val = float(m.group(1))
                cpu_vals.append(val)
                times.append(idx)  # index as time proxy
                found = True
                break
        if not found:
            # append zero to keep timeline consistent
            cpu_vals.append(0.0)
            times.append(idx)
    # convert times to datetime
    t0 = datetime.utcnow()
    times = [t0 + timedelta(seconds=i) for i in times]
    return times, cpu_vals

def main():
    parser = argparse.ArgumentParser(description="Plot CPU from top_log.txt")
    parser.add_argument('--toplog', default='top_log.txt', help='Top log file (from top -b -d 1)')
    parser.add_argument('--process', default=None, help='Optional: process name to track (substring match)')
    parser.add_argument('--out', default='cpu_usage.png', help='Output PNG filename')
    args = parser.parse_args()

    with open(args.toplog, 'r', errors='ignore') as f:
        lines = f.readlines()

    if args.process:
        times, vals = parse_top_by_process(lines, args.process)
        label = f"Process '{args.process}' %CPU (approx)"
    else:
        times, vals = parse_top_overall(lines)
        label = "Overall user CPU % (us) from top header"

    if not vals:
        print("لم أعثر على بيانات قابلة للرسم في top_log.txt. تأكد أنك سجلت top باستخدام: top -b -d 1 -n <samples> > top_log.txt")
        return

    plt.figure(figsize=(10,4))
    plt.plot(times, vals)
    plt.xlabel('Time')
    plt.ylabel('% CPU')
    plt.title('CPU Usage Over Time')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(args.out)
    print(f"Saved plot to {args.out}")

if __name__ == "__main__":
    main()

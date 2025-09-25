
import argparse
import multiprocessing as mp
import hashlib
import os
import socket
import json
import time
import random
import datetime
import signal
import sys
try:
    import psutil
except Exception:
    psutil = None

stop_flag = mp.Event()

def send_c2(payload, c2_port):
    try:
        with socket.create_connection(('127.0.0.1', c2_port), timeout=1) as s:
            s.sendall(json.dumps(payload).encode('utf-8'))
            # try to read ack non-blocking briefly
            s.settimeout(0.5)
            try:
                data = s.recv(1024)
                if data:
                    return data.decode('utf-8', errors='ignore')
            except Exception:
                pass
    except Exception:
        pass
    return None

def worker_loop(worker_id, args):
    pid = os.getpid()
    counter = 0
    last_hb = time.time()
    start = time.time()
    logfile = f"worker_{worker_id}.log"
    with open(logfile, "a") as lf:
        lf.write(f"# worker {worker_id} start pid={pid}\n")
    # determine pattern params
    if args.mode == "steady":
        burst_len = None
        idle_len = None
    else:
        # bursty: runtime is split into active bursts and idle gaps
        burst_len = args.burst_len
        idle_len = args.idle_len

    while not stop_flag.is_set():
        # polite mode: check system cpu load (if psutil available)
        if args.polite and psutil:
            try:
                load = psutil.cpu_percent(interval=0.1)
                if load > args.polite_threshold:
                    # throttle: sleep a bit and skip heavy hashing
                    time.sleep(0.2)
                    continue
            except Exception:
                pass

        # determine if in active phase for burst mode
        if args.mode == "bursty":
            # simple burst/idle toggling using time
            phase = int((time.time() - start) / (burst_len + idle_len))  # not perfect but fine for demo
            in_burst = ((time.time() - start) % (burst_len + idle_len)) < burst_len
            if not in_burst:
                # idle: sleep small randomized
                time.sleep(random.uniform(0.05, 0.2))
                continue

        # produce work: variable amount of hashing per iteration to simulate different intensities
        work_units = random.randint(max(1, args.min_units), args.max_units)
        for _ in range(work_units):
            data = f"{worker_id}-{counter}-{random.random()}".encode('utf-8')
            hashlib.sha256(data).hexdigest()
            counter += 1
            # optional micro-yield to change scheduling
            if args.yield_every and (counter % args.yield_every == 0):
                time.sleep(0)  # yield to scheduler

        # periodic heartbeat with optional metrics
        if time.time() - last_hb >= args.heartbeat:
            last_hb = time.time()
            hb = {
                'type': 'heartbeat',
                'worker': worker_id,
                'pid': pid,
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                'counter': counter,
                'mode': args.mode
            }
            # include psutil metrics if available and allowed
            if psutil and args.send_metrics:
                try:
                    p = psutil.Process(pid)
                    hb['cpu_percent_proc'] = p.cpu_percent(interval=None)
                    hb['mem_rss_mb'] = int(p.memory_info().rss / (1024*1024))
                    hb['system_cpu_percent'] = psutil.cpu_percent(interval=None)
                except Exception:
                    pass

            # send to local C2
            ack = send_c2(hb, args.c2_port)
            with open(logfile, "a") as lf:
                lf.write(json.dumps({'time': datetime.datetime.utcnow().isoformat() + 'Z', 'hb': hb, 'ack': ack}) + "\n")

        # jitter between iterations to avoid perfect loops
        time.sleep(random.uniform(0, args.jitter))

def sigterm_handler(signum, frame):
    stop_flag.set()

def main():
    parser = argparse.ArgumentParser(description="Enhanced cryptojacker simulation (safe, local-only)")
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--duration', type=int, default=60)
    parser.add_argument('--c2-port', type=int, default=4444)
    parser.add_argument('--heartbeat', type=int, default=5)
    parser.add_argument('--mode', choices=['steady','bursty'], default='steady')
    parser.add_argument('--burst-len', type=int, default=10, dest='burst_len', help='active seconds in burst mode')
    parser.add_argument('--idle-len', type=int, default=10, dest='idle_len', help='idle seconds in burst mode')
    parser.add_argument('--min-units', type=int, default=1, dest='min_units', help='min hash units per loop')
    parser.add_argument('--max-units', type=int, default=5, dest='max_units', help='max hash units per loop')
    parser.add_argument('--jitter', type=float, default=0.02, help='max jitter (s) between iterations')
    parser.add_argument('--yield-every', type=int, default=0, help='call time.sleep(0) every N hashes to yield scheduler (0=disabled)')
    parser.add_argument('--polite', action='store_true', help='enable polite mode (throttle when system busy) - requires psutil')
    parser.add_argument('--polite-threshold', type=float, default=70.0, help='system CPU% threshold to throttle in polite mode')
    parser.add_argument('--send-metrics', action='store_true', help='include psutil-based metrics in heartbeat (requires psutil)')
    args = parser.parse_args()

    if args.send_metrics or args.polite:
        if not psutil:
            print("Warning: psutil not available. Install psutil in venv for metrics/polite mode.")
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)

    procs = []
    for i in range(args.workers):
        p = mp.Process(target=worker_loop, args=(i, args))
        p.start()
        procs.append(p)

    start = time.time()
    try:
        while time.time() - start < args.duration and not stop_flag.is_set():
            time.sleep(0.5)
    finally:
        stop_flag.set()
        for p in procs:
            p.join(timeout=5)

if __name__ == "__main__":
    main()

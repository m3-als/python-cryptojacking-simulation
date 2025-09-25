#!/usr/bin/env python3
# c2_server_enh.py
# Enhanced local C2 for simulation: logs JSON, prints simple stats, safe (127.0.0.1 only)

import socketserver
import json
import datetime
import threading
import os
from collections import Counter

LOGFILE = "c2_received_enh.log"
HOST, PORT = "127.0.0.1", 4444

stats_lock = threading.Lock()
stats = {
    'total_msgs': 0,
    'by_worker': Counter(),
    'last_seen': {}
}

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(8192).strip()
        now = datetime.datetime.utcnow().isoformat() + "Z"
        try:
            msg = json.loads(data.decode('utf-8'))
        except Exception:
            msg = {'raw': data.decode('utf-8', errors='ignore')}

        entry = {'time': now, 'addr': self.client_address[0], 'msg': msg}
        # print human-friendly
        print(f"[{now}] from {self.client_address[0]} -> {msg}")

        # append to log
        with open(LOGFILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # update in-memory stats (thread-safe)
        with stats_lock:
            stats['total_msgs'] += 1
            wt = msg.get('worker') if isinstance(msg, dict) else None
            if wt is not None:
                stats['by_worker'][str(wt)] += 1
                stats['last_seen'][str(wt)] = now

        # optional: send tiny ack (safe, only local)
        try:
            ack = {'status': 'ok', 'recv_time': now}
            self.request.sendall(json.dumps(ack).encode('utf-8'))
        except Exception:
            pass

def print_stats_loop():
    while True:
        with stats_lock:
            s = stats.copy()
        # simple one-line summary every 10s
        print(f"STATS: total_msgs={s['total_msgs']} workers={len(s['by_worker'])} per_worker={dict(s['by_worker'])}")
        threading.Event().wait(10)

if __name__ == "__main__":
    # ensure logfile exists
    open(LOGFILE, "a").close()
    # start stats printer thread
    t = threading.Thread(target=print_stats_loop, daemon=True)
    t.start()
    with socketserver.ThreadingTCPServer((HOST, PORT), Handler) as server:
        print(f"C2 (enh) listening on {HOST}:{PORT} (127.0.0.1 only). Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down C2 server.")
            server.shutdown()
            server.server_close()

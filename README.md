# python-cryptojacking-simulation
A Python-based cryptojacker simulation that generates CPU load and sends heartbeats to a local C2 server — fully safe for lab use.

Cryptojacker Lab - Package contents and quickstart
-------------------------------------------------

Files included:
- c2_server.py             : basic local C2 server (logs to c2_received.log)
- cryptojack_sim.py        : simple cryptojacker simulation (cpu + heartbeat)
- c2_server_enh.py         : enhanced C2 server (logs, stats, ACKs) - listens on 127.0.0.1:4444
- cryptojack_sim_enh.py    : enhanced simulation (modes, jitter, psutil metrics, polite mode)
- gather_evidence.py       : collects logs/pcap/screenshots into evidence_bundle.tar.gz
- plot_cpu.py              : plots CPU usage from top_log.txt
- this README.txt

Quickstart (recommended: use a python virtualenv inside the VM):
1) create and activate venv:
   python3 -m venv venv
   source venv/bin/activate

2) install dependencies (inside venv):
   pip install --upgrade pip
   pip install psutil matplotlib

   Or, install system packages:
   sudo apt update
   sudo apt install -y python3-psutil python3-matplotlib

3) make scripts executable:
   chmod +x *.py

4) start enhanced C2 server in terminal A:
   python3 c2_server_enh.py

5) in terminal B start top logging:
   top -b -d 1 -n 120 > top_log.txt &

6) in terminal C run simulation (example):
   python3 cryptojack_sim_enh.py --workers 3 --duration 120 --mode bursty --burst-len 8 --idle-len 12 --heartbeat 4 --send-metrics --polite --polite-threshold 80

7) monitor logs and outputs:
   tail -f c2_received_enh.log
   tail -f worker_0.log worker_1.log
   htop

8) after run, gather evidence:
   python3 gather_evidence.py --out evidence_bundle.tar.gz
   python3 plot_cpu.py --toplog top_log.txt --process python3 --out cpu_python3.png
   python3 plot_cpu.py --toplog top_log.txt --out cpu_overall.png

Notes:
- ALWAYS run inside an isolated VM and do NOT expose to external networks.
- Use low worker counts first to avoid overloading the VM.

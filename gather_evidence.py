#!/usr/bin/env python3
# gather_evidence.py
# يجمع الأدلة من مجلد العمل ويضعها في archive evidence_bundle.tar.gz

import os
import tarfile
import argparse
import shutil
from datetime import datetime
import subprocess

def collect_snapshot(outdir):
    os.makedirs(outdir, exist_ok=True)
    # snapshots of ps and ss
    with open(os.path.join(outdir, "ps_aux_snapshot.txt"), "w") as f:
        subprocess.run(["ps", "aux"], stdout=f, stderr=subprocess.DEVNULL)
    with open(os.path.join(outdir, "ss_tulpn_snapshot.txt"), "w") as f:
        subprocess.run(["ss", "-tulpn"], stdout=f, stderr=subprocess.DEVNULL)

def gather_files(target_dir, patterns):
    files = []
    for root, _, fnames in os.walk("."):
        for name in fnames:
            path = os.path.join(root, name)
            for p in patterns:
                if name.endswith(p) or name == p:
                    files.append(path)
    return files

def main():
    parser = argparse.ArgumentParser(description="Gather evidence into a tar.gz")
    parser.add_argument('--out', '-o', default='evidence_bundle.tar.gz', help='Output archive name')
    parser.add_argument('--workdir', '-w', default='.', help='Working directory to search (default .)')
    args = parser.parse_args()

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    tmpdir = f".evidence_tmp_{timestamp}"
    os.makedirs(tmpdir, exist_ok=True)

    # collect snapshots
    collect_snapshot(tmpdir)

    # file patterns to include (extendable)
    patterns = [
        'c2_received.log', 'top_log.txt', 'lo_capture.pcap',
        '.pcap', '.png', '.jpg', '.jpeg', '.txt', 'strace_output.txt',
        'strace_summary.txt'
    ]

    # gather matching files
    os.chdir(args.workdir)
    files = gather_files(args.workdir, patterns)
    for f in files:
        # avoid copying our temp dir if present
        if tmpdir in f:
            continue
        try:
            dest = os.path.join(tmpdir, os.path.relpath(f, start=args.workdir))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(f, dest)
        except Exception as e:
            print("Warning copying", f, e)

    # create tar.gz
    with tarfile.open(args.out, "w:gz") as tar:
        tar.add(tmpdir, arcname=os.path.basename(tmpdir))
    print(f"Created archive: {args.out}")

    # cleanup
    try:
        shutil.rmtree(tmpdir)
    except Exception:
        pass

if __name__ == "__main__":
    main()

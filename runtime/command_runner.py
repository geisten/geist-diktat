#!/usr/bin/env python3
"""Own one command group and stop its descendants on INT/TERM (desktop wrapper)."""
import os
import signal
import subprocess
import sys
import time

def main():
    command=sys.argv[1:]
    if command[:1]==['--']:command=command[1:]
    if not command:print('command required',file=sys.stderr);return 2
    cancelled=[]
    def stop(sig,_frame):cancelled.append(sig)
    for s in (signal.SIGTERM,signal.SIGINT):signal.signal(s,stop)
    p=subprocess.Popen(command,start_new_session=True)
    try:
        while p.poll() is None and not cancelled:time.sleep(.025)
        if not cancelled:return p.returncode if p.returncode>=0 else 1
        os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=2)
        except subprocess.TimeoutExpired:pass
        return 128+cancelled[0]
    finally:
        try:os.killpg(p.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        time.sleep(.1)
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        p.wait()
if __name__=='__main__':
    try:raise SystemExit(main())
    except OSError as e:print('geist-diktat: command failed: '+str(e),file=sys.stderr);raise SystemExit(1)

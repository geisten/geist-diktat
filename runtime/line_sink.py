#!/usr/bin/env python3
"""Run a command once per UTF-8 transcript line, appending text as ONE argument.

Example (explicitly types into the focused Wayland application):
  geist-diktat run | python3 line_sink.py -- wtype --
No shell expansion is performed. Ctrl-C stops; first failed insertion aborts.
"""
import argparse
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args();cmd=a.command[1:] if a.command[:1]==['--'] else a.command
    if not cmd:p.error('insertion command required')
    try:
        while True:
            line=sys.stdin.buffer.readline(65537)
            if not line:return 0
            if len(line)>65536:raise ValueError('transcript exceeds 64 KiB')
            text=line.decode('utf-8').rstrip('\r\n')
            if text:
                r=subprocess.run(cmd+[text],stdin=subprocess.DEVNULL,timeout=10)
                if r.returncode:return r.returncode if r.returncode>0 else 1
    except (OSError,ValueError,subprocess.TimeoutExpired) as e:
        print('geist-diktat: insertion failed: '+str(e),file=sys.stderr);return 1
    except KeyboardInterrupt:return 130

if __name__=='__main__':raise SystemExit(main())

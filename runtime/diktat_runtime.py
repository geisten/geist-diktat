#!/usr/bin/env python3
"""Supervise capture + recognizer with bounded memory and explicit overload.

Only caller-owned children are signalled. Audio is never written to disk.
Exit 75 = input outran recognition; 130/143 = user cancellation.
"""
import argparse
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time


def supervise(capture, decoder, buffer_seconds=6):
    if not 0.1 <= buffer_seconds <= 60:
        raise ValueError('buffer seconds must be between 0.1 and 60')
    chunks=queue.Queue(maxsize=max(1,int(buffer_seconds*50)))
    stopped=threading.Event(); eof=threading.Event(); fault=[]
    children=[]
    def fail(code,message):
        if not stopped.is_set():
            fault.append(code);print('geist-diktat: '+message,file=sys.stderr,flush=True)
            stopped.set()
    def cancel(signum,_frame):fail(128+signum,'stopped')
    previous={s:signal.signal(s,cancel) for s in (signal.SIGTERM,signal.SIGINT)}
    try:
        rec=subprocess.Popen(decoder,stdin=subprocess.PIPE,start_new_session=True)
        children.append(rec)
        mic=subprocess.Popen(capture,stdout=subprocess.PIPE,start_new_session=True)
        children.append(mic)
        def read_audio():
            try:
                while not stopped.is_set():
                    data=mic.stdout.read(640)
                    if not data:break
                    try:chunks.put_nowait(data)
                    except queue.Full:
                        fail(75,'overload: recognition cannot keep up; audio stopped. Choose a faster engine or shorter dictation.')
                        break
            except OSError as error:fail(74,'capture read failed: '+str(error))
            finally:eof.set()
        def write_audio():
            try:
                while not stopped.is_set():
                    try:data=chunks.get(timeout=.05)
                    except queue.Empty:
                        if eof.is_set():break
                        continue
                    rec.stdin.write(data);rec.stdin.flush()
            except (BrokenPipeError,OSError):
                # The main thread reports the recognizer's actual exit code.
                pass
            finally:
                try:rec.stdin.close()
                except (OSError,BrokenPipeError):pass
        readers=[threading.Thread(target=f,daemon=True) for f in (read_audio,write_audio)]
        for t in readers:t.start()
        print('geist-diktat: capture process started; Ctrl-C stops all audio',file=sys.stderr,flush=True)
        while not stopped.wait(.025):
            capture_status=mic.poll();decode_status=rec.poll()
            if capture_status not in (None,0):
                fail(capture_status if capture_status>0 else 1,'capture failed ('+str(capture_status)+')');break
            if decode_status is not None:
                if decode_status:fail(decode_status if decode_status>0 else 1,'recognizer failed ('+str(decode_status)+')')
                else:
                    if capture_status is None:
                        # EOF can arrive just before the recorder's exit status.
                        # Bound that race; never turn a late recorder failure into success.
                        try:capture_status=mic.wait(timeout=.25)
                        except subprocess.TimeoutExpired:capture_status=None
                    if capture_status is None:fail(70,'recognizer ended while capture was active')
                    elif capture_status:fail(capture_status if capture_status>0 else 1,'capture failed ('+str(capture_status)+')')
                break
        return fault[0] if fault else 0
    except (OSError,ValueError) as error:
        print('geist-diktat: '+str(error),file=sys.stderr);return 1
    finally:
        stopped.set()
        for p in children:
            # Kill the group even if its leader already exited: a capture
            # command may have spawned descendants which still hold the pipe.
            try:os.killpg(p.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        # Allow both leaders and descendants a fixed, bounded TERM grace.
        # Avoid signal-0 probes: some macOS process policies reject those
        # even when terminating our own group is permitted.
        deadline=time.monotonic()+.5
        for p in children:
            try:p.wait(timeout=max(0,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:pass
        time.sleep(max(0,deadline-time.monotonic()))
        for p in children:
            # A reaped group leader does not imply its descendants exited.
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            p.wait()
        for s,handler in previous.items():signal.signal(s,handler)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',required=True)
    parser.add_argument('--buffer-seconds',type=float,default=6)
    parser.add_argument('decoder',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.decoder[1:] if args.decoder[:1]==['--'] else args.decoder
    if not command:parser.error('decoder command required')
    if not 0.1 <= args.buffer_seconds <= 60:parser.error('buffer seconds must be between 0.1 and 60')
    return supervise(['sh','-c',args.capture],command,args.buffer_seconds)

if __name__=='__main__':raise SystemExit(main())

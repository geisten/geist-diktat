#!/usr/bin/env python3
"""Supervise capture + recognizer with bounded memory and explicit overload.

Only caller-owned children are signalled. Audio is never written to disk.
Exit 75 = input outran recognition; 130/143 = user cancellation.
"""
import argparse
import os
from pathlib import Path
import queue
import select
import signal
import subprocess
import sys
import threading
import time
from trace_metrics import emit
from pipe_limits import pipe_options


def supervise(capture, decoder, buffer_seconds=6, ready_timeout=None):
    if not 0.1 <= buffer_seconds <= 60:
        raise ValueError('buffer seconds must be between 0.1 and 60')
    if ready_timeout is not None and not 0<ready_timeout<=300:raise ValueError('invalid ready timeout')
    ready_fds=[]
    chunks=queue.Queue(maxsize=max(1,int(buffer_seconds*50)))
    stopped=threading.Event(); eof=threading.Event(); fault=[]
    children=[]
    metrics=dict(received_bytes=0,delivered_bytes=0,peak_queue_bytes=0,
                 max_write_block_ns=0,max_queue_age_ns=0,inflight_write_ns=0)
    metric_lock=threading.Lock()
    def snapshot():
        now=time.monotonic_ns()
        with metric_lock:
            result=dict(metrics);inflight=result.pop('inflight_write_ns')
            if inflight:result['max_write_block_ns']=max(result['max_write_block_ns'],now-inflight)
            with chunks.mutex:
                result['queued_bytes']=sum(len(data) for data,_ in chunks.queue)
                result['oldest_queued_age_ns']=max(0,time.monotonic_ns()-chunks.queue[0][1]) if chunks.queue else 0
        return result
    def fail(code,message):
        if not stopped.is_set():
            fault.append(code);print('geist-diktat: '+message,file=sys.stderr,flush=True)
            stopped.set()
    def cancel(signum,_frame):fail(128+signum,'stopped')
    previous={s:signal.signal(s,cancel) for s in (signal.SIGTERM,signal.SIGINT)}
    try:
        options=pipe_options()
        if ready_timeout is not None:
            read_fd,write_fd=os.pipe();ready_fds.extend((read_fd,write_fd))
            options.update(pass_fds=(write_fd,),env=dict(os.environ,GEIST_DIKTAT_READY_FD=str(write_fd)))
        rec=subprocess.Popen(decoder,stdin=subprocess.PIPE,start_new_session=True,**options)
        children.append(rec)
        if ready_timeout is not None:
            os.close(write_fd);ready_fds.remove(write_fd)
            deadline=time.monotonic()+ready_timeout
            while not stopped.is_set():
                if select.select([read_fd],[],[],.025)[0]:
                    if os.read(read_fd,1)==b'1':break
                    try:status=rec.wait(timeout=.2)
                    except subprocess.TimeoutExpired:status=70
                    fail(status if status>0 else 70,'recognizer failed before readiness');break
                if time.monotonic()>=deadline:fail(70,'recognizer readiness timed out');break
            os.close(read_fd);ready_fds.remove(read_fd)
            if stopped.is_set():return fault[0]
            emit('runtime','recognizer_ready')
        mic=subprocess.Popen(capture,stdout=subprocess.PIPE,start_new_session=True,**pipe_options())
        children.append(mic)
        emit("runtime","capture_started")
        def read_audio():
            try:
                while not stopped.is_set():
                    data=mic.stdout.read(640)
                    if not data:break
                    arrived=time.monotonic_ns()
                    with metric_lock:metrics['received_bytes']+=len(data)
                    try:
                        chunks.put_nowait((data,arrived))
                        with metric_lock:
                            metrics['peak_queue_bytes']=max(metrics['peak_queue_bytes'],chunks.qsize()*640)
                    except queue.Full:
                        fail(75,'overload: recognition cannot keep up; audio stopped. Choose a faster engine or shorter dictation.')
                        break
            except OSError as error:fail(74,'capture read failed: '+str(error))
            finally:eof.set()
        def write_audio():
            try:
                while not stopped.is_set():
                    try:data,arrived=chunks.get(timeout=.05)
                    except queue.Empty:
                        if eof.is_set():break
                        continue
                    before=time.monotonic_ns()
                    with metric_lock:
                        metrics['max_queue_age_ns']=max(metrics['max_queue_age_ns'],before-arrived)
                        metrics['inflight_write_ns']=before
                    rec.stdin.write(data);rec.stdin.flush()
                    with metric_lock:
                        metrics['delivered_bytes']+=len(data)
                        metrics['max_write_block_ns']=max(metrics['max_write_block_ns'],time.monotonic_ns()-before)
                        metrics['inflight_write_ns']=0
            except (BrokenPipeError,OSError):
                # The main thread reports the recognizer's actual exit code.
                pass
            finally:
                with metric_lock:
                    if metrics['inflight_write_ns']:
                        metrics['max_write_block_ns']=max(metrics['max_write_block_ns'],time.monotonic_ns()-metrics['inflight_write_ns'])
                        metrics['inflight_write_ns']=0
                try:rec.stdin.close()
                except (OSError,BrokenPipeError):pass
        readers=[threading.Thread(target=f,daemon=True) for f in (read_audio,write_audio)]
        for t in readers:t.start()
        print('geist-diktat: capture process started; Ctrl-C stops all audio',file=sys.stderr,flush=True)
        next_progress=time.monotonic()+5
        while not stopped.wait(.025):
            if time.monotonic()>=next_progress:
                emit('runtime','buffer_state',**snapshot())
                next_progress=time.monotonic()+5
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
        if not fault:fault.append(1)
        print('geist-diktat: '+str(error),file=sys.stderr);return 1
    finally:
        stopped.set()
        for fd in ready_fds:os.close(fd)
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
        for thread in locals().get('readers',[]):thread.join(timeout=.2)
        try:
            summary=snapshot()
            emit("runtime","input_summary",**summary,
                 unconfirmed_bytes=summary['received_bytes']-summary['delivered_bytes'],
                 failed=bool(fault))
        except (OSError,ValueError) as error:
            print('geist-diktat: trace failed: '+str(error),file=sys.stderr)
        for s,handler in previous.items():signal.signal(s,handler)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',required=True)
    parser.add_argument('--buffer-seconds',type=float,default=6)
    parser.add_argument('--ready-timeout',type=float)
    parser.add_argument('decoder',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.decoder[1:] if args.decoder[:1]==['--'] else args.decoder
    if not command:parser.error('decoder command required')
    if not 0.1 <= args.buffer_seconds <= 60:parser.error('buffer seconds must be between 0.1 and 60')
    if args.ready_timeout is not None and not 0<args.ready_timeout<=300:parser.error('invalid ready timeout')
    return supervise(['sh','-c',args.capture],command,args.buffer_seconds,args.ready_timeout)

if __name__=='__main__':raise SystemExit(main())

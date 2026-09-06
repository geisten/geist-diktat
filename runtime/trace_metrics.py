"""Opt-in numeric diagnostic events. No transcript/audio; no network access."""
import json
import os
import stat
import time


def emit(component,event,**metrics):
    path=os.environ.get('GEIST_DIKTAT_TRACE')
    if not path:return
    if any(type(v) not in (int,float,bool) for v in metrics.values()):
        raise ValueError('trace metrics must be numeric')
    record=dict(schema=1,component=component,event=event,pid=os.getpid(),
                monotonic_ns=time.monotonic_ns(),**metrics)
    data=(json.dumps(record,allow_nan=False,separators=(',',':'))+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NONBLOCK,0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):raise ValueError('trace requires regular file')
        if os.write(fd,data)!=len(data):raise OSError('incomplete trace write')
    finally:os.close(fd)

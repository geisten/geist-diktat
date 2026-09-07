"""Bound Linux subprocess pipes before either child can write audio.

Linux rounds the request to its page size (16 KiB on the tested Pi5).
macOS does not support F_SETPIPE_SZ; its native pipe policy remains in effect.
"""
import fcntl


def pipe_options():
    return {'pipesize':8192} if hasattr(fcntl,'F_SETPIPE_SZ') else {}

import os
import signal
from ptools import OperationException

class LinuxOperationException(OperationException):
    pass

def list_pids():
    pids = []
    for pid in os.listdir('/proc/'):
        try:
            pids.append(long(pid))
        except ValueError:
            pass
    return pids

def get_pid_info(pid):
    try:
        cmd = open('/proc/%d/cmdline' % (pid,)).read()
        env = dict(line.split('=',1) for line in open('/proc/%d/environ' % (pid,)).read().split('\0') if '=' in line)
    except IOError as ioe:
        raise LinuxOperationException(str(ioe))
    return (cmd, env)

def kill_pid(pid):
    os.kill(pid, signal.SIGTERM)

__all__ = ['list_pids', 'get_pid_info', 'kill_pid', 'OperationException']

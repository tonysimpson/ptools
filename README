
ptools
======

Cross Platform Process Infomation (cmdline, environ) and Management

ptools has windows and linux implementations of several functions:

* list_pids - list all processes
* get_pid_info - get the command line used to launch the process and
the environment as a map
* kill_pid - forcefully kill the process

get_pid_info may fail with ptools.OperationException especially if you
do not have the required access to see the processes command line or
environment

To get the functions for your current os do:

    from ptools.current import *

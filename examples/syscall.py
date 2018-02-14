#!/usr/bin/env python

"""
A contrived example of shredder usage. It works but shredder runs the worker
function in a process it creates itself, so we're creating num_cpus processes +
a process for each interface. The overhead of the queue and the message passing
probably won't be worth for short-lived programs.

You can compare this program to syscall-compare.py which does the same thing
but from one process. It runs slightly faster on my 8 core machine.


Run this program:
    PYTHONPATH=. python example/syscall.py

"""

from glob import glob
from subprocess import Popen, PIPE
from shredder import Shredder

ifconfig_by_iface = {}

def work_generator():
    for interface in glob('/sys/class/net/*'):
        name = interface.split('/')[-1]
        yield name

def worker(interface):
    process = Popen(["ifconfig", interface], stdout=PIPE)
    output, _ = process.communicate()
    process.wait()
    shredder.logger.debug("sending output of ifconfig %s", interface)
    return {interface : output}

def aggregator(interface_dict):
    shredder.logger.info("Handling output for interface %s", interface_dict.keys()[0])

    for k,v in interface_dict.iteritems():
        ifconfig_by_iface[k] = v


# try log_level='debug' for overwhelming output
shredder = Shredder(work_generator, worker, aggregator, log_level='info')
shredder.start()

print "Found %d network interfaces: %s " % (len(ifconfig_by_iface.keys()),
                                            ifconfig_by_iface.keys())
print ifconfig_by_iface

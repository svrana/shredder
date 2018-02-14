#!/usr/bin/env python

"""
A contrived example of shredder usage. It works but shredder runs the worker
function in a process it creates itself, so we're creating 2 x num_cpus
processes here.

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

print ifconfig_by_iface
